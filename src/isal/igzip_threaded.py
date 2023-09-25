import io
import queue
import threading
from time import perf_counter_ns

from . import igzip


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
    def __init__(self, fp, queue_size = 8, block_size = 128 * 1024):
        self.raw = fp
        self.fileobj = igzip._IGzipReader(fp)
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
            block_queue.put(data)

    def read(self, size: int = -1) -> bytes:
        if size < 0:
            return self.readall()
        data = self.buffer.read(size)
        if not data:
            while True:
                try:
                    data_from_queue = self.queue.get(timeout=0.01)
                    break
                except queue.Empty:
                    if not self.worker.is_alive():
                        if self.exception:
                            raise self.exception
                        # EOF reached
                        return b""
            self.buffer = io.BytesIO(data_from_queue)
            data = self.buffer.read(size)
        self.pos += len(data)
        return data

    def readinto(self, b):
        with memoryview(b) as view, view.cast("B") as byte_view:
            data = self.read(len(byte_view))
            byte_view[:len(data)] = data
        return len(data)

    def readable(self) -> bool:
        return True

    def writable(self) -> bool:
        return False

    def tell(self) -> int:
        return self.pos

    def close(self) -> None:
        self.fileobj.close()
