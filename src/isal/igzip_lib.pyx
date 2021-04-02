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
# cython: binding=True

from libc.stdint cimport UINT64_MAX, UINT32_MAX
from cpython.mem cimport PyMem_Malloc, PyMem_Realloc, PyMem_Free
from cpython.buffer cimport PyBUF_C_CONTIGUOUS, PyObject_GetBuffer, PyBuffer_Release
from cpython.bytes cimport PyBytes_FromStringAndSize

cdef extern from "<Python.h>":
    const Py_ssize_t PY_SSIZE_T_MAX

ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = 2

DEF DEF_BUF_SIZE_I = 16 * 1024
DEF_BUF_SIZE = DEF_BUF_SIZE_I
MAX_HIST_BITS = ISAL_DEF_MAX_HIST_BITS

ISAL_NO_FLUSH = NO_FLUSH
ISAL_SYNC_FLUSH = SYNC_FLUSH
ISAL_FULL_FLUSH = FULL_FLUSH

COMP_DEFLATE = IGZIP_DEFLATE
COMP_GZIP = IGZIP_GZIP
COMP_GZIP_NO_HDR = IGZIP_GZIP_NO_HDR
COMP_ZLIB = IGZIP_ZLIB
COMP_ZLIB_NO_HDR = IGZIP_ZLIB_NO_HDR

DECOMP_DEFLATE = ISAL_DEFLATE
DECOMP_GZIP = ISAL_GZIP
DECOMP_GZIP_NO_HDR = ISAL_GZIP_NO_HDR
DECOMP_ZLIB = ISAL_ZLIB
DECOMP_ZLIB_NO_HDR = ISAL_ZLIB_NO_HDR
DECOMP_ZLIB_NO_HDR_VER = ISAL_ZLIB_NO_HDR_VER
DECOMP_GZIP_NO_HDR_VER = ISAL_GZIP_NO_HDR_VER

DEF MEM_LEVEL_DEFAULT_I = 0
DEF MEM_LEVEL_MIN_I = 1
DEF MEM_LEVEL_SMALL_I = 2
DEF MEM_LEVEL_MEDIUM_I = 3
DEF MEM_LEVEL_LARGE_I = 4
DEF MEM_LEVEL_EXTRA_LARGE_I = 5
MEM_LEVEL_DEFAULT = MEM_LEVEL_DEFAULT_I
MEM_LEVEL_MIN = MEM_LEVEL_MIN_I
MEM_LEVEL_SMALL = MEM_LEVEL_SMALL_I
MEM_LEVEL_MEDIUM = MEM_LEVEL_MEDIUM_I
MEM_LEVEL_LARGE = MEM_LEVEL_LARGE_I
MEM_LEVEL_EXTRA_LARGE = MEM_LEVEL_EXTRA_LARGE_I

class IsalError(OSError):
    """Exception raised on compression and decompression errors."""
    pass



cdef Py_ssize_t arrange_output_buffer_with_maximum(stream_or_state *stream,
                                                   unsigned char **buffer,
                                                   Py_ssize_t length,
                                                   Py_ssize_t max_length):
    # The zlibmodule.c function builds a PyBytes object. A unsigned char *
    # is build here because building raw PyObject * stuff in cython is somewhat
    # harder due to cython's interference. FIXME
    cdef Py_ssize_t occupied
    cdef Py_ssize_t new_length
    cdef unsigned char * new_buffer
    if buffer[0] == NULL:
        buffer[0] = <unsigned char*>PyMem_Malloc(length * sizeof(char))
        if buffer[0] == NULL:
            return -1
        occupied = 0
    else:
        occupied = stream.next_out - buffer[0]
        if length == occupied:
            if length == max_length:
                return -2
            if length <= max_length >> 1:
                new_length = length << 1
            else:
                new_length = max_length
            new_buffer = <unsigned char *>PyMem_Realloc(buffer[0], new_length)
            if new_buffer == NULL:
                return -1
            buffer[0] = new_buffer
            length = new_length
    stream.avail_out = <unsigned int>py_ssize_t_min(length - occupied, UINT32_MAX)
    stream.next_out = buffer[0] + occupied
    return length

cdef Py_ssize_t arrange_output_buffer(stream_or_state *stream,
                                      unsigned char **buffer,
                                      Py_ssize_t length):
    cdef Py_ssize_t ret
    ret = arrange_output_buffer_with_maximum(stream, buffer, length, PY_SSIZE_T_MAX)
    if ret == -2:  # Maximum reached.
        return -1
    return ret

