# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import gzip
import io
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


def test_threaded_error():
    with open(TEST_FILE, "rb") as f:
        data = f.read()
    truncated_data = data[:-8]
    with igzip_threaded.open(io.BytesIO(truncated_data), "rb") as tr_f:
        with pytest.raises(EOFError):
            tr_f.read()
