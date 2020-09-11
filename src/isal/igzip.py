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

"""Similar to the stdlib gzip module. But using the Intel Storage Accelaration
Library to speed up its methods."""

import argparse
import gzip
import io
import os
from gzip import BadGzipFile

import _compression

from . import isal_zlib

__all__ = ["BadGzipFile", "IGzipFile", "open", "compress", "decompress"]

_COMPRESS_LEVEL_FAST = isal_zlib.ISAL_BEST_SPEED
_COMPRESS_LEVEL_TRADEOFF = isal_zlib.ISAL_DEFAULT_COMPRESSION
_COMPRESS_LEVEL_BEST = isal_zlib.ISAL_BEST_COMPRESSION
_BLOCK_SIZE = 64*1024


# The open method was copied from the python source with minor adjustments.
def open(filename, mode="rb", compresslevel=_COMPRESS_LEVEL_TRADEOFF,
         encoding=None, errors=None, newline=None):
    """Open a gzip-compressed file in binary or text mode. This uses the isa-l
    library for optimized speed.

    The filename argument can be an actual filename (a str or bytes object), or
    an existing file object to read from or write to.

    The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for
    binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is
    "rb", and the default compresslevel is 9.

    For binary mode, this function is equivalent to the GzipFile constructor:
    GzipFile(filename, mode, compresslevel). In this case, the encoding, errors
    and newline arguments must not be provided.

    For text mode, a GzipFile object is created, and wrapped in an
    io.TextIOWrapper instance with the specified encoding, error handling
    behavior, and line ending(s).

    """
    if "t" in mode:
        if "b" in mode:
            raise ValueError("Invalid mode: %r" % (mode,))
    else:
        if encoding is not None:
            raise ValueError(
                "Argument 'encoding' not supported in binary mode")
        if errors is not None:
            raise ValueError("Argument 'errors' not supported in binary mode")
        if newline is not None:
            raise ValueError("Argument 'newline' not supported in binary mode")

    gz_mode = mode.replace("t", "")
    if isinstance(filename, (str, bytes, os.PathLike)):
        binary_file = IGzipFile(filename, gz_mode, compresslevel)
    elif hasattr(filename, "read") or hasattr(filename, "write"):
        binary_file = IGzipFile(None, gz_mode, compresslevel, filename)
    else:
        raise TypeError("filename must be a str or bytes object, or a file")

    if "t" in mode:
        return io.TextIOWrapper(binary_file, encoding, errors, newline)
    else:
        return binary_file


class IGzipFile(gzip.GzipFile):
    def __init__(self, filename=None, mode=None,
                 compresslevel=isal_zlib.ISAL_DEFAULT_COMPRESSION,
                 fileobj=None, mtime=None):
        if not (isal_zlib.ISAL_BEST_SPEED <= compresslevel
                <= isal_zlib.ISAL_BEST_COMPRESSION):
            raise ValueError(
                "Compression level should be between {0} and {1}.".format(
                    isal_zlib.ISAL_BEST_SPEED, isal_zlib.ISAL_BEST_COMPRESSION
                ))
        super().__init__(filename, mode, compresslevel, fileobj, mtime)
        if hasattr(self, "compress"):
            self.compress = isal_zlib.compressobj(compresslevel,
                                                  isal_zlib.DEFLATED,
                                                  -isal_zlib.MAX_WBITS,
                                                  isal_zlib.DEF_MEM_LEVEL,
                                                  0)
        if self.mode == gzip.READ:
            raw = _IGzipReader(self.fileobj)
            self._buffer = io.BufferedReader(raw)

    def __repr__(self):
        s = repr(self.fileobj)
        return '<igzip ' + s[1:-1] + ' ' + hex(id(self)) + '>'

    def flush(self, zlib_mode=isal_zlib.Z_SYNC_FLUSH):
        super().flush(zlib_mode)

    def write(self, data):
        self._check_not_closed()
        if self.mode != gzip.WRITE:
            import errno
            raise OSError(errno.EBADF, "write() on read-only IGzipFile object")

        if self.fileobj is None:
            raise ValueError("write() on closed IGzipFile object")

        if isinstance(data, bytes):
            length = len(data)
        else:
            # accept any data that supports the buffer protocol
            data = memoryview(data)
            length = data.nbytes

        if length > 0:
            self.fileobj.write(self.compress.compress(data))
            self.size += length
            self.crc = isal_zlib.crc32(data, self.crc)
            self.offset += length
        return length


# The gzip._GzipReader does all sorts of complex stuff. While using the
# standard DecompressReader by _compression relies more on the C implementation
# side of things. It is much simpler. Gzip header interpretation and gzip
# checksum checking is already implemented in the isa-l library. So no need
# to do so in pure python.
class _IGzipReader(_compression.DecompressReader):
    def __init__(self, fp):
        super().__init__(fp, isal_zlib.decompressobj,
                         wbits=16 + isal_zlib.MAX_WBITS)


# Plagiarized from gzip.py from python's stdlib.
def compress(data, compresslevel=_COMPRESS_LEVEL_BEST, *, mtime=None):
    """Compress data in one shot and return the compressed string.
    Optional argument is the compression level, in range of 0-3.
    """
    buf = io.BytesIO()
    with IGzipFile(fileobj=buf, mode='wb',
                   compresslevel=compresslevel, mtime=mtime) as f:
        f.write(data)
    return buf.getvalue()


def decompress(data):
    """Decompress a gzip compressed string in one shot.
    Return the decompressed string.
    """
    return isal_zlib.decompress(data, wbits=16 + isal_zlib.MAX_WBITS)


def main():
    parser = argparse.ArgumentParser()
    parser.description = (
        "A simple command line interface for the igzip module. "
        "Acts like igzip.")
    parser.add_argument("file")
    parser.add_argument("--fast", action="store_true",
                        help="use fastest compression")
    parser.add_argument("--best", action="store_true",
                        help="use best compression")
    parser.add_argument("-d", "--decompress", action="store_false",
                        dest="compress",
                        help="Decompress the file instead of compressing.")
    args = parser.parse_args()

    if args.fast:
        compresslevel = _COMPRESS_LEVEL_FAST
    elif args.best:
        compresslevel = _COMPRESS_LEVEL_BEST
    else:
        compresslevel = _COMPRESS_LEVEL_TRADEOFF

    if args.compress:
        out_filename = args.file + ".gz"
        with io.open(args.file, "rb") as in_file:
            with open(out_filename, mode="rb", compresslevel=compresslevel
                      ) as out_file:
                while True:
                    block = in_file.read(_BLOCK_SIZE)
                    if block == b"":
                        break
                    out_file.write(block)
    else:
        base, extension = os.path.splitext(args.file)
        if extension != ".gz":
            raise ValueError("Can only decompress files with a .gz extension")
        out_filename = base
        with open(args.file, "rb") as in_file:
            with io.open(out_filename, mode="rb") as out_file:
                while True:
                    block = in_file.read(_BLOCK_SIZE)
                    if block == b"":
                        break
                    out_file.write(block)


if __name__ == "__main__":
    main()
