# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

# TestIgzipDecompressor was modified from TestBZ2Decompress from Cpython's
# Lib/test/test_bz2.py.

import gzip
import itertools
import os
import pickle
import sys
import zlib
from typing import NamedTuple

from isal import igzip_lib
from isal.igzip_lib import (
    COMP_DEFLATE, COMP_GZIP, COMP_GZIP_NO_HDR, COMP_ZLIB, COMP_ZLIB_NO_HDR,
    DECOMP_DEFLATE, DECOMP_GZIP, DECOMP_GZIP_NO_HDR, DECOMP_GZIP_NO_HDR_VER,
    DECOMP_ZLIB, DECOMP_ZLIB_NO_HDR, DECOMP_ZLIB_NO_HDR_VER, MEM_LEVEL_DEFAULT,
    MEM_LEVEL_EXTRA_LARGE, MEM_LEVEL_LARGE, MEM_LEVEL_MEDIUM, MEM_LEVEL_MIN,
    MEM_LEVEL_SMALL)
from isal.igzip_lib import IgzipDecompressor

import pytest

from .test_compat import DATA as RAW_DATA


class Flag(NamedTuple):
    comp: int
    decomp: int


DATA = RAW_DATA[:128 * 1024]
ZLIB_COMPRESSED = zlib.compress(DATA)
GZIP_COMPRESSED = gzip.compress(DATA)

