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

import itertools
from typing import NamedTuple

from isal import igzip_lib
from isal.igzip_lib import (
    COMP_DEFLATE, COMP_GZIP, COMP_GZIP_NO_HDR, COMP_ZLIB, COMP_ZLIB_NO_HDR,
    DECOMP_DEFLATE, DECOMP_GZIP, DECOMP_GZIP_NO_HDR, DECOMP_GZIP_NO_HDR_VER,
    DECOMP_ZLIB, DECOMP_ZLIB_NO_HDR, DECOMP_ZLIB_NO_HDR_VER, MEM_LEVEL_DEFAULT,
    MEM_LEVEL_EXTRA_LARGE, MEM_LEVEL_LARGE, MEM_LEVEL_MEDIUM, MEM_LEVEL_MIN,
    MEM_LEVEL_SMALL)

import pytest

from .test_compat import DATA as RAW_DATA


class Flag(NamedTuple):
    comp: int
    decomp: int


DATA = RAW_DATA[:128 * 1024]

COMPRESS_LEVELS = list(range(4))
HIST_BITS = list(range(16))
FLAGS = [
    Flag(COMP_DEFLATE, DECOMP_DEFLATE),
    Flag(COMP_ZLIB, DECOMP_ZLIB),
    Flag(COMP_GZIP, DECOMP_GZIP),
    Flag(COMP_ZLIB_NO_HDR, DECOMP_ZLIB_NO_HDR),
    Flag(COMP_GZIP_NO_HDR, DECOMP_GZIP_NO_HDR),
    Flag(COMP_ZLIB_NO_HDR, DECOMP_ZLIB_NO_HDR_VER),
    Flag(COMP_GZIP_NO_HDR, DECOMP_GZIP_NO_HDR_VER),
]
MEM_LEVELS = [MEM_LEVEL_DEFAULT, MEM_LEVEL_MIN, MEM_LEVEL_SMALL,
              MEM_LEVEL_MEDIUM, MEM_LEVEL_LARGE, MEM_LEVEL_EXTRA_LARGE]


@pytest.mark.parametrize(["level", "flag", "mem_level", "hist_bits"],
                         itertools.product(
                             COMPRESS_LEVELS, FLAGS, MEM_LEVELS, HIST_BITS))
def test_compress_decompress(level, flag: Flag, mem_level, hist_bits):
    comp = igzip_lib.compress(DATA, level, flag.comp, mem_level, hist_bits)
    decomp = igzip_lib.decompress(comp, flag.decomp, hist_bits)
    assert decomp == DATA
