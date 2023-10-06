# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

"""Test script for the isal_zlib module.

Adapted from test_zlib.py in CPython's lib/test directory.
Python software license applies:
https://github.com/python/cpython/blob/master/LICENSE

Changes made:
- Change all instances of zlib with isal_zlib
- Isal_zlib raises a ValueError when an incompatible compression level is used.
  Test is changed accordingly.

"""
import binascii
import copy
import functools
import os
import pickle
import random
import sys
import unittest
from test import support  # type: ignore
from test.support import _1G, _4G, bigmemtest  # type: ignore

import isal
from isal import isal_zlib

requires_Compress_copy = unittest.skipUnless(
    hasattr(isal_zlib.compressobj(), "copy"),
    'requires Compress.copy()')
requires_Decompress_copy = unittest.skipUnless(
    hasattr(isal_zlib.decompressobj(), "copy"),
    'requires Decompress.copy()')


class VersionTestCase(unittest.TestCase):

    @unittest.skipIf(os.getenv("PYTHON_ISAL_LINK_DYNAMIC") is not None and
                     sys.platform.startswith("win"),
                     "Header file missing on windows")
    def test_library_version(self):
        # Test that the major version of the actual library in use matches the
        # major version that we were compiled against. We can't guarantee that
        # the minor versions will match (even on the machine on which the
        # module was compiled), and the API is stable between minor versions,
        # so testing only the major versions avoids spurious failures.
        self.assertEqual(isal.ISAL_MAJOR_VERSION, 2)


class ChecksumTestCase(unittest.TestCase):
    # checksum test cases
    def test_crc32start(self):
        self.assertEqual(isal_zlib.crc32(b""), isal_zlib.crc32(b"", 0))
        self.assertTrue(isal_zlib.crc32(b"abc", 0xffffffff))

    def test_crc32empty(self):
        self.assertEqual(isal_zlib.crc32(b"", 0), 0)
        self.assertEqual(isal_zlib.crc32(b"", 1), 1)
        self.assertEqual(isal_zlib.crc32(b"", 432), 432)

    def test_adler32start(self):
        self.assertEqual(isal_zlib.adler32(b""), isal_zlib.adler32(b"", 1))
        self.assertTrue(isal_zlib.adler32(b"abc", 0xffffffff))

    def test_adler32empty(self):
        self.assertEqual(isal_zlib.adler32(b"", 0), 0)
        self.assertEqual(isal_zlib.adler32(b"", 1), 1)
        self.assertEqual(isal_zlib.adler32(b"", 432), 432)

    def test_penguins(self):
        self.assertEqual(isal_zlib.crc32(b"penguin", 0), 0x0e5c1a120)
        self.assertEqual(isal_zlib.crc32(b"penguin", 1), 0x43b6aa94)
        self.assertEqual(isal_zlib.adler32(b"penguin", 0), 0x0bcf02f6)
        self.assertEqual(isal_zlib.adler32(b"penguin", 1), 0x0bd602f7)

        self.assertEqual(isal_zlib.crc32(b"penguin"),
                         isal_zlib.crc32(b"penguin", 0))
        self.assertEqual(isal_zlib.adler32(b"penguin"),
                         isal_zlib.adler32(b"penguin", 1))

    def test_crc32_adler32_unsigned(self):
        foo = b'abcdefghijklmnop'
        # explicitly test signed behavior
        self.assertEqual(isal_zlib.crc32(foo), 2486878355)
        self.assertEqual(isal_zlib.crc32(b'spam'), 1138425661)
        self.assertEqual(isal_zlib.adler32(foo + foo), 3573550353)
        self.assertEqual(isal_zlib.adler32(b'spam'), 72286642)

    def test_crc32_combine(self):
        foo = b'abcdefghijklmnop'
        self.assertEqual(isal_zlib.crc32_combine(0, 0, 0), 0)
        self.assertEqual(isal_zlib.crc32_combine(1, 0, 0), 1)
        self.assertEqual(isal_zlib.crc32_combine(432, 0, 0), 432)
        self.assertEqual(
            isal_zlib.crc32_combine(
                isal_zlib.crc32(foo), isal_zlib.crc32(foo), len(foo)),
            isal_zlib.crc32(foo + foo)
        )

    def test_same_as_binascii_crc32(self):
        foo = b'abcdefghijklmnop'
        crc = 2486878355
        self.assertEqual(binascii.crc32(foo), crc)
        self.assertEqual(isal_zlib.crc32(foo), crc)
        self.assertEqual(binascii.crc32(b'spam'), isal_zlib.crc32(b'spam'))


