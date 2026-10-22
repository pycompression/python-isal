import concurrent.futures
import io
import random
import string
import threading

from isal import igzip_lib, isal_zlib

import pytest


HAMLET_SCENE = b"""
LAERTES

       O, fear me not.
       I stay too long: but here my father comes.

       Enter POLONIUS

       A double blessing is a double grace,
       Occasion smiles upon a second leave.

LORD POLONIUS

       Yet here, Laertes! aboard, aboard, for shame!
       The wind sits in the shoulder of your sail,
       And you are stay'd for. There; my blessing with thee!
       And these few precepts in thy memory
       See thou character. Give thy thoughts no tongue,
       Nor any unproportioned thought his act.
       Be thou familiar, but by no means vulgar.
       Those friends thou hast, and their adoption tried,
       Grapple them to thy soul with hoops of steel;
       But do not dull thy palm with entertainment
       Of each new-hatch'd, unfledged comrade. Beware
       Of entrance to a quarrel, but being in,
       Bear't that the opposed may beware of thee.
       Give every man thy ear, but few thy voice;
       Take each man's censure, but reserve thy judgment.
       Costly thy habit as thy purse can buy,
       But not express'd in fancy; rich, not gaudy;
       For the apparel oft proclaims the man,
       And they in France of the best rank and station
       Are of a most select and generous chief in that.
       Neither a borrower nor a lender be;
       For loan oft loses both itself and friend,
       And borrowing dulls the edge of husbandry.
       This above all: to thine ownself be true,
       And it must follow, as the night the day,
       Thou canst not then be false to any man.
       Farewell: my blessing season this in thee!

LAERTES

       Most humbly do I take my leave, my lord.

LORD POLONIUS

       The time invites you; go; your servants tend.

LAERTES

       Farewell, Ophelia; and remember well
       What I have said to you.

OPHELIA

       'Tis in my memory lock'd,
       And you yourself shall keep the key of it.

LAERTES

       Farewell.
"""

NUM_THREADS = 10
NUM_ITERATIONS = 20
NUM_JOBS = 50  # To simulate 50 jobs running in 10 threads
barrier = threading.Barrier(parties=NUM_THREADS)


def isal_compress_decompress(compress, decompress):
    for _ in range(NUM_ITERATIONS):
        barrier.wait()
        x = compress(HAMLET_SCENE)
        assert decompress(x) == HAMLET_SCENE

        length = len(HAMLET_SCENE)
        hamlet_random = HAMLET_SCENE + b"".join(
            [s.encode() for s in random.choices(string.printable, k=length)]
        )
        barrier.wait()
        x = compress(hamlet_random)
        assert decompress(x) == hamlet_random


@pytest.mark.parametrize(
    "compress,decompress",
    [
        pytest.param(isal_zlib.compress, isal_zlib.decompress, id="zlib"),
        pytest.param(igzip_lib.compress, igzip_lib.decompress, id="igzip"),
    ]
)
def test_isal_compress_decompress_threaded(compress, decompress):
    with concurrent.futures.ThreadPoolExecutor(NUM_THREADS) as executor:
        futures = [
            executor.submit(isal_compress_decompress, compress, decompress)
            for _ in range(NUM_JOBS)
        ]
        for future in concurrent.futures.as_completed(futures):
            future.result()  # To fire assertion error if there is one


def run_in_threads(function):
    """Call function(index) in NUM_THREADS threads at the same time."""
    start = threading.Barrier(parties=NUM_THREADS)

    def run(index):
        start.wait()
        return function(index)

    with concurrent.futures.ThreadPoolExecutor(NUM_THREADS) as executor:
        return list(executor.map(run, range(NUM_THREADS)))


def test_compressobj_shared_between_threads():
    compressobj = isal_zlib.compressobj()

    def compress(index):
        for _ in range(NUM_ITERATIONS):
            compressobj.compress(HAMLET_SCENE)
            if index == 0:
                compressobj.flush(isal_zlib.Z_SYNC_FLUSH)

    # The order of the calls is unknown, so the output cannot be checked.
    # This test is for ThreadSanitizer.
    run_in_threads(compress)
    compressobj.flush()