COMPRESS_LEVELS = list(range(4))
HIST_BITS = list(range(16))
FLAGS = [
    Flag(COMP_DEFLATE, DECOMP_DEFLATE),
    Flag(COMP_ZLIB, DECOMP_ZLIB),
    Flag(COMP_GZIP, DECOMP_GZIP),
    # DECOMP_GZIP_NO_HDR and DECOMP_ZLIB_NO_HDR do not read headers
    # and trailers
    Flag(COMP_DEFLATE, DECOMP_ZLIB_NO_HDR),
    Flag(COMP_DEFLATE, DECOMP_GZIP_NO_HDR),
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


class TestIgzipDecompressor():
    # Tests adopted from CPython's test_bz2.py
    TEXT = DATA
    DATA = igzip_lib.compress(DATA)
    BAD_DATA = b"Not a valid deflate block"

    def test_decompress(self):
        decomp = IgzipDecompressor()
        decompressed = decomp.decompress(self.DATA)
        assert decompressed == self.TEXT

    def testDecompressChunks10(self):
        igzd = IgzipDecompressor()
        text = b''
        n = 0
        while True:
            str = self.DATA[n*10:(n+1)*10]
            if not str:
                break
            text += igzd.decompress(str)
            n += 1
        assert text == self.TEXT

    def testDecompressUnusedData(self):
        igzd = IgzipDecompressor()
        unused_data = b"this is unused data"
        text = igzd.decompress(self.DATA+unused_data)
        assert text == self.TEXT
        assert igzd.unused_data == unused_data

    def testEOFError(self):
        igzd = IgzipDecompressor()
        igzd.decompress(self.DATA)
        with pytest.raises(EOFError):
            igzd.decompress(b"anything")
        with pytest.raises(EOFError):
            igzd.decompress(b"")

    @pytest.mark.skip(reason="Causes memory issues on CI systems.")
    def testDecompress4G(self):
        # "Test igzdecompressor.decompress() with >4GiB input"
        size = 4 * 1024 ** 3 + 100  # 4 GiB + 100
        blocksize = 10 * 1024 * 1024
        block = os.urandom(blocksize)
        try:
            data = block * (size // blocksize + 1)
            compressed = igzip_lib.compress(data)
            igzd = IgzipDecompressor()
            decompressed = igzd.decompress(compressed)
            assert decompressed == data
        finally:
            data = None
            compressed = None
            decompressed = None

    @pytest.mark.skipif(sys.implementation.name == "pypy",
                        reason="Pickling is not a requirement, and certainly "
                               "not a blocker for PyPy.")
    def testPickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with pytest.raises(TypeError):
                pickle.dumps(IgzipDecompressor(), proto)

    def testDecompressorChunksMaxsize(self):
        igzd = IgzipDecompressor()
        max_length = 100
        out = []

        # Feed some input
        len_ = len(self.DATA) - 64
        out.append(igzd.decompress(self.DATA[:len_],
                                   max_length=max_length))
        assert not igzd.needs_input
        assert len(out[-1]) == max_length

        # Retrieve more data without providing more input
        out.append(igzd.decompress(b'', max_length=max_length))
        assert not igzd.needs_input
        assert len(out[-1]) == max_length

        # Retrieve more data while providing more input
        out.append(igzd.decompress(self.DATA[len_:],
                                   max_length=max_length))
        assert len(out[-1]) == max_length

        # Retrieve remaining uncompressed data
        while not igzd.eof:
            out.append(igzd.decompress(b'', max_length=max_length))
            assert len(out[-1]) <= max_length

        out = b"".join(out)
        assert out == self.TEXT
        assert igzd.unused_data == b""

    def test_decompressor_inputbuf_1(self):
        # Test reusing input buffer after moving existing
        # contents to beginning
        igzd = IgzipDecompressor()
        out = []

        # Create input buffer and fill it
        assert igzd.decompress(self.DATA[:100], max_length=0) == b''

        # Retrieve some results, freeing capacity at beginning
        # of input buffer
        out.append(igzd.decompress(b'', 2))

        # Add more data that fits into input buffer after
        # moving existing data to beginning
        out.append(igzd.decompress(self.DATA[100:105], 15))

        # Decompress rest of data
        out.append(igzd.decompress(self.DATA[105:]))
        assert b''.join(out) == self.TEXT

    def test_decompressor_inputbuf_2(self):
        # Test reusing input buffer by appending data at the
        # end right away
        igzd = IgzipDecompressor()
        out = []

        # Create input buffer and empty it
        assert igzd.decompress(self.DATA[:200], max_length=0) == b''
        out.append(igzd.decompress(b''))

        # Fill buffer with new data
        out.append(igzd.decompress(self.DATA[200:280], 2))

        # Append some more data, not enough to require resize
        out.append(igzd.decompress(self.DATA[280:300], 2))

        # Decompress rest of data
        out.append(igzd.decompress(self.DATA[300:]))
        assert b''.join(out) == self.TEXT

    def test_decompressor_inputbuf_3(self):
        # Test reusing input buffer after extending it

        igzd = IgzipDecompressor()
        out = []

        # Create almost full input buffer
        out.append(igzd.decompress(self.DATA[:200], 5))

        # Add even more data to it, requiring resize
        out.append(igzd.decompress(self.DATA[200:300], 5))

        # Decompress rest of data
        out.append(igzd.decompress(self.DATA[300:]))
        assert b''.join(out) == self.TEXT

    def test_failure(self):
        igzd = IgzipDecompressor()
        with pytest.raises(Exception):
            igzd.decompress(self.BAD_DATA * 30)
        # Make sure there are no internal consistencies
        with pytest.raises(Exception):
            igzd.decompress(self.BAD_DATA * 30)

    def test_dictionary(self):
        compressor = zlib.compressobj(zdict=b"bla")
        data = compressor.compress(b"bladiebla") + compressor.flush()
        igzd = IgzipDecompressor(flag=DECOMP_ZLIB, zdict=b"bla")
        assert igzd.decompress(data) == b"bladiebla"


@pytest.mark.parametrize("test_offset", range(5))
def test_igzip_decompressor_raw_deflate_unused_data_zlib(test_offset):
    data = zlib.compress(b"bla")
    no_header = data[2:]
    trailer = data[-4:]
    raw_deflate_incomplete_trailer = no_header[:-test_offset]
    true_unused_data = trailer[:-test_offset]
    igzd = IgzipDecompressor(flag=DECOMP_DEFLATE)
    igzd.decompress(raw_deflate_incomplete_trailer)
    if igzd.eof:
        assert igzd.unused_data == true_unused_data


@pytest.mark.parametrize("test_offset", range(9))
def test_igzip_decompressor_raw_deflate_unused_data_gzip(test_offset):
    data = gzip.compress(b"bla")
    no_header = data[10:]
    trailer = data[-8:]
    raw_deflate_incomplete_trailer = no_header[:-test_offset]
    true_unused_data = trailer[:-test_offset]
    igzd = IgzipDecompressor(flag=DECOMP_DEFLATE)
    igzd.decompress(raw_deflate_incomplete_trailer)
    if igzd.eof:
        assert igzd.unused_data == true_unused_data


@pytest.mark.parametrize(["unused_size", "flag_pair", "data_size"],
                         itertools.product([26], FLAGS,
                                           [128 * 1024 - 3, 874, 81923, 9111]))
def test_decompression_flags(unused_size, flag_pair, data_size):
    comp_flag, decomp_flag = flag_pair
    unused_data = b"abcdefghijklmnopqrstuvwxyz"[:unused_size]
    data = RAW_DATA[:data_size]
    compressed = igzip_lib.compress(data, flag=comp_flag)
    decompressor = igzip_lib.IgzipDecompressor(flag=decomp_flag)
    result = decompressor.decompress(compressed + unused_data)
    assert result == data

    # CRC should be present on the ZLIB and GZIP type flags.
    if decomp_flag in {DECOMP_ZLIB, DECOMP_ZLIB_NO_HDR,
                       DECOMP_ZLIB_NO_HDR_VER}:
        assert decompressor.crc == zlib.adler32(data)
    elif decomp_flag in {DECOMP_GZIP, DECOMP_GZIP_NO_HDR,
                         DECOMP_GZIP_NO_HDR_VER}:
        assert decompressor.crc == zlib.crc32(data)
    else:
        assert decompressor.crc == 0

    assert decompressor.unused_data == unused_data
