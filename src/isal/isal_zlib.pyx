# Copyright (c) 2020 Leiden University Medical Center
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# cython: language_level=3

import warnings
import zlib

from .crc cimport crc32_gzip_refl
from .igzip_lib cimport *
from libc.stdint cimport UINT64_MAX, UINT32_MAX, uint32_t
from cpython cimport PyObject_GetBuffer,  Py_buffer, PyBUF_SIMPLE, PyBUF_WRITABLE
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
from cython cimport view

ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = 2
Z_BEST_SPEED = ISAL_BEST_SPEED
Z_BEST_COMPRESSION = ISAL_BEST_COMPRESSION
Z_DEFAULT_COMPRESSION = ISAL_DEFAULT_COMPRESSION

DEF_BUF_SIZE = zlib.DEF_BUF_SIZE
DEF_MEM_LEVEL = zlib.DEF_MEM_LEVEL
cdef int DEF_MEM_LEVEL_I = DEF_MEM_LEVEL  # Can not be manipulated by user.
MAX_WBITS = ISAL_DEF_MAX_HIST_BITS
ISAL_DEFAULT_HIST_BITS=0

# Compression methods
DEFLATED = zlib.DEFLATED

# Strategies
Z_DEFAULT_STRATEGY=zlib.Z_DEFAULT_STRATEGY
Z_RLE=zlib.Z_RLE 
Z_HUFFMAN_ONLY=zlib.Z_HUFFMAN_ONLY
Z_FILTERED=zlib.Z_FILTERED
Z_FIXED=zlib.Z_FIXED

# Flush methods
ISAL_NO_FLUSH=NO_FLUSH 
ISAL_SYNC_FLUSH=SYNC_FLUSH 
ISAL_FULL_FLUSH=FULL_FLUSH

Z_NO_FLUSH=ISAL_NO_FLUSH
Z_SYNC_FLUSH=ISAL_SYNC_FLUSH
Z_FULL_FLUSH=ISAL_FULL_FLUSH

class IsalError(Exception):
    pass


if ISAL_DEF_MAX_HIST_BITS > zlib.MAX_WBITS:
    raise  IsalError("ISAL max window size no longer compatible with zlib. "
                     "Please contact the developers.")


cpdef adler32(data, unsigned long value = 1):
    cdef Py_ssize_t length = len(data)
    if length > UINT64_MAX:
        raise ValueError("Data too big for adler32")
    return isal_adler32(value, data, length)

cpdef crc32(data, unsigned long value = 0):
    cdef Py_ssize_t length = len(data)
    if length > UINT64_MAX:
        raise ValueError("Data too big for crc32")
    return crc32_gzip_refl(value, data, length)

cdef Py_ssize_t Py_ssize_t_min(Py_ssize_t a, Py_ssize_t b):
    if a <= b:
        return a
    else:
        return b

cpdef compress(data, int level=ISAL_DEFAULT_COMPRESSION):
    if level == zlib.Z_DEFAULT_COMPRESSION:
        level = ISAL_DEFAULT_COMPRESSION

    # Initialise stream
    cdef isal_zstream stream
    level_buf_size = zlib_mem_level_to_isal(level, DEF_MEM_LEVEL_I)
    cdef unsigned char* level_buf = <unsigned char*> PyMem_Malloc(level_buf_size * sizeof(char))
    isal_deflate_init(&stream)
    stream.level = level
    stream.level_buf = level_buf
    stream.level_buf_size = level_buf_size
    stream.gzip_flag = IGZIP_ZLIB

    # Initialise output buffer
    cdef unsigned long obuflen = DEF_BUF_SIZE
    cdef unsigned char * obuf = <unsigned char*> PyMem_Malloc(obuflen * sizeof(char))
    out = []
    
    # initialise input
    cdef Py_ssize_t max_input_buffer = UINT32_MAX
    cdef Py_ssize_t total_length = len(data)
    cdef Py_ssize_t remains = total_length
    cdef Py_ssize_t ibuflen = total_length
    cdef Py_ssize_t position = 0
    cdef bytes ibuf

    # initialise helper variables
    cdef int err

    # Implementation imitated from CPython's zlibmodule.c
    try:
        while stream.internal_state.state != ZSTATE_END or ibuflen !=0:
            # This loop runs n times (at least twice). n-1 times to fill the input
            # buffer with data. The nth time the input is empty. In that case
            # stream.flush is set to FULL_FLUSH and the end_of_stream is activated.
            ibuflen = Py_ssize_t_min(remains, max_input_buffer)
            ibuf = data[position: position + ibuflen]
            position += ibuflen
            stream.next_in = ibuf
            remains -= ibuflen
            stream.avail_in = ibuflen
            if ibuflen == 0:
                stream.flush = FULL_FLUSH
                stream.end_of_stream = 1
            else:
                stream.flush = NO_FLUSH

            # This loop reads all the input bytes. The check is at the end,
            # because when flush = FULL_FLUSH the input buffer is empty. But
            # this loop still needs to run one time.
            while True:
                stream.next_out = obuf  # Reset output buffer.
                stream.avail_out = obuflen
                err = isal_deflate(&stream)
                if err != COMP_OK:
                    # There is some python interacting when possible exceptions
                    # Are raised. So we remain in pure C code if we check for
                    # COMP_OK first.
                    check_isal_deflate_rc(err)
                total_bytes = obuflen - stream.avail_out
                # Instead of output buffer resizing as the zlibmodule.c example
                # the data is appended to a list.
                # TODO: Improve this with the buffer protocol.
                out.append(obuf[:total_bytes])
                if stream.avail_in == 0:
                    break
        return b"".join(out)
    finally:
        PyMem_Free(level_buf)
        PyMem_Free(obuf)

