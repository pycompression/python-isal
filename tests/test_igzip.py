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
import itertools
import os
import re
import struct
import subprocess
import sys
import tempfile
import textwrap
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


def test_repr(tmp_path):
    with igzip.IGzipFile(str(tmp_path / "test.gz"), "wb") as test:
        assert "<igzip _io.BufferedWriter name='" in repr(test)


@pytest.mark.parametrize("level", range(4))
def test_igzipfile_compresses_with_isal_zlib(level):
    # 30,000 bytes fit in the write buffer that GzipFile has on Python 3.12
    # and later (32 KiB or more), so IGzipFile compresses them with one
    # compress() call.
    with gzip.open(TEST_FILE, "rb") as f:
        data = f.read(30_000)
    buffer = io.BytesIO()
    with igzip.IGzipFile(fileobj=buffer, mode="wb", compresslevel=level,
                         mtime=0) as f:
        f.write(data)
    compressor = isal_zlib.compressobj(level, wbits=-isal_zlib.MAX_WBITS)
    expected = compressor.compress(data) + compressor.flush()
    # Leave out the 10-byte header and the 8-byte trailer.
    assert buffer.getvalue()[10:-8] == expected


def test_write_readonly_file():
    with igzip.IGzipFile(TEST_FILE, "rb") as test:
        with pytest.raises(OSError) as error:
            test.write(b"bla")
    error.match(r"write\(\) on read-only IGzipFile object")


def test_igzipfile_write_skips_check_not_closed_when_open(monkeypatch):
    calls = []
    check_not_closed = igzip.IGzipFile._check_not_closed
    monkeypatch.setattr(igzip.IGzipFile, "_check_not_closed",
                        lambda self: calls.append(1) or check_not_closed(self))
    output = io.BytesIO()
    igzip_file = igzip.IGzipFile(fileobj=output, mode="wb")
    for _ in range(100):
        assert igzip_file.write(b"a\n") == 2
    # Open files skip the check, which costs two Python calls per write
    assert calls == []
    igzip_file.close()
    assert gzip.decompress(output.getvalue()) == b"a\n" * 100
    with pytest.raises(ValueError, match="I/O operation on closed file"):
        igzip_file.write(b"a\n")
    assert calls == [1]


def test_igzip_reader_readall():
    data = io.BytesIO(COMPRESSED_DATA)
    test = igzip._IGzipReader(data)
    assert test.read(-1) == DATA


def test_igzip_reader_read_zero():
    data = io.BytesIO(COMPRESSED_DATA)
    test = igzip._IGzipReader(data)
    assert test.read(0) == b""


@pytest.mark.parametrize(["method", "args"], [
    ("read", ("x",)),
    ("read", (1, 2)),
    ("seek", ("x",)),
    ("seek", (0, "x")),
])
def test_igzip_reader_wrong_arguments(method, args):
    test = igzip._IGzipReader(io.BytesIO(COMPRESSED_DATA))
    with pytest.raises(TypeError):
        getattr(test, method)(*args)


def test_igzip_reader_readinto_read_only():
    test = igzip._IGzipReader(io.BytesIO(COMPRESSED_DATA))
    buffer = bytes(10)
    with pytest.raises(TypeError):
        test.readinto(buffer)
    assert buffer == bytes(10)


def test_igzipfile_read_truncated():
    # Chop of trailer (8 bytes) and part of DEFLATE stream
    data = io.BytesIO(COMPRESSED_DATA[:-10])
    test = igzip.GzipFile(fileobj=data, mode="rb")
    with pytest.raises(EOFError) as error:
        test.read()
    error.match("Compressed file ended before the end-of-stream marker was "
                "reached")


LINES_DATA = [
    b"",
    b"no newline",
    b"a\nb\n\nc",
    b"".join(b"line %d\n" % i for i in range(10_000)),
    b"x" * 200_000 + b"\n" + b"y" * 10,
]


@pytest.mark.parametrize("data", LINES_DATA,
                         ids=["empty", "no_newline", "blank_line",
                              "many_lines", "long_line"])
