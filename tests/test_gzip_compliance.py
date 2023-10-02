# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

"""Test script for the igzip module.

Adapted from test_gzip.py in CPython's lib/test directory.
Python software license applies:
https://github.com/python/cpython/blob/master/LICENSE

Changes made:
- removed test.support specific functionally that is not distributed with the
  binary releases of python:
    - tempfile module was used to create the temporary files and dirs
    - replaced os_helper.unlink with os.unlink
    - replaced os_helper.rmtree with shutil.rmtree

"""

import array
import functools
import gzip
import io
import os
import pathlib
import shutil
import struct
import sys
import tempfile
import unittest
from subprocess import PIPE, Popen
from test.support import _4G, bigmemtest  # type: ignore
from test.support.script_helper import assert_python_failure, assert_python_ok  # type: ignore  # noqa: E501

from isal import igzip

data1 = b"""  int length=DEFAULTALLOC, err = Z_OK;
  PyObject *RetVal;
  int flushmode = Z_FINISH;
  unsigned long start_total_out;

"""

data2 = b"""/* zlibmodule.c -- igzip-compatible data compression */
/* See http://www.igzip.org/zlib/
/* See http://www.winimage.com/zLibDll for Windows */
"""

TEMPDIR = os.path.abspath(tempfile.mkdtemp(suffix='-gzdir'))


class UnseekableIO(io.BytesIO):
    def seekable(self):
        return False

    def tell(self):
        raise io.UnsupportedOperation

    def seek(self, *args):
        raise io.UnsupportedOperation


class BaseTest(unittest.TestCase):

    def __init__(self, methodName):
        fileno, self.filename = tempfile.mkstemp()
        os.close(fileno)
        super().__init__(methodName)

    def setUp(self):
        if os.path.exists(self.filename):
            os.unlink(self.filename)

    def tearDown(self):
        if os.path.exists(self.filename):
            os.unlink(self.filename)


