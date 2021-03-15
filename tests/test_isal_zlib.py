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

from isal import isal_zlib

import pytest


@pytest.mark.parametrize("wbits", [-15, 15, 31])
def test_decompress_unused_data(wbits):
    """
    Test from CPython's zlib test suite, now improved for all possible modes
    raw deflate, zlib and gzip
    :return:
    """
    source = b'abcdefghijklmnopqrstuvwxyz'
    remainder = b'0123456789'
    y = isal_zlib.compress(source, wbits=wbits)
    x = y + remainder

    for maxlen in 0, 1000:
        for step in 1, 2, len(y), len(x):
            dco = isal_zlib.decompressobj(wbits=wbits)
            data = b''
            for i in range(0, len(x), step):
                if i < len(y):
                    assert dco.unused_data == b''
                if maxlen == 0:
                    data += dco.decompress(x[i: i + step])
                    assert dco.unconsumed_tail == b''
                else:
                    data += dco.decompress(
                        dco.unconsumed_tail + x[i: i + step], maxlen)
            data += dco.flush()
            assert dco.eof
            assert data == source
            assert dco.unconsumed_tail == b''
            assert dco.unused_data == remainder
