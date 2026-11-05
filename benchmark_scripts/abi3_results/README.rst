Stable ABI performance and compatibility
========================================

The stable ABI wheel (``cp311-abi3``) is slower than the original wheel where a
call returns its whole decompressed output at once: such calls take up to 23%
longer at 16 MiB + 137 bytes of output, where 6 of the 12 cases are beyond the
control's variation, and up to 2.160 times as long for 1 MiB + 137 bytes of
incompressible raw deflate data. Compression, CRC-32, gzip file reads, and
bounded ``IgzipDecompressor`` output show no measurable difference apart from
three outliers listed below.

All timings come from one Linux x86_64 machine (Intel i7-3770, no AVX2) and do
not establish behaviour on other hardware or runtimes. A ratio is candidate CPU
time divided by original-baseline CPU time; above 1 means slower.

Where the cost comes from
-------------------------

The stable ABI is the binary interface that one wheel can use on CPython 3.11
and later; the Limited API is the subset of the C API that builds against it.
``_PyBytes_Resize`` is not in the Limited API, so output that grows during a
call is kept in a ``PyMem`` buffer and copied into a new bytes object with
``PyBytes_FromStringAndSize`` when the call finishes. This is the design that
the python-isal maintainer, rhpvorderman, set out for this port in a
`comment on xopen#182
<https://github.com/pycompression/xopen/issues/182#issuecomment-6633029582>`_,
for the request in `python-isal#240
<https://github.com/pycompression/python-isal/issues/240>`_. This report calls
it *native output*.

These calls avoid the copy because their output goes straight into a
Python-owned object; output shorter than ``max_length`` or the requested size
is still copied:

- ``igzip_lib.IgzipDecompressor().decompress(data, max_length)`` when
  ``max_length`` is at most 16 MiB and the output fills it.
- ``isal_zlib.decompressobj().decompress(data, max_length)`` when
  ``max_length`` is at most 16 KiB and the output fills it.
- ``read()`` and ``readinto()`` on files from ``igzip.open()``, which read
  through ``_GzipReader.readinto()`` into Python-owned buffers.
  ``igzip.decompress()`` and ``read()`` without a size collect full chunks
  without a copy and copy only a short last chunk.

``isal_zlib.decompressobj().decompress(data, max_length)`` with a
``max_length`` above 16 KiB still starts from a 16 KiB allocation, grows it as
native output and copies it once. While the copy is made, the grown buffer and
the result are both alive, so peak memory is at least twice the output, where
the original wheel resized one bytes object. The first allocation is not raised
to ``max_length``, so that a large limit does not allocate memory that a
shorter output never uses. The same applies to ``IgzipDecompressor`` with a
``max_length`` above 16 MiB. The final-wheel benchmark below does not time
either case.

When ``IgzipDecompressor().decompress()`` returns less than a ``max_length``
of at most 16 MiB, or ``decompressobj().decompress()`` less than a
``max_length`` of at most 16 KiB, the copy is made while the
``max_length``-sized allocation is still held. Peak memory is then the limit
plus the output, where the original wheel shrank the allocation in place and
needed only the limit: for 12 MiB of output under a 16 MiB limit, 28 MiB
against 16 MiB. The random 1 KiB ``bounded-decompress`` case below shows the
time cost of such a copy for a small output.

Final installed-wheel comparison
--------------------------------

``cpython311.json`` holds all 27 worker runs: nine randomized paired rounds,
each timing the original baseline, the baseline again as a control, and the
candidate. It records input SHA-256 values, iteration counts, CPU and wall
times, and the interpreter and extension paths of each worker.
``cpython311.csv`` holds the median of the nine paired ratios for each of the
128 cases. Each case's output is checked against the original input or stdlib
``zlib`` outside the timed loop. Print every summary quoted here with::

    python benchmark_scripts/benchmark_abi3.py --library isal \
      --summarize benchmark_scripts/abi3_results/cpython311.json

