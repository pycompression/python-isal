# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

# This file does not include original code from CPython. It is used to ensure
# that compression and decompression between CPython's zlib and isal_zlib
# is compatible.

import gzip
import itertools
import random
import subprocess
import sys
import textwrap
import threading
import warnings
import zlib
from pathlib import Path

from isal import igzip, isal_zlib

import pytest

DATA_DIR = Path(__file__).parent / "data"
COMPRESSED_FILE = DATA_DIR / "test.fastq.gz"
with gzip.open(str(COMPRESSED_FILE), mode="rb") as file_h:
    DATA = file_h.read()

DATA_SIZES = [2**i for i in range(3, 20)]
# 100 seeds generated with random.randint(0, 2**32-1)
SEEDS_FILE = DATA_DIR / "seeds.txt"
INT_OVERFLOW = 211928379812738912738917238971289378912379823871932719823798123
# Get some negative ints and some really big ints into the mix.
SEEDS = [-INT_OVERFLOW, -3, -1, 0, 1, INT_OVERFLOW] + [
    int(seed) for seed in SEEDS_FILE.read_text().splitlines()]

# Wbits for ZLIB compression, GZIP compression, and RAW compressed streams
WBITS_RANGE = list(range(9, 16)) + list(range(25, 32)) + list(range(-15, -8))


@pytest.mark.parametrize(["data_size", "value"],
                         itertools.product(DATA_SIZES, SEEDS))
def test_crc32(data_size, value):
    data = DATA[:data_size]
    assert zlib.crc32(data, value) == isal_zlib.crc32(data, value)


@pytest.mark.parametrize(["data_size", "value"],
                         itertools.product(DATA_SIZES, SEEDS))
def test_adler32(data_size, value):
    data = DATA[:data_size]
    assert zlib.adler32(data, value) == isal_zlib.adler32(data, value)


@pytest.mark.parametrize("args", [("a", 1, 2), (1, "a", 2), (1, 2, "a"),
                                  (1, 2)])
def test_crc32_combine_wrong_arguments(args):
    with pytest.raises(TypeError):
        isal_zlib.crc32_combine(*args)


@pytest.mark.parametrize("factory",
                         [isal_zlib.compressobj, isal_zlib.decompressobj])
def test_compress_and_decompress_types_cannot_be_called(factory):
    with pytest.raises(TypeError):
        type(factory())()


@pytest.mark.skipif(sys.implementation.name != "cpython",
                    reason="Needs _testcapi.set_nomemory")
@pytest.mark.parametrize("factory", ["compressobj", "decompressobj"])
def test_compressobj_decompressobj_no_memory(factory):
    pytest.importorskip("_testcapi")
    # Fail each memory allocation in turn, such as the one for the lock. A
    # subprocess keeps the failing allocations away from the test runner.
    code = textwrap.dedent(f"""
        import _testcapi
        from isal import isal_zlib
        for start in range(20):
            _testcapi.set_nomemory(start, start + 1)
            try:
                isal_zlib.{factory}()
            except MemoryError:
                pass
            finally:
                _testcapi.remove_mem_hooks()
    """)
    subprocess.run([sys.executable, "-c", code], check=True)


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(4)))
def test_compress(data_size, level):
    data = DATA[:data_size]
    compressed = isal_zlib.compress(data, level=level)
    assert zlib.decompress(compressed) == data


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(10)))
def test_decompress_zlib(data_size, level):
    data = DATA[:data_size]
    compressed = zlib.compress(data, level=level)
    decompressed = isal_zlib.decompress(compressed)
    assert decompressed == data


@pytest.mark.parametrize(["data_size", "level", "wbits", "memLevel"],
                         itertools.product([128 * 1024], range(4),
                                           WBITS_RANGE, range(1, 10)))
def test_decompress_wbits(data_size, level, wbits, memLevel):
    data = DATA[:data_size]
    compressobj = zlib.compressobj(level=level, wbits=wbits, memLevel=memLevel)
    compressed = compressobj.compress(data) + compressobj.flush()
    decompressed = isal_zlib.decompress(compressed, wbits=wbits)
    assert data == decompressed


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(4)))
def test_decompress_isal_zlib(data_size, level):
    data = DATA[:data_size]
    compressed = isal_zlib.compress(data, level=level)
    decompressed = isal_zlib.decompress(compressed)
    print(len(decompressed))
    assert decompressed == data


@pytest.mark.parametrize(["data_size", "level", "wbits", "memLevel"],
                         itertools.product([128 * 1024], range(4),
                                           WBITS_RANGE, range(1, 10)))
def test_compress_compressobj(data_size, level, wbits, memLevel):
    data = DATA[:data_size]
    compressobj = isal_zlib.compressobj(level=level,
                                        wbits=wbits,
                                        memLevel=memLevel)
    compressed = compressobj.compress(data) + compressobj.flush()
    decompressed = zlib.decompress(compressed, wbits=wbits)
    assert data == decompressed