# Issue #10276 - check that inputs >=4 GiB are handled correctly.
class ChecksumBigBufferTestCase(unittest.TestCase):

    @bigmemtest(size=_4G + 4, memuse=1, dry_run=False)
    def test_big_buffer(self, size):
        data = b"nyan" * (_1G + 1)
        self.assertEqual(isal_zlib.crc32(data), 1044521549)
        self.assertEqual(isal_zlib.adler32(data), 2256789997)


class ExceptionTestCase(unittest.TestCase):
    # make sure we generate some expected errors
    def test_badlevel(self):
        # specifying compression level out of range causes an error
        # (but -1 is Z_DEFAULT_COMPRESSION and apparently the isal_zlib
        # accepts 0 too)
        self.assertRaises(isal_zlib.error, isal_zlib.compress, b'ERROR', 10)

    def test_badargs(self):
        self.assertRaises(TypeError, isal_zlib.adler32)
        self.assertRaises(TypeError, isal_zlib.crc32)
        self.assertRaises(TypeError, isal_zlib.compress)
        self.assertRaises(TypeError, isal_zlib.decompress)
        for arg in (42, None, '', 'abc', (), []):
            self.assertRaises(TypeError, isal_zlib.adler32, arg)
            self.assertRaises(TypeError, isal_zlib.crc32, arg)
            self.assertRaises(TypeError, isal_zlib.compress, arg)
            self.assertRaises(TypeError, isal_zlib.decompress, arg)

    def test_badcompressobj(self):
        # verify failure on building compress object with bad params
        self.assertRaises(ValueError, isal_zlib.compressobj, 1,
                          isal_zlib.DEFLATED, 0)
        # specifying total bits too large causes an error
        self.assertRaises(ValueError,
                          isal_zlib.compressobj, 1, isal_zlib.DEFLATED,
                          isal_zlib.MAX_WBITS + 1)

    def test_baddecompressobj(self):
        # verify failure on building decompress object with bad params
        self.assertRaises(ValueError, isal_zlib.decompressobj, -1)

    def test_decompressobj_badflush(self):
        # verify failure on calling decompressobj.flush with bad params
        self.assertRaises(ValueError, isal_zlib.decompressobj().flush, 0)
        self.assertRaises(ValueError, isal_zlib.decompressobj().flush, -1)

    @support.cpython_only
    def test_overflow(self):
        with self.assertRaisesRegex(OverflowError, 'int too large'):
            isal_zlib.decompress(b'', 15, sys.maxsize + 1)
        with self.assertRaisesRegex(OverflowError, 'int too large'):
            isal_zlib.decompressobj().decompress(b'', sys.maxsize + 1)
        with self.assertRaisesRegex(OverflowError, 'int too large'):
            isal_zlib.decompressobj().flush(sys.maxsize + 1)