def test_igzipfile_iteration_like_gzipfile(data):
    compressed = gzip.compress(data)
    with gzip.GzipFile(fileobj=io.BytesIO(compressed)) as gzip_file:
        expected = list(gzip_file)
    with igzip.IGzipFile(fileobj=io.BytesIO(compressed)) as igzip_file:
        assert list(igzip_file) == expected
        igzip_file.seek(0)
        assert igzip_file.readlines() == expected
        igzip_file.seek(0)
        assert list(itertools.islice(igzip_file, 2)) == expected[:2]
        assert igzip_file.read() == b"".join(expected[2:])


def test_igzipfile_is_its_own_iterator():
    with igzip.IGzipFile(fileobj=io.BytesIO(COMPRESSED_DATA)) as igzip_file:
        assert iter(igzip_file) is igzip_file


def test_igzipfile_readline_skips_check_not_closed_when_open(monkeypatch):
    calls = []
    check_not_closed = igzip.IGzipFile._check_not_closed
    monkeypatch.setattr(igzip.IGzipFile, "_check_not_closed",
                        lambda self: calls.append(1) or check_not_closed(self))
    data = gzip.compress(b"a\nb\n" * 100)
    igzip_file = igzip.IGzipFile(fileobj=io.BytesIO(data))
    assert len(list(igzip_file)) == 200
    # Open files skip the check, which costs two Python calls per line
    assert calls == []
    igzip_file.close()
    with pytest.raises(ValueError, match="I/O operation on closed file"):
        igzip_file.readline()
    assert calls == [1]


def test_igzipfile_iteration_uses_replaced_methods(monkeypatch):
    class ReadlineSubclass(igzip.IGzipFile):
        def readline(self, size=-1):
            return super().readline(size).upper()

    class NextSubclass(igzip.IGzipFile):
        def __next__(self):
            return super().__next__().upper()

    compressed = gzip.compress(b"a\nb\n")
    for cls in (ReadlineSubclass, NextSubclass):
        with cls(fileobj=io.BytesIO(compressed)) as igzip_file:
            assert list(igzip_file) == [b"A\n", b"B\n"]
    with igzip.IGzipFile(fileobj=io.BytesIO(compressed)) as igzip_file:
        igzip_file.readline = lambda size=-1: b""
        assert list(igzip_file) == []
    monkeypatch.setattr(igzip.IGzipFile, "readline", lambda self, size=-1: b"")
    with igzip.IGzipFile(fileobj=io.BytesIO(compressed)) as igzip_file:
        assert list(igzip_file) == []


def test_igzipfile_iteration_after_close():
    igzip_file = igzip.IGzipFile(fileobj=io.BytesIO(gzip.compress(b"a\nb\n")))
    lines = iter(igzip_file)
    assert next(lines) == b"a\n"
    igzip_file.close()
    with pytest.raises(ValueError, match="I/O operation on closed file"):
        next(lines)
    with pytest.raises(ValueError, match="I/O operation on closed file"):
        iter(igzip_file)


def test_igzipfile_iteration_in_write_mode_like_gzipfile():
    errors = []
    for cls in (gzip.GzipFile, igzip.IGzipFile):
        with cls(fileobj=io.BytesIO(), mode="wb") as gzip_file:
            with pytest.raises(Exception) as error:
                next(iter(gzip_file))
            errors.append(type(error.value))
    assert errors[0] == errors[1]


@pytest.mark.parametrize("level", range(1, 10))
def test_decompress_stdin_stdout(monkeypatch, capsysbinary, level):
    """Test if the command line can decompress data that has been compressed
    by gzip at all levels."""
    mock_stdin = io.BytesIO(gzip.compress(DATA, level))
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(mock_stdin))
    monkeypatch.setattr(sys, "argv", ["", "-d"])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert out == DATA


