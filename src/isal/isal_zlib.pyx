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

import zlib

from .crc cimport crc32_gzip_refl
from .igzip_lib cimport *
from libc.stdint cimport UINT64_MAX, UINT32_MAX, uint32_t
from cpython cimport PyObject_GetBuffer,  Py_buffer, PyBUF_SIMPLE, PyBUF_WRITABLE

ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = 2
Z_BEST_SPEED = ISAL_BEST_SPEED
Z_BEST_COMPRESSION = ISAL_BEST_COMPRESSION
Z_DEFAULT_COMPRESSION = ISAL_DEFAULT_COMPRESSION

DEF_BUF_SIZE = zlib.DEF_BUF_SIZE
DEF_MEM_LEVEL = zlib.DEF_MEM_LEVEL
MAX_WBITS = ISAL_DEF_MAX_HIST_BITS

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

cpdef compress(data, level=ISAL_DEFAULT_COMPRESSION):
    if level == zlib.Z_DEFAULT_COMPRESSION:
        level = ISAL_DEFAULT_COMPRESSION

    obuflen = DEF_BUF_SIZE
    ibuflen = len(data)
    cdef Py_ssize_t start, stop
    cdef isal_zstream stream
    cdef bytes ibuf
    cdef bytearray obuf = bytearray(obuflen)
    cdef long level_buf_size = zlib_mem_level_to_isal(level, DEF_MEM_LEVEL)
    cdef bytearray level_buf = bytearray(level_buf_size)
    cdef int err
    isal_deflate_init(&stream)
    stream.level = level
    stream.level_buf = level_buf
    stream.level_buf_size = level_buf_size
    stream.next_out = obuf
    stream.avail_out = obuflen
    stream.gzip_flag = IGZIP_ZLIB
    stream.flush = NO_FLUSH
    for start in range(0, ibuflen, UINT32_MAX):
        stop = start + UINT32_MAX
        ibuf = data[start: stop]
        stream.next_in = ibuf
        stream.avail_in = len(ibuf)
        if stop >= ibuflen:
            stream.flush = FULL_FLUSH
            stream.end_of_stream = 1

        while True:
            err = isal_deflate(&stream)
            if err == STATELESS_OVERFLOW:
                obuf.extend(bytearray(obuflen))
                obuflen *= 2
                stream.next_out = obuf
                stream.avail_out = obuflen
            elif err == COMP_OK:
                break
            else:
                check_isal_deflate_rc(err)
    return bytes(obuf[:stream.total_out])


cpdef compressobj(int level=ISAL_DEFAULT_COMPRESSION,
                  int method=zlib.DEFLATED,
                  int wbits=ISAL_DEF_MAX_HIST_BITS,
                  int memLevel=DEF_MEM_LEVEL,
                  int strategy=zlib.Z_DEFAULT_STRATEGY,
                  zdict = None):
    pass 


cpdef decompress(unsigned char *data,
                 int wbits=ISAL_DEF_MAX_HIST_BITS,
                 Py_ssize_t bufsize=DEF_BUF_SIZE,):
    pass


cpdef decompressobj(int wbits=ISAL_DEF_MAX_HIST_BITS,
                    zdict = None):
    pass


cdef class Compress:
    cpdef compress(self, unsigned char *data):
        pass
    
    cpdef flush(self, int mode=zlib.Z_FINISH):
        pass 
    
    cpdef copy(self):
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
    if mem_level == zlib.DEF_MEM_LEVEL:
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