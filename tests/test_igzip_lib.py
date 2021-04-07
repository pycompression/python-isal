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

import pytest

from .test_compat import DATA as RAW_DATA


class Flag(NamedTuple):
    comp: int
    decomp: int


DATA = RAW_DATA[:128 * 1024]

COMPRESS_LEVELS = list(range(4))
HIST_BITS = list(range(16))
FLAGS = [
    Flag(igzip_lib.COMP_DEFLATE, igzip_lib.DECOMP_DEFLATE),
    Flag(igzip_lib.COMP_ZLIB, igzip_lib.DECOMP_ZLIB),
    Flag(igzip_lib.COMP_GZIP, igzip_lib.DECOMP_GZIP),
    Flag(igzip_lib.COMP_ZLIB_NO_HDR, igzip_lib.DECOMP_ZLIB_NO_HDR),
    Flag(igzip_lib.COMP_GZIP_NO_HDR, igzip_lib.DECOMP_GZIP_NO_HDR),
    Flag(igzip_lib.COMP_ZLIB_NO_HDR, igzip_lib.DECOMP_ZLIB_NO_HDR_VER),
    Flag(igzip_lib.COMP_GZIP_NO_HDR, igzip_lib.DECOMP_GZIP_NO_HDR_VER),
]


@pytest.mark.parametrize(["level", "flag", "hist_bits"],
                         itertools.product(COMPRESS_LEVELS, FLAGS, HIST_BITS))
def test_compress_decompress(level, flag: Flag, hist_bits):
    comp = igzip_lib.compress(DATA, level, flag.comp, hist_bits)
    decomp = igzip_lib.decompress(comp, flag.decomp, hist_bits)
    assert decomp == DATA


class TestIgzipDecompressor():
    compressed = igzip_lib.compress(DATA)

    def test_decompress(self):
        decomp = igzip_lib.IgzipDecompressor()
        decompressed = decomp.decompress(self.compressed)
        assert decompressed == DATA
