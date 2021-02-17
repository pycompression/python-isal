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

import gzip
import io
import sys

from isal import igzip

import pytest

DATA = b'This is a simple test with igzip'
COMPRESSED_DATA = gzip.compress(DATA)


@pytest.mark.parametrize("level", range(1, 10))
def test_decompress_stdin_stdout(capsysbinary, level):
    """Test if the command line can decompress data that has been compressed
    by gzip at all levels."""
    mock_stdin = io.BytesIO(gzip.compress(DATA, level))
    sys.stdin = io.TextIOWrapper(mock_stdin)
    sys.argv = ["", "-d"]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert out == DATA


@pytest.mark.parametrize("level", [str(x) for x in range(4)])
def test_compress_stdin_stdout(capsysbinary, level):
    mock_stdin = io.BytesIO(DATA)
    sys.stdin = io.TextIOWrapper(mock_stdin)
    sys.argv = ["", f"-{level}"]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out) == DATA


def test_decompress_infile_outfile(tmp_path):
    test_file = tmp_path / "test"
    compressed_temp = test_file.with_suffix(".gz")
    compressed_temp.write_bytes(gzip.compress(DATA))
    sys.argv = ['', '-d', str(compressed_temp)]
    igzip.main()
    assert test_file.read_bytes() == DATA


def test_compress_infile_outfile(tmp_path):
    test_file = tmp_path / "test"
    test_file.write_bytes(DATA)
    sys.argv = ['', str(test_file)]
    igzip.main()
    assert gzip.decompress(test_file.with_suffix(".gz").read_bytes()) == DATA