@pytest.mark.parametrize("level", [str(x) for x in range(4)])
def test_compress_stdin_stdout(monkeypatch, capsysbinary, level):
    mock_stdin = io.BytesIO(DATA)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(mock_stdin))
    monkeypatch.setattr(sys, "argv", ["", f"-{level}"])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert gzip.decompress(out) == DATA
    # The XFL byte of the gzip header is 4 only at the fastest level.
    assert out[8] == (4 if level == "0" else 0)


def test_decompress_infile_outfile(monkeypatch, tmp_path, capsysbinary):
    test_file = tmp_path / "test"
    compressed_temp = test_file.with_suffix(".gz")
    compressed_temp.write_bytes(gzip.compress(DATA))
    monkeypatch.setattr(sys, "argv", ['', '-d', str(compressed_temp)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert err == b''
    assert out == b''
    assert test_file.exists()
    assert test_file.read_bytes() == DATA


def test_compress_infile_outfile(monkeypatch, tmp_path, capsysbinary):
    test_file = tmp_path / "test"
    test_file.write_bytes(DATA)
    monkeypatch.setattr(sys, "argv", ['', str(test_file)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    out_file = test_file.with_suffix(".gz")
    assert err == b''
    assert out == b''
    assert out_file.exists()
    assert gzip.decompress(out_file.read_bytes()) == DATA


def test_decompress_infile_outfile_error(monkeypatch, capsysbinary):
    monkeypatch.setattr(sys, "argv", ['', '-d', 'thisisatest.out'])
    with pytest.raises(SystemExit) as error:
        igzip.main()
    assert error.match("filename doesn't end")
    out, err = capsysbinary.readouterr()
    assert out == b''


def test_decompress_infile_stdout_noerror(monkeypatch, capsysbinary,
                                          tmp_path):
    test_file = tmp_path / "test"
    test_file.write_bytes(COMPRESSED_DATA)
    monkeypatch.setattr(sys, "argv", ['', '-cd', str(tmp_path / 'test')])
    igzip.main()
    result = capsysbinary.readouterr()
    assert DATA == result.out


def test_decompress_infile_stdout(monkeypatch, capsysbinary, tmp_path):
    test_gz = tmp_path / "test.gz"
    test_gz.write_bytes(gzip.compress(DATA))
    monkeypatch.setattr(sys, "argv", ['', '-cd', str(test_gz)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert out == DATA
    assert err == b''


def test_compress_infile_stdout(monkeypatch, capsysbinary, tmp_path):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    monkeypatch.setattr(sys, "argv", ['', '-c', str(test)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out) == DATA
    assert err == b''


def test_decompress_infile_out_file(monkeypatch, tmp_path, capsysbinary):
    test_gz = tmp_path / "test.gz"
    test_gz.write_bytes(gzip.compress(DATA))
    out_file = tmp_path / "out"
    monkeypatch.setattr(sys, "argv",
                        ['', '-d', '-o', str(out_file), str(test_gz)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert out_file.read_bytes() == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file(monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    args = ['-o', str(out_file), str(test)]
    monkeypatch.setattr(sys, "argv", ['', *args])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out_file.read_bytes()) == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file_force(monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    out_file.touch()
    args = ['-f', '-o', str(out_file), str(test)]
    monkeypatch.setattr(sys, "argv", ['', *args])
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert gzip.decompress(out_file.read_bytes()) == DATA
    assert err == b''
    assert out == b''


def test_compress_infile_out_file_prompt(monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    out_file.touch()
    monkeypatch.setattr(sys, "argv", ['', '-o', str(out_file), str(test)])
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO()))
    with pytest.raises(EOFError):
        # EOFError because the prompt gets no answer from the empty stdin.
        igzip.main()
    out, err = capsysbinary.readouterr()
    assert b"compressed.gz already exists; do you wish to overwrite (y/n)?" \
           in out


def test_compress_infile_out_file_inmplicit_name_prompt_refuse(
        monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "test.gz"
    out_file.touch()
    monkeypatch.setattr(sys, "argv", ['', str(test)])
    mock_stdin = io.BytesIO(b"n")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(mock_stdin))
    with pytest.raises(SystemExit) as error:
        igzip.main()
    error.match("not overwritten")
    out, err = capsysbinary.readouterr()
    assert b"test.gz already exists; do you wish to overwrite (y/n)?" \
           in out


def test_compress_infile_out_file_inmplicit_name_prompt_accept(
        monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "test.gz"
    out_file.touch()
    monkeypatch.setattr(sys, "argv", ['', str(test)])
    mock_stdin = io.BytesIO(b"y")
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(mock_stdin))
    igzip.main()
    out, err = capsysbinary.readouterr()
    assert b"already exists; do you wish to overwrite" in out
    assert err == b""
    assert gzip.decompress(out_file.read_bytes()) == DATA


def test_compress_infile_out_file_no_name(monkeypatch, tmp_path, capsysbinary):
    test = tmp_path / "test"
    test.write_bytes(DATA)
    out_file = tmp_path / "compressed.gz"
    monkeypatch.setattr(sys, "argv",
                        ['', '-n', '-o', str(out_file), str(test)])
    igzip.main()
    out, err = capsysbinary.readouterr()
    output = out_file.read_bytes()
    assert gzip.decompress(output) == DATA
    assert err == b''
    assert out == b''
    assert output[3] & gzip.FNAME == 0  # No filename set.
    assert output[4:8] == b"\x00\x00\x00\x00"  # No timestamp set.


def test_import_does_not_load_cli_modules():
    # Each of these modules takes milliseconds to import
    code = ("import sys; before = set(sys.modules); "
            "import isal.igzip, isal.igzip_threaded; "
            "print(*(set(sys.modules) - before))")
    result = subprocess.run([sys.executable, "-c", code], check=True,
                            capture_output=True, text=True)
    new_modules = set(result.stdout.split())
    assert "isal.igzip_threaded" in new_modules
    assert not new_modules & {"argparse", "shutil", "multiprocessing"}


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


@pytest.mark.skipif(sys.implementation.name != "cpython",
                    reason="Needs _testcapi.set_nomemory")
def test_decompress_not_a_gzip_no_memory():
    pytest.importorskip("_testcapi")
    # Fail each memory allocation in turn, such as the one for the bytes in
    # the error message. A subprocess keeps the failing allocations away from
    # the test runner. Each call raises MemoryError or BadGzipFile.
    code = textwrap.dedent("""
        import _testcapi
        from isal import igzip
        for start in range(50):
            _testcapi.set_nomemory(start, start + 1)
            try:
                igzip.decompress(b"This is not a gzip data stream.")
            except (MemoryError, igzip.BadGzipFile):
                pass
            finally:
                _testcapi.remove_mem_hooks()
    """)
    subprocess.run([sys.executable, "-c", code], check=True)


def test_decompress_unknown_compression_method():
    corrupted_data = COMPRESSED_DATA[:2] + b'\x09' + COMPRESSED_DATA[3:]
    with pytest.raises(igzip.BadGzipFile) as error:
        igzip.decompress(corrupted_data)
    assert error.match("Unknown compression method")


def test_decompress_empty():
    assert igzip.decompress(b"") == b""


@pytest.mark.parametrize("data", ["x", 1, None])
def test_decompress_not_bytes_like(data):
    with pytest.raises(TypeError) as error:
        igzip.decompress(data)
    error.match("a bytes-like object is required")


def test_decompress_not_contiguous():
    with pytest.raises(BufferError):
        igzip.decompress(memoryview(b"abcd")[::2])


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


@pytest.mark.parametrize("header", list(headers()))
def test_decompress_header(header):
    data = b"hello world" * 100
    compressed = (header + isal_zlib.compress(data, wbits=-15) +
                  struct.pack("<II", zlib.crc32(data), len(data)))
    assert gzip.decompress(compressed) == data
    assert igzip.decompress(compressed) == data
    with igzip.open(io.BytesIO(compressed), "rb") as gzip_file:
        assert gzip_file.read() == data


def test_seek_from_end_before_reading():
    # The size is not known before the end of the stream, so seek() has to
    # decompress all of the data first.
    data = b"X" * 100_000 + b"END"
    with igzip.open(io.BytesIO(gzip.compress(data)), "rb") as gzip_file:
        assert gzip_file.seek(-3, io.SEEK_END) == 100_000
        assert gzip_file.read() == b"END"


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
              (igzip.READ_BUFFER_SIZE - 11) * b"A" +
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


def test_seek(tmp_path):
    from io import SEEK_CUR, SEEK_END, SEEK_SET
    with open(tmp_path / "test.gz", "wb") as tmpfile:
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


def test_bgzip():
    bgzip_file = Path(__file__).parent / "data" / "test.fastq.bgzip.gz"
    gzip_file = Path(__file__).parent / "data" / "test.fastq.gz"
    with igzip.open(bgzip_file, "rb") as bgz:
        bgz_data = bgz.read()
    with igzip.open(gzip_file, "rb") as gz:
        gz_data = gz.read()
    assert bgz_data == gz_data


def test_adverserial_header():
    magic = b"\x1f\x8b"
    method = 8
    mtime = 0
    flags = FCOMMENT
    _os = 255
    xfl = 0
    header = struct.pack("<2sBBIBB", magic, method, flags, mtime, xfl, _os)
    comment = b"A" * 10 * 1024 * 1024 + b"\00"
    compressed = isal_zlib.compress(b"", wbits=-15)
    crc = isal_zlib.crc32(b"")
    length = 0
    trailer = struct.pack("<II", crc, length)
    adverserial = header + comment + compressed + trailer
    with tempfile.NamedTemporaryFile("wb", delete=False) as tmpfile:
        tmpfile.write(adverserial)
    try:
        with pytest.raises(OverflowError):
            with igzip.open(tmpfile.name, "rb") as gzip_file:
                gzip_file.read()
    finally:
        os.remove(tmpfile.name)


@pytest.mark.skipif(not igzip._GZIP_BUFFERS_WRITES,
                    reason="GzipFile buffers writes from Python 3.12 onwards")
def test_small_writes_are_compressed_in_large_chunks(monkeypatch):
    chunk_sizes = []
    write_raw = igzip.IGzipFile._write_raw

    def recording_write_raw(self, data):
        chunk_sizes.append(memoryview(data).nbytes)
        return write_raw(self, data)

    monkeypatch.setattr(igzip.IGzipFile, "_write_raw", recording_write_raw)
    lines = [b"line %d\n" % i for i in range(10_000)]
    output = io.BytesIO()
    with igzip.IGzipFile(fileobj=output, mode="wb") as gzip_file:
        for line in lines:
            assert gzip_file.write(line) == len(line)
    data = b"".join(lines)
    assert sum(chunk_sizes) == len(data)
    # Each compressor call has overhead, so small writes must be combined
    assert len(chunk_sizes) < len(lines) // 100
    assert gzip.decompress(output.getvalue()) == data


def test_seek_in_write_mode_returns_new_position():
    output = io.BytesIO()
    with igzip.IGzipFile(fileobj=output, mode="wb") as gzip_file:
        gzip_file.write(b"abc")
        assert gzip_file.seek(10) == 10
        assert gzip_file.seek(5, io.SEEK_CUR) == 15
        assert gzip_file.tell() == 15
    assert gzip.decompress(output.getvalue()) == b"abc" + bytes(12)


def test_small_writes_tell_and_flush():
    output = io.BytesIO()
    with igzip.IGzipFile(fileobj=output, mode="wb") as gzip_file:
        assert gzip_file.write(b"ab") == 2
        assert gzip_file.tell() == 2
        assert gzip_file.write(bytearray(b"cd")) == 2
        assert gzip_file.write(memoryview(b"ef")) == 2
        assert gzip_file.tell() == 6
        gzip_file.flush()
        # A flush emits all data written so far
        decompressor = zlib.decompressobj(wbits=31)
        assert decompressor.decompress(output.getvalue()) == b"abcdef"
        gzip_file.write(b"gh")
    assert gzip.decompress(output.getvalue()) == b"abcdefgh"