class TestGzip(BaseTest):
    def write_and_read_back(self, data, mode='b'):
        b_data = bytes(data)
        with igzip.GzipFile(self.filename, 'w' + mode) as f:
            length = f.write(data)
        self.assertEqual(length, len(b_data))
        with igzip.GzipFile(self.filename, 'r' + mode) as f:
            self.assertEqual(f.read(), b_data)

    def test_write(self):
        with igzip.GzipFile(self.filename, 'wb') as f:
            f.write(data1 * 50)

            # Try flush and fileno.
            f.flush()
            f.fileno()
            if hasattr(os, 'fsync'):
                os.fsync(f.fileno())
            f.close()

        # Test multiple close() calls.
        f.close()

    def test_write_read_with_pathlike_file(self):
        filename = pathlib.Path(self.filename)
        with igzip.GzipFile(filename, 'w') as f:
            f.write(data1 * 50)
        self.assertIsInstance(f.name, str)
        with igzip.GzipFile(filename, 'a') as f:
            f.write(data1)
        with igzip.GzipFile(filename) as f:
            d = f.read()
        self.assertEqual(d, data1 * 51)
        self.assertIsInstance(f.name, str)

    # The following test_write_xy methods test that write accepts
    # the corresponding bytes-like object type as input
    # and that the data written equals bytes(xy) in all cases.
    def test_write_memoryview(self):
        self.write_and_read_back(memoryview(data1 * 50))
        m = memoryview(bytes(range(256)))
        data = m.cast('B', shape=[8, 8, 4])
        self.write_and_read_back(data)

    def test_write_bytearray(self):
        self.write_and_read_back(bytearray(data1 * 50))

    def test_write_array(self):
        self.write_and_read_back(array.array('I', data1 * 40))

    def test_write_incompatible_type(self):
        # Test that non-bytes-like types raise TypeError.
        # Issue #21560: attempts to write incompatible types
        # should not affect the state of the fileobject
        with igzip.GzipFile(self.filename, 'wb') as f:
            with self.assertRaises(TypeError):
                f.write('')
            with self.assertRaises(TypeError):
                f.write([])
            f.write(data1)
        with igzip.GzipFile(self.filename, 'rb') as f:
            self.assertEqual(f.read(), data1)

    def test_read(self):
        self.test_write()
        # Try reading.
        with igzip.GzipFile(self.filename, 'r') as f:
            d = f.read()
        self.assertEqual(d, data1 * 50)

    def test_read1(self):
        self.test_write()
        blocks = []
        nread = 0
        with igzip.GzipFile(self.filename, 'r') as f:
            while True:
                d = f.read1()
                if not d:
                    break
                blocks.append(d)
                nread += len(d)
                # Check that position was updated correctly (see issue10791).
                self.assertEqual(f.tell(), nread)
        self.assertEqual(b''.join(blocks), data1 * 50)

    @bigmemtest(size=_4G, memuse=1)
    def test_read_large(self, size):
        # Read chunk size over UINT_MAX should be supported, despite zlib's
        # limitation per low-level call
        compressed = igzip.compress(data1, compresslevel=1)
        f = igzip.GzipFile(fileobj=io.BytesIO(compressed), mode='rb')
        self.assertEqual(f.read(size), data1)

    def test_io_on_closed_object(self):
        # Test that I/O operations on closed GzipFile objects raise a
        # ValueError, just like the corresponding functions on file objects.

        # Write to a file, open it for reading, then close it.
        self.test_write()
        f = igzip.GzipFile(self.filename, 'r')
        fileobj = f.fileobj
        self.assertFalse(fileobj.closed)
        f.close()
        self.assertTrue(fileobj.closed)
        with self.assertRaises(ValueError):
            f.read(1)
        with self.assertRaises(ValueError):
            f.seek(0)
        with self.assertRaises(ValueError):
            f.tell()
        # Open the file for writing, then close it.
        f = igzip.GzipFile(self.filename, 'w')
        fileobj = f.fileobj
        self.assertFalse(fileobj.closed)
        f.close()
        self.assertTrue(fileobj.closed)
        with self.assertRaises(ValueError):
            f.write(b'')
        with self.assertRaises(ValueError):
            f.flush()

    def test_append(self):
        self.test_write()
        # Append to the previous file
        with igzip.GzipFile(self.filename, 'ab') as f:
            f.write(data2 * 15)

        with igzip.GzipFile(self.filename, 'rb') as f:
            d = f.read()
        self.assertEqual(d, (data1 * 50) + (data2 * 15))

    def test_many_append(self):
        # Bug #1074261 was triggered when reading a file that contained
        # many, many members.  Create such a file and verify that reading it
        # works.
        with igzip.GzipFile(self.filename, 'wb') as f:
            f.write(b'a')
        for i in range(0, 200):
            with igzip.GzipFile(self.filename, "ab") as f:  # append
                f.write(b'a')

        # Try reading the file
        with igzip.GzipFile(self.filename, "rb") as zgfile:
            contents = b""
            while 1:
                ztxt = zgfile.read(8192)
                contents += ztxt
                if not ztxt:
                    break
        self.assertEqual(contents, b'a' * 201)

    def test_exclusive_write(self):
        with igzip.GzipFile(self.filename, 'xb') as f:
            f.write(data1 * 50)
        with igzip.GzipFile(self.filename, 'rb') as f:
            self.assertEqual(f.read(), data1 * 50)
        with self.assertRaises(FileExistsError):
            igzip.GzipFile(self.filename, 'xb')

    def test_buffered_reader(self):
        # Issue #7471: a GzipFile can be wrapped in a BufferedReader for
        # performance.
        self.test_write()

        with igzip.GzipFile(self.filename, 'rb') as f:
            with io.BufferedReader(f) as r:
                lines = [line for line in r]

        self.assertEqual(lines, 50 * data1.splitlines(keepends=True))

    def test_readline(self):
        self.test_write()
        # Try .readline() with varying line lengths

        with igzip.GzipFile(self.filename, 'rb') as f:
            line_length = 0
            while 1:
                L = f.readline(line_length)
                if not L and line_length != 0:
                    break
                self.assertTrue(len(L) <= line_length)
                line_length = (line_length + 1) % 50

    def test_readlines(self):
        self.test_write()
        # Try .readlines()

        with igzip.GzipFile(self.filename, 'rb') as f:
            L = f.readlines()

        with igzip.GzipFile(self.filename, 'rb') as f:
            while 1:
                L = f.readlines(150)
                if L == []:
                    break

    def test_seek_read(self):
        self.test_write()
        # Try seek, read test

        with igzip.GzipFile(self.filename) as f:
            while 1:
                oldpos = f.tell()
                line1 = f.readline()
                if not line1:
                    break
                newpos = f.tell()
                f.seek(oldpos)  # negative seek
                if len(line1) > 10:
                    amount = 10
                else:
                    amount = len(line1)
                line2 = f.read(amount)
                self.assertEqual(line1[:amount], line2)
                f.seek(newpos)  # positive seek

    def test_seek_whence(self):
        self.test_write()
        # Try seek(whence=1), read test

        with igzip.GzipFile(self.filename) as f:
            f.read(10)
            f.seek(10, whence=1)
            y = f.read(10)
        self.assertEqual(y, data1[20:30])

    def test_seek_write(self):
        # Try seek, write test
        with igzip.GzipFile(self.filename, 'w') as f:
            for pos in range(0, 256, 16):
                f.seek(pos)
                f.write(b'GZ\n')

    def test_mode(self):
        self.test_write()
        with igzip.GzipFile(self.filename, 'r') as f:
            self.assertEqual(f.myfileobj.mode, 'rb')
        os.unlink(self.filename)
        with igzip.GzipFile(self.filename, 'x') as f:
            self.assertEqual(f.myfileobj.mode, 'xb')

    def test_1647484(self):
        for mode in ('wb', 'rb'):
            with igzip.GzipFile(self.filename, mode) as f:
                self.assertTrue(hasattr(f, "name"))
                self.assertEqual(f.name, self.filename)

    def test_paddedfile_getattr(self):
        self.test_write()
        with igzip.GzipFile(self.filename, 'rb') as f:
            self.assertTrue(hasattr(f.fileobj, "name"))
            self.assertEqual(f.fileobj.name, self.filename)

    def test_mtime(self):
        mtime = 123456789
        with igzip.GzipFile(self.filename, 'w', mtime=mtime) as fWrite:
            fWrite.write(data1)
        with igzip.GzipFile(self.filename) as fRead:
            self.assertTrue(hasattr(fRead, 'mtime'))
            self.assertIsNone(fRead.mtime)
            dataRead = fRead.read()
            self.assertEqual(dataRead, data1)
            self.assertEqual(fRead.mtime, mtime)

    def test_metadata(self):
        mtime = 123456789

        with igzip.GzipFile(self.filename, 'w', mtime=mtime) as fWrite:
            fWrite.write(data1)

        with open(self.filename, 'rb') as fRead:
            # see RFC 1952: http://www.faqs.org/rfcs/rfc1952.html

            idBytes = fRead.read(2)
            self.assertEqual(idBytes, b'\x1f\x8b')  # igzip ID

            cmByte = fRead.read(1)
            self.assertEqual(cmByte, b'\x08')  # deflate

            try:
                expectedname = os.path.basename(self.filename).encode(
                    'Latin-1') + b'\x00'
                expectedflags = b'\x08'  # only the FNAME flag is set
            except UnicodeEncodeError:
                expectedname = b''
                expectedflags = b'\x00'

            flagsByte = fRead.read(1)
            self.assertEqual(flagsByte, expectedflags)

            mtimeBytes = fRead.read(4)
            self.assertEqual(mtimeBytes,
                             struct.pack('<i', mtime))  # little-endian

            xflByte = fRead.read(1)
            if ("compresslevel" in
                    gzip.GzipFile._write_gzip_header.__code__.co_varnames):
                self.assertEqual(xflByte, b'\x00')  # fast compression
            else:
                self.assertEqual(xflByte, b'\x02')  # maximum compression
            osByte = fRead.read(1)
            self.assertEqual(osByte, b'\xff')  # OS "unknown" (OS-independent)

            # Since the FNAME flag is set, the zero-terminated filename
            # follows. RFC 1952 specifies that this is the name of the input
            # file, if any. However, the gzip module defaults to storing the
            # name of the output file in this field.
            nameBytes = fRead.read(len(expectedname))
            self.assertEqual(nameBytes, expectedname)

            # Since no other flags were set, the header ends here.
            # Rather than process the compressed data, let's seek to the
            # trailer.
            fRead.seek(os.stat(self.filename).st_size - 8)

            crc32Bytes = fRead.read(4)  # CRC32 of uncompressed data [data1]
            self.assertEqual(crc32Bytes, b'\xaf\xd7d\x83')

            isizeBytes = fRead.read(4)
            self.assertEqual(isizeBytes, struct.pack('<i', len(data1)))

    def test_metadata_ascii_name(self):
        fd, self.filename = tempfile.mkstemp()
        os.close(fd)
        self.test_metadata()

    def test_compresslevel_metadata(self):
        # see RFC 1952: http://www.faqs.org/rfcs/rfc1952.html
        # specifically, discussion of XFL in section 2.3.1
        cases = [
            ('fast', 0, b'\x04'),
            ('best', 3, b'\x00'),  # Smaller than fast, bigger than best gzip.
            ('tradeoff', 2, b'\x00'),  # therefore medium is appropriate.
            ('1', 1, b'\x00')
        ]
        xflOffset = 8

        for (name, level, expectedXflByte) in cases:
            major, minor, _, _, _ = sys.version_info
            if not ("compresslevel" in
                    gzip.GzipFile._write_gzip_header.__code__.co_varnames
                    and hasattr(gzip, "_COMPRESS_LEVEL_FAST")
                    and hasattr(gzip, "_COMPRESS_LEVEL_TRADEOFF")):
                # Specific xfl bytes introduced in 3.9 and backported to
                # earlier versions
                expectedXflByte = b'\x02'
            with self.subTest(name):
                fWrite = igzip.GzipFile(self.filename, 'w',
                                        compresslevel=level)
                with fWrite:
                    fWrite.write(data1)
                with open(self.filename, 'rb') as fRead:
                    fRead.seek(xflOffset)
                    xflByte = fRead.read(1)
                    self.assertEqual(xflByte, expectedXflByte)

    def test_with_open(self):
        # GzipFile supports the context management protocol
        with igzip.GzipFile(self.filename, "wb") as f:
            f.write(b"xxx")
        f = igzip.GzipFile(self.filename, "rb")
        f.close()
        try:
            with f:
                pass
        except ValueError:
            pass
        else:
            self.fail("__enter__ on a closed file didn't raise an exception")
        try:
            with igzip.GzipFile(self.filename, "wb") as f:
                1 / 0
        except ZeroDivisionError:
            pass
        else:
            self.fail("1/0 didn't raise an exception")

    def test_zero_padded_file(self):
        with igzip.GzipFile(self.filename, "wb") as f:
            f.write(data1 * 50)

        # Pad the file with zeroes
        with open(self.filename, "ab") as f:
            f.write(b"\x00" * 50)

        with igzip.GzipFile(self.filename, "rb") as f:
            d = f.read()
            self.assertEqual(d, data1 * 50, "Incorrect data in file")

    def test_igzip_BadGzipFile_exception(self):
        self.assertTrue(issubclass(igzip.BadGzipFile, OSError))

    def test_bad_gzip_file(self):
        major, minor, _, _, _ = sys.version_info
        with open(self.filename, 'wb') as file:
            file.write(data1 * 50)
        with igzip.GzipFile(self.filename, 'r') as file:
            self.assertRaises(igzip.BadGzipFile, file.readlines)

    def test_non_seekable_file(self):
        uncompressed = data1 * 50
        buf = UnseekableIO()
        with igzip.GzipFile(fileobj=buf, mode="wb") as f:
            f.write(uncompressed)
        compressed = buf.getvalue()
        buf = UnseekableIO(compressed)
        with igzip.GzipFile(fileobj=buf, mode="rb") as f:
            self.assertEqual(f.read(), uncompressed)

    def test_peek(self):
        uncompressed = data1 * 200
        with igzip.GzipFile(self.filename, "wb") as f:
            f.write(uncompressed)

        def sizes():
            while True:
                for n in range(5, 50, 10):
                    yield n

        with igzip.GzipFile(self.filename, "rb") as f:
            f.max_read_chunk = 33
            nread = 0
            for n in sizes():
                s = f.peek(n)
                if s == b'':
                    break
                self.assertEqual(f.read(len(s)), s)
                nread += len(s)
            self.assertEqual(f.read(100), b'')
            self.assertEqual(nread, len(uncompressed))

    def test_textio_readlines(self):
        # Issue #10791: TextIOWrapper.readlines() fails when wrapping GzipFile.
        lines = (data1 * 50).decode("ascii").splitlines(keepends=True)
        self.test_write()
        with igzip.GzipFile(self.filename, 'r') as f:
            with io.TextIOWrapper(f, encoding="ascii") as t:
                self.assertEqual(t.readlines(), lines)

    def test_fileobj_from_fdopen(self):
        # Issue #13781: Opening a GzipFile for writing fails when using a
        # fileobj created with os.fdopen().
        fd = os.open(self.filename, os.O_WRONLY | os.O_CREAT)
        with os.fdopen(fd, "wb") as f:
            with igzip.GzipFile(fileobj=f, mode="w"):
                pass

    def test_fileobj_mode(self):
        igzip.GzipFile(self.filename, "wb").close()
        with open(self.filename, "r+b") as f:
            with igzip.GzipFile(fileobj=f, mode='r') as g:
                self.assertEqual(g.mode, gzip.READ)
            with igzip.GzipFile(fileobj=f, mode='w') as g:
                self.assertEqual(g.mode, gzip.WRITE)
            with igzip.GzipFile(fileobj=f, mode='a') as g:
                self.assertEqual(g.mode, gzip.WRITE)
            with igzip.GzipFile(fileobj=f, mode='x') as g:
                self.assertEqual(g.mode, gzip.WRITE)
            with self.assertRaises(ValueError):
                igzip.GzipFile(fileobj=f, mode='z')
        for mode in "rb", "r+b":
            with open(self.filename, mode) as f:
                with igzip.GzipFile(fileobj=f) as g:
                    self.assertEqual(g.mode, gzip.READ)
        for mode in "wb", "ab", "xb":
            if "x" in mode:
                os.unlink(self.filename)
            with open(self.filename, mode) as f:
                major, minor, _, _, _ = sys.version_info
                if major == 3 and minor >= 9 or major > 3:
                    with self.assertWarns(FutureWarning):
                        g = igzip.GzipFile(fileobj=f)
                else:
                    g = igzip.GzipFile(fileobj=f)
                with g:
                    self.assertEqual(g.mode, gzip.WRITE)

    def test_bytes_filename(self):
        str_filename = self.filename
        try:
            bytes_filename = str_filename.encode("ascii")
        except UnicodeEncodeError:
            self.skipTest("Temporary file name needs to be ASCII")
        with igzip.GzipFile(bytes_filename, "wb") as f:
            f.write(data1 * 50)
        with igzip.GzipFile(bytes_filename, "rb") as f:
            self.assertEqual(f.read(), data1 * 50)
        # Sanity check that we are actually operating on the right file.
        with igzip.GzipFile(str_filename, "rb") as f:
            self.assertEqual(f.read(), data1 * 50)

    def test_decompress_limited(self):
        """Decompressed data buffering should be limited"""
        bomb_size = int(2e6)
        self.assertLess(igzip.READ_BUFFER_SIZE, bomb_size)
        bomb = gzip.compress(b'\0' * bomb_size, compresslevel=9)
        self.assertLess(len(bomb), igzip.READ_BUFFER_SIZE)

        bomb = io.BytesIO(bomb)
        decomp = igzip.GzipFile(fileobj=bomb)
        self.assertEqual(decomp.read(1), b'\0')
        max_decomp = 1 + igzip.READ_BUFFER_SIZE
        self.assertLessEqual(decomp._buffer.raw.tell(), max_decomp,
                             "Excessive amount of data was decompressed")

    # Testing compress/decompress shortcut functions

    def test_compress(self):
        for data in [data1, data2]:
            for args in [(), (1,), (2,), (3,), (0,)]:
                datac = igzip.compress(data, *args)
                self.assertEqual(type(datac), bytes)
                with igzip.GzipFile(fileobj=io.BytesIO(datac),  mode="rb"
                                    ) as f:
                    self.assertEqual(f.read(), data)

    def test_compress_mtime(self):
        mtime = 123456789
        for data in [data1, data2]:
            for args in [(), (0,), (1,), (2,), (3,)]:
                with self.subTest(data=data, args=args):
                    datac = igzip.compress(data, *args, mtime=mtime)
                    self.assertEqual(type(datac), bytes)
                    with igzip.GzipFile(fileobj=io.BytesIO(datac), mode="rb"
                                        ) as f:
                        f.read(1)  # to set mtime attribute
                        self.assertEqual(f.mtime, mtime)

    def test_decompress(self):
        for data in (data1, data2):
            buf = io.BytesIO()
            with igzip.GzipFile(fileobj=buf, mode="wb") as f:
                f.write(data)
            self.assertEqual(igzip.decompress(buf.getvalue()), data)
            # Roundtrip with compress
            datac = igzip.compress(data)
            self.assertEqual(igzip.decompress(datac), data)

    def test_read_truncated(self):
        data = data1 * 50
        # Drop the CRC (4 bytes) and file size (4 bytes).
        truncated = igzip.compress(data)[:-8]
        with igzip.GzipFile(fileobj=io.BytesIO(truncated)) as f:
            self.assertRaises(EOFError, f.read)
        with igzip.GzipFile(fileobj=io.BytesIO(truncated)) as f:
            self.assertRaises(EOFError, f.read, len(data))
        # Incomplete 10-byte header.
        for i in range(2, 10):
            with igzip.GzipFile(fileobj=io.BytesIO(truncated[:i])) as f:
                self.assertRaises(EOFError, f.read, 1)

    def test_read_with_extra(self):
        # Gzip data with an extra field
        gzdata = (b'\x1f\x8b\x08\x04\xb2\x17cQ\x02\xff'
                  b'\x05\x00Extra'
                  b'\x0bI-.\x01\x002\xd1Mx\x04\x00\x00\x00')
        with igzip.GzipFile(fileobj=io.BytesIO(gzdata)) as f:
            self.assertEqual(f.read(), b'Test')

    def test_public_consts(self):
        # Confirm that all of the gzip module public consts are
        # also accessible via igzip, for drop-in compatibility.
        self.assertEqual(gzip.FCOMMENT, igzip.FCOMMENT)
        self.assertEqual(gzip.FEXTRA, igzip.FEXTRA)
        self.assertEqual(gzip.FHCRC, igzip.FHCRC)
        self.assertEqual(gzip.FNAME, igzip.FNAME)
        self.assertEqual(gzip.FTEXT, igzip.FTEXT)
        self.assertEqual(gzip.READ, igzip.READ)
        self.assertEqual(gzip.WRITE, igzip.WRITE)