class BaseCompressTestCase(object):
    def check_big_compress_buffer(self, size, compress_func):
        _1M = 1024 * 1024
        # Generate 10 MiB worth of random, and expand it by repeating it.
        # The assumption is that isal_zlib's memory is not big enough to
        # exploit such spread out redundancy.
        if hasattr(random, "randbytes"):  # Available from 3.9
            data = random.randbytes(_1M * 10)
        elif hasattr(os, "urandom"):
            data = os.urandom(_1M * 10)
        else:  # Test as defined in 3.6 branch of cpython as fallback.
            data = b'x' * _1M * 10
        data = data * (size // len(data) + 1)
        try:
            compress_func(data)
        finally:
            # Release memory
            data = None

    def check_big_decompress_buffer(self, size, decompress_func):
        data = b'x' * size
        try:
            compressed = isal_zlib.compress(data, 1)
        finally:
            # Release memory
            data = None
        data = decompress_func(compressed)
        # Sanity check
        try:
            self.assertEqual(len(data), size)
            self.assertEqual(len(data.strip(b'x')), 0)
        finally:
            data = None


class CompressTestCase(BaseCompressTestCase, unittest.TestCase):
    # Test compression in one go (whole message compression)
    def test_speech(self):
        x = isal_zlib.compress(HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(x), HAMLET_SCENE)

    def test_keywords(self):
        x = isal_zlib.compress(HAMLET_SCENE, level=3)
        self.assertEqual(isal_zlib.decompress(x), HAMLET_SCENE)
        with self.assertRaises(TypeError):
            isal_zlib.compress(data=HAMLET_SCENE, level=3)
        self.assertEqual(isal_zlib.decompress(x,
                                              wbits=isal_zlib.MAX_WBITS,
                                              bufsize=isal_zlib.DEF_BUF_SIZE),
                         HAMLET_SCENE)

    def test_speech128(self):
        # compress more data
        data = HAMLET_SCENE * 128
        x = isal_zlib.compress(data)
        self.assertEqual(isal_zlib.compress(bytearray(data)), x)
        for ob in x, bytearray(x):
            self.assertEqual(isal_zlib.decompress(ob), data)

    def test_incomplete_stream(self):
        # A useful error message is given
        x = isal_zlib.compress(HAMLET_SCENE)
        self.assertRaisesRegex(isal_zlib.error,
                               "incomplete or truncated stream",
                               isal_zlib.decompress, x[:-1])

    # Memory use of the following functions takes into account overallocation

    @bigmemtest(size=_1G + 1024 * 1024, memuse=3)
    def test_big_compress_buffer(self, size):
        compress = functools.partial(isal_zlib.compress, level=1)
        self.check_big_compress_buffer(size, compress)

    @bigmemtest(size=_1G + 1024 * 1024, memuse=2)
    def test_big_decompress_buffer(self, size):
        self.check_big_decompress_buffer(size, isal_zlib.decompress)

    @bigmemtest(size=_4G, memuse=1)
    def test_large_bufsize(self, size):
        # Test decompress(bufsize) parameter greater than the internal limit
        data = HAMLET_SCENE * 10
        compressed = isal_zlib.compress(data, 1)
        self.assertEqual(isal_zlib.decompress(compressed, 15, size), data)

    def test_custom_bufsize(self):
        data = HAMLET_SCENE * 10
        compressed = isal_zlib.compress(data, 1)
        self.assertEqual(isal_zlib.decompress(compressed, 15, CustomInt()),
                         data)

    @unittest.skipUnless(sys.maxsize > 2 ** 32, 'requires 64bit platform')
    @bigmemtest(size=_4G + 100, memuse=4)
    def test_64bit_compress(self, size):
        data = b'x' * size
        try:
            comp = isal_zlib.compress(data, 0)
            self.assertEqual(isal_zlib.decompress(comp), data)
        finally:
            comp = data = None


class CompressObjectTestCase(BaseCompressTestCase, unittest.TestCase):
    # Test compression object
    def test_pair(self):
        # straightforward compress/decompress objects
        datasrc = HAMLET_SCENE * 128
        datazip = isal_zlib.compress(datasrc)
        # should compress both bytes and bytearray data
        for data in (datasrc, bytearray(datasrc)):
            co = isal_zlib.compressobj()
            x1 = co.compress(data)
            x2 = co.flush()
            # Flushing multiple times no problem for isa-l.
            # self.assertRaises(isal_zlib.error, co.flush)
            self.assertEqual(x1 + x2, datazip)
        for v1, v2 in ((x1, x2), (bytearray(x1), bytearray(x2))):
            dco = isal_zlib.decompressobj()
            y1 = dco.decompress(v1 + v2)
            y2 = dco.flush()
            self.assertEqual(data, y1 + y2)
            self.assertIsInstance(dco.unconsumed_tail, bytes)
            self.assertIsInstance(dco.unused_data, bytes)

    def test_keywords(self):
        level = 2
        method = isal_zlib.DEFLATED
        wbits = -12
        memLevel = 9
        strategy = isal_zlib.Z_FILTERED
        co = isal_zlib.compressobj(level=level,
                                   method=method,
                                   wbits=wbits,
                                   memLevel=memLevel,
                                   strategy=strategy,
                                   zdict=b"")
        do = isal_zlib.decompressobj(wbits=wbits, zdict=b"")
        with self.assertRaises(TypeError):
            co.compress(data=HAMLET_SCENE)
        with self.assertRaises(TypeError):
            do.decompress(data=isal_zlib.compress(HAMLET_SCENE))
        x = co.compress(HAMLET_SCENE) + co.flush()
        y = do.decompress(x, max_length=len(HAMLET_SCENE)) + do.flush()
        self.assertEqual(HAMLET_SCENE, y)

    def test_compressoptions(self):
        # specify lots of options to compressobj()
        level = 2
        method = isal_zlib.DEFLATED
        wbits = -12
        memLevel = 9
        strategy = isal_zlib.Z_FILTERED
        co = isal_zlib.compressobj(level, method, wbits, memLevel, strategy)
        x1 = co.compress(HAMLET_SCENE)
        x2 = co.flush()
        dco = isal_zlib.decompressobj(wbits)
        y1 = dco.decompress(x1 + x2)
        y2 = dco.flush()
        self.assertEqual(HAMLET_SCENE, y1 + y2)

    def test_compressincremental(self):
        # compress object in steps, decompress object as one-shot
        data = HAMLET_SCENE * 128
        co = isal_zlib.compressobj()
        bufs = []
        for i in range(0, len(data), 256):
            bufs.append(co.compress(data[i:i + 256]))
        bufs.append(co.flush())

        dco = isal_zlib.decompressobj()
        y1 = dco.decompress(b''.join(bufs))
        y2 = dco.flush()
        self.assertEqual(data, y1 + y2)

    def test_decompinc(self, flush=False, source=None, cx=256, dcx=64):
        # compress object in steps, decompress object in steps
        source = source or HAMLET_SCENE
        data = source * 128
        co = isal_zlib.compressobj()
        bufs = []
        for i in range(0, len(data), cx):
            bufs.append(co.compress(data[i:i + cx]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)

        decombuf = isal_zlib.decompress(combuf)
        # Test type of return value
        self.assertIsInstance(decombuf, bytes)

        self.assertEqual(data, decombuf)

        dco = isal_zlib.decompressobj()
        bufs = []
        for i in range(0, len(combuf), dcx):
            bufs.append(dco.decompress(combuf[i:i + dcx]))
            self.assertEqual(b'', dco.unconsumed_tail,
                             "(A) uct should be b'': not %d long" %
                             len(dco.unconsumed_tail))
            self.assertEqual(b'', dco.unused_data)
        if flush:
            bufs.append(dco.flush())
        else:
            while True:
                chunk = dco.decompress(b'')
                if chunk:
                    bufs.append(chunk)
                else:
                    break
        self.assertEqual(b'', dco.unconsumed_tail,
                         "(B) uct should be b'': not %d long" %
                         len(dco.unconsumed_tail))
        self.assertEqual(b'', dco.unused_data)
        self.assertEqual(data, b''.join(bufs))
        # Failure means: "decompressobj with init options failed"

    def test_decompincflush(self):
        self.test_decompinc(flush=True)

    def test_decompimax(self, source=None, cx=256, dcx=64):
        # compress in steps, decompress in length-restricted steps
        source = source or HAMLET_SCENE
        # Check a decompression object with max_length specified
        data = source * 128
        co = isal_zlib.compressobj()
        bufs = []
        for i in range(0, len(data), cx):
            bufs.append(co.compress(data[i:i + cx]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)
        self.assertEqual(data, isal_zlib.decompress(combuf),
                         'compressed data failure')

        dco = isal_zlib.decompressobj()
        bufs = []
        cb = combuf
        while not dco.eof:
            # max_length = 1 + len(cb)//10
            chunk = dco.decompress(cb, dcx)
            self.assertFalse(len(chunk) > dcx,
                             'chunk too big (%d>%d)' % (len(chunk), dcx))
            bufs.append(chunk)
            cb = dco.unconsumed_tail
        bufs.append(dco.flush())
        self.assertEqual(data, b''.join(bufs), 'Wrong data retrieved')

    def test_decompressmaxlen(self, flush=False):
        # Check a decompression object with max_length specified
        data = HAMLET_SCENE * 128
        co = isal_zlib.compressobj()
        bufs = []
        for i in range(0, len(data), 256):
            bufs.append(co.compress(data[i:i + 256]))
        bufs.append(co.flush())
        combuf = b''.join(bufs)
        self.assertEqual(data, isal_zlib.decompress(combuf),
                         'compressed data failure')

        dco = isal_zlib.decompressobj()
        bufs = []
        cb = combuf
        while not dco.eof:
            max_length = 1 + len(cb) // 10
            chunk = dco.decompress(cb, max_length)
            self.assertFalse(len(chunk) > max_length,
                             'chunk too big (%d>%d)' % (
                             len(chunk), max_length))
            bufs.append(chunk)
            cb = dco.unconsumed_tail
        if flush:
            bufs.append(dco.flush())
        else:
            while chunk:
                chunk = dco.decompress(b'', max_length)
                self.assertFalse(len(chunk) > max_length,
                                 'chunk too big (%d>%d)' % (
                                 len(chunk), max_length))
                bufs.append(chunk)
        self.assertEqual(data, b''.join(bufs), 'Wrong data retrieved')

    def test_decompressmaxlenflush(self):
        self.test_decompressmaxlen(flush=True)

    def test_maxlenmisc(self):
        # Misc tests of max_length
        dco = isal_zlib.decompressobj()
        self.assertRaises(ValueError, dco.decompress, b"", -1)
        self.assertEqual(b'', dco.unconsumed_tail)

    def test_maxlen_large(self):
        # Sizes up to sys.maxsize should be accepted, although isal_zlib is
        # internally limited to expressing sizes with unsigned int
        data = HAMLET_SCENE * 10
        self.assertGreater(len(data), isal_zlib.DEF_BUF_SIZE)
        compressed = isal_zlib.compress(data, 1)
        dco = isal_zlib.decompressobj()
        self.assertEqual(dco.decompress(compressed, sys.maxsize), data)

    def test_maxlen_custom(self):
        data = HAMLET_SCENE * 10
        compressed = isal_zlib.compress(data, 1)
        dco = isal_zlib.decompressobj()
        self.assertEqual(dco.decompress(compressed, CustomInt()), data[:100])

    def test_clear_unconsumed_tail(self):
        # Issue #12050: calling decompress() without providing max_length
        # should clear the unconsumed_tail attribute.
        cdata = b"x\x9cKLJ\x06\x00\x02M\x01"  # "abc"
        dco = isal_zlib.decompressobj()
        ddata = dco.decompress(cdata, 1)
        ddata += dco.decompress(dco.unconsumed_tail)
        self.assertEqual(dco.unconsumed_tail, b"")

    def test_flushes(self):
        # Test flush() with the various options, using all the
        # different levels in order to provide more variations.
        sync_opt = ['Z_NO_FLUSH', 'Z_SYNC_FLUSH', 'Z_FULL_FLUSH']

        sync_opt = [getattr(isal_zlib, opt) for opt in sync_opt
                    if hasattr(isal_zlib, opt)]
        data = HAMLET_SCENE * 8

        for sync in sync_opt:
            for level in range(3):
                try:
                    obj = isal_zlib.compressobj(level)
                    a = obj.compress(data[:3000])
                    b = obj.flush(sync)
                    c = obj.compress(data[3000:])
                    d = obj.flush()
                except:  # noqa: E722
                    print("Error for flush mode={}, level={}"
                          .format(sync, level))
                    raise
                result = isal_zlib.decompress(b''.join([a, b, c, d]))
                self.assertEqual(result,
                                 data, ("Decompress failed: flush "
                                        "mode=%i, level=%i") % (sync, level))
                del obj

    @unittest.skipUnless(hasattr(isal_zlib, 'Z_SYNC_FLUSH'),
                         'requires isal_zlib.Z_SYNC_FLUSH')
    def test_odd_flush(self):
        # Test for odd flushing bugs noted in 2.0, and hopefully fixed in 2.1
        import random
        # Testing on 17K of "random" data

        # Create compressor and decompressor objects
        co = isal_zlib.compressobj(isal_zlib.Z_BEST_COMPRESSION)
        dco = isal_zlib.decompressobj()

        # Try 17K of data
        # generate random data stream
        try:
            # In 2.3 and later, WichmannHill is the RNG of the bug report
            gen = random.WichmannHill()
        except AttributeError:
            try:
                # 2.2 called it Random
                gen = random.Random()
            except AttributeError:
                # others might simply have a single RNG
                gen = random
        gen.seed(1)
        if hasattr(gen, "randbytes"):
            data = gen.randbytes(17 * 1024)
        elif hasattr(os, "urandom"):
            data = os.urandom(17 * 1024)
        else:
            data = b"12345678910111213" * 1024

        # compress, sync-flush, and decompress
        first = co.compress(data)
        second = co.flush(isal_zlib.Z_SYNC_FLUSH)
        expanded = dco.decompress(first + second)

        # if decompressed data is different from the input data, choke.
        self.assertEqual(expanded, data, "17K random source doesn't match")

    def test_empty_flush(self):
        # Test that calling .flush() on unused objects works.
        # (Bug #1083110 -- calling .flush() on decompress objects
        # caused a core dump.)

        co = isal_zlib.compressobj(isal_zlib.Z_BEST_COMPRESSION)
        self.assertTrue(co.flush())  # Returns a isal_zlib header
        dco = isal_zlib.decompressobj()
        self.assertEqual(dco.flush(), b"")  # Returns nothing

    def test_dictionary(self):
        h = HAMLET_SCENE
        # Build a simulated dictionary out of the words in HAMLET.
        words = h.split()
        random.shuffle(words)
        zdict = b''.join(words)
        # Use it to compress HAMLET.
        co = isal_zlib.compressobj(zdict=zdict)
        cd = co.compress(h) + co.flush()
        # Verify that it will decompress with the dictionary.
        dco = isal_zlib.decompressobj(zdict=zdict)
        self.assertEqual(dco.decompress(cd) + dco.flush(), h)
        # Verify that it fails when not given the dictionary.
        dco = isal_zlib.decompressobj()
        self.assertRaises(isal_zlib.error, dco.decompress, cd)

    def test_dictionary_streaming(self):
        # This simulates the reuse of a compressor object for compressing
        # several separate data streams.
        co = isal_zlib.compressobj(zdict=HAMLET_SCENE)
        do = isal_zlib.decompressobj(zdict=HAMLET_SCENE)
        piece = HAMLET_SCENE[1000:1500]
        d0 = co.compress(piece) + co.flush(isal_zlib.Z_SYNC_FLUSH)
        d1 = co.compress(piece[100:]) + co.flush(isal_zlib.Z_SYNC_FLUSH)
        d2 = co.compress(piece[:-100]) + co.flush(isal_zlib.Z_SYNC_FLUSH)
        self.assertEqual(do.decompress(d0), piece)
        self.assertEqual(do.decompress(d1), piece[100:])
        self.assertEqual(do.decompress(d2), piece[:-100])

    def test_decompress_incomplete_stream(self):
        # This is 'foo', deflated
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'
        # For the record
        self.assertEqual(isal_zlib.decompress(x), b'foo')
        self.assertRaises(isal_zlib.error, isal_zlib.decompress, x[:-5])
        # Omitting the stream end works with decompressor objects
        # (see issue #8672).
        dco = isal_zlib.decompressobj()
        y = dco.decompress(x[:-5])
        y += dco.flush()
        self.assertEqual(y, b'foo')

    def test_decompress_eof(self):
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'  # 'foo'
        dco = isal_zlib.decompressobj()
        self.assertFalse(dco.eof)
        dco.decompress(x[:-5])
        self.assertFalse(dco.eof)
        dco.decompress(x[-5:])
        self.assertTrue(dco.eof)
        dco.flush()
        self.assertTrue(dco.eof)

    def test_decompress_eof_incomplete_stream(self):
        x = b'x\x9cK\xcb\xcf\x07\x00\x02\x82\x01E'  # 'foo'
        dco = isal_zlib.decompressobj()
        self.assertFalse(dco.eof)
        dco.decompress(x[:-5])
        self.assertFalse(dco.eof)
        dco.flush()
        self.assertFalse(dco.eof)

    def test_decompress_unused_data(self):
        # Repeated calls to decompress() after EOF should accumulate data in
        # dco.unused_data, instead of just storing the arg to the last call.
        source = b'abcdefghijklmnopqrstuvwxyz'
        remainder = b'0123456789'
        y = isal_zlib.compress(source)
        x = y + remainder
        for maxlen in 0, 1000:
            for step in 1, 2, len(y), len(x):
                dco = isal_zlib.decompressobj()
                data = b''
                for i in range(0, len(x), step):
                    if i < len(y):
                        self.assertEqual(dco.unused_data, b'')
                    if maxlen == 0:
                        data += dco.decompress(x[i: i + step])
                        self.assertEqual(dco.unconsumed_tail, b'')
                    else:
                        data += dco.decompress(
                            dco.unconsumed_tail + x[i: i + step], maxlen)
                data += dco.flush()
                self.assertTrue(dco.eof)
                self.assertEqual(data, source)
                self.assertEqual(dco.unconsumed_tail, b'')
                self.assertEqual(dco.unused_data, remainder)

    # issue27164
    def test_decompress_raw_with_dictionary(self):
        zdict = b'abcdefghijklmnopqrstuvwxyz'
        co = isal_zlib.compressobj(wbits=-isal_zlib.MAX_WBITS, zdict=zdict)
        comp = co.compress(zdict) + co.flush()
        dco = isal_zlib.decompressobj(wbits=-isal_zlib.MAX_WBITS, zdict=zdict)
        uncomp = dco.decompress(comp) + dco.flush()
        self.assertEqual(zdict, uncomp)

    def test_flush_with_freed_input(self):
        # Issue #16411: decompressor accesses input to last decompress() call
        # in flush(), even if this object has been freed in the meanwhile.
        input1 = b'abcdefghijklmnopqrstuvwxyz'
        input2 = b'QWERTYUIOPASDFGHJKLZXCVBNM'
        data = isal_zlib.compress(input1)
        dco = isal_zlib.decompressobj()
        dco.decompress(data, 1)
        del data
        data = isal_zlib.compress(input2)  # noqa: F841
        self.assertEqual(dco.flush(), input1[1:])

    @bigmemtest(size=_4G, memuse=1)
    def test_flush_large_length(self, size):
        # Test flush(length) parameter greater than internal limit UINT_MAX
        input = HAMLET_SCENE * 10
        data = isal_zlib.compress(input, 1)
        dco = isal_zlib.decompressobj()
        dco.decompress(data, 1)
        self.assertEqual(dco.flush(size), input[1:])

    # Skip this test for pypy. This is an extreme fringe use case. There are
    # constants provided for the mode parameter, so it seems very unlikely
    # custom ints will be used.
    @unittest.skipIf(sys.implementation.name == "pypy",
                     "PyPy does not handle __index__ properly")
    def test_flush_custom_length(self):
        input = HAMLET_SCENE * 10
        data = isal_zlib.compress(input, 1)
        dco = isal_zlib.decompressobj()
        dco.decompress(data, 1)
        self.assertEqual(dco.flush(CustomInt()), input[1:])

    @requires_Compress_copy
    def test_compresscopy(self):
        # Test copying a compression object
        data0 = HAMLET_SCENE
        data1 = bytes(str(HAMLET_SCENE, "ascii").swapcase(), "ascii")
        for func in lambda c: c.copy(), copy.copy, copy.deepcopy:
            c0 = isal_zlib.compressobj(isal_zlib.Z_BEST_COMPRESSION)
            bufs0 = []
            bufs0.append(c0.compress(data0))

            c1 = func(c0)
            bufs1 = bufs0[:]

            bufs0.append(c0.compress(data0))
            bufs0.append(c0.flush())
            s0 = b''.join(bufs0)

            bufs1.append(c1.compress(data1))
            bufs1.append(c1.flush())
            s1 = b''.join(bufs1)

            self.assertEqual(isal_zlib.decompress(s0), data0 + data0)
            self.assertEqual(isal_zlib.decompress(s1), data0 + data1)

    @requires_Compress_copy
    def test_badcompresscopy(self):
        # Test copying a compression object in an inconsistent state
        c = isal_zlib.compressobj()
        c.compress(HAMLET_SCENE)
        c.flush()
        self.assertRaises(ValueError, c.copy)
        self.assertRaises(ValueError, copy.copy, c)
        self.assertRaises(ValueError, copy.deepcopy, c)

    @requires_Decompress_copy
    def test_decompresscopy(self):
        # Test copying a decompression object
        data = HAMLET_SCENE
        comp = isal_zlib.compress(data)
        # Test type of return value
        self.assertIsInstance(comp, bytes)

        for func in lambda c: c.copy(), copy.copy, copy.deepcopy:
            d0 = isal_zlib.decompressobj()
            bufs0 = []
            bufs0.append(d0.decompress(comp[:32]))

            d1 = func(d0)
            bufs1 = bufs0[:]

            bufs0.append(d0.decompress(comp[32:]))
            s0 = b''.join(bufs0)

            bufs1.append(d1.decompress(comp[32:]))
            s1 = b''.join(bufs1)

            self.assertEqual(s0, s1)
            self.assertEqual(s0, data)

    @requires_Decompress_copy
    def test_baddecompresscopy(self):
        # Test copying a compression object in an inconsistent state
        data = isal_zlib.compress(HAMLET_SCENE)
        d = isal_zlib.decompressobj()
        d.decompress(data)
        d.flush()
        self.assertRaises(ValueError, d.copy)
        self.assertRaises(ValueError, copy.copy, d)
        self.assertRaises(ValueError, copy.deepcopy, d)

    def test_compresspickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(
                    isal_zlib.compressobj(isal_zlib.Z_BEST_COMPRESSION), proto)

    def test_decompresspickle(self):
        for proto in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.assertRaises((TypeError, pickle.PicklingError)):
                pickle.dumps(isal_zlib.decompressobj(), proto)

    # Memory use of the following functions takes into account overallocation

    @bigmemtest(size=_1G + 1024 * 1024, memuse=3)
    def test_big_compress_buffer(self, size):
        c = isal_zlib.compressobj(1)

        def compress(data):
            return c.compress(data) + c.flush()
        self.check_big_compress_buffer(size, compress)

    @bigmemtest(size=_1G + 1024 * 1024, memuse=2)
    def test_big_decompress_buffer(self, size):
        d = isal_zlib.decompressobj()

        def decompress(data):
            return d.decompress(data) + d.flush()
        self.check_big_decompress_buffer(size, decompress)

    @unittest.skipUnless(sys.maxsize > 2 ** 32, 'requires 64bit platform')
    @bigmemtest(size=_4G + 100, memuse=4)
    def test_64bit_compress(self, size):
        data = b'x' * size
        co = isal_zlib.compressobj(0)
        do = isal_zlib.decompressobj()
        try:
            comp = co.compress(data) + co.flush()
            uncomp = do.decompress(comp) + do.flush()
            self.assertEqual(uncomp, data)
        finally:
            comp = uncomp = data = None

    @unittest.skipUnless(sys.maxsize > 2 ** 32, 'requires 64bit platform')
    @bigmemtest(size=_4G + 100, memuse=3)
    def test_large_unused_data(self, size):
        data = b'abcdefghijklmnop'
        unused = b'x' * size
        comp = isal_zlib.compress(data) + unused
        do = isal_zlib.decompressobj()
        try:
            uncomp = do.decompress(comp) + do.flush()
            self.assertEqual(unused, do.unused_data)
            self.assertEqual(uncomp, data)
        finally:
            unused = comp = do = None

    @unittest.skipUnless(sys.maxsize > 2 ** 32, 'requires 64bit platform')
    @bigmemtest(size=_4G + 100, memuse=5)
    def test_large_unconsumed_tail(self, size):
        data = b'x' * size
        do = isal_zlib.decompressobj()
        try:
            comp = isal_zlib.compress(data, 0)
            uncomp = do.decompress(comp, 1) + do.flush()
            self.assertEqual(uncomp, data)
            self.assertEqual(do.unconsumed_tail, b'')
        finally:
            comp = uncomp = data = None

    def test_wbits(self):
        co = isal_zlib.compressobj(level=1, wbits=15)
        isal_zlib15 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(isal_zlib.decompress(isal_zlib15, 15), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(isal_zlib15, 0), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(isal_zlib15, 32 + 15),
                         HAMLET_SCENE)
        with self.assertRaisesRegex(isal_zlib.error, 'nvalid'):
            isal_zlib.decompress(isal_zlib15, 9)
        dco = isal_zlib.decompressobj(wbits=32 + 15)
        self.assertEqual(dco.decompress(isal_zlib15), HAMLET_SCENE)
        dco = isal_zlib.decompressobj(wbits=9)
        with self.assertRaisesRegex(isal_zlib.error, 'nvalid'):
            dco.decompress(isal_zlib15)

        co = isal_zlib.compressobj(level=1, wbits=9)
        isal_zlib9 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(isal_zlib.decompress(isal_zlib9, 9), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(isal_zlib9, 15), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(isal_zlib9, 0), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(isal_zlib9, 32 + 9),
                         HAMLET_SCENE)
        dco = isal_zlib.decompressobj(wbits=32 + 9)
        self.assertEqual(dco.decompress(isal_zlib9), HAMLET_SCENE)

        co = isal_zlib.compressobj(level=1, wbits=-15)
        deflate15 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(isal_zlib.decompress(deflate15, -15), HAMLET_SCENE)
        dco = isal_zlib.decompressobj(wbits=-15)
        self.assertEqual(dco.decompress(deflate15), HAMLET_SCENE)

        co = isal_zlib.compressobj(level=1, wbits=-9)
        deflate9 = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(isal_zlib.decompress(deflate9, -9), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(deflate9, -15), HAMLET_SCENE)
        dco = isal_zlib.decompressobj(wbits=-9)
        self.assertEqual(dco.decompress(deflate9), HAMLET_SCENE)

        co = isal_zlib.compressobj(level=1, wbits=16 + 15)
        gzip = co.compress(HAMLET_SCENE) + co.flush()
        self.assertEqual(isal_zlib.decompress(gzip, 16 + 15), HAMLET_SCENE)
        self.assertEqual(isal_zlib.decompress(gzip, 32 + 15), HAMLET_SCENE)
        dco = isal_zlib.decompressobj(32 + 15)
        self.assertEqual(dco.decompress(gzip), HAMLET_SCENE)


def choose_lines(source, number, seed=None, generator=random):
    """Return a list of number lines randomly chosen from the source"""
    if seed is not None:
        generator.seed(seed)
    sources = source.split('\n')
    return [generator.choice(sources) for n in range(number)]


HAMLET_SCENE = b"""
LAERTES

       O, fear me not.
       I stay too long: but here my father comes.

       Enter POLONIUS

       A double blessing is a double grace,
       Occasion smiles upon a second leave.

LORD POLONIUS

       Yet here, Laertes! aboard, aboard, for shame!
       The wind sits in the shoulder of your sail,
       And you are stay'd for. There; my blessing with thee!
       And these few precepts in thy memory
       See thou character. Give thy thoughts no tongue,
       Nor any unproportioned thought his act.
       Be thou familiar, but by no means vulgar.
       Those friends thou hast, and their adoption tried,
       Grapple them to thy soul with hoops of steel;
       But do not dull thy palm with entertainment
       Of each new-hatch'd, unfledged comrade. Beware
       Of entrance to a quarrel, but being in,
       Bear't that the opposed may beware of thee.
       Give every man thy ear, but few thy voice;
       Take each man's censure, but reserve thy judgment.
       Costly thy habit as thy purse can buy,
       But not express'd in fancy; rich, not gaudy;
       For the apparel oft proclaims the man,
       And they in France of the best rank and station
       Are of a most select and generous chief in that.
       Neither a borrower nor a lender be;
       For loan oft loses both itself and friend,
       And borrowing dulls the edge of husbandry.
       This above all: to thine ownself be true,
       And it must follow, as the night the day,
       Thou canst not then be false to any man.
       Farewell: my blessing season this in thee!

LAERTES

       Most humbly do I take my leave, my lord.

LORD POLONIUS

       The time invites you; go; your servants tend.

LAERTES

       Farewell, Ophelia; and remember well
       What I have said to you.

OPHELIA

       'Tis in my memory lock'd,
       And you yourself shall keep the key of it.

LAERTES

       Farewell.
"""


class CustomInt:
    def __index__(self):
        return 100
