# Copyright (c) 2020 Leiden University Medical Center
# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

import copy
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

SYSTEM_IS_UNIX = (sys.platform.startswith("linux") or
                  sys.platform.startswith("darwin"))
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
    ]

# This does not add the extension on windows for dynamic linking. The required
# header file might be missing.
if not (SYSTEM_IS_WINDOWS and
        os.getenv("PYTHON_ISAL_LINK_DYNAMIC") is not None):
    EXTENSIONS.append(Extension("isal._isal", ["src/isal/_isalmodule.c"]))


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
            if self.compiler.compiler_type == "msvc":
                compiler = copy.deepcopy(self.compiler)
                if not compiler.initialized:
                    compiler.initialize()
                compiler_command = f'"{compiler.cc}"'
                compiler_args = compiler.compile_options
            elif self.compiler.compiler_type == "unix":
                compiler_command = self.compiler.compiler[0]
                compiler_args = self.compiler.compiler[1:]
            else:
                raise NotImplementedError("Unknown compiler")
            isa_l_prefix_dir = build_isa_l(compiler_command,
                                           " ".join(compiler_args))
            if SYSTEM_IS_UNIX:
                ext.extra_objects = [
                    os.path.join(isa_l_prefix_dir, "lib", "libisal.a")]
            elif SYSTEM_IS_WINDOWS:
                ext.extra_objects = [
                    os.path.join(isa_l_prefix_dir, "isa-l_static.lib")]
            else:
                raise NotImplementedError(
                    f"Unsupported platform: {sys.platform}")
            ext.include_dirs = [os.path.join(isa_l_prefix_dir,
                                             "include")]
            # -fPIC needed for proper static linking
            ext.extra_compile_args = ["-fPIC"]
        super().build_extension(ext)


# Use a cache to prevent isa-l from being build twice. According to the
# functools docs lru_cache with maxsize None is faster. The shortcut called
# 'cache' is only available from python 3.9 onwards.
# see: https://docs.python.org/3/library/functools.html#functools.cache
@functools.lru_cache(maxsize=None)
def build_isa_l(compiler_command: str, compiler_options: str):
    # Check for cache
    if BUILD_CACHE:
        if BUILD_CACHE_FILE.exists():
            cache_path = Path(BUILD_CACHE_FILE.read_text())
            if (cache_path / "include" / "isa-l").exists():
                return str(cache_path)

    # Creating temporary directories
    build_dir = tempfile.mktemp()
    temp_prefix = tempfile.mkdtemp()
    shutil.copytree(ISA_L_SOURCE, build_dir)

    # Build environment is a copy of OS environment to allow user to influence
    # it.
    build_env = os.environ.copy()
    # Add -fPIC flag to allow static compilation
    build_env["CC"] = compiler_command
    if SYSTEM_IS_UNIX:
        build_env["CFLAGS"] = compiler_options + " -fPIC"
    elif SYSTEM_IS_WINDOWS:
        # The nmake file has CLFAGS_REL for all the compiler options.
        # This is added to CFLAGS with all the necessary include options.
        build_env["CFLAGS_REL"] = compiler_options
    if hasattr(os, "sched_getaffinity"):
        cpu_count = len(os.sched_getaffinity(0))
    else:  # sched_getaffinity not available on all platforms
        cpu_count = os.cpu_count() or 1  # os.cpu_count() can return None
    run_args = dict(cwd=build_dir, env=build_env)
    if SYSTEM_IS_UNIX:
        subprocess.run(os.path.join(build_dir, "autogen.sh"), **run_args)
        subprocess.run([os.path.join(build_dir, "configure"),
                        "--prefix", temp_prefix], **run_args)
        subprocess.run(["make", "-j", str(cpu_count)], **run_args)
        subprocess.run(["make", "-j", str(cpu_count), "install"], **run_args)
    elif SYSTEM_IS_WINDOWS:
        subprocess.run(["nmake", "/E", "/f", "Makefile.nmake"], **run_args)
        Path(temp_prefix, "include").mkdir()
        print(temp_prefix, file=sys.stderr)
        shutil.copytree(os.path.join(build_dir, "include"),
                        Path(temp_prefix, "include", "isa-l"))
        shutil.copy(os.path.join(build_dir, "isa-l_static.lib"),
                    os.path.join(temp_prefix, "isa-l_static.lib"))
        shutil.copy(os.path.join(build_dir, "isa-l.h"),
                    os.path.join(temp_prefix, "include", "isa-l.h"))
    else:
        raise NotImplementedError(f"Unsupported platform: {sys.platform}")
    shutil.rmtree(build_dir)
    if BUILD_CACHE:
        BUILD_CACHE_FILE.write_text(temp_prefix)
    return temp_prefix


setup(
    name="isal",
    version="1.0.1",
    description="Faster zlib and gzip compatible compression and "
                "decompression by providing python bindings for the ISA-L "
                "library.",
    author="Leiden University Medical Center",
    author_email="r.h.p.vorderman@lumc.nl",  # A placeholder for now
    long_description=Path("README.rst").read_text(),
    long_description_content_type="text/x-rst",
    cmdclass={"build_ext": BuildIsalExt},
    license="PSF-2.0",
    keywords="isal isa-l compression deflate gzip igzip",
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
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
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
    python_requires=">=3.7",  # We use METH_FASTCALL
    ext_modules=EXTENSIONS
)
