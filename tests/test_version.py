"""Check the version module that setuptools-scm writes."""
import subprocess
import sys
from importlib import metadata

import isal


def test_version_matches_package_metadata():
    assert isal.__version__ == metadata.version("isal")


def test_version_does_not_import_future():
    code = ("import sys; before = set(sys.modules); "
            "from isal import __version__; "
            "print(*(set(sys.modules) - before))")
    result = subprocess.run([sys.executable, "-c", code], check=True,
                            capture_output=True, text=True)
    new_modules = set(result.stdout.split())
    assert "isal._version" in new_modules
    assert "__future__" not in new_modules
