# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

"""Tests for igzip that are not tested with the gzip_compliance tests taken
 from CPython. Uses pytest which is easier to work with. Meant to complement
 the gzip module compliance tests. It should improve coverage as well."""

import gzip
import io
import os
import re
import shutil
import struct
import sys
import tempfile
import zlib
from gzip import FCOMMENT, FEXTRA, FHCRC, FNAME, FTEXT  # type: ignore
from pathlib import Path

from isal import igzip, isal_zlib

import pytest

DATA = b'This is a simple test with igzip'
COMPRESSED_DATA = gzip.compress(DATA)
TEST_FILE = str((Path(__file__).parent / "data" / "test.fastq.gz"))


def test_wrong_compresslevel_igzipfile():
    with pytest.raises(ValueError) as error:
        igzip.IGzipFile("test.gz", mode="wb", compresslevel=6)
    error.match("Compression level should be between 0 and 3")


def test_repr():
    tempdir = tempfile.mkdtemp()
    with igzip.IGzipFile(os.path.join(tempdir, "test.gz"), "wb") as test:
        assert "<igzip _io.BufferedWriter name='" in repr(test)
    shutil.rmtree(tempdir)


def test_write_readonly_file():
    with igzip.IGzipFile(TEST_FILE, "rb") as test:
        with pytest.raises(OSError) as error:
            test.write(b"bla")
    error.match(r"write\(\) on read-only IGzipFile object")


def test_igzip_reader_readall():
    data = io.BytesIO(COMPRESSED_DATA)
    test = igzip._IGzipReader(data)
    assert test.read(-1) == DATA


def test_igzip_reader_read_zero():
    data = io.BytesIO(COMPRESSED_DATA)
    test = igzip._IGzipReader(data)
    assert test.read(0) == b""


def test_igzipfile_read_truncated():
    # Chop of trailer (8 bytes) and part of DEFLATE stream
    data = io.BytesIO(COMPRESSED_DATA[:-10])
    test = igzip.GzipFile(fileobj=data, mode="rb")
    with pytest.raises(EOFError) as error:
        test.read()
    error.match("Compressed file ended before the end-of-stream marker was "
                "reached")


@pytest.mark.parametrize("level", range(1, 10))
def test_decompress_stdin_stdout(capsysbinary, level):
    """Test if the command line can decompress data that has been compressed
    by gzip at all levels."""
    mock_stdin = io.BytesIO(gzip.compress(DATA, level))
    sys.stdin = io.TextIOWrapper(mock_stdin)
    sys.argv = ["", "-d"]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert out == DATA


@pytest.mark.parametrize("level", [str(x) for x in range(4)])
def test_compress_stdin_stdout(capsysbinary, level):
    mock_stdin = io.BytesIO(DATA)
    sys.stdin = io.TextIOWrapper(mock_stdin)
    sys.argv = ["", f"-{level}"]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert gzip.decompress(out) == DATA