class TestOpen(BaseTest):
    def test_binary_modes(self):
        uncompressed = data1 * 50

        with igzip.open(self.filename, "wb") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed)

        with igzip.open(self.filename, "rb") as f:
            self.assertEqual(f.read(), uncompressed)

        with igzip.open(self.filename, "ab") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed * 2)

        with self.assertRaises(FileExistsError):
            igzip.open(self.filename, "xb")
        os.unlink(self.filename)
        with igzip.open(self.filename, "xb") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed)

    def test_pathlike_file(self):
        filename = pathlib.Path(self.filename)
        with igzip.open(filename, "wb") as f:
            f.write(data1 * 50)
        with igzip.open(filename, "ab") as f:
            f.write(data1)
        with igzip.open(filename) as f:
            self.assertEqual(f.read(), data1 * 51)

    def test_implicit_binary_modes(self):
        # Test implicit binary modes (no "b" or "t" in mode string).
        uncompressed = data1 * 50

        with igzip.open(self.filename, "w") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed)

        with igzip.open(self.filename, "r") as f:
            self.assertEqual(f.read(), uncompressed)

        with igzip.open(self.filename, "a") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed * 2)

        with self.assertRaises(FileExistsError):
            igzip.open(self.filename, "x")
        os.unlink(self.filename)
        with igzip.open(self.filename, "x") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read())
            self.assertEqual(file_data, uncompressed)

    def test_text_modes(self):
        uncompressed = data1.decode("ascii") * 50
        uncompressed_raw = uncompressed.replace("\n", os.linesep)
        with igzip.open(self.filename, "wt") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read()).decode("ascii")
            self.assertEqual(file_data, uncompressed_raw)
        with igzip.open(self.filename, "rt") as f:
            self.assertEqual(f.read(), uncompressed)
        with igzip.open(self.filename, "at") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read()).decode("ascii")
            self.assertEqual(file_data, uncompressed_raw * 2)

    def test_fileobj(self):
        uncompressed_bytes = data1 * 50
        uncompressed_str = uncompressed_bytes.decode("ascii")
        compressed = igzip.compress(uncompressed_bytes)
        with igzip.open(io.BytesIO(compressed), "r") as f:
            self.assertEqual(f.read(), uncompressed_bytes)
        with igzip.open(io.BytesIO(compressed), "rb") as f:
            self.assertEqual(f.read(), uncompressed_bytes)
        with igzip.open(io.BytesIO(compressed), "rt") as f:
            self.assertEqual(f.read(), uncompressed_str)

    def test_bad_params(self):
        # Test invalid parameter combinations.
        with self.assertRaises(TypeError):
            igzip.open(123.456)
        with self.assertRaises(ValueError):
            igzip.open(self.filename, "wbt")
        with self.assertRaises(ValueError):
            igzip.open(self.filename, "xbt")
        with self.assertRaises(ValueError):
            igzip.open(self.filename, "rb", encoding="utf-8")
        with self.assertRaises(ValueError):
            igzip.open(self.filename, "rb", errors="ignore")
        with self.assertRaises(ValueError):
            igzip.open(self.filename, "rb", newline="\n")

    def test_encoding(self):
        # Test non-default encoding.
        uncompressed = data1.decode("ascii") * 50
        uncompressed_raw = uncompressed.replace("\n", os.linesep)
        with igzip.open(self.filename, "wt", encoding="utf-16") as f:
            f.write(uncompressed)
        with open(self.filename, "rb") as f:
            file_data = igzip.decompress(f.read()).decode("utf-16")
            self.assertEqual(file_data, uncompressed_raw)
        with igzip.open(self.filename, "rt", encoding="utf-16") as f:
            self.assertEqual(f.read(), uncompressed)

    def test_encoding_error_handler(self):
        # Test with non-default encoding error handler.
        with igzip.open(self.filename, "wb") as f:
            f.write(b"foo\xffbar")
        with igzip.open(self.filename, "rt", encoding="ascii",
                        errors="ignore") as f:
            self.assertEqual(f.read(), "foobar")

    def test_newline(self):
        # Test with explicit newline (universal newline mode disabled).
        uncompressed = data1.decode("ascii") * 50
        with igzip.open(self.filename, "wt", newline="\n") as f:
            f.write(uncompressed)
        with igzip.open(self.filename, "rt", newline="\r") as f:
            self.assertEqual(f.readlines(), [uncompressed])


