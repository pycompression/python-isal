# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import errno
import gzip
import io
import itertools
import os
import queue
import subprocess
import sys
import tempfile
import threading
import time
import types
import zlib
from pathlib import Path

from isal import igzip_threaded

import pytest

TEST_FILE = str((Path(__file__).parent / "data" / "test.fastq.gz"))


def test_threaded_read():
    with igzip_threaded.open(TEST_FILE, "rb") as thread_f:
        thread_data = thread_f.read()
    with gzip.open(TEST_FILE, "rb") as f:
        data = f.read()
    assert thread_data == data


@pytest.mark.parametrize("block_size", [8 * 1024, 64 * 1024])
@pytest.mark.parametrize(["mode", "threads"],
                         list(itertools.product(["wb", "wt"], [1, 3, -1])))
def test_threaded_write(tmp_path, mode, threads, block_size):
    with open(tmp_path / "output.gz", "wb") as tmp:
        # Use small block sizes to simulate many writes. Each block uses up
        # to 32 KiB from the end of the previous block as a dictionary, so
        # also test a block size above 32 KiB.
        with igzip_threaded.open(tmp, mode, threads=threads,
                                 block_size=block_size) as out_file:
            gzip_open_mode = "rb" if "b" in mode else "rt"
            with gzip.open(TEST_FILE, gzip_open_mode) as in_file:
                while True:
                    block = in_file.read(128 * 1024)
                    if not block:
                        break
                    out_file.write(block)
    with gzip.open(TEST_FILE, "rt") as test_file:
        test_data = test_file.read()
    with gzip.open(tmp.name, "rt") as test_out:
        out_data = test_out.read()
    assert test_data == out_data


def test_threaded_open_no_threads():
    with tempfile.TemporaryFile("rb") as tmp:
        klass = igzip_threaded.open(tmp, "rb", threads=0)
        # igzip.IGzipFile inherits gzip.Gzipfile
        assert isinstance(klass, gzip.GzipFile)


def test_threaded_open_threads():
    with igzip_threaded.open(io.BytesIO(), "wb", threads=3) as f:
        workers = f.raw.compression_workers
        assert len(workers) == 3
        assert all(worker.is_alive() for worker in workers)


def test_threaded_open_not_a_file_or_pathlike():
    i_am_a_tuple = (1, 2, 3)
    with pytest.raises(TypeError) as error:
        igzip_threaded.open(i_am_a_tuple)
    error.match("str")
    error.match("bytes")
    error.match("file")


# Test whether threaded readers and writers throw an error rather than hang
# indefinitely.

@pytest.mark.timeout(5)
def test_threaded_read_error():
    with open(TEST_FILE, "rb") as f:
        data = f.read()
    truncated_data = data[:-8]
    with igzip_threaded.open(io.BytesIO(truncated_data), "rb") as tr_f:
        with pytest.raises(EOFError):
            tr_f.read()


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_write_oversized_block_no_error(tmp_path, threads):
    # Random bytes are incompressible, and therefore are guaranteed to
    # trigger a buffer overflow when larger than block size unless handled
    # correctly.
    data = os.urandom(1024 * 63)  # not a multiple of block_size
    with open(tmp_path / "output.gz", "wb") as tmp:
        with igzip_threaded.open(
                tmp, "wb", compresslevel=3, threads=threads,
                block_size=8 * 1024
        ) as writer:
            writer.write(data)
    with gzip.open(tmp.name, "rb") as gzipped:
        decompressed = gzipped.read()
    assert data == decompressed


@pytest.mark.timeout(5)
@pytest.mark.parametrize(["threads", "block_size"],
                         list(itertools.product([1, 3],
                                                [8 * 1024, 1024 * 1024])))
def test_threaded_write_incompressible_level_0(tmp_path, threads, block_size):
    # Level 0 codes all data with one precomputed Huffman table and never
    # falls back to stored blocks, so random bytes grow by more than 20%.
    data = os.urandom(3 * block_size)
    test_file = tmp_path / "output.gz"
    with igzip_threaded.open(test_file, "wb", compresslevel=0,
                             threads=threads, block_size=block_size) as f:
        f.write(data)
    with gzip.open(test_file, "rb") as f:
        assert f.read() == data


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_write_error(threads):
    f = igzip_threaded._ThreadedGzipWriter(
        io.BytesIO(), level=3,
        threads=threads, block_size=8 * 1024)
    # Bypass the write method which should not allow blocks larger than
    # block_size.
    f.input_queues[0].put((os.urandom(1024 * 64), b""))
    with pytest.raises(OverflowError) as error:
        f.close()
    error.match("Compressed output exceeds buffer size")


