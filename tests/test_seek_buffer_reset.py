"""Force backward seeks past the outer buffer and through the raw reader."""
import gzip
import io
import random

from isal import igzip

import pytest


@pytest.mark.parametrize('writer', [gzip.compress, igzip.compress])
@pytest.mark.parametrize('random_data', [False, True])
def test_backward_seek_discards_compressed_buffer(writer, random_data):
    data = (random.Random(42).randbytes(1048576) if random_data
            else b'hello world' * 100000)
    with igzip.open(io.BytesIO(writer(data)), 'rb') as reader:
        for offset in (12345, 0, 750000, 10, 32768, 0):
            assert reader.seek(offset) == offset
            assert reader.read(400) == data[offset:offset+400]
        reader.seek(0)
        assert reader.read() == data


@pytest.mark.parametrize('size', [110, 8192, 32768])
def test_raw_reader_backward_seek(size):
    data = random.Random(42).randbytes(size)
    reader = igzip._GzipReader(io.BytesIO(gzip.compress(data)))
    assert reader.read(1) == data[:1]
    assert reader.seek(0) == 0
    assert reader.readall() == data
