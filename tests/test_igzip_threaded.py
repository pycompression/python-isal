# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import gzip
import io
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


@pytest.mark.parametrize("mode", ["wb", "wt"])
def test_threaded_write(mode):
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmp:
        with igzip_threaded.open(tmp, mode, threads=-1) as out_file:
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
def test_threaded_write_error(monkeypatch):
    tmp = tempfile.mktemp()
    # Compressobj method is called in a worker thread.
    monkeypatch.delattr(igzip_threaded.isal_zlib, "compressobj")
    with pytest.raises(AttributeError) as error:
        with igzip_threaded.open(tmp, "wb", compresslevel=3) as writer:
            writer.write(b"x")
    error.match("no attribute 'compressobj'")
