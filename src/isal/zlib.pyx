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

from libc.stdint cimport uint64_t, uint32_t

cimport cython
cdef extern from "<isa-l/igzip_lib.h>":
    int ISAL_DEF_MIN_LEVEL
    int ISAL_DEF_MAX_LEVEL

ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = 2

cdef extern from "<isa-l/crc.h>":
    uint32_t crc32_gzip_refl(
    uint32_t init_crc,          #!< initial CRC value, 32 bits
    const unsigned char *buf, #!< buffer to calculate CRC on
    uint64_t len                #!< buffer length in bytes (64-bit data)
    )

cdef _crc32(bytes data, unsigned int value = 0):
    cdef uint64_t buffer_length = len(data)
    cdef unsigned char* buf = data
    cdef unsigned int result = crc32_gzip_refl(value, buf, buffer_length)
    return result

cpdef crc32(bytes data, unsigned int value = 0):
    return _crc32(bytes, value)