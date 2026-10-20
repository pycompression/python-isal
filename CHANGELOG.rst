==========
Changelog
==========

.. Newest changes should be on top.

.. This document is user facing. Please word the changes in such a way
.. that users understand how the changes affect the new version.


version 1.8.1-dev
-----------------
+ Speed up ``import isal.igzip`` and ``import isal.igzip_threaded`` by
  importing ``argparse`` and ``shutil`` only when the command line interface
  runs, and by dropping the ``multiprocessing`` import.
+ Updated ISA-L to 2.32.1.
+ Python 3.10 and PyPy 3.10 are no longer supported. Added support for PyPy
  3.12 and Python 3.15.
+ Restore PyPy wheel builds.
+ Speed up reading lines from binary ``igzip`` files through iteration,
  ``readlines()``, and ``readline()``. On an Apple M4, reading FASTQ data is
  1.13 times faster, and reading lines of a few bytes is 1.5 times faster.
+ Speed up each ``write()`` call to binary ``igzip`` files on CPython. On an
  AMD Ryzen 7 9800X3D with Python 3.14.8, writing FASTQ data or Python source
  code one line at a time is 1.1 times faster.
+ Fix zlib streams compressed with a preset dictionary so they can be decoded
  by standard zlib, including builds linked against older ISA-L releases.
+ Fix backward seeking in igzip files by discarding buffered compressed data
  when rewinding the underlying file.
+ Fix a crash when ``igzip.decompress`` gets an object that is not
  bytes-like, such as a ``str``. It raises a ``TypeError`` instead.
+ Fix a crash after creating ``igzip_lib.IgzipDecompressor`` objects with a
  ``zdict``.
+ Fix a hang in ``isal_zlib.Compress``: after ``flush()`` raised an error for
  an unsupported mode, the next call on the same object never returned.
+ Fix a crash when you call ``flush(Z_FINISH)`` twice on a level 0
  ``isal_zlib.Compress`` object.
+ Fix ``unused_data`` of ``isal_zlib.Decompress`` and
  ``igzip_lib.IgzipDecompressor``, which could contain bytes from outside the
  input buffer when ``max_length`` split the end of a stream. At the end of a
  stream, ``isal_zlib.Decompress.unconsumed_tail`` is empty, matching the
  CPython fix for gh-158169.
+ ``igzip_threaded.open`` raises ``ValueError`` for a ``block_size`` of about
  3.6 GiB or more and ``TypeError`` for a ``compresslevel`` that is not an
  integer. Both raised ``SystemError`` before.
+ Fix ``igzip_threaded`` writers at compression level 0, which raised
  ``OverflowError`` for data that does not compress, such as random bytes or
  already compressed files. At compression level 0, ``block_size`` must now be
  less than about 2 GiB.
+ Extraordinarily large gzip headers with either a very long comment or
  filename will now cause an ``OverflowError`` rather than use more and more
  memory. The size is limited to the internal buffer size which is currently
  set at 512 KiB.
+ Fix ``igzip_threaded`` readers and writers that waited for a polling timeout
  of up to 50 ms at the end of the stream or when closed. Writing and closing
  a small file takes less than a millisecond instead of 60 ms.
+ Speed up many small writes to ``igzip.IGzipFile`` on Python 3.12 and later.
  ``IGzipFile`` collects these writes in the write buffer of
  ``gzip.GzipFile`` and compresses them in large chunks, which makes writing
  lines 1.4 times faster.
+ Fix builds on macOS with Apple Silicon, which used the portable C code of
  ISA-L rather than its optimized aarch64 assembly. On an Apple M4,
  decompression is 1.6 to 3 times faster, CRC-32 is 50 times faster, and
  Adler-32 is 7 times faster.
+ Fix ``igzip_threaded`` writers that waited forever when writing to the
  underlying file failed, for example, because the disk was full. A later call
  to ``write()``, ``flush()``, or ``close()`` raises the error. After an error,
  ``close()`` no longer closes a file object that you passed to
  ``igzip_threaded.open``.
