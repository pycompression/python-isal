"""Output boundaries and ownership affected by the Limited API port."""
import gc
import gzip
import io
import os
import random
import subprocess
import sys
import sysconfig
import zlib

from isal import _isal, igzip_lib, isal_zlib

import pytest


@pytest.mark.parametrize("size", [0, 1, 16383, 16384, 16385,
                                  1048576, 1048713])
@pytest.mark.parametrize("raw", [False, True])
def test_output_growth_and_stream_end(size, raw):
    data = random.Random(240).randbytes(size)
    packed = zlib.compress(data, wbits=-15 if raw else 15)
    if raw:
        assert igzip_lib.decompress(packed, bufsize=1) == data
        decoder = igzip_lib.IgzipDecompressor()
        output = [decoder.decompress(packed + b"tail", 16384)]
        while not decoder.eof:
            output.append(decoder.decompress(b"", 16384))
        assert decoder.unused_data == b"tail"
    else:
        assert isal_zlib.decompress(packed, bufsize=1) == data
        decoder = isal_zlib.decompressobj()
        output = [decoder.decompress(packed + b"tail", 16384)]
        while not decoder.eof:
            output.append(decoder.decompress(decoder.unconsumed_tail, 16384))
        assert decoder.unused_data == b"tail"
    assert b"".join(output) == data