Baseline: commit 2498167283fb4598d3daf757bc2a80b53d798c52, unchanged. Both
wheels use CPython 3.11.15, GCC 15.2.0 with ``-O3 -DNDEBUG``, and the same
ISA-L 2.32.1 build. The interpreter itself was built with Clang 22.1.1. The
worker is pinned to CPU 1 and the garbage collector is disabled in workers.
``build-metadata.json`` records the wheel and source SHA-256 values, the build
recipe, and the timing window. No build, test, or other benchmark ran during the
timings, but desktop processes (a remote-desktop service and a browser) did.

The workload has four corpora: the repository's FASTQ fixture, concatenated
stdlib Python source (repeating with a period longer than the deflate window),
seeded incompressible bytes, and zero bytes. Each corpus is cut to 1 KiB,
64 KiB, 1 MiB + 137, and 16 MiB + 137 bytes and compressed by stdlib ``zlib``
at level 6. Calibration runs on the baseline only and freezes iteration counts
for all variants: each case targets 20 ms, capped at 10,000 iterations. The
operations are:

=====================  ========================================================
Operation              Call
=====================  ========================================================
compress1              ``isal_zlib.compress(data, 1)``
decompress             ``isal_zlib.decompress(data)``
raw-decompress         ``igzip_lib.decompress(raw_deflate)``
stream-decompress      ``decompressobj()``: ``decompress(data)`` + ``flush()``
bounded-decompress     ``IgzipDecompressor().decompress(raw, 65536)`` in a loop
gzip-read128k          ``igzip.open(...).read(131072)`` in a loop
gzip-readinto128k      ``igzip.open(...).readinto(buffer)``, 128 KiB buffer
crc32                  ``isal_zlib.crc32(data)``
=====================  ========================================================

The control's absolute deviation from 1 across the 128 case medians is
4.345% at p95 and 9.116% at most. Every p95 in this report is the inclusive
percentile, ``statistics.quantiles(values, n=100, method="inclusive")[94]``.
A case counts as slower or faster only when it differs from 1 by more than the
control maximum of its own run; smaller differences count as no measurable
difference.

At 16 MiB + 137 bytes:

=====================  ======  ======  ======  ======
Operation              FASTQ   Python  Random  Zeros
=====================  ======  ======  ======  ======
compress1              1.021×  1.005×  0.943×  1.005×
decompress             1.060×  1.076×  1.193×  1.153×
raw-decompress         1.070×  1.085×  1.231×  1.195×
stream-decompress      1.052×  1.125×  1.208×  1.087×
bounded-decompress     1.047×  1.029×  1.036×  1.122×
gzip-read128k          1.007×  1.003×  0.973×  1.006×
gzip-readinto128k      0.996×  1.005×  1.039×  0.997×
crc32                  0.998×  1.014×  1.017×  1.014×
=====================  ======  ======  ======  ======

Across all four sizes and corpora, the median ratio and range per operation
are:

=====================  ======  =============
Operation              Median  Range
=====================  ======  =============
compress1              1.006×  0.943-1.091×
decompress             1.076×  0.890-1.504×
raw-decompress         1.078×  0.919-2.160×
stream-decompress      1.075×  0.859-1.519×
bounded-decompress     1.009×  0.939-1.151×
gzip-read128k          1.003×  0.965-1.060×
gzip-readinto128k      1.013×  0.996-1.115×
crc32                  1.003×  0.966-1.022×
=====================  ======  =============

Of the 128 cases, 22 are slower. Nineteen of them are whole-output decoding
(``decompress``, ``raw-decompress``, and ``stream-decompress``); the worst is
random 1 MiB + 137 ``raw-decompress`` at 2.160×, with ``decompress`` at
1.504× and ``stream-decompress`` at 1.519× for the same input, and zeros
1 MiB + 137 ``raw-decompress`` at 1.636×. The other three are:

- random 1 KiB ``bounded-decompress``, 1.151×. Its 1 KiB result is shorter
  than the 64 KiB limit, so it is copied where the original wheel shrank the
  bytes object. All four 1 KiB bounded cases copy, and only this one exceeds
  the control, so the copy is a plausible but unprofiled cause.
