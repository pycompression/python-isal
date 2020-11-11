# Copyright (c) 2020 Leiden University Medical Center
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import os
import sys
from pathlib import Path

from setuptools import Extension, find_packages, setup

EXTENSION_OPTS = dict()

# Make sure conda prefix is loaded if installed in a conda environment.
CONDA_PREFIX = os.environ.get("CONDA_PREFIX")
if CONDA_PREFIX:
    EXTENSION_OPTS["include_dirs"] = [os.path.join(CONDA_PREFIX, "include")]
if os.environ.get("READTHEDOCS"):
    # Readthedocs uses a conda environment but does not activate it.
    EXTENSION_OPTS["include_dirs"] = [os.path.join(sys.exec_prefix, "include")]

setup(
    name="isal",
    version="0.1.0",
    description="Faster zlib and gzip compatible compression and "
                "decompression by providing python bindings for the isa-l "
                "library.",
    author="Leiden University Medical Center",
    author_email="r.h.p.vorderman@lumc.nl",  # A placeholder for now
    long_description=Path("README.rst").read_text(),
    long_description_content_type="text/x-rst",
    license="MIT",
    keywords="isal isa-l compression deflate gzip igzip",
    zip_safe=False,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'isal': ['*.pxd', '*.pyx']},
    url="https://github.com/rhpvorderman/python-isal",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Cython",
        "Development Status :: 3 - Alpha",
        "Topic :: System :: Archiving :: Compression",
        "License :: OSI Approved :: MIT License",
    ],
    python_requires=">=3.6",
    setup_requires=["cython"],
    install_requires=[],
    ext_modules=[
        Extension("isal.isal_zlib", ["src/isal/isal_zlib.pyx"],
                  libraries=["isal"], **EXTENSION_OPTS),
        Extension("isal._isal", ["src/isal/_isal.pyx"],
                  libraries=["isal"], **EXTENSION_OPTS),
    ]
)