@pytest.mark.parametrize("size", [16384, 1048576])
def test_truncated_trailer_at_full_output_boundary(size):
    data = b"boundary" * (size // 8)
    packed = zlib.compress(data)
    with pytest.raises(isal_zlib.error):
        isal_zlib.decompress(packed[:-1])
    packed = igzip_lib.compress(data, flag=igzip_lib.COMP_GZIP)
    with pytest.raises(igzip_lib.error):
        igzip_lib.decompress(packed[:-1], flag=igzip_lib.DECOMP_GZIP)


@pytest.mark.skipif(sys.implementation.name != "cpython",
                    reason="Needs _testcapi.set_nomemory")
@pytest.mark.parametrize("operation", [
    "isal_zlib.compress(data)", "isal_zlib.decompress(packed)",
    "igzip_lib.compress(data)", "igzip_lib.decompress(raw, bufsize=1)",
    "igzip_lib.IgzipDecompressor().decompress(raw)",
    "isal_zlib.decompressobj().decompress(packed)",
    "stream_compress()",
    "isal_zlib._GzipReader(io.BytesIO(gz)).read(len(data))",
    "isal_zlib._GzipReader(io.BytesIO(gz)).readall()",
])
def test_output_allocation_failure_cleanup(operation):
    pytest.importorskip("_testcapi")
    code = f"""
import gc
import gzip
import io
import random
import tracemalloc
import zlib
import _testcapi
from isal import igzip_lib, isal_zlib
data = random.Random(240).randbytes(256 * 1024)
packed = zlib.compress(data)
raw = zlib.compress(data, wbits=-15)
gz = gzip.compress(data)
def stream_compress():
    obj = isal_zlib.compressobj()
    return obj.compress(data) + obj.flush()
def operation():
    return {operation}
def fail_each_allocation():
    failures = successes = 0
    for start in range(80):
        _testcapi.set_nomemory(start, start + 1)
        try:
            operation()
        except MemoryError:
            failures += 1
        else:
            successes += 1
        finally:
            _testcapi.remove_mem_hooks()
    assert failures and successes
# The first pass fills caches that would otherwise look like leaks.
fail_each_allocation()
tracemalloc.start()
fail_each_allocation()
gc.collect()
retained = tracemalloc.get_traced_memory()[0]
tracemalloc.stop()
# A single leaked output buffer is at least 16 KiB.
assert retained < 8 * 1024, retained
# A clean call after all failure paths still produces valid output.
result = operation()
if 'compress' in {operation!r} and 'decompress' not in {operation!r}:
    wbits = -15 if {operation!r}.startswith('igzip') else 15
    assert zlib.decompress(result, wbits=wbits) == data
else:
    assert result == data
"""
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 0, result.stderr


def allocation_peak(function):
    """Return the result of function() and the most memory it had in use."""
    import tracemalloc

    gc.collect()
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    try:
        result = function()
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not tracing:
            tracemalloc.stop()
    return result, peak - before


needs_tracemalloc = pytest.mark.skipif(
    sys.implementation.name != "cpython",
    reason="Needs CPython tracemalloc allocation accounting")


@needs_tracemalloc
def test_full_bounded_output_does_not_allocate_a_second_result():
    data = b"filled buffer" * 100000
    packed = igzip_lib.compress(data)
    decoder = igzip_lib.IgzipDecompressor()
    output, peak = allocation_peak(
        lambda: decoder.decompress(packed, len(data)))
    assert output == data
    # Codec state fits well within this margin; a second output copy does not.
    assert peak < len(data) * 3 // 2


@needs_tracemalloc
def test_gzip_reader_full_read_does_not_allocate_a_second_result():
    size = 256 * 1024  # Below the 10 * buffersize cap of a single read.
    data = random.Random(240).randbytes(size)
    reader = isal_zlib._GzipReader(io.BytesIO(gzip.compress(data)))
    output, peak = allocation_peak(lambda: reader.read(size))
    assert output == data
    assert peak < size * 3 // 2


@pytest.mark.parametrize("size", [0, 1, 131071, 131072, 131073,
                                  262144, 262145])
def test_gzip_reader_readall_at_chunk_boundaries(size):
    # readall() reads chunks of 4 * buffersize: 131072 bytes by default.
    data = random.Random(240).randbytes(size)
    reader = isal_zlib._GzipReader(io.BytesIO(gzip.compress(data)))
    output = reader.readall()
    assert type(output) is bytes
    assert output == data
    assert reader.readall() == b""


@needs_tracemalloc
@pytest.mark.parametrize("decoder", ["decompressobj", "IgzipDecompressor"])
def test_output_ending_at_the_first_buffer_size_does_not_grow_it(decoder):
    size = 16384  # DEF_BUF_SIZE, the first output allocation.
    data = random.Random(240).randbytes(size)
    if decoder == "decompressobj":
        obj = isal_zlib.decompressobj()
        packed = zlib.compress(data)
    else:
        obj = igzip_lib.IgzipDecompressor()
        packed = zlib.compress(data, wbits=-15)
    output, peak = allocation_peak(lambda: obj.decompress(packed))
    assert output == data
    assert obj.eof
    # Growing to 32 KiB at the end of the stream raises the peak to about
    # 32 KiB on full-API builds and 48 KiB with the Limited API copy.
    full_api = sysconfig.get_config_var("Py_GIL_DISABLED")
    assert peak < (size * 3 // 2 if full_api else size * 5 // 2)


def corrupt_last_byte(data):
    return data[:-1] + bytes([data[-1] ^ 1])


ERROR_DATA = random.Random(240).randbytes(256 * 1024)
ZLIB_DATA = zlib.compress(ERROR_DATA)
GZIP_DATA = gzip.compress(ERROR_DATA)


@needs_tracemalloc
@pytest.mark.parametrize("operation,error", [
    (lambda: isal_zlib.decompress(ZLIB_DATA[:-1]), isal_zlib.error),
    (lambda: igzip_lib.decompress(zlib.compress(ERROR_DATA, wbits=-15)[:-1]),
     igzip_lib.error),
    (lambda: isal_zlib.decompressobj().decompress(
        corrupt_last_byte(ZLIB_DATA)), isal_zlib.error),
    (lambda: igzip_lib.IgzipDecompressor(flag=igzip_lib.DECOMP_ZLIB)
     .decompress(corrupt_last_byte(ZLIB_DATA)), igzip_lib.error),
    (lambda: isal_zlib._GzipReader(io.BytesIO(GZIP_DATA[:-1]))
     .read(len(ERROR_DATA) + 1), EOFError),
    (lambda: isal_zlib._GzipReader(io.BytesIO(GZIP_DATA[:-1])).readall(),
     EOFError),
], ids=["decompress", "igzip_lib.decompress", "decompressobj",
        "IgzipDecompressor", "_GzipReader.read", "_GzipReader.readall"])
def test_invalid_input_releases_output(operation, error):
    import tracemalloc

    def fail_repeatedly():
        for _ in range(10):
            with pytest.raises(error):
                operation()

    # The first pass fills caches that would otherwise look like leaks.
    fail_repeatedly()
    gc.collect()
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    try:
        fail_repeatedly()
        gc.collect()
        retained = tracemalloc.get_traced_memory()[0] - before
    finally:
        if not tracing:
            tracemalloc.stop()
    # The output grew past 256 KiB before each error.
    assert retained < 64 * 1024


@pytest.mark.parametrize("size", [1, 65536, 65537])
def test_gzip_reader_full_and_short_bytes(size):
    data = random.Random(240).randbytes(size)
    reader = isal_zlib._GzipReader(io.BytesIO(gzip.compress(data)))
    output = reader.read(65536)
    assert type(output) is bytes
    assert output == data[:65536]
    assert reader.readall() == data[len(output):]


def test_gzip_reader_readinto_rejects_read_only_buffer():
    reader = isal_zlib._GzipReader(io.BytesIO(gzip.compress(b"data")))
    with pytest.raises(TypeError) as error:
        reader.readinto(b"read-only")
    # The same text as the readinto() methods of io.
    assert str(error.value) == ("readinto() argument must be read-write "
                                "bytes-like object, not bytes")


@pytest.mark.parametrize("name,factory", [("Compress", "compressobj"),
                                          ("Decompress", "decompressobj")])
def test_factory_retains_type_after_module_attribute_is_deleted(name, factory):
    # No test-side strong reference may keep the heap type alive.
    code = f"""
import gc
import weakref
from isal import isal_zlib
reference = weakref.ref(getattr(isal_zlib, {name!r}))
delattr(isal_zlib, {name!r})
gc.collect()
obj = getattr(isal_zlib, {factory!r})()
assert type(obj) is reference()
"""
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize("name", ["Compress", "Decompress"])
def test_factory_types_cannot_be_instantiated(name):
    with pytest.raises(TypeError):
        getattr(isal_zlib, name)()


@pytest.mark.parametrize("cls", [isal_zlib.Compress, isal_zlib.Decompress,
                                 igzip_lib.IgzipDecompressor,
                                 isal_zlib._GzipReader,
                                 isal_zlib._ParallelCompress])
def test_extension_types_remain_immutable_and_cannot_be_subclassed(cls):
    with pytest.raises(TypeError):
        cls.extra_attribute = True
    with pytest.raises(TypeError):
        type("Subclass", (cls,), {})


@pytest.mark.skipif(sys.implementation.name != "cpython" or
                    sysconfig.get_config_var("Py_GIL_DISABLED"),
                    reason="Needs exact reference counts of CPython types")
@pytest.mark.parametrize("factory", [
    isal_zlib.compressobj, isal_zlib.decompressobj,
    igzip_lib.IgzipDecompressor,
    lambda: isal_zlib._GzipReader(io.BytesIO()),
    lambda: isal_zlib._ParallelCompress(65536, 1)])
def test_instances_release_their_type(factory):
    cls = type(factory())
    gc.collect()
    before = sys.getrefcount(cls)
    for _ in range(100):
        instance = factory()
    del instance
    gc.collect()
    assert sys.getrefcount(cls) == before


EXTENSION_MODULES = {"isal_zlib": isal_zlib, "igzip_lib": igzip_lib,
                     "_isal": _isal}


@pytest.mark.parametrize("module", EXTENSION_MODULES.values(),
                         ids=EXTENSION_MODULES.keys())
def test_types_are_named_after_the_module_that_exports_them(module):
    types = [value for value in vars(module).values()
             if isinstance(value, type)]
    if module is isal_zlib:
        types += [type(isal_zlib.compressobj()),
                  type(isal_zlib.decompressobj())]
    for cls in types:
        # IsalError is defined by igzip_lib and also exported by isal_zlib.
        assert cls.__module__ in EXTENSION_MODULES, cls
        assert getattr(EXTENSION_MODULES[cls.__module__], cls.__name__) is cls


@pytest.mark.skipif(not sysconfig.get_config_var("Py_GIL_DISABLED"),
                    reason="Needs a free-threaded interpreter")
def test_import_keeps_the_gil_disabled():
    env = os.environ.copy()
    env.pop("PYTHON_GIL", None)
    code = """
import sys
assert not sys._is_gil_enabled()
from isal import igzip_lib, isal_zlib
assert not sys._is_gil_enabled()
"""
    result = subprocess.run([sys.executable, "-c", code], env=env,
                            capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