+ Fix a crash on the free-threaded build when one thread reads
  ``unused_data`` or ``unconsumed_tail`` of an ``isal_zlib`` decompressor
  while another thread decompresses with it. Reading the attributes of
  ``isal_zlib`` decompressors and ``igzip_lib.IgzipDecompressor`` from other
  threads is now safe, and so is calling ``decompress()`` from several
  threads at the same time when ``wbits`` detects the format.
+ ``isal_zlib.crc32_combine`` and the ``read()`` and ``seek()`` methods of the
  private ``isal_zlib._GzipReader`` class raise ``TypeError`` instead of
  ``SystemError`` for arguments of the wrong type or number.
  ``igzip.IGzipFile`` was not affected.
+ Fix ``isal_zlib.decompressobj`` with a ``wbits`` of 40 to 47, which detects
  zlib or gzip data. It failed on gzip data when the first ``decompress()``
  call got fewer than 2 bytes, for example, when the data arrived byte by
  byte.
+ Fix ``isal_zlib.decompressobj`` with a ``wbits`` of 40 to 47 after a
  ``flush()`` call that came before any data. It then failed on both zlib and
  gzip data.
+ Fix a crash on PyPy when you create an ``isal_zlib.Compress`` or
  ``isal_zlib.Decompress`` object by calling the type, for example,
  ``isal_zlib.Compress()``, and then use it. Calling the type raises
  ``TypeError`` now, as it does on CPython. Use ``compressobj()`` and
  ``decompressobj()`` instead.
+ Fix error handling when more than one interpreter imports
  ``isal.isal_zlib`` or ``isal.igzip_lib``, for example, the main interpreter
  and a legacy subinterpreter that ``Py_NewInterpreter()`` creates. Each
  import replaced the error classes that the C code raises, so
  ``except isal_zlib.error``, ``except igzip_lib.error``, and
  ``except gzip.BadGzipFile`` caught errors only in the interpreter that
  imported the modules last.
+ Fix ``readinto()`` of the private ``isal_zlib._GzipReader`` class, which
  wrote into read-only objects such as ``bytes``. It raises ``TypeError`` now.
  ``igzip.IGzipFile`` was not affected.
+ Fix a crash when there is not enough memory to create an
  ``igzip_lib.IgzipDecompressor``. It raises ``MemoryError`` now.

version 1.8.0
-----------------
+ Python 3.14 is supported.
+ Python 3.8 and 3.9 are no longer supported.
+ Fix an issue where flushing using igzip_threaded caused a gzip end of stream
  and started a new gzip stream. In essence creating a concatenated gzip
  stream. Now it is in concordance with how single threaded gzip streams
  are flushed using Z_SYNC_FLUSH.
+ Change build backend to setuptools-scm which is more commonly used and
  supported.
+ Include test packages in the source distribution, so source distribution
  installations can be verified.
+ Fix an issue where some tests failed because they ignored PYTHONPATH.
+ Enable support for free-threading and build free-threaded wheels for
  CPython 3.14. Thanks to @lysnikolaou and @ngoldbaum.

version 1.7.2
-----------------
+ Use upstream ISA-L version 2.31.1 which includes patches to make 
  installation on MacOS ARM64 possible.
+ Fix a bug where bytes were copied in the wrong order on big endian
  architectures. Fixes test failures on s390x.
+ Enable building on GNU/Hurd platforms.

version 1.7.1
-----------------
+ Fix a bug where flushing files when writing in threaded mode did not work
  properly.
+ Prevent threaded opening from blocking python exit when an error is thrown
  in the calling thread.

version 1.7.0
-----------------
+ Include a patched ISA-L version 2.31. The applied patches make compilation
  and wheelbuilding on MacOS ARM64 possible.
+ Fix a bug where READ and WRITE in isal.igzip were inconsistent with the
  values in gzip on Python 3.13
+ Small simplifications to the ``igzip.compress`` function, which should lead
  to less overhead.

version 1.6.1
-----------------
+ Fix a bug where streams that were passed to igzip_threaded.open where closed.

