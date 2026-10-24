"""Tests for reading all of a gzip stream at once, as igzip.decompress()
and IGzipFile.read() do with _GzipReader.readall()."""
import io
import random

from isal import igzip

import pytest


def compressible(size):
    """JSON-like lines that compress well."""
    rng = random.Random(size)
    lines = []
    length = 0
    while length < size:
        line = (b'{"id": %d, "type": "event", "entity": "sensor.temp_%d"}\n'
                % (rng.randrange(1000), rng.randrange(50)))
        lines.append(line)
        length += len(line)
    return b"".join(lines)[:size]


def incompressible(size):
    return random.Random(size).randbytes(size)


def zeros(size):
    return bytes(size)


KINDS = [compressible, incompressible, zeros]
SIZES = [0, 1, 1000, 100_000, 3_000_000]


class UnknownSize(io.RawIOBase):
    """A stream without fileno(), so its size is unknown."""
    def __init__(self, data, read_size=65536):
        self._data = io.BytesIO(data)
        self._read_size = read_size

    def readable(self):
        return True

    def readinto(self, b):
        # Return less than asked for, as pipes do.
        return self._data.readinto(memoryview(b)[:self._read_size])


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("size", SIZES)
def test_decompress(kind, size):
    data = kind(size)
    assert igzip.decompress(igzip.compress(data)) == data


@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("size", SIZES)
def test_read_file(tmp_path, kind, size):
    data = kind(size)
    path = tmp_path / "test.gz"
    path.write_bytes(igzip.compress(data))
    with igzip.open(path) as f:
        assert f.read() == data
    with open(path, "rb") as f:
        assert igzip._GzipReader(f).readall() == data


@pytest.mark.parametrize("kind", KINDS)
def test_read_unknown_size(kind):
    data = kind(5_000_000)
    with igzip.IGzipFile(fileobj=UnknownSize(igzip.compress(data))) as f:
        assert f.read() == data
    with igzip.IGzipFile(fileobj=io.BytesIO(igzip.compress(data))) as f:
        assert f.read() == data
    # readall() reads a stream that fits in the input buffer to the end
    # first. With a small input buffer, it must join chunks.
    compressed = igzip.compress(data)
    assert len(compressed) > 4096
    reader = igzip._GzipReader(UnknownSize(compressed), 4096)
    assert reader.readall() == data


def members():
    """Members that compress very differently, so that the size that
    readall() expects is wrong in both directions."""
    parts = [zeros(4_000_000), incompressible(1_000_000),
             compressible(2_000_000), zeros(8_000_000), b"end"]
    return b"".join(parts), b"".join(igzip.compress(p) for p in parts)


def test_decompress_members():
    data, compressed = members()
    assert igzip.decompress(compressed) == data


def test_read_file_members(tmp_path):
    data, compressed = members()
    path = tmp_path / "test.gz"
    path.write_bytes(compressed)
    with igzip.open(path) as f:
        assert f.read() == data


@pytest.mark.parametrize("buffersize", [4096, 32 * 1024, 512 * 1024])
def test_read_many_members(tmp_path, buffersize):
    # Members end at many places relative to the input and output buffers.
    rng = random.Random(buffersize)
    parts = [rng.choice(KINDS)(rng.randrange(1, 50_000)) for _ in range(300)]
    data = b"".join(parts)
    compressed = b"".join(igzip.compress(p, 1) for p in parts)
    path = tmp_path / "test.gz"
    path.write_bytes(compressed)
    with open(path, "rb") as f:
        assert igzip._GzipReader(f, buffersize).readall() == data
    reader = igzip._GzipReader(UnknownSize(compressed), buffersize)
    assert reader.readall() == data
    assert igzip._GzipReader(compressed).readall() == data


@pytest.mark.parametrize("buffersize", [4096, 32 * 1024])
@pytest.mark.parametrize("kind", [compressible, zeros])
def test_readall_after_read(tmp_path, kind, buffersize):
    # read() stops at many places in a member and in the input buffer.
    data = kind(100_000)
    path = tmp_path / "test.gz"
    path.write_bytes(igzip.compress(data) + igzip.compress(data[:5000]))
    expected = data + data[:5000]
    for size in sorted({1, 100, 4095, 4096, 16384, 65536, 99_000, 99_992,
                        99_999, 100_000, 100_001, *range(30_000, 100_000,
                                                         7919)}):
        with open(path, "rb") as f:
            reader = igzip._GzipReader(f, buffersize)
            start = reader.read(size)
            assert start + reader.readall() == expected, size


def test_readall_after_read_inside_deflate_block():
    # Some of these read() calls stop inside a deflate block with all input
    # in the buffer used. If readall() refilled the input buffer there, the
    # end of the member would fail with "CRC check failed".
    data = b"".join(b"line %d of some text %d\n" % (i, i % 97)
                    for i in range(8000))
    compressed = igzip.compress(data, 0) + igzip.compress(b"tail", 1)
    expected = data + b"tail"
    for size in range(201_600, 201_800):
        reader = igzip._GzipReader(UnknownSize(compressed, 1000), 32 * 1024)
        start = reader.read(size)
        assert start + reader.readall() == expected, size


def test_read_file_after_partial_read(tmp_path):
    data = compressible(3_000_000)
    path = tmp_path / "test.gz"
    path.write_bytes(igzip.compress(data))
    with igzip.open(path) as f:
        assert f.read(10) == data[:10]
        assert f.read() == data[10:]
    with open(path, "rb") as f:
        reader = igzip._GzipReader(f)
        assert reader.read(100_000) == data[:100_000]
        assert reader.readall() == data[100_000:]


class BadTell(io.FileIO):
    def tell(self):
        raise OSError("tell() does not work")


class TellPastEnd(io.FileIO):
    def tell(self):
        return 2**40


@pytest.mark.parametrize("file_class", [BadTell, TellPastEnd])
def test_read_file_with_unusable_tell(tmp_path, file_class):
    # The size that tell() and fileno() suggest only guides the allocation.
    data = compressible(3_000_000)
    path = tmp_path / "test.gz"
    path.write_bytes(igzip.compress(data))
    with file_class(path, "rb") as f:
        assert igzip._GzipReader(f).readall() == data


@pytest.mark.parametrize("kind", [compressible, zeros])
@pytest.mark.parametrize("source", ["bytes", "file"])
def test_peak_memory(tmp_path, kind, source):
    # Joining chunks needs memory for the chunks and the joined result, so
    # about twice the output. One buffer that grows needs about the output.
    # PyPy has no tracemalloc.
    tracemalloc = pytest.importorskip("tracemalloc")
    data = kind(8_000_000)
    compressed = igzip.compress(data)
    path = tmp_path / "test.gz"
    path.write_bytes(compressed)
    tracemalloc.start()
    try:
        if source == "bytes":
            result = igzip.decompress(compressed)
        else:
            with igzip.open(path) as f:
                result = f.read()
        peak = tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()
    assert result == data
    # One MiB allows for the 512 KiB input buffer of a file.
    assert peak < 1.5 * len(data) + 1024 * 1024