- zeros 16 MiB + 137 ``bounded-decompress``, 1.122×. This output fills
  every 64 KiB call and is not copied. The run committed at 65d3eb3, with
  the earlier candidate, measured 0.995× for this case, and the repair check
  below measured 1.005× between the two candidates. Run-to-run variation is
  the likely cause (interpretation).
- Python 1 KiB ``gzip-readinto128k``, 1.115×, unexplained; the change does
  not alter the ``readinto()`` output path.

Three cases are faster: FASTQ 1 MiB + 137 ``stream-decompress`` 0.859×
(its own control 0.986), ``decompress`` 0.896× (control 0.998), and FASTQ
1 KiB ``decompress`` 0.890× (control 0.909, so that case is noisy). The FASTQ
1 MiB + 137 gains were not profiled. The end-of-stream stop described below
does not explain them: the strategy studies' reference includes the stop and
native output was still 0.837-0.868× for FASTQ 1 MiB + 137 there.

The candidate also stops growing a decompression buffer once ISA-L reports the
end of the stream. Before, a stream that ended exactly when the buffer was
full grew it once more; the full-API builds get the same correction.

Earlier run and repair check
~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The same protocol was first run on the earlier candidate (commit 65d3eb3,
whose ``cpython311.json`` is in that commit). Its control was 2.170% at p95
and 4.121% at most. This run's control is about twice as wide, and some
candidate ratios are larger; the desktop processes noted above are the likely
cause (interpretation).

``repair-check.json`` times the earlier candidate's wheel as baseline and
control against this candidate, with the same protocol, immediately after the
final run. Its control was 4.175% at p95 and 6.836% at most. The per-operation
medians range 0.992-1.006, so the repairs show no measurable effect at the
operation level. Five of the 128 cases differ by more than the control
maximum, in both directions, four of them at 16 MiB + 137 bytes: random
16 MiB + 137 ``compress1`` 0.869×, ``stream-decompress`` 0.917×, and
``raw-decompress`` 1.072×, zeros
16 MiB + 137 ``compress1`` 1.071×, and random 1 MiB + 137
``bounded-decompress`` 1.105×. The random 16 MiB + 137 ``compress1`` case
also varies in the final run (0.943×), although compression output handling did
not change between the candidates.

Output strategy studies
-----------------------

Before the final comparison, prototype builds compared ways to return growing
output. These are separate studies with their own harness, so their ratios are
not comparable with the final-wheel tables. Their reference is a full-API
build that already includes the end-of-stream stop, so that correction cannot
hide the copy cost. Their files record neither the interpreter nor input
hashes; the interpreter versions below come from the report committed with the
studies at 65d3eb3. Their Python corpus was built from repeated package sources
rather than the final harness's stdlib files, which the files do not record
either. The bounded-output study, the free-threaded probe, and the 64 MiB
memory test use exact power-of-two sizes, which can favour strategies that
allocate exactly the output size. Two strategies differ measurably in a case
only when their ratios differ by more than the study's control maximum.

The JSON and CSV files name the variants by ID:

==================  =========================  ==================================
ID                  Name in this report        Output handling
==================  =========================  ==================================
``baseline-eof``    full-API reference         bytes object resized in place
``abi3-eof``        native output (selected)   ``PyMem`` buffer, one final copy
``abi3-chunks``     joined chunks              1 MiB bytes chunks, joined once
``abi3-bytesio``    eager BytesIO              ``io.BytesIO`` from the start
``abi3-hybrid``     delayed BytesIO            ``io.BytesIO`` on the first growth
``abi3-fast``       native scratch buffer      bounded output copied from
                                               ``PyMem``, despite the ID
``abi3-bounded``    direct bytes return        bounded output owned by bytes
``ft-retain``       bytes resizing (shipped)   free-threaded, full API
``ft-common``       native output              free-threaded, ``PyMem`` buffer
==================  =========================  ==================================

