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

ISAL_BEST_SPEED: int
ISAL_BEST_COMPRESSION: int
ISAL_DEFAULT_COMPRESSION: int
Z_BEST_SPEED: int
Z_BEST_COMPRESSION: int
Z_DEFAULT_COMPRESSION: int

DEF_BUF_SIZE: int
DEF_MEM_LEVEL: int
MAX_WBITS: int

DEFLATED: int

Z_DEFAULT_STRATEGY: int
Z_RLE: int
Z_HUFFMAN_ONLY: int
Z_FILTERED: int
Z_FIXED: int

Z_NO_FLUSH: int
Z_SYNC_FLUSH: int
Z_FULL_FLUSH: int
Z_FINISH: int

class IsalError(OSError): ...

error: IsalError

def adler32(data, value: int = ...) -> int: ...
def crc32(data, value: int = ...) -> int: ...

def compress(data, level: int = ..., wbits: int = ...) -> bytes: ...
def decompress(data, wbits: int = ..., bufsize: int = ...) -> bytes: ...

class Compress:
    def compress(self, data) -> bytes: ...
    def flush(self, mode: int = ...) -> bytes: ...

class Decompress:
    unused_data: bytes
    unconsumed_tail: bytes
    eof: bool
    crc: int

    def decompress(self, data, max_length: int = ...) -> bytes: ...
    def flush(self, length: int = ...) -> bytes: ...

def compressobj(level: int = ..., method: int = ..., wbits: int = ...,
                memLevel: int = ..., strategy: int = ..., zdict = ...
                ) -> Compress: ...
def decompressobj(wbits: int = ..., zdict = ...) -> Decompress: ...