def test_compressobj_flush_unsupported_mode():
    compressor = isal_zlib.compressobj()
    with pytest.raises(isal_zlib.error) as error:
        compressor.flush(isal_zlib.Z_PARTIAL_FLUSH)
    error.match("Unsupported flush mode")
    # The next call hangs if the failed flush kept the lock
    result = []
    thread = threading.Thread(target=lambda: result.append(
        compressor.compress(b"data") + compressor.flush()), daemon=True)
    thread.start()
    thread.join(timeout=10)
    assert result
    assert zlib.decompress(result[0]) == b"data"


def test_compressobj_level_0_flush_after_finish():
    compressor = isal_zlib.compressobj(0)
    compressed = compressor.compress(b"data") + compressor.flush()
    assert compressor.flush() == b""
    assert zlib.decompress(compressed) == b"data"


@pytest.mark.parametrize("flush_mode", [isal_zlib.Z_SYNC_FLUSH,
                                        isal_zlib.Z_FULL_FLUSH])
@pytest.mark.parametrize(["strategy", "btype"],
                         [(isal_zlib.Z_DEFAULT_STRATEGY, 2),
                          (isal_zlib.Z_FIXED, 1)])
def test_compressobj_level_0_block_type(strategy, btype, flush_mode):
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compressor = isal_zlib.compressobj(0, wbits=-15, strategy=strategy)
    decompressor = zlib.decompressobj(wbits=-15)
    for i in range(0, 64 * 1024, 4096):
        data = DATA[i:i + 4096]
        compressed = compressor.compress(data) + compressor.flush(flush_mode)
        # Sync and full flushes end on a byte boundary, so each output starts
        # with a new block header. Bits 1 and 2 of the first byte hold BTYPE:
        # 1 for fixed Huffman codes, 2 for dynamic Huffman codes.
        assert compressed[0] >> 1 & 3 == btype
        assert decompressor.decompress(compressed) == data


# Gzip has no preset dictionary, so zdict is only tested with zlib and raw.
@pytest.mark.parametrize(["wbits", "use_zdict"],
                         [(wbits, False) for wbits in WBITS_RANGE] +
                         [(wbits, True) for wbits in WBITS_RANGE
                          if not 25 <= wbits <= 31])
def test_compressobj_level_0_z_fixed_round_trip(wbits, use_zdict):
    kwargs = {"zdict": DATA[:1024]} if use_zdict else {}
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        compressor = isal_zlib.compressobj(
            0, wbits=wbits, strategy=isal_zlib.Z_FIXED, **kwargs)
    # Random bytes use all literal codes, including the 9-bit ones.
    data = DATA[:64 * 1024] + random.Random(0).randbytes(64 * 1024)
    flush_modes = itertools.cycle([isal_zlib.Z_SYNC_FLUSH,
                                   isal_zlib.Z_FULL_FLUSH,
                                   isal_zlib.Z_NO_FLUSH])
    compressed = b""
    for i, mode in zip(range(0, len(data), 1000), flush_modes):
        compressed += (compressor.compress(data[i:i + 1000]) +
                       compressor.flush(mode))
    compressed += compressor.flush()
    decompressor = zlib.decompressobj(wbits=wbits, **kwargs)
    assert decompressor.decompress(compressed) == data
    assert decompressor.eof


@pytest.mark.parametrize(["level", "strategy"],
                         list(itertools.product(range(4),
                                                [isal_zlib.Z_FILTERED,
                                                 isal_zlib.Z_HUFFMAN_ONLY,
                                                 isal_zlib.Z_RLE])) +
                         [(level, isal_zlib.Z_FIXED) for level in range(1, 4)])
def test_compressobj_unsupported_strategy(level, strategy):
    data = DATA[:64 * 1024]
    with pytest.warns(UserWarning, match="Using the default strategy"):
        compressor = isal_zlib.compressobj(level, strategy=strategy)
    default_compressor = isal_zlib.compressobj(level)
    compressed = compressor.compress(data) + compressor.flush()
    assert compressed == (default_compressor.compress(data) +
                          default_compressor.flush())


@pytest.mark.parametrize(["data_size", "level", "wbits", "memLevel"],
                         itertools.product([128 * 1024], range(4),
                                           WBITS_RANGE, range(1, 10)))
def test_decompress_decompressobj(data_size, level, wbits, memLevel):
    data = DATA[:data_size]
    compressobj = zlib.compressobj(level=level, wbits=wbits, memLevel=memLevel)
    compressed = compressobj.compress(data) + compressobj.flush()
    decompressobj = isal_zlib.decompressobj(wbits=wbits)
    decompressed = decompressobj.decompress(compressed) + decompressobj.flush()
    assert data == decompressed
    assert decompressobj.unused_data == b""
    assert decompressobj.unconsumed_tail == b""


