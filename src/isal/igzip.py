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
import zlib
from gzip import WRITE
from . import isal_zlib


class IGzipFile(gzip.GzipFile):
    def __init__(self, filename=None, mode=None,
                 compresslevel=isal_zlib.ISAL_DEFAULT_COMPRESSION,
                 fileobj=None, mtime=None):
        super().__init__(filename, mode, compresslevel, fileobj, mtime)

        # Overwrite buffers and compress objects with isal equivalents.
        if mode.startswith('r'):
            raw = _IGzipReader(fileobj)
            self._buffer = io.BufferedReader(raw)

        elif mode.startswith(('w', 'a', 'x')):
            self._init_write(filename)
            self.compress = zlib.compressobj(compresslevel,
                                             zlib.DEFLATED,
                                             -zlib.MAX_WBITS,
                                             zlib.DEF_MEM_LEVEL,
                                             0)

    def _init_write(self, filename):
        self.name = filename
        self.crc = isal_zlib.crc32(b"")
        self.size = 0
        self.writebuf = []
        self.bufsize = 0
        self.offset = 0  # Current file offset for seek(), tell(), etc

    def __repr__(self):
        s = repr(self.fileobj)
        return '<igzip ' + s[1:-1] + ' ' + hex(id(self)) + '>'

    def write(self, data):
        self._check_not_closed()
        if self.mode != WRITE:
            import errno
            raise OSError(errno.EBADF, "write() on read-only GzipFile object")

        if self.fileobj is None:
            raise ValueError("write() on closed GzipFile object")

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

    def flush(self, zlib_mode=zlib.Z_SYNC_FLUSH):
        self._check_not_closed()
        if self.mode == WRITE:
            # Ensure the compressor's buffer is flushed
            self.fileobj.write(self.compress.flush(zlib_mode))
            self.fileobj.flush()


class _IGzipReader(gzip._GzipReader):
    def __init__(self, fp):
        super().__init__(fp)
        self._decomp_factory = zlib.decompressobj
        self._decompressor = self._decomp_factory(**self._decomp_args)

    def _init_read(self):
        self._crc = isal_zlib.crc32(b"")
        self._stream_size = 0  # Decompressed size of unconcatenated stream

    def _add_read_data(self, data):
        self._crc = isal_zlib.crc32(data, self._crc)
        self._stream_size = self._stream_size + len(data)