version 1.6.0
-----------------
+ Fix a bug where compression levels for IGzipFile where checked in read mode.
+ Update statically linked ISA-L release to 2.31.0
+ Fix an error that occurred in the ``__close__`` function when a threaded
  writer was initialized with incorrect parameters.

version 1.5.3
-----------------
+ Fix a bug where append mode would not work when using
  ``igzip_threaded.open``.

version 1.5.2
-----------------
+ Fix a bug where a filehandle remained opened when ``igzip_threaded.open``
  was used for writing with a wrong compression level.
+ Fix a memory leak that occurred when an error was thrown for a gzip header
  with the wrong magic numbers.
+ Fix a memory leak that occurred when isal_zlib.decompressobj was given a
  wrong wbits value.

version 1.5.1
-----------------
+ Fix a memory leak in the GzipReader.readall implementation.

version 1.5.0
-----------------
+ Make a special case for threads==1 in ``igzip_threaded.open`` for writing
  files. This now combines the writing and compression thread for less
  overhead.
+ Maximize time spent outside the GIL for ``igzip_threaded.open`` writing.
  This has decreased wallclock time significantly.

version 1.4.1
-----------------
+ Fix several errors related to unclosed files and buffers.

version 1.4.0
-----------------
+ Drop support for python 3.7 and PyPy 3.8 as these are no longer supported.
  Add testing and support for python 3.12 and PyPy 3.10.
+ Added an experimental ``isal.igzip_threaded`` module which has an
  ``open`` function.
  This can be used to read and write large files in a streaming fashion
  while escaping the GIL.
+ The internal ``igzip._IGzipReader`` has been rewritten in C. As a result the
  overhead of decompressing files has significantly been reduced and
  ``python -m isal.igzip`` is now very close to the C ``igzip`` application.
+ The ``igzip._IGZipReader`` in C is now used in ``igzip.decompress``. The
  ``_GzipReader`` also can read from objects that support the buffer protocol.
  This has reduced overhead significantly.

version 1.3.0
-----------------
+ Gzip headers are now actively checked for a BGZF extra field. If found the
  block size is taken into account when decompressing. This has further
  improved bgzf decompression speed by 5% on some files compared to the
  more generic solution of 1.2.0.
+ Integrated CPython 3.11 code for reading gzip headers. This leads to more
  commonality between the python-isal code and the upstream gzip.py code.
  This has enabled the change above. It comes at the cost of a slight increase
  in overhead at the ``gzip.decompress`` function.

version 1.2.0
-----------------
+ Bgzip files are now detected and a smaller reading buffer is used to
  accomodate the fact that bgzip blocks are typically less than 64K. (Unlike
  normal gzip files that consist of one block that spans the entire file.)
  This has reduced decompression time for bgzip files by roughly 12%.
+ Speed-up source build by using ISA-L Unix-specific makefile rather than the
  autotools build.
+ Simplify build setup. ISA-L release flags are now used and not
  overwritten with python release flags when building the included static
  library.
+ Fix bug where zdict's could not be set for ``isal_zlib.decompressobj`` and
  ``igzip_lib.IgzipDecompressor``.
+ Escape GIL when calling inflate, deflate, crc32 and adler32 functions just
  like in CPython. This allows for utilising more CPU cores in combination
  with the threading module. This comes with a very slight cost in efficiency
  for strict single-threaded applications.

version 1.1.0
-----------------
+ Added tests and support for Python 3.11.

version 1.0.1
------------------
+ Fixed failing tests and wheel builds for PyPy.

version 1.0.0
------------------
Python-isal has been rewritten as a C-extension (first implementation was in
Cython). This has made the library faster in many key areas.

+ Since the module now mostly contains code copied from CPython and then
  modified to work with ISA-L the license has been changed to the
  Python Software Foundation License version 2.
+ Python versions lower than 3.7 are no longer supported. Python 3.6 is out
  of support since December 2021.
+ Stub files with type information have now been updated to correctly display
  positional-only arguments.
+ Expose ``READ`` and ``WRITE`` constants on the ``igzip`` module. These are
  also present in Python's stdlib ``gzip`` module and exposing them allows for
  better drop-in capability of ``igzip``. Thanks to @alexander-beedie in
  https://github.com/pycompression/python-isal/pull/115.
