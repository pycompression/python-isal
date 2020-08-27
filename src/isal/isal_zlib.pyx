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

ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = 2
DEF_BUF_SIZE = zlib.DEF_BUF_SIZE
DEF_MEM_LEVEL = zlib.DEF_MEM_LEVEL

class IsalError(Exception):
    pass


if ISAL_DEF_MAX_HIST_BITS > zlib.MAX_WBITS:
    raise  IsalError("ISAL max window size no longer compatible with zlib. "
                     "Please contact the developers.")


cdef int zlib_mem_level_to_isal(int compression_level, int mem_level):
    """
    Convert zlib memory levels to isal equivalents
    """
    if not (1 < mem_level < 9):
        raise ValueError("Memory level must be between 1 and 9")
    if not (ISAL_DEF_MIN_LEVEL < compression_level < ISAL_DEF_MAX_LEVEL):
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


def adler32(data, value = 0):
    zlib.adler32(data, value)

cpdef crc32(unsigned char *data, unsigned int value = 0):
    return crc32_gzip_refl(value, data, len(data))

cpdef compress(unsigned char *data, int level =ISAL_DEFAULT_COMPRESSION):
    if level == -1:
        level = ISAL_DEFAULT_COMPRESSION
    pass


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