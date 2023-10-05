import io
import queue
import struct
import threading
import typing

from . import igzip, isal_zlib

DEFLATE_WINDOW_SIZE = 2 ** 15

def open(filename, mode="rb", compresslevel=igzip._COMPRESS_LEVEL_TRADEOFF,
         encoding=None, errors=None, newline=None, *, threads=-1):
    if threads == 0 or "w" in mode:
        return igzip.open(filename, mode, compresslevel, encoding, errors,
                          newline)
    if hasattr(filename, "read"):
        fp = filename
    else:
        fp = io.open(filename, "rb")
    return io.BufferedReader(ThreadedGzipReader(fp))


class ThreadedGzipReader(io.RawIOBase):
    def __init__(self, fp, queue_size=4, block_size=8 * 1024 * 1024):
        self.raw = fp
        self.fileobj = igzip._IGzipReader(fp, buffersize=8 * 1024 * 1024)
        self.pos = 0
        self.read_file = False
        self.queue = queue.Queue(queue_size)
        self.eof = False
        self.exception = None
        self.buffer = io.BytesIO()
        self.block_size = block_size
        self.worker = threading.Thread(target=self._decompress)
        self.running = True
        self.worker.start()

    def _decompress(self):
        block_size = self.block_size
        block_queue = self.queue
        while self.running:
            try:
                data = self.fileobj.read(block_size)
            except Exception as e:
                self.exception = e
                return
            if not data:
                return
            while self.running:
                try:
                    block_queue.put(data, timeout=0.05)
                    break
                except queue.Full:
                    pass

    def readinto(self, b):
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

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        return self.pos

    def close(self) -> None:
        self.running = False
        self.worker.join()
        self.fileobj.close()


class ThreadedWriter(io.RawIOBase):
    def __init__(self, fp: typing.BinaryIO, level: int=isal_zlib.ISAL_DEFAULT_COMPRESSION,
                 threads: int=1,
                 queue_size=2):
        self.raw = fp
        self.level = level
        self.previous_block = b""
        self.crc_queue = queue.Queue(maxsize=threads * queue_size)
        self.input_queues = [queue.Queue(queue_size) for _ in range(threads)]
        self.output_queues = [queue.Queue(queue_size) for _ in range(threads)]
        self.index = 0
        self.threads = threads
        self._crc = None
        self.running = False
        self._size = None
        self.crc_worker = threading.Thread(target=self._calculate_crc)
        self.output_worker = threading.Thread(target=self.write)
        self.compression_workers = [
            threading.Thread(target=self._compress, args=(i,))
            for i in range(threads)
        ]
        self._closed = False
        self._write_gzip_header()
        self.start()

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
            "BBBBIBB", magic1,magic2, method, flags, mtime, os, xfl))

    def start(self):
        self.running = True
        self.crc_worker.start()
        self.output_worker.start()
        for worker in self.compression_workers:
            worker.start()

    def stop_immediately(self):
        """Stop, but do not care for remaining work"""
        self.running = False
        self.crc_worker.join()
        self.output_worker.join()
        for worker in self.compression_workers:
            worker.join()

    def write(self, b) -> int:
        if self._closed:
            raise IOError("Can not write closed file")
        index = self.index
        data = bytes(b)
        zdict = memoryview(self.previous_block)[:-DEFLATE_WINDOW_SIZE]
        self.previous_block = data
        self.index += 1
        worker_index = index % self.threads
        self.crc_queue.put(data)
        self.input_queues[worker_index].put((data, zdict))
        return len(data)

    def flush(self):
        if self._closed:
            raise IOError("Can not write closed file")
        # Wait for all data to be compressed
        for in_q in self.input_queues:
            in_q.join()
        # Wait for all data to be written
        for out_q in self.output_queues:
            out_q.join()
        self.raw.flush()

    def close(self) -> None:
        self.flush()
        self.crc_queue.join()
        self.stop_immediately()
        trailer = struct.pack("<II", self._crc, self._size & 0xFFFFFFFF)
        self.raw.write(trailer)
        self.raw.flush()
        self.raw.close()
        self._closed = True

    def closed(self) -> bool:
        return self._closed

    def _calculate_crc(self):
        crc = isal_zlib.crc32(b"")
        size = 0
        while self.running:
            try:
                data = self.crc_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            crc = isal_zlib.crc32(data, crc)
            size += len(data)
            self.crc_queue.task_done()
        self._crc = crc
        self._size = size

    def _compress(self, index: int):
        in_queue = self.input_queues[index]
        out_queue = self.output_queues[index]
        while self.running:
            try:
                data, zdict = in_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            compressor = isal_zlib.compressobj(self.level, wbits=-15, zdict=zdict)
            compressed = compressor.compress(data) + compressor.flush(isal_zlib.Z_SYNC_FLUSH)
            out_queue.put(compressed)
            in_queue.task_done()

    def _write(self):
        index = 0
        output_queues = self.output_queues
        fp = self.raw
        while self.running:
            output_queue = output_queues[index]
            try:
                data = output_queue.get(timeout=0.05)
            except queue.Empty:
                continue
            fp.write(data)
            output_queue.task_done()
            index += 1