+ A ``--no-name`` flag has been added to ``python -m isal.igzip``.
+ Reduced wheel size by not including debug symbols in the binary. Thanks to
  @marcelm in https://github.com/pycompression/python-isal/pull/108.
+ Cython is no longer required as a build dependency.
+ isal_zlib.compressobj and isal_zlib.decompressobj are now about six times
  faster.
+ igzip.decompress has 30% less overhead when called.
+ Error structure has been simplified. There is only ``IsalError`` which has
  ``Exception`` as baseclass instead of ``OSError``. ``isal_zlib.IsalError``,
  ``igzip_lib.IsalError``, ``isal_zlib.error`` and ``igzip_lib.error`` are
  all aliases of the same error class.
+ GzipReader now uses larger input and output buffers (128k) by default and
  IgzipDecompressor.decompress has been updated to allocate ``maxsize`` buffers
  when these are of reasonable size, instead of growing the buffer to maxsize
  on every call. This has improved gzip decompression speeds by 7%.
+ Patch statically linked included library (ISA-L 2.30.0) to fix the following:

  + ISA-L library version variables are now available on windows as well,
    for the statically linked version available on PyPI.
  + Wheels are now always build with nasm for the x86 architecture.
    Previously yasm was used for Linux and MacOS due to build issues.
  + Fixed a bug upstream in ISA-L were zlib headers would be created with an
    incorrect wbits value.

+ Python-isal shows up in Python profiler reports.
+ Support and tests for Python 3.10 were added.
+ Due to a change in the deployment process wheels should work for older
  versions of pip.
+ Added a ``crc`` property to the IgzipDecompressor class. Depending on the
  decompression flag chosen, this will update with an adler32 or crc32
  checksum.
+ All the decompression NO_HDR flags on igzip_lib were
  incorrectly documented. This is now fixed.

version 0.11.1
------------------
+ Fixed an issue which occurred rarely that caused IgzipDecompressor's
  unused_data to report back incorrectly. This caused checksum errors when
  reading gzip files. The issue was more likely to trigger in multi-member gzip
  files.

version 0.11.0
------------------
In this release the ``python -m isal.igzip`` relatively slow decompression rate
has been improved in both speed and usability. Previously it was 19% slower
than ``igzip`` when used with the ``-d`` flag for decompressing, now it is
just 8% slower. Also some extra flags were added to make it easier to select
the output file.

+ Prompt when an output file is overwritten with the ``python -m isal.igzip``
  command line utility and provide the ``-f`` or ``--force`` flags to force
  overwriting.
+ Added ``-o`` and ``--output`` flags to the ``python -m isal.igzip`` command
  line utility to allow the user to select the destination of the output file.
+ Reverse a bug in the build system which caused some docstring and parameter
  information on ``igzip_lib`` and ``isal_zlib`` to disappear in the
  documentation and the REPL.
+ Increase the buffer size for ``python -m isal.igzip`` so it is now closer
  to speeds reached with ``igzip``.
+ Add a ``READ_BUFFER_SIZE`` attribute to ``igzip`` which allows setting the
  amount of raw data that is read at once.
+ Add an ``igzip_lib.IgzipDecompressor`` object which can decompress without
  using an unconsumed_tail and is therefore more efficient.

version 0.10.0
------------------
+ Added an ``igzip_lib`` module which allows more direct access to ISA-L's
  igzip_lib API. This allows features such as headerless compression and
  decompression, as well as setting the memory levels manually.
+ Added more extensive documentation.

version 0.9.0
-----------------
+ Fix a bug where a AttributeError was triggered when zlib.Z_RLE or
  zlib.Z_FIXED were not present.
+ Add support for Linux aarch64 builds.
+ Add support for pypy by adding pypy tests to the CI and setting up wheel
  building support.

version 0.8.1
-----------------
+ Fix a bug where multi-member gzip files where read incorrectly due to an
  offset error. This was caused by ISA-L's decompressobj having a small
  bitbuffer which was not taken properly into account in some circumstances.

