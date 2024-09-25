# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import builtins
import io
import multiprocessing
import os
import queue
import struct
import threading
from typing import List, Optional, Tuple

from . import igzip, isal_zlib

DEFLATE_WINDOW_SIZE = 2 ** 15


def open(filename, mode="rb", compresslevel=igzip._COMPRESS_LEVEL_TRADEOFF,
         encoding=None, errors=None, newline=None, *, threads=1,
         block_size=1024 * 1024):
    """
    Utilize threads to read and write gzip objects and escape the GIL.
    Comparable to gzip.open. This method is only usable for streamed reading
    and writing of objects. Seeking is not supported.

    threads == 0 will defer to igzip.open. A threads < 0 will attempt to use
    the number of threads in the system.

    :param filename: str, bytes or file-like object (supporting read or write
                    method)
    :param mode: the mode with which the file should be opened.
    :param compresslevel: Compression level, only used for gzip writers.
    :param encoding: Passed through to the io.TextIOWrapper, if applicable.
    :param errors: Passed through to the io.TextIOWrapper, if applicable.
    :param newline: Passed through to the io.TextIOWrapper, if applicable.
    :param threads: If 0 will defer to igzip.open, if < 0 will use all threads
                    available to the system. Reading gzip can only
                    use one thread.
    :param block_size: Determines how large the blocks in the read/write
                       queues are for threaded reading and writing.
    :return: An io.BufferedReader, io.BufferedWriter, or io.TextIOWrapper,
             depending on the mode.
    """
    if threads == 0:
        return igzip.open(filename, mode, compresslevel, encoding, errors,
                          newline)
    elif threads < 0:
        try:
            threads = len(os.sched_getaffinity(0))
        except:  # noqa: E722
            try:
                threads = multiprocessing.cpu_count()
            except:  # noqa: E722
                threads = 1
    if "r" in mode:
        gzip_file = io.BufferedReader(
            _ThreadedGzipReader(filename, block_size=block_size))
    else:
        gzip_file = FlushableBufferedWriter(
            _ThreadedGzipWriter(
                filename,
                mode.replace("t", "b"),
                block_size=block_size,
                level=compresslevel,
                threads=threads
            ),
            buffer_size=block_size
        )
    if "t" in mode:
        return io.TextIOWrapper(gzip_file, encoding, errors, newline)
    return gzip_file


def open_as_binary_stream(filename, open_mode):
    if isinstance(filename, (str, bytes)) or hasattr(filename, "__fspath__"):
        binary_file = builtins.open(filename, open_mode)
        closefd = True
    elif hasattr(filename, "read") or hasattr(filename, "write"):
        binary_file = filename
        closefd = False
    else:
        raise TypeError("filename must be a str or bytes object, or a file")
    return binary_file, closefd


class _ThreadedGzipReader(io.RawIOBase):
    def __init__(self, filename, queue_size=2, block_size=1024 * 1024):
        self.raw, self.closefd = open_as_binary_stream(filename, "rb")
        self.fileobj = igzip._IGzipReader(self.raw, buffersize=8 * block_size)
        self.pos = 0
        self.read_file = False
        self.queue = queue.Queue(queue_size)
        self.eof = False
        self.exception = None
        self.buffer = io.BytesIO()
        self.block_size = block_size
        self.worker = threading.Thread(target=self._decompress)
        self._closed = False
        self.running = True
        self._calling_thread = threading.current_thread()
        self.worker.start()

    def _check_closed(self, msg=None):
        if self._closed:
            raise ValueError("I/O operation on closed file")

    def _decompress(self):
        block_size = self.block_size
        block_queue = self.queue
        while self.running and self._calling_thread.is_alive():
            try:
                data = self.fileobj.read(block_size)
            except Exception as e:
                self.exception = e
                return
            if not data:
                return
            while self.running and self._calling_thread.is_alive():
                try:
                    block_queue.put(data, timeout=0.05)
                    break
                except queue.Full:
                    pass

    def readinto(self, b):
        self._check_closed()
        result = self.buffer.readinto(b)
        if result == 0:
            while True:
                try:
                    data_from_queue = self.queue.get(timeout=0.01)
                    break
                except queue.Empty:
                    if not self.worker.is_alive():
                        if self.exception:
                            raise self.exception
                        # EOF reached
                        return 0
            self.buffer = io.BytesIO(data_from_queue)
            result = self.buffer.readinto(b)
        self.pos += result
        return result

    def readable(self) -> bool:
        return True

    def tell(self) -> int:
        self._check_closed()
        return self.pos

    def close(self) -> None:
        if self._closed:
            return
        self.running = False
        self.worker.join()
        self.fileobj.close()
        if self.closefd:
            self.raw.close()
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed


