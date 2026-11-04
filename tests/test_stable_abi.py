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

from isal import igzip_lib, isal_zlib

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
])
def test_output_allocation_failure_cleanup(operation):
    pytest.importorskip("_testcapi")
    code = f"""
import random
import zlib
import _testcapi
from isal import igzip_lib, isal_zlib
data = random.Random(240).randbytes(256 * 1024)
packed = zlib.compress(data)
raw = zlib.compress(data, wbits=-15)
def stream_compress():
    obj = isal_zlib.compressobj()
    return obj.compress(data) + obj.flush()
def operation():
    return {operation}
failures = successes = 0
for start in range(40):
    _testcapi.set_nomemory(start, start + 1)
    try:
        result = operation()
    except MemoryError:
        failures += 1
    else:
        successes += 1
    finally:
        _testcapi.remove_mem_hooks()
assert failures and successes
# A clean call after all failure paths still produces valid output.
result = operation()
if 'compress' in {operation!r} and 'decompress' not in {operation!r}:
    wbits = -15 if {operation!r}.startswith('igzip') else 15
    assert zlib.decompress(result, wbits=wbits) == data
else:
    assert result == data
"""
    result = subprocess.run([sys.executable, "-c", code],
                            capture_output=True, text=True, timeout=45)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(sys.implementation.name != "cpython",
                    reason="Needs CPython tracemalloc allocation accounting")
def test_full_bounded_output_does_not_allocate_a_second_result():
    import tracemalloc

    data = b"filled buffer" * 100000
    packed = igzip_lib.compress(data)
    gc.collect()
    tracing = tracemalloc.is_tracing()
    if not tracing:
        tracemalloc.start()
    before, _ = tracemalloc.get_traced_memory()
    tracemalloc.reset_peak()
    try:
        decoder = igzip_lib.IgzipDecompressor()
        output = decoder.decompress(packed, len(data))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        if not tracing:
            tracemalloc.stop()
    assert output == data
    # Codec state fits well within this margin; a second output copy does not.
    assert peak - before < len(data) * 3 // 2


@pytest.mark.parametrize("size", [1, 65536, 65537])
def test_gzip_reader_full_and_short_bytes(size):
    data = random.Random(240).randbytes(size)
    reader = isal_zlib._GzipReader(io.BytesIO(gzip.compress(data)))
    output = reader.read(65536)
    assert type(output) is bytes
    assert output == data[:65536]
    assert reader.readall() == data[len(output):]


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
