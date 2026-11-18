"""Check the version module that setuptools-scm writes."""
from importlib import metadata

import isal


def test_version_matches_package_metadata():
    assert isal.__version__ == metadata.version("isal")