cdef void arrange_input_buffer(stream_or_state *stream, Py_ssize_t *remains):
    stream.avail_in = <unsigned int>py_ssize_t_min(remains[0], UINT32_MAX)
    remains[0] -= stream.avail_in

def compress(data,
             int level=ISAL_DEFAULT_COMPRESSION,
             int compress_type = COMP_DEFLATE,
             int hist_bits = ISAL_DEF_MAX_HIST_BITS,
            ):
    """
    Compresses the bytes in *data*. Returns a bytes object with the
    compressed data.

    :param level: the compression level from 0 to 3. 0 is the lowest
                  compression (NOT no compression as in stdlib zlib!) and the
                  fastest. 3 is the best compression and the slowest. Default
                  is a compromise at level 2.
    """
    # Initialise stream
    cdef isal_zstream stream
    cdef unsigned int level_buf_size
    mem_level_to_bufsize(level, MEM_LEVEL_DEFAULT_I, &level_buf_size)
    cdef unsigned char* level_buf = <unsigned char*> PyMem_Malloc(level_buf_size * sizeof(char))
    isal_deflate_init(&stream)
    stream.level = level
    stream.level_buf = level_buf
    stream.level_buf_size = level_buf_size
    stream.hist_bits = hist_bits
    stream.gzip_flag = compress_type

    # Initialise output buffer
    cdef Py_ssize_t bufsize = DEF_BUF_SIZE_I
    cdef unsigned char * obuf = NULL
    
    # initialise input
    cdef Py_buffer buffer_data
    cdef Py_buffer* buffer = &buffer_data
    # Cython makes sure error is handled when acquiring buffer fails.
    PyObject_GetBuffer(data, buffer, PyBUF_C_CONTIGUOUS)
    cdef Py_ssize_t ibuflen = buffer.len
    stream.next_in = <unsigned char*>buffer.buf

    # initialise helper variables
    cdef int err

    try:
        while True:
            arrange_input_buffer(&stream, &ibuflen)
            if ibuflen == 0:
                stream.flush = FULL_FLUSH
                stream.end_of_stream = 1
            else:
                stream.flush = NO_FLUSH

            while True:
                bufsize = arrange_output_buffer(&stream, &obuf, bufsize)
                if bufsize == -1:
                    raise MemoryError("Unsufficient memory for buffer allocation")
                err = isal_deflate(&stream)
                if err != COMP_OK:
                    check_isal_deflate_rc(err)
                if stream.avail_out != 0:
                    break
            if stream.avail_in != 0:
                raise AssertionError("Input stream should be empty")
            if stream.internal_state.state == ZSTATE_END:
                break
        return PyBytes_FromStringAndSize(<char*>obuf, stream.next_out - obuf)
    finally:
        PyBuffer_Release(buffer)
        PyMem_Free(level_buf)
        PyMem_Free(obuf)

cdef mem_level_to_bufsize(int compression_level, int mem_level, unsigned int *bufsize):
    """
    Convert zlib memory levels to isal equivalents
    """
    if not (0 <= mem_level <= MEM_LEVEL_EXTRA_LARGE_I):
        raise ValueError("Invalid memory level")
    if not (ISAL_DEF_MIN_LEVEL <= compression_level <= ISAL_DEF_MAX_LEVEL):
        raise ValueError("Invalid compression level.")

    if mem_level == MEM_LEVEL_DEFAULT_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_DEFAULT
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_DEFAULT
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_DEFAULT
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_DEFAULT
    if mem_level == MEM_LEVEL_MIN_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_MIN
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_MIN
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_MIN
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_MIN
    elif mem_level == MEM_LEVEL_SMALL_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_SMALL
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_SMALL
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_SMALL
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_SMALL
    elif mem_level == MEM_LEVEL_MEDIUM_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_MEDIUM
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_MEDIUM
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_MEDIUM
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_MEDIUM
    elif mem_level == MEM_LEVEL_LARGE_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_LARGE
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_LARGE
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_LARGE
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_LARGE
    elif mem_level == MEM_LEVEL_EXTRA_LARGE_I:
        if compression_level == 0:
            bufsize[0] = ISAL_DEF_LVL0_EXTRA_LARGE
        elif compression_level == 1:
            bufsize[0] = ISAL_DEF_LVL1_EXTRA_LARGE
        elif compression_level == 2:
            bufsize[0] = ISAL_DEF_LVL2_EXTRA_LARGE
        elif compression_level == 3:
            bufsize[0] = ISAL_DEF_LVL3_EXTRA_LARGE

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