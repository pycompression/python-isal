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
import functools
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext

ISA_L_SOURCE = os.path.join("src", "isal", "isa-l")


class IsalExtension(Extension):
    """Custom extension to allow for targeted modification."""
    pass


class BuildIsalExt(build_ext):
    def build_extension(self, ext):
        if not isinstance(ext, IsalExtension):
            super().build_extension(ext)
            return

        # Add option to link dynamically for packaging systems such as conda.
        # Always link dynamically on readthedocs to simplify install.
        if (os.getenv("PYTHON_ISAL_LINK_DYNAMIC") is not None or
                os.environ.get("READTHEDOCS") is not None):
            # Check for isa-l include directories. This is useful when
            # installing in a conda environment.
            possible_prefixes = [sys.exec_prefix, sys.base_exec_prefix]
            for prefix in possible_prefixes:
                if os.path.exists(os.path.join(prefix, "include", "isa-l")):
                    ext.include_dirs = [
                        os.path.join(prefix, "include")]
                    break  # Only one include directory is needed.
            ext.libraries = ["isal"]
        else:
            isa_l_prefix_dir = build_isa_l()
            ext.include_dirs = [os.path.join(isa_l_prefix_dir,
                                             "include")]
            # -fPIC needed for proper static linking
            ext.extra_compile_args = ["-fPIC"]
            ext.extra_objects = [
                os.path.join(isa_l_prefix_dir, "lib", "libisal.a")]

        if os.getenv("CYTHON_COVERAGE") is not None:
            # Import cython here so python setup.py can be used without
            # installing cython.
            from Cython.Build import cythonize
            # Add cython directives and macros for coverage support.
            cythonized_exts = cythonize(ext, compiler_directives=dict(
                linetrace=True
            ))
            for cython_ext in cythonized_exts:
                cython_ext.define_macros = [("CYTHON_TRACE_NOGIL", "1")]
                cython_ext._needs_stub = False
                super().build_extension(cython_ext)
            return

        super().build_extension(ext)


# Use a cache to prevent isa-l from being build twice. According to the
# functools docs lru_cache with maxsize None is faster. The shortcut called
# 'cache' is only available from python 3.9 onwards.
# see: https://docs.python.org/3/library/functools.html#functools.cache
@functools.lru_cache(maxsize=None)
def build_isa_l():
    # Creating temporary directories
    build_dir = tempfile.mktemp()
    temp_prefix = tempfile.mkdtemp()
    shutil.copytree(ISA_L_SOURCE, build_dir)

    # Build environment is a copy of OS environment to allow user to influence
    # it.
    build_env = os.environ.copy()
    # Add -fPIC flag to allow static compilation
    build_env["CFLAGS"] = build_env.get("CFLAGS", "") + " -fPIC"
    if hasattr(os, "sched_getaffinity"):
        cpu_count = len(os.sched_getaffinity(0))
    else:  # sched_getaffinity not available on all platforms
        cpu_count = os.cpu_count() or 1  # os.cpu_count() can return None
    run_args = dict(cwd=build_dir, env=build_env)
    subprocess.run(os.path.join(build_dir, "autogen.sh"), **run_args)
    subprocess.run([os.path.join(build_dir, "configure"),
                    "--prefix", temp_prefix], **run_args)
    subprocess.run(["make", "-j", str(cpu_count)],
                   **run_args)
    subprocess.run(["make", "install"], **run_args)
    shutil.rmtree(build_dir)
    return temp_prefix


setup(
    name="isal",
    version="0.4.0",
    description="Faster zlib and gzip compatible compression and "
                "decompression by providing python bindings for the isa-l "
                "library.",
    author="Leiden University Medical Center",
    author_email="r.h.p.vorderman@lumc.nl",  # A placeholder for now
    long_description=Path("README.rst").read_text(),
    long_description_content_type="text/x-rst",
    cmdclass={"build_ext": BuildIsalExt},
    license="MIT",
    keywords="isal isa-l compression deflate gzip igzip",
    zip_safe=False,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'isal': ['*.pxd', '*.pyx',
                           # Include isa-l LICENSE and other relevant files
                           # with the binary distribution.
                           'isa-l/LICENSE', 'isa-l/README.md',
                           'isa-l/Release_notes.txt']},
    url="https://github.com/pycompression/python-isal",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Cython",
        "Development Status :: 3 - Alpha",
        "Topic :: System :: Archiving :: Compression",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS"
    ],
    python_requires=">=3.6",
    ext_modules=[
        IsalExtension("isal.isal_zlib", ["src/isal/isal_zlib.pyx"]),
        IsalExtension("isal._isal", ["src/isal/_isal.pyx"]),
    ]
)