cpdef decompress(data,
                 int wbits=ISAL_DEF_MAX_HIST_BITS,
                 Py_ssize_t bufsize=DEF_BUF_SIZE,):

    if bufsize < 0:
        raise ValueError("bufsize must be non-negative")
    elif bufsize == 0:
        bufsize = 1
    if wbits > ISAL_DEF_MAX_HIST_BITS:
        raise ValueError("Wbits can not be larger than {0}".format(
            ISAL_DEF_MAX_HIST_BITS))
   
   
    cdef inflate_state stream
    isal_inflate_init(&stream)
    stream.hist_bits = wbits
    stream.crc_flag = ISAL_ZLIB
    
    # initialise input
    cdef Py_ssize_t max_input_buffer = UINT32_MAX
    cdef Py_ssize_t total_length = len(data)
    cdef Py_ssize_t remains = total_length
    cdef Py_ssize_t ibuflen = total_length
    cdef Py_ssize_t position = 0
    cdef bytes ibuf

    # Initialise output buffer
    cdef unsigned long obuflen = DEF_BUF_SIZE
    cdef unsigned char * obuf = <unsigned char*> PyMem_Malloc(obuflen * sizeof(char))
    out = []
    cdef int err

    # Implementation imitated from CPython's zlibmodule.c
    try:
        while ibuflen != 0 or stream.block_state != ISAL_BLOCK_FINISH:
            # This loop runs n times (at least twice). n-1 times to fill the input
            # buffer with data. The nth time the input is empty. In that case
            # stream.flush is set to FULL_FLUSH and the end_of_stream is activated.
            ibuflen = Py_ssize_t_min(remains, max_input_buffer)
            ibuf = data[position: position + ibuflen]
            position += ibuflen
            stream.next_in = ibuf
            remains -= ibuflen
            stream.avail_in = ibuflen

            # This loop reads all the input bytes. The check is at the end,
            # because when the block state is not at FINISH, the function needs
            # to be called again.
            while True:
                stream.next_out = obuf  # Reset output buffer.
                stream.avail_out = obuflen
                err = isal_inflate(&stream)
                if err != ISAL_DECOMP_OK:
                    # There is some python interacting when possible exceptions
                    # Are raised. So we remain in pure C code if we check for
                    # COMP_OK first.
                    check_isal_inflate_rc(err)
                # Instead of output buffer resizing as the zlibmodule.c example
                # the data is appended to a list.
                # TODO: Improve this with the buffer protocol.
                out.append(obuf[:obuflen - stream.avail_out])
                if stream.avail_in == 0:
                    break
        return b"".join(out)
    finally:
        PyMem_Free(obuf)


cpdef decompressobj(int wbits=ISAL_DEF_MAX_HIST_BITS,
                    zdict = None):
    pass


cpdef compressobj(int level=ISAL_DEFAULT_COMPRESSION,
                  int method=DEFLATED,
                  int wbits=ISAL_DEF_MAX_HIST_BITS,
                  int memLevel=DEF_MEM_LEVEL,
                  int strategy=zlib.Z_DEFAULT_STRATEGY,
                  zdict = None):
    return Compress.__new__(Compress, level, method, wbits, memLevel, strategy, zdict)


