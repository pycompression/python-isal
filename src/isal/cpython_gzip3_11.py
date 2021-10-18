# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021
# Python Software Foundation; All Rights Reserved"
#
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2
# --------------------------------------------
#
# 1. This LICENSE AGREEMENT is between the Python Software Foundation
# ("PSF"), and the Individual or Organization ("Licensee") accessing and
# otherwise using this software ("Python") in source or binary form and
# its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF hereby
# grants Licensee a nonexclusive, royalty-free, world-wide license to
# reproduce, analyze, test, perform and/or display publicly, prepare derivative
# works, distribute, and otherwise use Python alone or in any derivative
# version,provided, however, that PSF's License Agreement and PSF's notice of
# copyright, i.e., "Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007,
# 2008, 2009, 2010, 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020,
# 2021 Python Software Foundation; All Rights Reserved" are retained in Python
# alone or in any derivative version prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on
# or incorporates Python or any part thereof, and wants to make
# the derivative work available to others as provided herein, then
# Licensee hereby agrees to include in any such work a brief summary of
# the changes made to Python.
#
# 4. PSF is making Python available to Licensee on an "AS IS"
# basis.  PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR
# IMPLIED.  BY WAY OF EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND
# DISCLAIMS ANY REPRESENTATION OR WARRANTY OF MERCHANTABILITY OR FITNESS
# FOR ANY PARTICULAR PURPOSE OR THAT THE USE OF PYTHON WILL NOT
# INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON
# FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS
# A RESULT OF MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON,
# OR ANY DERIVATIVE THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material
# breach of its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any
# relationship of agency, partnership, or joint venture between PSF and
# Licensee.  This License Agreement does not grant permission to use PSF
# trademarks or trade name in a trademark sense to endorse or promote
# products or services of Licensee, or any third party.
#
# 8. By copying, installing or otherwise using Python, Licensee
# agrees to be bound by the terms and conditions of this License
# Agreement.

"""
This module contains some of the refactoring work done in CPython by the author
of python-isal to make the gzip.compress and gzip.decompress implementation a
lot faster. see: https://github.com/python/cpython/pull/27941

In order to ensure backwards-compatibility the CPython implementation was
different from the python-isal implementation. In order to maintain the drop-in
replacement capability of python-isal, the CPython changes are now included in
python-isal. This requires the _read_exact and _read_gzip_header functions
that are only available from python 3.11 onwards. In order to keep the fast
igzip.compress and igzip.decompress implementations and provide full
compatibility with the CPython implementation these functions are also
distributed in this module. No changes were made since CPython commit:
ea23e7820f02840368569db8082bd0ca4d59b62a

https://github.com/python/cpython/commit/ea23e7820f02840368569db8082bd0ca4d59b62a
"""
import io
import struct
import zlib
from gzip import FCOMMENT, FEXTRA, FHCRC, FNAME, BadGzipFile


def _read_exact(fp, n):
    '''Read exactly *n* bytes from `fp`

    This method is required because fp may be unbuffered,
    i.e. return short reads.
    '''
    data = fp.read(n)
    while len(data) < n:
        b = fp.read(n - len(data))
        if not b:
            raise EOFError("Compressed file ended before the "
                           "end-of-stream marker was reached")
        data += b
    return data


def _read_gzip_header(fp):
    '''Read a gzip header from `fp` and progress to the end of the header.

    Returns last mtime if header was present or None otherwise.
    '''
    magic = fp.read(2)
    if magic == b'':
        return None
    if magic != b'\037\213':
        raise BadGzipFile('Not a gzipped file (%r)' % magic)
    header_buffer = io.BytesIO()
    header_buffer.write(magic)
    base_header = _read_exact(fp, 8)
    (method, flag, last_mtime, xfl, os_flag
        ) = struct.unpack("<BBIBB", base_header)
    if method != 8:
        raise BadGzipFile('Unknown compression method')
    header_buffer.write(base_header)

    if flag & FEXTRA:
        # Read the extra field, if present
        extra_len_bytes = _read_exact(fp, 2)
        header_buffer.write(extra_len_bytes)
        extra_len, = struct.unpack("<H", extra_len_bytes)
        header_buffer.write(_read_exact(fp, extra_len))

    if flag & FNAME:
        # Read and discard a null-terminated string containing the filename
        while True:
            s = _read_exact(fp, 1)
            header_buffer.write(s)
            if s == b'\000':
                break
    if flag & FCOMMENT:
        # Read and discard a null-terminated string containing a comment
        while True:
            s = _read_exact(fp, 1)
            header_buffer.write(s)
            if s == b'\000':
                break
    if flag & FHCRC:
        # Read the 16-bit header CRC
        header_crc, = struct.unpack("<H", _read_exact(fp, 2))
        true_crc = zlib.crc32(header_buffer.getvalue()) & 0xFFFF
        if header_crc != true_crc:
            raise BadGzipFile(f"Corrupted gzip header. Checksums do not "
                              f"match: {true_crc} != {header_crc}")
    return last_mtime