Large irregular output
~~~~~~~~~~~~~~~~~~~~~~

``mitigation-irregular.json`` holds the raw nine-round study,
``mitigation-irregular-summary.json`` its per-case medians including the
control, and ``mitigation-irregular.csv`` the candidate rows. Across all 52
cases the control was 5.32% at p95 and 6.32% at most. The 24 large
decoding cases (four corpora; 1 MiB + 137 and 16 MiB + 137 bytes;
``decompress``, ``igzip_lib.decompress``, and streaming) give:

==================  ======  =============
Strategy            Median  Range
==================  ======  =============
native output       1.183×  0.837-1.731×
joined chunks       1.207×  0.419-1.555×
eager BytesIO       1.334×  1.146-1.858×
delayed BytesIO     1.316×  1.151-1.851×
==================  ======  =============

The evidence does not favour native output over joined chunks on speed or
memory. Their medians differ by less than the control, and joined chunks has
the lower median in 12 of the 24 cases; 10 are beyond the control for joined
chunks and 11 for native output. Joined chunks has the lower worst case, and
native output the higher traced peak (see Memory). Joined chunks is also
faster than the reference for random 16 MiB + 137 output, 0.419-0.514×, and
measured 0.786× for random 16 MiB + 137 compression; neither result was
profiled and both are unexplained.

The BytesIO strategies have higher medians but are not worse everywhere. At
1 MiB + 137, delayed BytesIO has the lower median in 9 of the 12 decoding
cases; 3 are beyond the control for delayed BytesIO and 3 for native output.
At 16 MiB + 137, native output is faster beyond the control in all 12. For
the natural FASTQ file (3,578,369 bytes), the three decoders measured
1.049-1.097× with native output, 1.070-1.095× with joined chunks,
1.003-1.045× with eager BytesIO, and 1.047-1.074× with delayed BytesIO; no
case differs from native output by more than the control.

``mitigation-315.json`` and ``mitigation-315-summary.json`` repeat native
output against delayed BytesIO on CPython 3.15.0a8 (alpha), nine rounds, for
``decompress`` and ``igzip_lib.decompress`` only. The control was 4.60% at p95
and 6.19% at most. Over the 16 large cases, native output measured 1.210×
(0.846-2.002×) and delayed BytesIO 1.403× (1.177-1.868×). Native output was
faster beyond the control in all 8 cases at 16 MiB + 137. At 1 MiB + 137,
delayed BytesIO has the lower median in 6 of the 8 cases; 1 is beyond the
control for delayed BytesIO and 2 for native output, including the two FASTQ
cases, where native output measured 0.846-0.856×.

Memory
~~~~~~

``mitigation-memory.json`` measures, in a fresh process per case, the
``tracemalloc`` peak and the RSS growth, both divided by the output size, for
zeros and random output. At 16 MiB + 137 bytes both corpora give:

==================  ============  ==========
Strategy            Traced peak   RSS growth
==================  ============  ==========
full-API reference  2.00          1.02
native output       3.00          2.02
joined chunks       2.06          2.01
eager BytesIO       2.00          2.02
delayed BytesIO     2.00          2.02
==================  ============  ==========

Native output has the highest traced peak. At exactly 64 MiB, both BytesIO
strategies and the reference grow RSS by 1.00 output sizes against 2.00 for
native output (2.00 for zeros and 2.01 for random with joined chunks). At
16 MiB + 137, BytesIO grows RSS as much as native output; zero-filled spare
capacity in the BytesIO buffer is the likely cause (interpretation).
These are allocation measurements, not a bound on whole-process memory.

Bounded output
~~~~~~~~~~~~~~

