# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import gzip
import io
import itertools
import os
import tempfile
from pathlib import Path

from isal import igzip_threaded

import pytest

TEST_FILE = str((Path(__file__).parent / "data" / "test.fastq.gz"))


def test_threaded_read():
    with igzip_threaded.open(TEST_FILE, "rb") as thread_f:
        thread_data = thread_f.read()
    with gzip.open(TEST_FILE, "rb") as f:
        data = f.read()
    assert thread_data == data


@pytest.mark.parametrize(["mode", "threads"],
                         itertools.product(["wb", "wt"], [1, 3, -1]))
def test_threaded_write(mode, threads):
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        # Use a small block size to simulate many writes.
        with igzip_threaded.open(tmp, mode, threads=threads,
                                 block_size=8*1024) as out_file:
            gzip_open_mode = "rb" if "b" in mode else "rt"
            with gzip.open(TEST_FILE, gzip_open_mode) as in_file:
                while True:
                    block = in_file.read(128 * 1024)
                    if not block:
                        break
                    out_file.write(block)
    with gzip.open(TEST_FILE, "rt") as test_file:
        test_data = test_file.read()
    with gzip.open(tmp.name, "rt") as test_out:
        out_data = test_out.read()
    assert test_data == out_data


def test_threaded_open_no_threads():
    with tempfile.TemporaryFile("rb") as tmp:
        klass = igzip_threaded.open(tmp, "rb", threads=0)
        # igzip.IGzipFile inherits gzip.Gzipfile
        assert isinstance(klass, gzip.GzipFile)


def test_threaded_open_not_a_file_or_pathlike():
    i_am_a_tuple = (1, 2, 3)
    with pytest.raises(TypeError) as error:
        igzip_threaded.open(i_am_a_tuple)
    error.match("str")
    error.match("bytes")
    error.match("file")


# Test whether threaded readers and writers throw an error rather than hang
# indefinitely.

@pytest.mark.timeout(5)
def test_threaded_read_error():
    with open(TEST_FILE, "rb") as f:
        data = f.read()
    truncated_data = data[:-8]
    with igzip_threaded.open(io.BytesIO(truncated_data), "rb") as tr_f:
        with pytest.raises(EOFError):
            tr_f.read()


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_write_oversized_block_no_error(threads):
    # Random bytes are incompressible, and therefore are guaranteed to
    # trigger a buffer overflow when larger than block size unless handled
    # correctly.
    data = os.urandom(1024 * 63)  # not a multiple of block_size
    with tempfile.NamedTemporaryFile(mode="wb", delete=False) as tmp:
        with igzip_threaded.open(
                tmp, "wb", compresslevel=3, threads=threads,
                block_size=8 * 1024
        ) as writer:
            writer.write(data)
    with gzip.open(tmp.name, "rb") as gzipped:
        decompressed = gzipped.read()
    assert data == decompressed


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_write_error(threads):
    f = igzip_threaded._ThreadedGzipWriter(
        fp=io.BytesIO(), level=3,
        threads=threads, block_size=8 * 1024)
    # Bypass the write method which should not allow blocks larger than
    # block_size.
    f.input_queues[0].put((os.urandom(1024 * 64), b""))
    with pytest.raises(OverflowError) as error:
        f.close()
    error.match("Compressed output exceeds buffer size")


def test_close_reader():
    tmp = io.BytesIO(Path(TEST_FILE).read_bytes())
    f = igzip_threaded._ThreadedGzipReader(tmp, "rb")
    f.close()
    assert f.closed
    # Make sure double closing does not raise errors
    f.close()


@pytest.mark.parametrize("threads", [1, 3])
def test_close_writer(threads):
    f = igzip_threaded._ThreadedGzipWriter(
        io.BytesIO(), threads=threads)
    f.close()
    assert f.closed
    # Make sure double closing does not raise errors
    f.close()


def test_reader_not_writable():
    with igzip_threaded.open(TEST_FILE, "rb") as f:
        assert not f.writable()


def test_writer_not_readable():
    with igzip_threaded.open(io.BytesIO(), "wb") as f:
        assert not f.readable()


def test_writer_wrong_level():
    with pytest.raises(ValueError) as error:
        igzip_threaded._ThreadedGzipWriter(io.BytesIO(), level=42)
    error.match("Invalid compression level")
    error.match("42")


def test_writer_too_low_threads():
    with pytest.raises(ValueError) as error:
        igzip_threaded._ThreadedGzipWriter(io.BytesIO(), threads=0)
    error.match("threads")
    error.match("at least 1")


def test_reader_read_after_close():
    with open(TEST_FILE, "rb") as test_f:
        f = igzip_threaded._ThreadedGzipReader(test_f)
        f.close()
        with pytest.raises(ValueError) as error:
            f.read(1024)
        error.match("closed")


@pytest.mark.parametrize("threads", [1, 3])
def test_writer_write_after_close(threads):
    f = igzip_threaded._ThreadedGzipWriter(io.BytesIO(), threads=threads)
    f.close()
    with pytest.raises(ValueError) as error:
        f.write(b"abc")
    error.match("closed")
