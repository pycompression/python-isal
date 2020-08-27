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
from .igzip_lib cimport (ISAL_DEF_MIN_LEVEL, 
                         ISAL_DEF_MAX_LEVEL,
                         ISAL_DEF_MAX_HIST_BITS,
                         ISAL_DEFLATE)
ISAL_BEST_SPEED = ISAL_DEF_MIN_LEVEL
ISAL_BEST_COMPRESSION = ISAL_DEF_MAX_LEVEL
ISAL_DEFAULT_COMPRESSION = -1
DEF_BUF_SIZE = zlib.DEF_BUF_SIZE
DEF_MEM_LEVEL = zlib.DEF_MEM_LEVEL

class IsalError(Exception):
    pass


if ISAL_DEF_MAX_HIST_BITS > zlib.MAX_WBITS:
    raise  IsalError("ISAL max window size no longer compatible with zlib. "
                     "Please contact the developers.")


cpdef adler32(unsigned char *data, unsigned int value = 0):
    raise NotImplementedError("Adler32 is not implemented in isal.")

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