class FullDiskStream(io.BytesIO):
    """Accepts the 10-byte gzip header, then fails like a full disk."""
    before_error = None

    def write(self, b):
        if self.tell() == 0:
            return super().write(b)
        if self.before_error:
            self.before_error()
        raise OSError(errno.ENOSPC, os.strerror(errno.ENOSPC))


def assert_writer_closed(f):
    assert f.closed
    workers = [f.output_worker] + f.compression_workers
    assert not any(worker.is_alive() for worker in workers)
    # Make sure double closing does not raise errors
    f.close()


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_write_error_with_full_queues(threads):
    raw = FullDiskStream()
    f = igzip_threaded._ThreadedGzipWriter(raw, threads=threads)
    queues = f.input_queues + f.output_queues

    def wait_until_queues_are_full():
        while not all(q.full() for q in queues):
            time.sleep(0.001)

    # Fail when all queues are full, so write() usually waits for room in a
    # full input queue.
    raw.before_error = wait_until_queues_are_full
    with pytest.raises(OSError) as error:
        while True:
            f.write(b"x")
    assert error.value.errno == errno.ENOSPC
    with pytest.raises(OSError):
        f.close()
    assert_writer_closed(f)


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_flush_error(threads):
    raw = FullDiskStream()
    f = igzip_threaded.open(raw, "wb", threads=threads)
    f.write(b"x")
    with pytest.raises(OSError) as error:
        f.flush()
    assert error.value.errno == errno.ENOSPC
    # Later calls raise the error again.
    with pytest.raises(OSError):
        f.flush()
    with pytest.raises(OSError):
        f.close()
    assert_writer_closed(f.raw)
    # The test passed the stream to open(), so close() leaves it open.
    assert not raw.closed


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 3])
def test_threaded_close_error(monkeypatch, threads):
    raw = FullDiskStream()
    # Make open() treat raw as a file that it opened by name.
    monkeypatch.setattr(igzip_threaded, "builtins",
                        types.SimpleNamespace(open=lambda name, mode: raw))
    with pytest.raises(OSError) as error:
        with igzip_threaded.open("full.gz", "wb", threads=threads) as f:
            f.write(b"x")
    assert error.value.errno == errno.ENOSPC
    assert_writer_closed(f.raw)
    assert raw.closed


def test_close_reader():
    tmp = io.BytesIO(Path(TEST_FILE).read_bytes())
    f = igzip_threaded._ThreadedGzipReader(tmp)
    f.close()
    assert f.closed
    # Make sure double closing does not raise errors
    f.close()


@pytest.mark.parametrize("threads", [1, 3])
def test_close_writer(threads):
    f = igzip_threaded._ThreadedGzipWriter(
        io.BytesIO(), threads=threads)
    f.close()
    assert_writer_closed(f)


# io.BufferedReader.writable() and io.BufferedWriter.readable() are always
# False, so check the raw streams.
def test_reader_not_writable():
    with igzip_threaded.open(TEST_FILE, "rb") as f:
        assert not f.raw.writable()


def test_writer_not_readable():
    with igzip_threaded.open(io.BytesIO(), "wb") as f:
        assert not f.raw.readable()


def test_writer_wrong_level():
    with tempfile.NamedTemporaryFile("wb") as tmp:
        with pytest.raises(ValueError) as error:
            igzip_threaded.open(tmp.name, mode="wb", compresslevel=42)
        error.match("Invalid compression level")
        error.match("42")


def test_writer_too_low_threads():
    with pytest.raises(ValueError) as error:
        igzip_threaded._ThreadedGzipWriter(io.BytesIO(), threads=0)
    error.match("threads")
    error.match("at least 1")


def test_writer_block_size_too_large():
    with pytest.raises(ValueError) as error:
        igzip_threaded.open(io.BytesIO(), "wb", block_size=2**32)
    error.match("buffersize must be at most")


def test_writer_level_not_an_integer():
    with pytest.raises(TypeError):
        igzip_threaded.open(io.BytesIO(), "wb", compresslevel="x")


def test_reader_read_after_close():
    with open(TEST_FILE, "rb") as test_f:
        f = igzip_threaded._ThreadedGzipReader(test_f)
        f.close()
        with pytest.raises(ValueError) as error:
            f.read(1024)
        error.match("closed")


@pytest.mark.parametrize("threads", [1, 3])
def test_writer_write_after_close(threads):
    f = igzip_threaded._ThreadedGzipWriter(io.BytesIO(), threads=threads)
    f.close()
    with pytest.raises(ValueError) as error:
        f.write(b"abc")
    error.match("closed")


