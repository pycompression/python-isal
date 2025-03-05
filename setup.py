# Copyright (c) 2020 Leiden University Medical Center
# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import functools
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from setuptools import Extension, find_packages, setup
from setuptools.command.build_ext import build_ext

import versioningit

ISA_L_SOURCE = os.path.join("src", "isal", "isa-l")

SYSTEM_IS_BSD = (sys.platform.startswith("freebsd") or
                 sys.platform.startswith("netbsd"))
SYSTEM_IS_UNIX = (sys.platform.startswith("linux") or
                  sys.platform.startswith("darwin") or
                  sys.platform.startswith("gnu") or
                  SYSTEM_IS_BSD)
SYSTEM_IS_WINDOWS = sys.platform.startswith("win")

# Since pip builds in a temp directory by default, setting a fixed file in
# /tmp works during the entire session.
DEFAULT_CACHE_FILE = Path(tempfile.gettempdir()
                          ).absolute() / ".isal_build_cache"
BUILD_CACHE = os.environ.get("PYTHON_ISAL_BUILD_CACHE")
BUILD_CACHE_FILE = Path(os.environ.get("PYTHON_ISAL_BUILD_CACHE_FILE",
                                       DEFAULT_CACHE_FILE))

EXTENSIONS = [
    Extension("isal.isal_zlib", ["src/isal/isal_zlibmodule.c"]),
    Extension("isal.igzip_lib", ["src/isal/igzip_libmodule.c"]),
    Extension("isal._isal", ["src/isal/_isalmodule.c"]),
    ]


class BuildIsalExt(build_ext):
    def build_extension(self, ext):
        # Add option to link dynamically for packaging systems such as conda.
        # Always link dynamically on readthedocs to simplify install.
        if (os.getenv("PYTHON_ISAL_LINK_DYNAMIC") is not None or
                os.environ.get("READTHEDOCS") is not None):
            # Check for isa-l include directories. This is useful when
            # installing in a conda environment.
            possible_prefixes = [sys.exec_prefix, sys.base_exec_prefix]
            for prefix in possible_prefixes:
                if Path(prefix, "include", "isa-l").exists():
                    ext.include_dirs = [os.path.join(prefix, "include")]
                    ext.library_dirs = [os.path.join(prefix, "lib")]
                    break   # Only one include directory is needed.
                # On windows include is in Library apparently
                elif Path(prefix, "Library", "include", "isa-l").exists():
                    ext.include_dirs = [os.path.join(prefix, "Library",
                                                     "include")]
                    ext.library_dirs = [os.path.join(prefix, "Library", "lib")]
                    break
            if SYSTEM_IS_UNIX:
                ext.libraries = ["isal"]  # libisal.so*
            elif SYSTEM_IS_WINDOWS:
                ext.libraries = ["isa-l"]  # isa-l.dll
            else:
                raise NotImplementedError(
                    f"Unsupported platform: {sys.platform}")
        else:
            isa_l_build_dir = build_isa_l()
            if SYSTEM_IS_UNIX:
                ext.extra_objects = [
                    os.path.join(isa_l_build_dir, "bin", "isa-l.a")]
            elif SYSTEM_IS_WINDOWS:
                ext.extra_objects = [
                    os.path.join(isa_l_build_dir, "isa-l_static.lib")]
            else:
                raise NotImplementedError(
                    f"Unsupported platform: {sys.platform}")
            ext.include_dirs = [isa_l_build_dir]
        super().build_extension(ext)


# Use a cache to prevent isa-l from being build twice. According to the
# functools docs lru_cache with maxsize None is faster. The shortcut called
# 'cache' is only available from python 3.9 onwards.
# see: https://docs.python.org/3/library/functools.html#functools.cache
@functools.lru_cache(maxsize=None)
def build_isa_l():
    # Check for cache
    if BUILD_CACHE:
        if BUILD_CACHE_FILE.exists():
            cache_path = Path(BUILD_CACHE_FILE.read_text())
            if (cache_path / "isa-l.h").exists():
                return str(cache_path)

    # Creating temporary directories
    build_dir = tempfile.mktemp()
    shutil.copytree(ISA_L_SOURCE, build_dir)

    # Build environment is a copy of OS environment to allow user to influence
    # it.
    build_env = os.environ.copy()
    if SYSTEM_IS_UNIX:
        build_env["CFLAGS"] = build_env.get("CFLAGS", "") + " -fPIC"
    if hasattr(os, "sched_getaffinity"):
        cpu_count = len(os.sched_getaffinity(0))
    else:  # sched_getaffinity not available on all platforms
        cpu_count = os.cpu_count() or 1  # os.cpu_count() can return None
    run_args = dict(cwd=build_dir, env=build_env)
    if SYSTEM_IS_UNIX:
        if platform.machine() == "aarch64":
            cflags_param = "CFLAGS_aarch64"
        else:
            cflags_param = "CFLAGS_"
        make_cmd = "make"
        if SYSTEM_IS_BSD:
            make_cmd = "gmake"
        subprocess.run([make_cmd, "-j", str(cpu_count), "-f", "Makefile.unx",
                        "isa-l.h", "bin/isa-l.a",
                        f"{cflags_param}={build_env.get('CFLAGS', '')}"],
                       **run_args)
    elif SYSTEM_IS_WINDOWS:
        subprocess.run(["nmake", "/f", "Makefile.nmake"], **run_args)
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    shutil.copytree(os.path.join(build_dir, "include"),
                    os.path.join(build_dir, "isa-l"))
    if BUILD_CACHE:
        BUILD_CACHE_FILE.write_text(build_dir)
    return build_dir


setup(
    name="isal",
    version=versioningit.get_version(),
    description="Faster zlib and gzip compatible compression and "
                "decompression by providing python bindings for the ISA-L "
                "library.",
    author="Leiden University Medical Center",
    author_email="r.h.p.vorderman@lumc.nl",  # A placeholder for now
    long_description=Path("README.rst").read_text(),
    long_description_content_type="text/x-rst",
    cmdclass={"build_ext": BuildIsalExt},
    license="PSF-2.0",
    keywords="isal isa-l compression deflate gzip igzip threads",
    zip_safe=False,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'isal': ['*.pyi', 'py.typed',
                           # Include isa-l LICENSE and other relevant files
                           # with the binary distribution.
                           'isa-l/LICENSE', 'isa-l/README.md',
                           'isa-l/Release_notes.txt']},
    url="https://github.com/pycompression/python-isal",
    classifiers=[
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
        "Programming Language :: Python :: Implementation :: CPython",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Programming Language :: C",
        "Development Status :: 5 - Production/Stable",
        "Topic :: System :: Archiving :: Compression",
        "License :: OSI Approved :: Python Software Foundation License",
        "Operating System :: POSIX :: Linux",
        "Operating System :: MacOS",
        "Operating System :: Microsoft :: Windows",
    ],
    python_requires=">=3.8",  # BadGzipFile imported
    ext_modules=EXTENSIONS
)