class FlushableBufferedWriter(io.BufferedWriter):
    def flush(self):
        super().flush()
        self.raw.flush()


class _ThreadedGzipWriter(io.RawIOBase):
    """
    Write a gzip file using multiple threads.

    This class is heavily inspired by pigz from Mark Adler
    (https://github.com/madler/pigz). It works similarly.

    Each thread gets its own input and output queue. The program performs a
    round robin using an index. The writer thread reads from the output
    queues in a round robin using an index. This way all the blocks will be
    written to the output stream in order while still allowing independent
    compression for each thread.

    Writing to the ThreadedGzipWriter happens on the main thread in a
    io.BufferedWriter. The BufferedWriter will offer a memoryview of its
    buffer. Using the bytes constructor this is made into an immutable block of
    data.

    A reference to the previous block is used to create a memoryview of the
    last 32k of that block. This is used as a dictionary for the compression
    allowing for better compression rates.

    The current block and the dictionary are pushed into an input queue. They
    are picked up by a compression worker that calculates the crc32, the
    length of the data and compresses the block. The compressed block, checksum
    and length are pushed into an output queue.

    The writer thread reads from output queues and uses the crc32_combine
    function to calculate the total crc. It also writes the compressed block.

    When only one thread is requested, only the input queue is used and
    compressing and output is handled in one thread.
    """
    def __init__(self,
                 filename,
                 mode: str = "wb",
                 level: int = isal_zlib.ISAL_DEFAULT_COMPRESSION,
                 threads: int = 1,
                 queue_size: int = 1,
                 block_size: int = 1024 * 1024,
                 ):
        # File should be closed during init, so __exit__ method does not
        # touch the self.raw value before it is initialized.
        self._closed = True
        if "t" in mode or "r" in mode:
            raise ValueError("Only binary writing is supported")
        if "b" not in mode:
            mode += "b"
        self.lock = threading.Lock()
        self._calling_thread = threading.current_thread()
        self.exception: Optional[Exception] = None
        self.level = level
        self.previous_block = b""
        # Deflating random data results in an output a little larger than the
        # input. Making the output buffer 10% larger is sufficient overkill.
        compress_buffer_size = block_size + max(block_size // 10, 500)
        self.block_size = block_size
        self.compressors: List[isal_zlib._ParallelCompress] = [
            isal_zlib._ParallelCompress(buffersize=compress_buffer_size,
                                        level=level) for _ in range(threads)
        ]
        if threads > 1:
            self.input_queues: List[queue.Queue[Tuple[bytes, memoryview]]] = [
                queue.Queue(queue_size) for _ in range(threads)]
            self.output_queues: List[queue.Queue[Tuple[bytes, int, int]]] = [
                queue.Queue(queue_size) for _ in range(threads)]
            self.output_worker = threading.Thread(target=self._write)
            self.compression_workers = [
                threading.Thread(target=self._compress, args=(i,))
                for i in range(threads)
            ]
        elif threads == 1:
            self.input_queues = [queue.Queue(queue_size)]
            self.output_queues = []
            self.compression_workers = []
            self.output_worker = threading.Thread(
                target=self._compress_and_write)
        else:
            raise ValueError(f"threads should be at least 1, got {threads}")
        self.threads = threads
        self.index = 0
        self._crc = 0
        self.running = False
        self._size = 0
        self.raw, self.closefd = open_as_binary_stream(filename, mode)
        self._closed = False
        self._write_gzip_header()
        self.start()

    def _check_closed(self, msg=None):
        if self._closed:
            raise ValueError("I/O operation on closed file")

    def _write_gzip_header(self):
        """Simple gzip header. Only xfl flag is set according to level."""
        magic1 = 0x1f
        magic2 = 0x8b
        method = 0x08
        flags = 0
        mtime = 0
        os = 0xff
        xfl = 4 if self.level == 0 else 0
        self.raw.write(struct.pack(
            "BBBBIBB", magic1, magic2, method, flags, mtime, os, xfl))

    def start(self):
        self.running = True
        self.output_worker.start()
        for worker in self.compression_workers:
            worker.start()

    def stop(self):
        """Stop, but do not care for remaining work"""
        self.running = False
        for worker in self.compression_workers:
            worker.join()
        self.output_worker.join()

    def write(self, b) -> int:
        self._check_closed()
        with self.lock:
            if self.exception:
                raise self.exception
        length = b.nbytes if isinstance(b, memoryview) else len(b)
        if length > self.block_size:
            # write smaller chunks and return the result
            memview = memoryview(b)
            start = 0
            total_written = 0
            while start < length:
                total_written += self.write(
                    memview[start:start+self.block_size])
                start += self.block_size
            return total_written
        data = bytes(b)
        index = self.index
        zdict = memoryview(self.previous_block)[-DEFLATE_WINDOW_SIZE:]
        self.previous_block = data
        self.index += 1
        worker_index = index % self.threads
        self.input_queues[worker_index].put((data, zdict))
        return len(data)

    def _end_gzip_stream(self):
        self._check_closed()
        # Wait for all data to be compressed
        for in_q in self.input_queues:
            in_q.join()
        # Wait for all data to be written
        for out_q in self.output_queues:
            out_q.join()
        # Write an empty deflate block with a lost block marker.
        self.raw.write(isal_zlib.compress(b"", wbits=-15))
        trailer = struct.pack("<II", self._crc, self._size & 0xFFFFFFFF)
        self.raw.write(trailer)
        self._crc = 0
        self._size = 0
        self.raw.flush()

    def flush(self):
        self._end_gzip_stream()
        self._write_gzip_header()

    def close(self) -> None:
        if self._closed:
            return
        self._end_gzip_stream()
        self.stop()
        if self.exception:
            self.raw.close()
            self._closed = True
            raise self.exception
        if self.closefd:
            self.raw.close()
        self._closed = True

    @property
    def closed(self) -> bool:
        return self._closed

    def _compress(self, index: int):
        in_queue = self.input_queues[index]
        out_queue = self.output_queues[index]
        compressor: isal_zlib._ParallelCompress = self.compressors[index]
        while True:
            try:
                data, zdict = in_queue.get(timeout=0.05)
            except queue.Empty:
                if not (self.running and self._calling_thread.is_alive()):
                    return
                continue
            try:
                compressed, crc = compressor.compress_and_crc(data, zdict)
            except Exception as e:
                in_queue.task_done()
                self._set_error_and_empty_queue(e, in_queue)
                return
            data_length = len(data)
            out_queue.put((compressed, crc, data_length))
            in_queue.task_done()

    def _write(self):
        index = 0
        output_queues = self.output_queues
        while True:
            out_index = index % self.threads
            output_queue = output_queues[out_index]
            try:
                compressed, crc, data_length = output_queue.get(timeout=0.05)
            except queue.Empty:
                if not (self.running and self._calling_thread.is_alive()):
                    return
                continue
            self._crc = isal_zlib.crc32_combine(self._crc, crc, data_length)
            self._size += data_length
            self.raw.write(compressed)
            output_queue.task_done()
            index += 1

    def _compress_and_write(self):
        if not self.threads == 1:
            raise SystemError("Compress_and_write is for one thread only")
        in_queue = self.input_queues[0]
        compressor = self.compressors[0]
        while True:
            try:
                data, zdict = in_queue.get(timeout=0.05)
            except queue.Empty:
                if not (self.running and self._calling_thread.is_alive()):
                    return
                continue
            try:
                compressed, crc = compressor.compress_and_crc(data, zdict)
            except Exception as e:
                in_queue.task_done()
                self._set_error_and_empty_queue(e, in_queue)
                return
            data_length = len(data)
            self._crc = isal_zlib.crc32_combine(self._crc, crc, data_length)
            self._size += data_length
            self.raw.write(compressed)
            in_queue.task_done()

    def _set_error_and_empty_queue(self, error, q):
        with self.lock:
            self.exception = error
            # Abort everything and empty the queue
            self.running = False
            while True:
                try:
                    _ = q.get(timeout=0.05)
                    q.task_done()
                except queue.Empty:
                    return

    def writable(self) -> bool:
        return True