def test_igzip_threaded_append(tmp_path):
    test_file = tmp_path / "test.txt.gz"
    with igzip_threaded.open(test_file, "wb") as f:
        f.write(b"AB")
    with igzip_threaded.open(test_file, mode="ab") as f:
        f.write(b"CD")
    with gzip.open(test_file, "rb") as f:
        contents = f.read()
    assert contents == b"ABCD"


def test_igzip_threaded_append_text_mode(tmp_path):
    test_file = tmp_path / "test.txt.gz"
    with igzip_threaded.open(test_file, "wt") as f:
        f.write("AB")
    with igzip_threaded.open(test_file, mode="at") as f:
        f.write("CD")
    with gzip.open(test_file, "rt") as f:
        contents = f.read()
    assert contents == "ABCD"


def test_igzip_threaded_open_compresslevel_and_reading(tmp_path):
    test_file = tmp_path / "test.txt.gz"
    test_file.write_bytes(gzip.compress(b"thisisatest"))
    with igzip_threaded.open(test_file, compresslevel=5) as f:
        text = f.read()
    assert text == b"thisisatest"


def test_threaded_reader_does_not_close_stream():
    test_stream = io.BytesIO()
    test_stream.write(gzip.compress(b"thisisatest"))
    test_stream.seek(0)
    with igzip_threaded.open(test_stream, "rb") as f:
        text = f.read()
    assert not test_stream.closed
    assert text == b"thisisatest"


def test_threaded_writer_does_not_close_stream():
    test_stream = io.BytesIO()
    with igzip_threaded.open(test_stream, "wb") as f:
        f.write(b"thisisatest")
    assert not test_stream.closed
    test_stream.seek(0)
    assert gzip.decompress(test_stream.read()) == b"thisisatest"


@pytest.mark.timeout(5)
@pytest.mark.parametrize(
    ["mode", "threads"], list(itertools.product(["rb", "wb"], [1, 2])))
def test_threaded_program_can_exit_on_error(tmp_path, mode, threads):
    program = tmp_path / "no_context_manager.py"
    test_file = tmp_path / "output.gz"
    # Write 40 mb input data to saturate read buffer. Because of the repetitive
    # nature the resulting gzip file is very small (~40 KiB).
    test_file.write_bytes(gzip.compress(b"test" * (10 * 1024 * 1024)))
    with open(program, "wt") as f:
        f.write("from isal import igzip_threaded\n")
        # ascii() escapes backslashes and non-ASCII characters in the path.
        f.write(
            f"f = igzip_threaded.open({str(test_file)!a}, "
            f"mode='{mode}', threads={threads})\n"
        )
        f.write("raise Exception('Reached the end')\n")
    result = subprocess.run([sys.executable, str(program)],
                            capture_output=True)
    # A sanitizer report changes the exit code.
    assert result.returncode == 1, result.stderr.decode()
    # A SyntaxError or a failed open() also exits with 1. FORCE_COLOR can
    # color the exception type, so check only the message.
    assert b"Reached the end" in result.stderr, result.stderr.decode()


@pytest.mark.parametrize("threads", [1, 2])
def test_flush(tmp_path, threads):
    empty_block_end = b"\x00\x00\xff\xff"
    compressobj = zlib.compressobj(wbits=-15)
    deflate_last_block = compressobj.compress(b"") + compressobj.flush()
    test_file = tmp_path / "output.gz"
    with igzip_threaded.open(test_file, "wb", threads=threads) as f:
        f.write(b"1")
        f.flush()
        data = test_file.read_bytes()
        assert data[-4:] == empty_block_end
        # Cut off gzip header and end data with an explicit last block to
        # test if the data was compressed correctly.
        deflate_block = data[10:] + deflate_last_block
        assert zlib.decompress(deflate_block, wbits=-15) == b"1"
        f.write(b"2")
        f.flush()
        data = test_file.read_bytes()
        assert data[-4:] == empty_block_end
        deflate_block = data[10:] + deflate_last_block
        assert zlib.decompress(deflate_block, wbits=-15) == b"12"
        f.write(b"3")
        f.flush()
        data = test_file.read_bytes()
        assert data[-4:] == empty_block_end
        deflate_block = data[10:] + deflate_last_block
        assert zlib.decompress(deflate_block, wbits=-15) == b"123"
    assert gzip.decompress(test_file.read_bytes()) == b"123"