``mitigation-bounded.json`` compares the two ways to return a finite output
limit that the output fills, at 64 KiB, 1 MiB, and 16 MiB, both as one call and
in chunks. Its control was 4.02% at p95 and 5.19% at most. Copying from a
native scratch buffer measured, for one call at 16 MiB, 1.517× (FASTQ), 8.162×
(Python), 1.915× (random), and 5.134× (zeros), and 2.369× for random at 1 MiB.
Returning the bytes object directly measured 1.000×, 0.971×, 0.989×, and 0.994×
for those 16 MiB cases, 0.973× for random 1 MiB, and 0.948-1.052× across all 24
cases. ``mitigation-bounded-memory.json`` records a traced peak of 33,641,953
bytes for a 16,777,216-byte output with the native scratch buffer, and
16,864,737 bytes both with the direct return and with the study's full-API
baseline; it does not record the corpus. The shipped code returns the bytes
object directly only when the first allocation already equals the limit, and
does not enlarge the first allocation to reach this path.

Free-threaded CPython
~~~~~~~~~~~~~~~~~~~~~

``free-threaded-probe.json`` compares the two approaches on free-threaded
CPython 3.13.11t, with nine rounds over 36 decoding cases. Its control was
3.17% at p95 and 3.58% at most. Bytes resizing, which the free-threaded build
ships, measured 0.971-1.140× at 1 KiB, 0.966-1.014× at 1 MiB, and 0.972-1.052×
at 16 MiB (median 1.006×). Native output measured 0.933-1.071× at 1 KiB,
0.778-1.008× at 1 MiB, and 0.914-2.217× at 16 MiB (median 0.970×). Native
output was faster beyond the control in 11 of the 12 cases at 1 MiB but had the
two largest outliers at 16 MiB; neither effect was profiled. These ratios
compare approaches within one free-threaded runtime, not free-threaded against
standard CPython.

Why native output was selected
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The studies do not show a strategy that is faster and smaller everywhere.
Native output was kept because it is the design the maintainer prescribed and
because it needs neither a chunk list and join step nor calls into
``io.BytesIO`` from C; that it is simpler to maintain is a judgment, not a
measurement. Joined chunks would be a defensible alternative on the measured
evidence. BytesIO was rejected because its median and its 16 MiB + 137 results
are worse, and its memory advantage appeared only at the exact 64 MiB size.

Compatibility and design limits
-------------------------------

- Free-threaded CPython and PyPy keep the full API and version-specific
  wheels. The ``cp311-abi3`` floor cannot cover free-threaded builds;
  `PEP 803 <https://peps.python.org/pep-0803/>`_ ("abi3t", Python 3.15 and
  later) is a possible follow-up. Full-API builds keep resizing bytes objects.
- PyPy keeps its existing static types, preserving existing behaviour; its
  wheels are version-specific, so heap types would bring no ABI benefit.
  PyPy 3.11.17's headers define ``Py_TPFLAGS_IMMUTABLETYPE`` and
  ``Py_TPFLAGS_DISALLOW_INSTANTIATION``, and PyPy honours
  ``Py_TPFLAGS_DISALLOW_INSTANTIATION`` on these static types.
- CPython types are created from specs as heap types. Instances are created
  with ``PyObject_New``, which the Limited API provides, freed with
  ``PyObject_Free``, and release their reference to the type. A prototype
  that used ``PyType_GenericAlloc``, which zeroes the whole instance including
  the ISA-L state, appeared slower on small calls; that was not measured in a
  committed study.
- The modules keep single-phase initialization and their shared exception
  objects. The ``Compress`` and ``Decompress`` type references live for the
  process, like the original static types. This change does not add
  per-interpreter module isolation.

``validation.txt`` lists the test, build, and audit results and the checks
that were not run.

Reproduce the final-wheel benchmark
-----------------------------------

Build the baseline revision and this revision with the same compiler and
ISA-L build, install their wheels into separate CPython 3.11 virtual
environments, and run from the repository::

    python benchmark_scripts/benchmark_abi3.py --library isal \
      --baseline /path/to/before/bin/python \
      --candidate /path/to/after/bin/python \
      --rounds 9 --cpu 1 --output /tmp/isal-abi3.json

Use a CPU number that is available on the test machine. Keep the Python
version the same to preserve the stdlib corpus hashes.
