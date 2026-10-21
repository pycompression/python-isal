"""Use isal from more than one interpreter."""
import gzip
import sys
import sysconfig
import textwrap

from isal import igzip, igzip_lib, isal_zlib

import pytest


@pytest.mark.skipif(sys.implementation.name != "cpython",
                    reason="Needs _testcapi.run_in_subinterp")
@pytest.mark.skipif(bool(sysconfig.get_config_var("Py_GIL_DISABLED")),
                    reason="Free-threaded subinterpreters cannot import isal")
def test_errors_after_import_in_subinterpreter():
    _testcapi = pytest.importorskip("_testcapi")
    # Each interpreter has its own gzip.BadGzipFile class. An error that the
    # except clause does not catch makes run_in_subinterp return -1.
    code = textwrap.dedent("""
        import gzip
        from isal import igzip, igzip_lib, isal_zlib
        for decompress, error in [(isal_zlib.decompress, isal_zlib.error),
                                  (igzip_lib.decompress, igzip_lib.error),
                                  (igzip.decompress, gzip.BadGzipFile)]:
            try:
                decompress(b"not compressed")
            except error:
                pass
    """)
    assert _testcapi.run_in_subinterp(code) == 0
    with pytest.raises(isal_zlib.error):
        isal_zlib.decompress(b"not compressed")
    with pytest.raises(igzip_lib.error):
        igzip_lib.decompress(b"not compressed")
    with pytest.raises(gzip.BadGzipFile):
        igzip.decompress(b"not compressed")