def create_and_remove_directory(directory):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            os.makedirs(directory, exist_ok=True)
            try:
                return function(*args, **kwargs)
            finally:
                shutil.rmtree(directory)

        return wrapper

    return decorator


class TestCommandLine(unittest.TestCase):
    data = b'This is a simple test with igzip'

    def test_decompress_stdin_stdout(self):
        with io.BytesIO() as bytes_io:
            with igzip.GzipFile(fileobj=bytes_io, mode='wb') as igzip_file:
                igzip_file.write(self.data)

            args = sys.executable, '-m', 'isal.igzip', '-d'
            with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
                out, err = proc.communicate(bytes_io.getvalue())

        self.assertEqual(err, b'')
        self.assertEqual(out, self.data)

    @create_and_remove_directory(TEMPDIR)
    def test_decompress_infile_outfile(self):
        igzipname = os.path.join(TEMPDIR, 'testigzip.gz')
        self.assertFalse(os.path.exists(igzipname))

        with igzip.open(igzipname, mode='wb') as fp:
            fp.write(self.data)
        sys.argv = ['', '-d', igzipname]
        igzip.main()

        with open(os.path.join(TEMPDIR, "testigzip"), "rb") as gunziped:
            self.assertEqual(gunziped.read(), self.data)

        self.assertTrue(os.path.exists(igzipname))

    def test_decompress_infile_outfile_error(self):
        rc, out, err = assert_python_failure('-m', 'isal.igzip', '-d',
                                             'thisisatest.out')
        self.assertEqual(b"filename doesn't end in .gz: 'thisisatest.out'. "
                         b"Cannot determine output filename.",
                         err.strip())
        self.assertEqual(rc, 1)
        self.assertEqual(out, b'')

    @create_and_remove_directory(TEMPDIR)
    def test_compress_stdin_outfile(self):
        args = sys.executable, '-m', 'isal.igzip'
        with Popen(args, stdin=PIPE, stdout=PIPE, stderr=PIPE) as proc:
            out, err = proc.communicate(self.data)

        self.assertEqual(err, b'')
        self.assertEqual(out[:2], b"\x1f\x8b")

    @create_and_remove_directory(TEMPDIR)
    def test_compress_infile_outfile_default(self):
        local_testigzip = os.path.join(TEMPDIR, 'testigzip')
        igzipname = local_testigzip + '.gz'
        self.assertFalse(os.path.exists(igzipname))

        with open(local_testigzip, 'wb') as fp:
            fp.write(self.data)

        rc, out, err = assert_python_ok('-m', 'isal.igzip', local_testigzip)

        self.assertTrue(os.path.exists(igzipname))
        self.assertEqual(out, b'')
        self.assertEqual(err, b'')

    @create_and_remove_directory(TEMPDIR)
    def test_compress_infile_outfile(self):
        for compress_level in ('--fast', '--best'):
            with self.subTest(compress_level=compress_level):
                local_testigzip = os.path.join(TEMPDIR, 'testigzip')
                igzipname = local_testigzip + '.gz'
                self.assertFalse(os.path.exists(igzipname))

                with open(local_testigzip, 'wb') as fp:
                    fp.write(self.data)

                rc, out, err = assert_python_ok('-m', 'isal.igzip',
                                                compress_level,
                                                local_testigzip)

                self.assertTrue(os.path.exists(igzipname))
                self.assertEqual(out, b'')
                self.assertEqual(err, b'')
                os.remove(igzipname)
                self.assertFalse(os.path.exists(igzipname))

    def test_compress_fast_best_are_exclusive(self):
        rc, out, err = assert_python_failure('-m', 'isal.igzip', '--fast',
                                             '--best')
        self.assertIn(
            b"error: argument -3/--best: not allowed with argument -0/--fast",
            err)
        self.assertEqual(out, b'')

    def test_decompress_cannot_have_flags_compression(self):
        rc, out, err = assert_python_failure('-m', 'isal.igzip', '--fast',
                                             '-d')
        self.assertIn(
            b'error: argument -d/--decompress: not allowed with argument '
            b'-0/--fast',
            err)
        self.assertEqual(out, b'')
