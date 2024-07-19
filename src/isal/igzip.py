# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

# This file uses code from CPython's Lib/gzip.py
# Changes compared to CPython:
# - Subclassed GzipFile to IGzipFile. Methods that included calls to zlib have
#   been overwritten with the same methods, but now calling to isal_zlib.
# - _GzipReader is implemented in C in isal_zlib and allows dropping the GIL.
# - Gzip.compress does not use a GzipFile to compress in memory, but creates a
#   simple header using _create_simple_gzip_header and compresses the data with
#   igzip_lib.compress using the DECOMP_GZIP_NO_HDR flag. This change was
#   ported to Python 3.11, using zlib.compress(wbits=-15) in that instance.
# - Gzip.decompress creates an isal_zlib.decompressobj and decompresses the
#   data that way instead of using GzipFile. This change was ported to
#   Python 3.11.
# - The main() function's gzip utility has now support for a -c flag for easier
#   use.


"""Similar to the stdlib gzip module. But using the Intel Storage Accelaration
Library to speed up its methods."""

import argparse
import builtins
import gzip
import io
import os
import shutil
import struct
import sys
import time
from typing import Optional, SupportsInt

from . import igzip_lib, isal_zlib
from .isal_zlib import _GzipReader

__all__ = ["IGzipFile", "open", "compress", "decompress", "BadGzipFile",
           "READ_BUFFER_SIZE"]

_COMPRESS_LEVEL_FAST = isal_zlib.ISAL_BEST_SPEED
_COMPRESS_LEVEL_TRADEOFF = isal_zlib.ISAL_DEFAULT_COMPRESSION
_COMPRESS_LEVEL_BEST = isal_zlib.ISAL_BEST_COMPRESSION

# The amount of data that is read in at once when decompressing a file.
# Increasing this value may increase performance.
# After 512K the performance does not increase anymore on a Ryzen 5 3600 test
# system.
READ_BUFFER_SIZE = 512 * 1024

FTEXT, FHCRC, FEXTRA, FNAME, FCOMMENT = 1, 2, 4, 8, 16
READ = gzip.READ
WRITE = gzip.WRITE

BadGzipFile = gzip.BadGzipFile  # type: ignore