cdef class Compress:
    cdef isal_zstream stream
    cdef bytearray level_buf

    def __cinit__(self,
                  int level = ISAL_DEFAULT_COMPRESSION,
                  int method = DEFLATED,
                  int wbits = ISAL_DEF_MAX_HIST_BITS,
                  int memLevel = DEF_MEM_LEVEL,
                  int strategy = Z_DEFAULT_STRATEGY,
                  zdict = None):
        if strategy != Z_DEFAULT_STRATEGY:
            warnings.warn("Only online strategy is supported when using "
                          "isal_zlib. Using the default strategy.")
        isal_deflate_init(&self.stream)
        if 9 <= wbits <= 15:  # zlib headers and trailers on compressed stream
            self.stream.hist_bits = wbits
            self.stream.gzip_flag = IGZIP_ZLIB
        elif 25 <= wbits <= 31: # gzip headers and trailers on compressed stream
            self.stream.hist_bits = wbits - 16
            self.stream.gzip_flag = IGZIP_GZIP
        elif -15 <= wbits <= -9:  # raw compressed stream
            self.stream.hist_bits = -wbits
            self.stream.gzip_flag = IGZIP_DEFLATE
        else:
            raise ValueError("Invalid wbits value")
        cdef Py_ssize_t zdict_length
        if zdict:
            zdict_length = len(zdict)
            if zdict_length > UINT32_MAX:
                raise OverflowError("zdict length does not fit in an unsigned int")
            err = isal_deflate_set_dict(&self.stream, zdict, zdict_length)
            if err != COMP_OK:
                check_isal_deflate_rc(err)
        if level == zlib.Z_DEFAULT_COMPRESSION:
            level = ISAL_DEFAULT_COMPRESSION
        self.stream.level = level
        self.stream.level_buf_size = zlib_mem_level_to_isal(level, memLevel)
        self.level_buf = bytearray(self.stream.level_buf_size)
        self.stream.level_buf = self.level_buf

    def compress(self, data):
        cdef isal_zstream * stream = &self.stream
        cdef Py_ssize_t ibuflen
        cdef Py_ssize_t position = 0
        cdef Py_ssize_t max_input_buffer = UINT32_MAX

        stream.next_in = data

        while self.stream.internal_state.state != ZSTATE_END or ibuflen !=0:
            # This loop runs n times (at least twice). n-1 times to fill the input
            # buffer with data. The nth time the input is empty. In that case
            # stream.flush is set to FULL_FLUSH and the end_of_stream is activated.
            ibuflen = Py_ssize_t_min(remains, max_input_buffer)
            ibuf = data[position: position + ibuflen]
            position += ibuflen
            stream.next_in = ibuf
            remains -= ibuflen
            stream.avail_in = ibuflen
    def flush(self, int mode=zlib.Z_FINISH):
        pass 
    
    def copy(self):
        raise NotImplementedError("Copy not yet implemented for isal_zlib")

cdef class Decompress:
    cdef unsigned char *unused_data
    cdef unsigned char *unconsumed_tail
    cdef bint eof
    cdef bint is_initialised


    cpdef decompress(self, unsigned char *data, Py_ssize_t max_length):
        pass

    cpdef flush(self, Py_ssize_t length = DEF_BUF_SIZE):
        pass

    cpdef copy(self):
        raise NotImplementedError("Copy not yet implemented for isal_zlib")


