Stable ABI performance and compatibility
========================================

The standard CPython build uses the Python 3.11 Limited API. Free-threaded
CPython and PyPy retain the full API and version-specific wheels. PyPy also
retains static extension types to preserve their immutability. Further
free-threaded optimization belongs to a separate change.

Final installed-wheel comparison
-------------------------------

``cpython311.json`` contains all 27 worker runs (nine randomized paired rounds
of original baseline, baseline control, and candidate), input SHA-256 values,
iteration counts, CPU and wall times, interpreter and extension paths.
``cpython311.csv`` contains the median of nine paired CPU-time ratios for each
of the 128 cases. A ratio above 1 means more time. Each case's output is checked
against the original input or stdlib zlib outside the timed loop.

Baseline: commit 2498167283fb4598d3daf757bc2a80b53d798c52, unchanged. Both
wheels use CPython 3.11.15, GCC 15.2.0, -O3 -DNDEBUG, and the same pinned
ISA-L 2.32.1 archive. Linux x86_64, Intel i7-3770 (no AVX2), CPU 1 pinned.
The Python interpreter itself was built with Clang; the extensions use GCC.
No other project build/test/benchmark ran during these timings.

Four corpora: the repository FASTQ fixture, concatenated stdlib Python source
(with a period longer than the deflate window), seeded incompressible bytes,
and zero bytes. Sizes: 1 KiB, 64 KiB, 1 MiB + 137, and 16 MiB + 137.
Calibration uses the baseline only and freezes counts for all variants.
Each case targets 20 ms, capped at 10,000 iterations. GC is disabled in workers.
The baseline-control absolute difference across case medians is 2.17% at p95
and 4.12% maximum; small changes within this range need caution.

At 16 MiB + 137, candidate CPU time divided by original baseline time:

Operation                   FASTQ   Python  Random  Zeros
==========================  ======  ======  ======  ======
compress1                   1.009x  1.013x  1.047x  1.002x
decompress                  1.053x  1.061x  1.158x  1.138x
raw-decompress              1.048x  1.058x  1.222x  1.182x
stream-decompress           1.060x  1.059x  1.183x  1.139x
bounded-decompress          0.990x  1.006x  0.993x  0.995x
gzip-read128k               0.999x  0.987x  1.000x  1.003x
gzip-readinto128k           1.010x  1.035x  1.003x  1.002x
crc32                       0.997x  0.998x  1.007x  1.000x
==========================  ======  ======  ======  ======

Unbounded decompression remains slower: roughly 5-22% in the table. The worst
case in the complete matrix is 1 MiB + 137 incompressible raw decompression,
2.055x; high-level and streaming versions of that case are 1.466x and 1.481x.
The 1 KiB decode-case medians across corpora range 0.958-1.103x; streaming
1 KiB decoding ranges 1.016-1.078x. Compression, checksums, filled bounded
output, and normal gzip chunk reads generally stay close to baseline.
These measurements do not establish parity on other hardware or runtimes.

Mitigation experiments
----------------------

``mitigation-irregular.csv`` retains the nine-round exploratory comparison of
native growing buffers, 1 MiB chunks joined once, eager BytesIO, and BytesIO
created on first growth. The reference includes the same EOF-stop correction
as every candidate, so that correction cannot disguise the copy cost.
Across 24 large irregular decode cases (four corpora, 1 MiB + 137 and
16 MiB + 137, three decoder APIs), median case ratios and ranges are:

==================  ======  =============
Strategy            Median  Range
==================  ======  =============
Native output       1.183x  0.837-1.731x
Joined chunks       1.207x  0.419-1.555x
Eager BytesIO       1.334x  1.146-1.858x
Delayed BytesIO     1.316x  1.151-1.851x
==================  ======  =============

Control p95 is 5.39%. Natural FASTQ output (3,578,369 bytes) gives native
1.05-1.10x versus delayed BytesIO 1.05-1.07x. A separate nine-round 3.15.0a8
confirmation also disfavors delayed BytesIO for large irregular output.
The speculative strategies are not part of the production implementation.
Power-of-two-only tests favored BytesIO more strongly; irregular sizes matter.

``mitigation-memory.json`` measures fresh-process traced peak and RSS growth
separately. Exact 64 MiB output can favor BytesIO (about one output resident,
versus two for native buffers). For 16 MiB + 137, BytesIO's spare-capacity
zero-fill raises residency to about two outputs, as with native buffers;
the original bytes-resize path remains near one output resident. Traced peak
can reach three output sizes with a growing native buffer plus final bytes.
These are allocation experiments, not a bound on whole-process memory.

``mitigation-bounded.json`` compares a fully filled finite output buffer.
Returning its bytes owner directly reduces 16 MiB random-output time from
1.915x to 0.989x and FASTQ from 1.517x to 1.000x. The traced peak for 16 MiB
zeros falls from 33,641,953 bytes to 16,864,737, matching the original.
The fast path applies only when the existing initial capacity equals the
finite limit and is fully filled. Short results still copy. Capacity is not
inflated merely to obtain this path.

``free-threaded-probe.json`` compares migration approaches on the same
3.13.11t interpreter, with the GIL off, nine rounds and 36 decode cases.
Retaining full-API bytes resizing gives 16 MiB median 1.006x (0.972-1.052x),
control p95 3.26%; tiny streaming cases retain up to 14% overhead. This is
migration overhead within a free-threaded runtime, not free-threaded versus
standard Python, and is not a claim of identical runtime speed.

Compatibility and design limits
-------------------------------

The maintainer's 3.11 ABI floor and native-buffer/final-copy design are retained
for growing output. Filled bounded output is a deliberate exception, measured
above. PyObject_New remains legal under the Limited API; replacing it with
GenericAlloc unnecessarily zeroed large codec structs and caused 2-3x tiny-call
regressions in the initial prototype. Instances use paired PyObject_Free and
CPython heap-type references are balanced. PyPy keeps static types because its
headers lack the immutable/disallow-instantiation flags used by CPython specs.

The existing legacy module policy and shared exception identity remain.
Two factory type references have process lifetime, like the original static
types. This change does not claim per-interpreter module isolation.
Python metadata now matches the project's already documented 3.11 support floor.

Validation uses the actual built wheels: strict abi3audit; one cp311-abi3 wheel
on 3.11.15, 3.12.14, 3.13.12, 3.14.4 and 3.15.0a8; a cp313-cp313t wheel
with the GIL off; and a pp311-pypy311_pp80 wheel on PyPy 3.11.17. Full-suite
counts and check details are in validation.txt. CI builds/audits a 3.11 wheel
on Linux, macOS Intel/ARM and Windows and tests that same wheel on 3.11-3.15.
Existing free-threaded/PyPy jobs remain, with Windows free-threaded coverage.
Windows/macOS/ARM execution and release cibuildwheel runs are not local results.

Reproduce the final wheel benchmark
----------------------------------

Build the baseline revision and this revision with the same compiler and vendor
library, install their wheels into separate CPython 3.11 virtual environments,
and run from the repository::

    python benchmark_scripts/benchmark_abi3.py --library isal \
      --baseline /path/to/before/bin/python \
      --candidate /path/to/after/bin/python \
      --rounds 9 --cpu 1 --output /tmp/isal-abi3.json

Use an available CPU number on the test machine. Keep the Python version equal
to preserve stdlib corpus hashes. The exploratory strategy summaries document
the design decision; the harness above benchmarks the shipped implementation.