# The open method was copied from the CPython source with minor adjustments.
def open(filename, mode="rb", compresslevel=_COMPRESS_LEVEL_TRADEOFF,
         encoding=None, errors=None, newline=None):
    """Open a gzip-compressed file in binary or text mode. This uses the isa-l
    library for optimized speed.

    The filename argument can be an actual filename (a str or bytes object), or
    an existing file object to read from or write to.

    The mode argument can be "r", "rb", "w", "wb", "x", "xb", "a" or "ab" for
    binary mode, or "rt", "wt", "xt" or "at" for text mode. The default mode is
    "rb", and the default compresslevel is 2.

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
    # __fspath__ method is os.PathLike
    if isinstance(filename, (str, bytes)) or hasattr(filename, "__fspath__"):
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
                <= isal_zlib.ISAL_BEST_COMPRESSION) and "r" not in mode:
            raise ValueError(
                f"Compression level should be between "
                f"{isal_zlib.ISAL_BEST_SPEED} and "
                f"{isal_zlib.ISAL_BEST_COMPRESSION}, got {compresslevel}."
            )
        super().__init__(filename, mode, compresslevel, fileobj, mtime)
        if self.mode == WRITE:
            self.compress = isal_zlib.compressobj(compresslevel,
                                                  isal_zlib.DEFLATED,
                                                  -isal_zlib.MAX_WBITS,
                                                  isal_zlib.DEF_MEM_LEVEL,
                                                  0)
        if self.mode == READ:
            raw = _GzipReader(self.fileobj, READ_BUFFER_SIZE)
            self._buffer = io.BufferedReader(raw)

    def __repr__(self):
        s = repr(self.fileobj)
        return '<igzip ' + s[1:-1] + ' ' + hex(id(self)) + '>'

    def _write_gzip_header(self, compresslevel=_COMPRESS_LEVEL_TRADEOFF):
        # Python 3.9 added a `compresslevel` parameter to write gzip header.
        # This only determines the value of one extra flag. Because this change
        # was backported to 3.7 and 3.8 in later point versions, the attributes
        # of the function should be checked before trying to use the
        # compresslevel parameter.
        # The gzip header has an extra flag that can be set depending on the
        # compression level used. This should be set when either the fastest or
        # best method is used. ISAL level 0 is larger than gzip level 1 and
        # much faster, so setting the flag for fastest level is appropriate.
        # ISAL level 1,2 and 3 (best)are similar in size and fall around the
        # gzip level 3 size. So setting no extra flag
        # (by using COMPRESS_LEVEL_TRADEOFF) is appropriate here.
        if ("compresslevel" in super()._write_gzip_header.__code__.co_varnames
            and hasattr(gzip, "_COMPRESS_LEVEL_FAST")
                and hasattr(gzip, "_COMPRESS_LEVEL_TRADEOFF")):
            if compresslevel == _COMPRESS_LEVEL_FAST:
                super()._write_gzip_header(gzip._COMPRESS_LEVEL_FAST)
            else:
                super()._write_gzip_header(gzip._COMPRESS_LEVEL_TRADEOFF)
        else:
            super()._write_gzip_header()

    def write(self, data):
        self._check_not_closed()
        if self.mode != WRITE:
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


# Aliases for improved compatibility with CPython gzip module.
GzipFile = IGzipFile
_IGzipReader = _GzipReader


def compress(data, compresslevel: int = _COMPRESS_LEVEL_BEST, *,
             mtime: Optional[SupportsInt] = None) -> bytes:
    """Compress data in one shot and return the compressed string.
    Optional argument is the compression level, in range of 0-3.
    """
    if mtime is None:
        mtime = time.time()
    # There is no best compression level. ISA-L only provides algorithms for
    # fast and medium levels.
    xfl = 4 if compresslevel == _COMPRESS_LEVEL_FAST else 0
    # Pack ID1 and ID2 magic bytes, method (8=deflate), header flags (no extra
    # fields added to header), mtime, xfl and os (255 for unknown OS).
    header = struct.pack("<BBBBLBB", 0x1f, 0x8b, 8, 0, int(mtime), xfl, 255)
    # use igzip_lib to compress the data without a gzip header but with a
    # gzip trailer.
    compressed = igzip_lib.compress(data, compresslevel,
                                    flag=igzip_lib.COMP_GZIP_NO_HDR)
    return header + compressed


def decompress(data):
    """Decompress a gzip compressed string in one shot.
    Return the decompressed string.

    This function checks for extra gzip members. Using
    isal_zlib.decompress(data, wbits=31) is faster in cases where only one
    gzip member is guaranteed to be present.
    """
    reader = _GzipReader(data)
    return reader.readall()


def _argument_parser():
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
    compress_group.set_defaults(compress=True)
    compress_group.add_argument(
        "-d", "--decompress", action="store_const",
        dest="compress",
        const=False,
        help="Decompress the file instead of compressing.")
    output_group = parser.add_mutually_exclusive_group()
    output_group.add_argument("-c", "--stdout", action="store_true",
                              help="write on standard output")
    output_group.add_argument("-o", "--output",
                              help="Write to this output file")
    parser.add_argument("-n", "--no-name", action="store_true",
                        dest="reproducible",
                        help="do not save or restore the original name and "
                             "timestamp")
    parser.add_argument("-f", "--force", action="store_true",
                        help="Overwrite output without prompting")
    # -b flag not taken by either gzip or igzip. Hidden attribute.
    parser.add_argument("-b", "--buffer-size",
                        default=READ_BUFFER_SIZE, type=int,
                        help=argparse.SUPPRESS)
    return parser


def main():
    args = _argument_parser().parse_args()

    compresslevel = args.compresslevel or _COMPRESS_LEVEL_TRADEOFF

    if args.output:
        out_filepath = args.output
    elif args.stdout:
        out_filepath = None  # to stdout
    elif args.file is None:
        out_filepath = None  # to stout
    else:
        if args.compress:
            out_filepath = args.file + ".gz"
        else:
            out_filepath, extension = os.path.splitext(args.file)
            if extension != ".gz" and not args.stdout:
                sys.exit(f"filename doesn't end in .gz: {args.file!r}. "
                         f"Cannot determine output filename.")
    if out_filepath is not None and not args.force:
        if os.path.exists(out_filepath):
            yes_or_no = input(f"{out_filepath} already exists; "
                              f"do you wish to overwrite (y/n)?")
            if yes_or_no not in {"y", "Y", "yes"}:
                sys.exit("not overwritten")

    out_buffer = None
    if args.compress:
        if args.file is None:
            in_file = sys.stdin.buffer
        else:
            in_file = builtins.open(args.file, mode="rb")
        if out_filepath is not None:
            out_buffer = builtins.open(out_filepath, "wb")
        else:
            out_buffer = sys.stdout.buffer

        if args.reproducible:
            gzip_file_kwargs = {"mtime": 0, "filename": b""}
        else:
            gzip_file_kwargs = {"filename": out_filepath}
        out_file = IGzipFile(mode="wb", fileobj=out_buffer,
                             compresslevel=compresslevel, **gzip_file_kwargs)
    else:
        if args.file:
            in_file = open(args.file, mode="rb")
        else:
            in_file = IGzipFile(mode="rb", fileobj=sys.stdin.buffer)
        if out_filepath is not None:
            out_file = builtins.open(out_filepath, mode="wb")
        else:
            out_file = sys.stdout.buffer

    try:
        shutil.copyfileobj(in_file, out_file, args.buffer_size)
    finally:
        if in_file is not sys.stdin.buffer:
            in_file.close()
        if out_file is not sys.stdout.buffer:
            out_file.close()
        if out_buffer is not None and out_buffer is not sys.stdout.buffer:
            out_buffer.close()


if __name__ == "__main__":  # pragma: no cover
    main()