cdef int zlib_mem_level_to_isal(int compression_level, int mem_level):
    """
    Convert zlib memory levels to isal equivalents
    """
    if not (1 < mem_level < 9):
        raise ValueError("Memory level must be between 1 and 9")
    if not (ISAL_DEF_MIN_LEVEL <= compression_level <= ISAL_DEF_MAX_LEVEL):
        raise ValueError("Invalid compression level.")

    # If the mem_level is zlib default, return isal defaults.
    # Current zlib def level = 8. On isal the def level is large.
    # Hence 7,8 return large. 9 returns extra large.
    if mem_level == DEF_MEM_LEVEL_I:
        if compression_level == 0:
            return ISAL_DEF_LVL0_DEFAULT
        elif compression_level == 1:
            return ISAL_DEF_LVL1_DEFAULT
        elif compression_level == 2:
            return ISAL_DEF_LVL2_DEFAULT
        elif compression_level == 3:
            return ISAL_DEF_LVL3_DEFAULT
    if mem_level == 1:
        if compression_level == 0:
            return ISAL_DEF_LVL0_MIN
        elif compression_level == 1:
            return ISAL_DEF_LVL1_MIN
        elif compression_level == 2:
            return ISAL_DEF_LVL2_MIN
        elif compression_level == 3:
            return ISAL_DEF_LVL3_MIN
    elif mem_level in [2,3]:
        if compression_level == 0:
            return ISAL_DEF_LVL0_SMALL
        elif compression_level == 1:
            return ISAL_DEF_LVL1_SMALL
        elif compression_level == 2:
            return ISAL_DEF_LVL2_SMALL
        elif compression_level == 3:
            return ISAL_DEF_LVL3_SMALL
    elif mem_level in [4,5,6]:
        if compression_level == 0:
            return ISAL_DEF_LVL0_MEDIUM
        elif compression_level == 1:
            return ISAL_DEF_LVL1_MEDIUM
        elif compression_level == 2:
            return ISAL_DEF_LVL2_MEDIUM
        elif compression_level == 3:
            return ISAL_DEF_LVL3_MEDIUM
    elif mem_level in [7,8]:
        if compression_level == 0:
            return ISAL_DEF_LVL0_LARGE
        elif compression_level == 1:
            return ISAL_DEF_LVL1_LARGE
        elif compression_level == 2:
            return ISAL_DEF_LVL2_LARGE
        elif compression_level == 3:
            return ISAL_DEF_LVL3_LARGE
    elif mem_level == 9:
        if compression_level == 0:
            return ISAL_DEF_LVL0_EXTRA_LARGE
        elif compression_level == 1:
            return ISAL_DEF_LVL1_EXTRA_LARGE
        elif compression_level == 2:
            return ISAL_DEF_LVL2_EXTRA_LARGE
        elif compression_level == 3:
            return ISAL_DEF_LVL3_EXTRA_LARGE
    raise ValueError("Incorrect memory level or compression level.")

cdef check_isal_deflate_rc(int rc):
    if rc == COMP_OK:
        return
    elif rc == INVALID_FLUSH:
        raise IsalError("Invalid flush type")
    elif rc == INVALID_PARAM:
        raise IsalError("Invalid parameter")
    elif rc == STATELESS_OVERFLOW:
        raise IsalError("Not enough room in output buffer")
    elif rc == ISAL_INVALID_OPERATION:
        raise IsalError("Invalid operation")
    elif rc == ISAL_INVALID_STATE:
        raise IsalError("Invalid state")
    elif rc == ISAL_INVALID_LEVEL:
        raise IsalError("Invalid compression level.")
    elif rc == ISAL_INVALID_LEVEL_BUF:
        raise IsalError("Level buffer too small.")
    else:
        raise IsalError("Unknown Error")

cdef check_isal_inflate_rc(int rc):
    if rc >= ISAL_DECOMP_OK:
        return
    if rc == ISAL_END_INPUT:
        raise IsalError("End of input reached")
    if rc == ISAL_OUT_OVERFLOW:
        raise IsalError("End of output reached")
    if rc == ISAL_NAME_OVERFLOW:
        raise IsalError("End of gzip name buffer reached")
    if rc == ISAL_COMMENT_OVERFLOW:
        raise IsalError("End of gzip name buffer reached")
    if rc == ISAL_EXTRA_OVERFLOW:
        raise IsalError("End of extra buffer reached")
    if rc == ISAL_NEED_DICT:
        raise IsalError("Dictionary needed to continue")
    if rc == ISAL_INVALID_BLOCK:
        raise IsalError("Invalid deflate block found")
    if rc == ISAL_INVALID_SYMBOL:
        raise IsalError("Invalid deflate symbol found")
    if rc == ISAL_INVALID_LOOKBACK:
        raise IsalError("Invalid lookback distance found")
    if rc == ISAL_INVALID_WRAPPER:
        raise IsalError("Invalid gzip/zlib wrapper found")
    if rc == ISAL_UNSUPPORTED_METHOD:
        raise IsalError("Gzip/zlib wrapper specifies unsupported compress method")
    if rc == ISAL_INCORRECT_CHECKSUM:
        raise IsalError("Incorrect checksum found")