version 0.8.0
-----------------
+ Speed up ``igzip.compress`` and ``igzip.decompress`` by improving the
  implementation.
+ Make sure compiler arguments are passed to ISA-L compilation step. Previously
  ISA-L was compiled without optimisation steps, causing the statically linked
  library to be significantly slower.
+ A unused constant from the ``isal_zlib`` library was removed:
  ``ISAL_DEFAULT_HIST_BITS``.
+ Refactor isal_zlib.pyx to work almost the same as zlibmodule.c. This has made
  the code look cleaner and has reduced some overhead.

version 0.7.0
-----------------
+ Remove workarounds in the ``igzip`` module for the ``unconsumed_tail``
  and ``unused_data`` bugs. ``igzip._IGzipReader`` now functions the same
  as ``gzip._GzipReader`` with only a few calls replaced with ``isal_zlib``
  calls for speed.
+ Correctly implement ``unused_data`` and ``unconsumed_tail`` on
  ``isal_zlib.Decompress`` objects.
  It works the same as in CPython's zlib now.
+ Correctly implement flush implementation on ``isal_zlib.Compress`` and
  ``isal_zlib.Decompress`` objects.
  It works the same as in CPython's zlib now.

version 0.6.1
-----------------
+ Fix a crash that occurs when opening a file that did not end in ``.gz`` while
  outputting to stdout using ``python -m isal.igzip``.

version 0.6.0
-----------------
+ ``python -m gzip``'s behaviour has been changed since fixing bug:
  `bpo-43316 <https://bugs.python.org/issue43316>`_. This bug was not present
  in ``python -m isal.igzip`` but it handled the error differently than the
  solution in CPython. This is now corrected and ``python -m isal.igzip``
  handles the error the same as the fixed ``python -m gzip``.
+ Installation on Windows is now supported. Wheels are provided for Windows as
  well.

version 0.5.0
-----------------
+ Fix a bug where negative integers were not allowed for the ``adler32`` and
  ``crc32`` functions in ``isal_zlib``.
+ Provided stubs (type-hint files) for ``isal_zlib`` and ``_isal`` modules.
  Package is now tested with mypy to ensure correct type information.
+ The command-line interface now reads in blocks of 32K instead of 8K. This
  improves performance by about 6% when compressing and 11% when decompressing.
  A hidden ``-b`` flag was added to adjust the buffer size for benchmarks.
+ A ``-c`` or ``--stdout`` flag was added to the CLI interface of isal.igzip.
  This allows it to behave more like the ``gzip`` or ``pigz`` command line
  interfaces.

version 0.4.0
-----------------
+ Move wheel building to cibuildwheel on github actions CI. Wheels are now
  provided for Mac OS as well.
+ Make a tiny change in setup.py so python-isal can be build on Mac OS X.

version 0.3.0
-----------------
+ Set included ISA-L library at version 2.30.0.
+ Python-isal now comes with a source distribution of ISA-L in its source
  distribution against which python-isal is linked statically upon installation
  by default. Dynamic linking against system libraries is now optional. Wheels
  with the statically linked ISA-L are now provided on PyPI.

version 0.2.0
-----------------
+ Fixed a bug where writing of the gzip header would crash if an older version
  of Python 3.7 was used such as on Debian or Ubuntu. This is due to
  differences between point releases because of a backported feature. The code
  now checks if the backported feature is present.
+ Added Python 3.9 to the testing.
+ Fixed ``setup.py`` to list setuptools as a requirement.
+ Changed homepage to reflect move to pycompression organization.

version 0.1.0
-----------------
+ Publish API documentation on readthedocs.
+ Add API documentation.
+ Ensure the igzip module is fully compatible with the gzip stdlib module.
+ Add compliance tests from CPython to ensure isal_zlib and igzip are validated
  to the same standards as the zlib and gzip modules.
+ Added a working gzip app using ``python -m isal.igzip``
+ Add test suite that tests all possible settings for functions on the
  isal_zlib module.
+ Create igzip module which implements all gzip functions and methods.
+ Create isal_zlib module which implements all zlib functions and methods.
