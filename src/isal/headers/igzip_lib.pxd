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

cdef extern from "<isa-l/igzip_lib.h>":
    int ISAL_DEF_MIN_LEVEL
    int ISAL_DEF_MAX_LEVEL
    int COMP_OK
    int INVALID_FLUSH
    int ISAL_INVALID_LEVEL
    int ISAL_INVALID_LEVEL_BUFF
    ctypedef enum isal_zstate_state:
        pass
    ctypedef enum isal_block_state:
        pass
    ctypedef struct isal_gzip_header:
        pass
    ctypedef struct isal_zstream:
        pass
    ctypedef struct inflate_state:
        pass
    void isal_deflate_init(isal_zstream *stream);
    int isal_deflate(isal_zstream *stream);