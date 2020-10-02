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
import sys

import _compression

from . import isal_zlib

__all__ = ["IGzipFile", "open", "compress", "decompress", "BadGzipFile"]

_COMPRESS_LEVEL_FAST = isal_zlib.ISAL_BEST_SPEED
_COMPRESS_LEVEL_TRADEOFF = isal_zlib.ISAL_DEFAULT_COMPRESSION
_COMPRESS_LEVEL_BEST = isal_zlib.ISAL_BEST_COMPRESSION

BUFFER_SIZE = _compression.BUFFER_SIZE

try:
    BadGzipFile = gzip.BadGzipFile
except AttributeError:  # Versions lower than 3.8 do not have BadGzipFile
    BadGzipFile = OSError


# The open method was copied from the CPython source with minor adjustments.
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
    """The IGzipFile class simulates most of the methods of a file object with
    the exception of the truncate() method.

    This class only supports opening files in binary mode. If you need to open
    a compressed file in text mode, use the gzip.open() function.
    """
    def __init__(self, filename=None, mode=None,
                 compresslevel=isal_zlib.ISAL_DEFAULT_COMPRESSION,
                 fileobj=None, mtime=None):
        """Constructor for the IGzipFile class.

        At least one of fileobj and filename must be given a
        non-trivial value.

        The new class instance is based on fileobj, which can be a regular
        file, an io.BytesIO object, or any other object which simulates a file.
        It defaults to None, in which case filename is opened to provide
        a file object.

        When fileobj is not None, the filename argument is only used to be
        included in the gzip file header, which may include the original
        filename of the uncompressed file.  It defaults to the filename of
        fileobj, if discernible; otherwise, it defaults to the empty string,
        and in this case the original filename is not included in the header.

        The mode argument can be any of 'r', 'rb', 'a', 'ab', 'w', 'wb', 'x',
        or 'xb' depending on whether the file will be read or written.
        The default is the mode of fileobj if discernible; otherwise, the
        default is 'rb'. A mode of 'r' is equivalent to one of 'rb', and
        similarly for 'w' and 'wb', 'a' and 'ab', and 'x' and 'xb'.

        The compresslevel argument is an integer from 0 to 3 controlling the
        level of compression; 0 is fastest and produces the least compression,
        and 3 is slowest and produces the most compression. Unlike
        gzip.GzipFile 0 is NOT no compression. The default is 2.

        The mtime argument is an optional numeric timestamp to be written
        to the last modification time field in the stream when compressing.
        If omitted or None, the current time is used.
        """
        if not (isal_zlib.ISAL_BEST_SPEED <= compresslevel
                <= isal_zlib.ISAL_BEST_COMPRESSION):
            raise ValueError(
                "Compression level should be between {0} and {1}.".format(
                    isal_zlib.ISAL_BEST_SPEED, isal_zlib.ISAL_BEST_COMPRESSION
                ))
        super().__init__(filename, mode, compresslevel, fileobj, mtime)
        if self.mode == gzip.WRITE:
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

    def _write_gzip_header(self, compresslevel=_COMPRESS_LEVEL_TRADEOFF):
        # Determine what xfl flag is written for the compression level.
        # Equate the fast level to gzip level 1. All the other levels are
        # medium.
        if sys.version_info[0] == 3 and sys.version_info[1] < 7:
            # Correct header introduced in 3.7
            super()._write_gzip_header()
        else:
            if compresslevel == _COMPRESS_LEVEL_FAST:
                compresslevel = gzip._COMPRESS_LEVEL_FAST
            else:
                compresslevel = gzip._COMPRESS_LEVEL_TRADEOFF
            super()._write_gzip_header(compresslevel)

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


class _IGzipReader(gzip._GzipReader):
    def __init__(self, fp):
        super().__init__(fp)
        self._decomp_factory = isal_zlib.decompressobj
        self._decomp_args = dict(wbits=64+isal_zlib.MAX_WBITS)
        # Set wbits such that ISAL_GZIP_NO_HDR_VER is used. This means that
        # it does not read a header, and it verifies the trailer.
        self._decompressor = self._decomp_factory(**self._decomp_args)

    def _add_read_data(self, data):
        # isa-l verifies the trailer data, so no need to keep track of the crc.
        self._stream_size = self._stream_size + len(data)

    def _read_eof(self):
        # Gzip files can be padded with zeroes and still have archives.
        # Consume all zero bytes and set the file position to the first
        # non-zero byte. See http://www.gzip.org/#faq8
        c = b"\x00"
        while c == b"\x00":
            c = self._fp.read(1)
        if c:
            self._fp.prepend(c)


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
    with IGzipFile(fileobj=io.BytesIO(data)) as f:
        return f.read()


def main():
    parser = argparse.ArgumentParser()
    parser.description = (
        "A simple command line interface for the igzip module. "
        "Acts like igzip.")
    parser.add_argument("file", nargs="?")
    compress_group = parser.add_mutually_exclusive_group()
    compress_group.add_argument(
        "-0", "--fast", action="store_const", dest="compresslevel",
        const=_COMPRESS_LEVEL_FAST,
        help="use compression level 0 (fastest)")
    compress_group.add_argument(
        "-1", action="store_const", dest="compresslevel",
        const=1,
        help="use compression level 1")
    compress_group.add_argument(
        "-2", action="store_const", dest="compresslevel",
        const=2,
        help="use compression level 2 (default)")
    compress_group.add_argument(
        "-3", "--best", action="store_const", dest="compresslevel",
        const=_COMPRESS_LEVEL_BEST,
        help="use compression level 3 (best)")
    compress_group.add_argument(
        "-d", "--decompress", action="store_false",
        dest="compress",
        help="Decompress the file instead of compressing.")
    args = parser.parse_args()

    compresslevel = args.compresslevel or _COMPRESS_LEVEL_TRADEOFF

    if args.file is None:
        if args.compress:
            in_file = sys.stdin.buffer
            out_file = IGzipFile(mode="wb", compresslevel=compresslevel,
                                 fileobj=sys.stdout.buffer)
        else:
            in_file = IGzipFile(mode="rb", fileobj=sys.stdin.buffer)
            out_file = sys.stdout.buffer
    else:
        if args.compress:
            in_file = io.open(args.file, mode="rb")
            out_file = open(args.file + ".gz", mode="wb",
                            compresslevel=compresslevel)
        else:
            base, extension = os.path.splitext(args.file)
            if extension != ".gz":
                print(f"filename doesn't end in .gz: {args.file}")
                return
            in_file = open(args.file, "rb")
            out_file = io.open(base, "wb")
    try:
        while True:
            block = in_file.read(BUFFER_SIZE)
            if block == b"":
                break
            out_file.write(block)
    finally:
        if in_file is not sys.stdin.buffer:
            in_file.close()
        if out_file is not sys.stdout.buffer:
            out_file.close()


if __name__ == "__main__":
    main()