def test_decompress_infile_outfile(tmp_path, capsysbinary):
    test_file = tmp_path / "test"
    compressed_temp = test_file.with_suffix(".gz")
    compressed_temp.write_bytes(gzip.compress(DATA))
    sys.argv = ['', '-d', str(compressed_temp)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert out == b''
    assert test_file.exists()
    assert test_file.read_bytes() == DATA


def test_compress_infile_outfile(tmp_path, capsysbinary):
    test_file = tmp_path / "test"
    test_file.write_bytes(DATA)
    sys.argv = ['', str(test_file)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    out_file = test_file.with_suffix(".gz")
    assert err == b''
    assert out == b''
    assert out_file.exists()
    assert gzip.decompress(out_file.read_bytes()) == DATA


def test_decompress_infile_outfile_error(capsysbinary):
    sys.argv = ['', '-d', 'thisisatest.out']
    with pytest.raises(SystemExit) as error:
        igzip.main()
    assert error.match("filename doesn't end")
    out, err = capsysbinary.readouterr()
    assert out == b''


def test_decompress_infile_stdout_noerror(capsysbinary, tmp_path):
    test_file = tmp_path / "test"
    test_file.write_bytes(COMPRESSED_DATA)
    sys.argv = ['', '-cd', str(tmp_path / 'test')]
    igzip.main()
    result = capsysbinary.readouterr()
    assert DATA == result.out


def test_decompress_infile_stdout(capsysbinary, tmp_path):
    test_gz = tmp_path / "test.gz"
    test_gz.write_bytes(gzip.compress(DATA))
    sys.argv = ['', '-cd', str(test_gz)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert out == DATA
    assert err == b''


def test_compress_infile_stdout(capsysbinary, tmp_path):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    sys.argv = ['', '-c', str(test)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out) == DATA
    assert err == b''


def test_decompress_infile_out_file(tmp_path, capsysbinary):
    test_gz = tmp_path / "test.gz"
    test_gz.write_bytes(gzip.compress(DATA))
    out_file = tmp_path / "out"
    sys.argv = ['', '-d', '-o', str(out_file), str(test_gz)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert out_file.read_bytes() == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file(tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    args = ['-o', str(out_file), str(test)]
    sys.argv = ['', *args]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out_file.read_bytes()) == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file_force(tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    out_file.touch()
    args = ['-f', '-o', str(out_file), str(test)]
    sys.argv = ['', *args]
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out_file.read_bytes()) == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file_prompt(tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    out_file.touch()
    sys.argv = ['', '-o', str(out_file), str(test)]
    with pytest.raises(EOFError):
        # EOFError because prompt cannot be answered non-interactively.
        igzip.main()
    out, err = capsysbinary.readouterr()
    assert b"compressed.gz already exists; do you wish to overwrite (y/n)?" \
           in out


def test_compress_infile_out_file_inmplicit_name_prompt_refuse(
        tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "test.gz"
    out_file.touch()
    sys.argv = ['', str(test)]
    mock_stdin = io.BytesIO(b"n")
    sys.stdin = io.TextIOWrapper(mock_stdin)
    with pytest.raises(SystemExit) as error:
        igzip.main()
    error.match("not overwritten")
    out, err = capsysbinary.readouterr()
    assert b"test.gz already exists; do you wish to overwrite (y/n)?" \
           in out


def test_compress_infile_out_file_inmplicit_name_prompt_accept(
        tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "test.gz"
    out_file.touch()
    sys.argv = ['', str(test)]
    mock_stdin = io.BytesIO(b"y")
    sys.stdin = io.TextIOWrapper(mock_stdin)
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert b"already exists; do you wish to overwrite" in out
    assert err == b""
    assert gzip.decompress(out_file.read_bytes()) == DATA


def test_compress_infile_out_file_no_name(tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    sys.argv = ['', '-n', '-o', str(out_file), str(test)]
    igzip.main()
    out, err = capsysbinary.readouterr()
    output = out_file.read_bytes()
    assert gzip.decompress(output) == DATA
    assert err == b''
    assert out == b''
    assert output[4] & gzip.FNAME == 0  # No filename set.
    assert output[4:8] == b"\x00\x00\x00\x00"  # No timestamp set.


def test_decompress():
    assert igzip.decompress(COMPRESSED_DATA) == DATA


def test_decompress_concatenated():
    assert igzip.decompress(COMPRESSED_DATA + COMPRESSED_DATA) == DATA + DATA


def test_decompress_concatenated_with_nulls():
    data = COMPRESSED_DATA + b"\x00\00\x00" + COMPRESSED_DATA
    assert igzip.decompress(data) == DATA + DATA


def test_decompress_missing_trailer():
    with pytest.raises(EOFError) as error:
        igzip.decompress(COMPRESSED_DATA[:-8])
    error.match("Compressed file ended before the end-of-stream marker was "
                "reached")


def test_decompress_truncated_trailer():
    with pytest.raises(EOFError) as error:
        igzip.decompress(COMPRESSED_DATA[:-4])
    error.match("Compressed file ended before the end-of-stream marker was "
                "reached")


def test_decompress_incorrect_length():
    fake_length = 27890
    # Assure our test is not bogus
    assert fake_length != len(DATA)
    incorrect_length_trailer = fake_length.to_bytes(4, "little", signed=False)
    corrupted_data = COMPRESSED_DATA[:-4] + incorrect_length_trailer
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(corrupted_data)
    error.match("Incorrect length of data produced")


def test_decompress_incorrect_checksum():
    # Create a wrong checksum by using a non-default seed.
    wrong_checksum = zlib.crc32(DATA, 50)
    wrong_crc_bytes = wrong_checksum.to_bytes(4, "little", signed=False)
    corrupted_data = (COMPRESSED_DATA[:-8] +
                      wrong_crc_bytes +
                      COMPRESSED_DATA[-4:])
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(corrupted_data)
    error.match("CRC check failed")


def test_decompress_not_a_gzip():
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(b"This is not a gzip data stream.")
    assert error.match(re.escape("Not a gzipped file (b'Th')"))


def test_decompress_unknown_compression_method():
    corrupted_data = COMPRESSED_DATA[:2] + b'\x09' + COMPRESSED_DATA[3:]
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(corrupted_data)
    assert error.match("Unknown compression method")


def test_decompress_empty():
    assert igzip.decompress(b"") == b""


def headers():
    magic = b"\x1f\x8b"
    method = b"\x08"
    mtime = b"\x00\x00\x00\x00"
    xfl = b"\x00"
    os = b"\xff"
    common_hdr_start = magic + method
    common_hdr_end = mtime + xfl + os
    xtra = b"METADATA"
    xlen = len(xtra)
    fname = b"my_data.tar"
    fcomment = b"I wrote this header with my bare hands"
    yield (common_hdr_start + FEXTRA.to_bytes(1, "little") +
           common_hdr_end + xlen.to_bytes(2, "little") + xtra)
    yield (common_hdr_start + FNAME.to_bytes(1, "little") +
           common_hdr_end + fname + b"\x00")
    yield (common_hdr_start + FCOMMENT.to_bytes(1, "little") +
           common_hdr_end + fcomment + b"\x00")
    flag = FHCRC.to_bytes(1, "little")
    header = common_hdr_start + flag + common_hdr_end
    crc = zlib.crc32(header) & 0xFFFF
    yield header + crc.to_bytes(2, "little")
    flag_bits = FTEXT | FEXTRA | FNAME | FCOMMENT | FHCRC
    flag = flag_bits.to_bytes(1, "little")
    header = (common_hdr_start + flag + common_hdr_end +
              xlen.to_bytes(2, "little") + xtra + fname + b"\x00" +
              fcomment + b"\x00")
    crc = zlib.crc32(header) & 0xFFFF
    yield header + crc.to_bytes(2, "little")


def test_header_too_short():
    with pytest.raises(igzip.BadGzipFile):
        gzip.decompress(b"00")


def test_header_corrupt():
    header = (b"\x1f\x8b\x08\x1f\x00\x00\x00\x00\x00\xff"  # All flags set
              b"\x05\x00"  # Xlen = 5
              b"extra"
              b"name\x00"
              b"comment\x00")
    # Create corrupt checksum by using wrong seed.
    crc = zlib.crc32(header, 50) & 0xFFFF
    true_crc = zlib.crc32(header) & 0xFFFF
    header += struct.pack("<H", crc)

    data = isal_zlib.compress(b"", wbits=-15)
    trailer = b"\x00" * 8
    compressed = header + data + trailer
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(compressed)
    error.match(f"Corrupted gzip header. "
                f"Checksums do not match: {true_crc:04x} != {crc:04x}")


TRUNCATED_HEADERS = [
    b"\x1f\x8b\x08\x00\x00\x00\x00\x00\x00",  # Missing OS byte
    b"\x1f\x8b\x08\x02\x00\x00\x00\x00\x00\xff",  # FHRC, but no checksum
    b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff",  # FEXTRA, but no xlen
    b"\x1f\x8b\x08\x04\x00\x00\x00\x00\x00\xff\xaa\x00",  # FEXTRA, xlen, but no data # noqa: E501
    b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x00\xff",  # FNAME but no fname
    b"\x1f\x8b\x08\x10\x00\x00\x00\x00\x00\xff",  # FCOMMENT, but no fcomment
]


@pytest.mark.parametrize("trunc", TRUNCATED_HEADERS)
def test_truncated_header(trunc):
    with pytest.raises(EOFError):
        igzip.decompress(trunc)


def test_very_long_header_in_data():
    # header with a very long filename.
    header = (b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x00\xff" + 256 * 1024 * b"A" +
              b"\x00")
    compressed = header + isal_zlib.compress(b"", 3, -15) + 8 * b"\00"
    assert igzip.decompress(compressed) == b""


def test_very_long_header_in_file():
    # header with a very long filename.
    header = (b"\x1f\x8b\x08\x08\x00\x00\x00\x00\x00\xff" +
              igzip.READ_BUFFER_SIZE * 2 * b"A" +
              b"\x00")
    compressed = header + isal_zlib.compress(b"", 3, -15) + 8 * b"\00"
    f = io.BytesIO(compressed)
    with igzip.open(f) as gzip_file:
        assert gzip_file.read() == b""


def test_concatenated_gzip():
    concat = Path(__file__).parent / "data" / "concatenated.fastq.gz"
    data = gzip.decompress(concat.read_bytes())
    with igzip.open(concat, "rb") as igzip_h:
        result = igzip_h.read()
    assert data == result


def test_seek():
    from io import SEEK_CUR, SEEK_END, SEEK_SET
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmpfile:
        tmpfile.write(gzip.compress(b"X" * 500 + b"A" + b"X" * 499))
        tmpfile.write(gzip.compress(b"X" * 500 + b"B" + b"X" * 499))
        tmpfile.write(gzip.compress(b"X" * 500 + b"C" + b"X" * 499))
        tmpfile.write(gzip.compress(b"X" * 500 + b"D" + b"X" * 499))
    with igzip.open(tmpfile.name, "rb") as gzip_file:
        # Start testing forward seek
        gzip_file.seek(500)
        assert gzip_file.read(1) == b"A"
        gzip_file.seek(1500)
        assert gzip_file.read(1) == b"B"
        # Test reverse
        gzip_file.seek(500)
        assert gzip_file.read(1) == b"A"
        # Again, but with explicit SEEK_SET
        gzip_file.seek(500, SEEK_SET)
        assert gzip_file.read(1) == b"A"
        gzip_file.seek(1500, SEEK_SET)
        assert gzip_file.read(1) == b"B"
        gzip_file.seek(500, SEEK_SET)
        assert gzip_file.read(1) == b"A"
        # Seeking from current position
        gzip_file.seek(500)
        gzip_file.seek(2000, SEEK_CUR)
        assert gzip_file.read(1) == b"C"
        gzip_file.seek(-1001, SEEK_CUR)
        assert gzip_file.read(1) == b"B"
        # Seeking from end
        # Any positive number should end up at the end
        gzip_file.seek(200, SEEK_END)
        assert gzip_file.read(1) == b""
        gzip_file.seek(-1500, SEEK_END)
        assert gzip_file.read(1) == b"C"
    os.remove(tmpfile.name)


def test_bgzip():
    bgzip_file = Path(__file__).parent / "data" / "test.fastq.bgzip.gz"
    gzip_file = Path(__file__).parent / "data" / "test.fastq.gz"
    with igzip.open(bgzip_file, "rb") as bgz:
        bgz_data = bgz.read()
    with igzip.open(gzip_file, "rb") as gz:
        gz_data = gz.read()
    assert bgz_data == gz_data