# Threads in igzip_threaded poll their queues with a timeout, so they can exit
# with the calling thread. Normal use should never wait for that timeout. This
# fixture stretches the timeouts to 2 seconds and records the ones that expire.
@pytest.fixture
def queue_monitor(monkeypatch):
    monitor = types.SimpleNamespace(expired=[], put_blocked=threading.Event())

    class PatientQueue(queue.Queue):
        def get(self, block=True, timeout=None):
            if not block or timeout is None:
                return super().get(block, timeout)
            try:
                return super().get(block, 2.0)
            except queue.Empty:
                monitor.expired.append("get")
                raise

        def put(self, item, block=True, timeout=None):
            if not block or timeout is None:
                return super().put(item, block, timeout)
            if self.full():
                monitor.put_blocked.set()
            try:
                return super().put(item, block, 2.0)
            except queue.Full:
                monitor.expired.append("put")
                raise

    monkeypatch.setattr(igzip_threaded, "queue", types.SimpleNamespace(
        Queue=PatientQueue, Empty=queue.Empty, Full=queue.Full))
    return monitor


@pytest.mark.timeout(10)
@pytest.mark.parametrize("threads", [1, 3])
def test_writer_does_not_wait_for_queue_timeouts(queue_monitor, threads):
    output = io.BytesIO()
    with igzip_threaded.open(output, "wb", threads=threads) as f:
        f.write(b"first")
        f.flush()
        f.write(b"second")
    assert gzip.decompress(output.getvalue()) == b"firstsecond"
    assert queue_monitor.expired == []


@pytest.mark.timeout(10)
def test_reader_does_not_wait_for_queue_timeouts(queue_monitor):
    data = os.urandom(100_000)
    with igzip_threaded.open(io.BytesIO(gzip.compress(data)), "rb",
                             block_size=8 * 1024) as f:
        assert f.read() == data
        # Reading at the end of the stream returns immediately
        assert f.read() == b""
        assert f.read(10) == b""
    assert queue_monitor.expired == []


@pytest.mark.timeout(10)
def test_reader_closes_early_without_waiting_for_queue_timeouts(
        queue_monitor):
    data = os.urandom(1024 * 1024)
    with igzip_threaded.open(io.BytesIO(gzip.compress(data)), "rb",
                             block_size=8 * 1024) as f:
        assert f.read(10) == data[:10]
        # Close while the reader thread waits for room in its full queue
        assert queue_monitor.put_blocked.wait(timeout=5)
    assert queue_monitor.expired == []


@pytest.mark.timeout(10)
def test_reader_error_does_not_wait_for_queue_timeouts(queue_monitor):
    truncated = gzip.compress(os.urandom(100_000))[:-8]
    with igzip_threaded.open(io.BytesIO(truncated), "rb") as f:
        with pytest.raises(EOFError):
            f.read()
        # The error is raised again on subsequent reads
        with pytest.raises(EOFError):
            f.read()
    assert queue_monitor.expired == []


@pytest.mark.timeout(5)
@pytest.mark.parametrize("threads", [1, 2, 3])
def test_threaded_compression_error(monkeypatch, threads):
    isal_zlib = igzip_threaded.isal_zlib
    ParallelCompress = isal_zlib._ParallelCompress
    all_written = threading.Event()

    class FailingCompressor:
        """Fails on the block b"bad" after the test wrote all blocks."""
        def __init__(self, **kwargs):
            self.compressor = ParallelCompress(**kwargs)

        def compress_and_crc(self, data, zdict):
            if data == b"bad":
                all_written.wait()
                raise MemoryError()
            return self.compressor.compress_and_crc(data, zdict)

    monkeypatch.setattr(isal_zlib, "_ParallelCompress", FailingCompressor)
    raw = io.BytesIO()
    f = igzip_threaded._ThreadedGzipWriter(raw, threads=threads)
    # Block 0 fails, so the writer thread must take the blocks of the other
    # threads from their output queues and drop them. Write as many blocks
    # as fit without waiting: two for each thread. The first thread works on
    # block 0, and its next block waits in its input queue, so one more block
    # would make write() wait for the first thread.
    try:
        f.write(b"bad")
        for _ in range(2 * threads - 1):
            f.write(b"good")
    finally:
        # Set the event even if a write fails, so the first thread does not
        # wait forever.
        all_written.set()
    with pytest.raises(MemoryError):
        f.flush()
    # Later calls raise the error again.
    with pytest.raises(MemoryError):
        f.write(b"good")
    with pytest.raises(MemoryError):
        f.close()
    assert_writer_closed(f)
    assert not raw.closed
    # raw holds only the gzip header. The writer thread dropped all blocks,
    # and close() did not end the stream.
    assert len(raw.getvalue()) == 10