def test_decompressobj_unconsumed_tail():
    data = DATA[:128*1024]
    compressed = zlib.compress(data)
    decompressobj = isal_zlib.decompressobj()
    output = decompressobj.decompress(compressed, 2048)
    assert len(output) == 2048


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(4)))
def test_igzip_compress(data_size, level):
    data = DATA[:data_size]
    compressed = igzip.compress(data, compresslevel=level)
    assert gzip.decompress(compressed) == data


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(10)))
def test_decompress_gzip(data_size, level):
    data = DATA[:data_size]
    compressed = gzip.compress(data, compresslevel=level)
    decompressed = igzip.decompress(compressed)
    assert decompressed == data


@pytest.mark.parametrize(["data_size", "level"],
                         itertools.product(DATA_SIZES, range(4)))
def test_decompress_igzip(data_size, level):
    data = DATA[:data_size]
    compressed = igzip.compress(data, compresslevel=level)
    decompressed = igzip.decompress(compressed)
    print(len(decompressed))
    assert decompressed == data


@pytest.mark.parametrize(["unused_size", "wbits"],
                         itertools.product([26], [-15, 15, 31]))
def test_unused_data(unused_size, wbits):
    unused_data = b"abcdefghijklmnopqrstuvwxyz"[:unused_size]
    compressor = zlib.compressobj(wbits=wbits)
    data = b"A meaningful sentence starts with a capital and ends with a."
    compressed = compressor.compress(data) + compressor.flush()
    decompressor = isal_zlib.decompressobj(wbits=wbits)
    result = decompressor.decompress(compressed + unused_data)
    assert result == data
    assert decompressor.unused_data == unused_data


@pytest.mark.parametrize("wbits", [15, 31])
def test_decompressobj_detects_format_byte_by_byte(wbits):
    data = DATA[:1000]
    compressor = zlib.compressobj(wbits=wbits)
    compressed = compressor.compress(data) + compressor.flush()
    decompressor = isal_zlib.decompressobj(wbits=47)
    result = b"".join(decompressor.decompress(compressed[i:i + 1])
                      for i in range(len(compressed)))
    assert result == data
    assert decompressor.eof


@pytest.mark.parametrize("wbits", [15, 31])
def test_decompressobj_detects_format_after_empty_input(wbits):
    data = DATA[:1000]
    compressor = zlib.compressobj(wbits=wbits)
    compressed = compressor.compress(data) + compressor.flush()
    for module in (zlib, isal_zlib):
        decompressor = module.decompressobj(wbits=47)
        assert decompressor.decompress(b"") == b""
        assert decompressor.decompress(compressed[:1]) == b""
        assert decompressor.decompress(compressed[1:] + b"unused") == data
        assert decompressor.eof
        assert decompressor.unused_data == b"unused"


@pytest.mark.parametrize("wbits", [15, 31])
def test_decompressobj_detects_format_after_flush(wbits):
    data = DATA[:1000]
    compressor = zlib.compressobj(wbits=wbits)
    compressed = compressor.compress(data) + compressor.flush()
    for module in (zlib, isal_zlib):
        decompressor = module.decompressobj(wbits=47)
        assert decompressor.flush() == b""
        assert decompressor.decompress(compressed) == data
        assert decompressor.eof


@pytest.mark.parametrize("data", [b"", b"\x1f", b"\x78"])
def test_decompress_detect_format_incomplete(data):
    with pytest.raises(zlib.error):
        zlib.decompress(data, wbits=47)
    with pytest.raises(isal_zlib.error):
        isal_zlib.decompress(data, wbits=47)


@pytest.mark.parametrize("wbits", [-15, 15, 31])
def test_decompressobj_unconsumed_tail_after_eof(wbits):
    source = b"abcdefghijklmnopqrstuvwxyz"
    remainder = b"0123456789"
    compressor = zlib.compressobj(wbits=wbits)
    compressed = compressor.compress(source) + compressor.flush()
    decompressor = isal_zlib.decompressobj(wbits=wbits)
    data = decompressor.decompress(compressed + remainder, 1)
    data += decompressor.decompress(decompressor.unconsumed_tail)
    assert decompressor.eof
    assert data == source
    assert decompressor.unconsumed_tail == b""
    assert decompressor.unused_data == remainder


def test_zlib_dictionary_decompress():
    dictionary = b"bla"
    data = b"bladiebla"
    compobj = zlib.compressobj(zdict=dictionary)
    compressed = compobj.compress(data) + compobj.flush()
    decompobj = isal_zlib.decompressobj(zdict=dictionary)
    assert decompobj.decompress(compressed) == data


def test_isal_zlib_dictionary_decompress():
    dictionary = b"bla"
    data = b"bladiebla"
    compobj = isal_zlib.compressobj(zdict=dictionary)
    compressed = compobj.compress(data) + compobj.flush()
    decompobj = zlib.decompressobj(zdict=dictionary)
    assert decompobj.decompress(compressed) == data