def test_decompressobj_shared_between_threads():
    decompressobj = isal_zlib.decompressobj()
    decompressobj.decompress(isal_zlib.compress(HAMLET_SCENE))
    assert decompressobj.eof

    def decompress(index):
        # Data after the end of the stream is added to unused_data.
        for _ in range(NUM_ITERATIONS):
            assert decompressobj.decompress(bytes([index]) * 10) == b""

    run_in_threads(decompress)
    unused_data = decompressobj.unused_data
    blocks = [unused_data[i:i + 10] for i in range(0, len(unused_data), 10)]
    assert sorted(blocks) == sorted(
        bytes([index]) * 10
        for index in range(NUM_THREADS)
        for _ in range(NUM_ITERATIONS)
    )


def test_igzip_decompressor_shared_between_threads():
    data = HAMLET_SCENE * 100
    decompressor = igzip_lib.IgzipDecompressor()
    first = decompressor.decompress(igzip_lib.compress(data), 100)

    def decompress(index):
        size = 0
        while True:
            try:
                size += len(decompressor.decompress(b"", 100))
            except EOFError:
                return size

    assert len(first) + sum(run_in_threads(decompress)) == len(data)


def test_decompressobj_shared_between_threads_detects_format():
    compressed = isal_zlib.compress(HAMLET_SCENE, wbits=31)
    for _ in range(NUM_ITERATIONS):
        # wbits=47 detects gzip or zlib in the first decompress() call.
        decompressobj = isal_zlib.decompressobj(wbits=47)
        results = run_in_threads(
            lambda index: decompressobj.decompress(compressed))
        assert sorted(results) == [b""] * (NUM_THREADS - 1) + [HAMLET_SCENE]
        assert decompressobj.unused_data == compressed * (NUM_THREADS - 1)


def test_decompressobj_attributes_while_decompressing():
    data = HAMLET_SCENE * 100
    compressed = isal_zlib.compress(data) + b"unused"
    decompressobj = isal_zlib.decompressobj()
    done = threading.Event()

    def decompress():
        output = []
        unconsumed = compressed
        while not decompressobj.eof:
            output.append(decompressobj.decompress(unconsumed, 100))
            unconsumed = decompressobj.unconsumed_tail
        # Each call replaces unused_data with a longer bytes object.
        for _ in range(NUM_ITERATIONS):
            decompressobj.decompress(b"!")
        return b"".join(output)

    def run(index):
        if index == 0:
            try:
                return decompress()
            finally:
                done.set()
        while not done.is_set():
            decompressobj.eof
            decompressobj.unused_data
            decompressobj.unconsumed_tail

    assert run_in_threads(run)[0] == data
    assert decompressobj.unused_data == b"unused" + b"!" * NUM_ITERATIONS


def test_igzip_decompressor_attributes_while_decompressing():
    data = HAMLET_SCENE * 100
    compressed = igzip_lib.compress(data, flag=igzip_lib.COMP_GZIP)
    decompressor = igzip_lib.IgzipDecompressor(flag=igzip_lib.DECOMP_GZIP)
    done = threading.Event()

    def decompress():
        output = [decompressor.decompress(compressed + b"unused", 100)]
        while not decompressor.eof:
            output.append(decompressor.decompress(b"", 100))
        return b"".join(output)

    def run(index):
        if index == 0:
            try:
                return decompress()
            finally:
                done.set()
        while not done.is_set():
            decompressor.eof
            decompressor.unused_data
            decompressor.needs_input
            decompressor.crc

    assert run_in_threads(run)[0] == data
    assert decompressor.unused_data == b"unused"
    assert decompressor.crc == isal_zlib.crc32(data)


def test_gzip_reader_seek_while_reading():
    # Each number appears once, so a chunk that mixes up parts is not in it.
    data = b"".join(b"%08d" % i for i in range(128 * 1024))
    compressed = isal_zlib.compress(data, wbits=31)
    reader = isal_zlib._GzipReader(io.BytesIO(compressed))

    def run(index):
        for i in range(NUM_ITERATIONS):
            if index % 2:
                reader.seek(len(data) // 2 if i % 2 else 0)
            else:
                # seek() can come between two reads, but not during one.
                assert reader.read(64 * 1024) in data

    run_in_threads(run)
    reader.seek(0)
    assert reader.read() == data
