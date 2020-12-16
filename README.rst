.. image:: https://img.shields.io/pypi/v/isal.svg
  :target: https://pypi.org/project/isal/
  :alt:

.. image:: https://img.shields.io/conda/v/conda-forge/python-isal.svg
  :target: https://github.com/conda-forge/python-isal-feedstock
  :alt:

.. image:: https://img.shields.io/pypi/pyversions/isal.svg
  :target: https://pypi.org/project/isal/
  :alt:

.. image:: https://img.shields.io/pypi/l/isal.svg
  :target: https://github.com/LUMC/isal/blob/main/LICENSE
  :alt:

.. image:: https://travis-ci.com/pycompression/python-isal.svg?branch=develop
  :target: https://travis-ci.com/github/pycompression/python-isal
  :alt:

.. image:: https://codecov.io/gh/pycompression/python-isal/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/pycompression/python-isal
  :alt:

.. image:: https://readthedocs.org/projects/python-isal/badge
   :target: https://python-isal.readthedocs.io
   :alt:


python-isal
===========

Faster zlib and gzip compatible compression and decompression
by providing python bindings for the isa-l library.

This package provides Python bindings for the `isa-l
<https://github.com/intel/isa-l>`_ library. The Intel Infrastructure Storage
Acceleration Library (isa-l) implements several key algorithms in `assembly
language <https://en.wikipedia.org/wiki/Assembly_language>`_. This includes
a variety of functions to provide zlib/gzip-compatible compression.

``python-isal`` provides the bindings by offering an ``isal_zlib`` and
``igzip`` module which are usable as drop-in replacements for the ``zlib``
and ``gzip`` modules from the stdlib (with some minor exceptions, see below).

Installation
------------

isa-l version 2.26.0 or higher is needed. This includes bindings for the
adler32 function.

isa-l is available in numerous Linux distro's as well as on conda via the
conda-forge channel. Checkout the `ports documentation
<https://github.com/intel/isa-l/wiki/Ports--Repos>`_ on the isa-l project wiki
to find out how to install it.

python-isal can be installed via pypi with:

.. code-block::

    pip install isal

This requires the isa-l library to be installed on your pc.

The latest development version of python-isal can be installed with

.. code-block::

    pip install git+https://github.com/rhpvorderman/python-isal.git

Usage
-----

Python-isal has faster versions of the stdlib's ``zlib`` and ``gzip`` module
these are called ``isal_zlib`` and ``igzip`` respectively.

They can be imported as follows

.. code-block:: python

    from isal import isal_zlib
    from isal import igzip

``isal_zlib`` and ``igzip`` were meant to be used as drop in replacements so
their api and functions are the same as the stdlib's modules. Except where
isa-l does not support the same calls as zlib (See differences below).

A full API documentation can be found on `our readthedocs page
<https://python-isal.readthedocs.io>`_.

``python -m isal.igzip`` implements a simple gzip-like command line
application (just like ``python -m gzip``).

Differences with zlib and gzip modules
--------------------------------------

+ Compression level 0 in ``zlib`` and ``gzip`` means **no compression**, while
  in ``isal_zlib`` and ``igzip`` this is the **lowest compression level**.
  This is a design choice that was inherited from the isa-l library.
+ Compression levels range from 0 to 3, not 1 to 9.
+ ``isal_zlib.crc32`` and ``isal_zlib.adler32`` do not support negative
  numbers for the value parameter.
+ ``zlib.Z_DEFAULT_STRATEGY``, ``zlib.Z_RLE`` etc. are exposed as
  ``isal_zlib.Z_DEFAULT_STRATEGY``, ``isal_zlib.Z_RLE`` etc. for compatibility
  reasons. However, ``isal_zlib`` only supports a default strategy and will
  give warnings when other strategies are used.
+ ``zlib`` supports different memory levels from 1 to 9 (with 8 default).
  ``isal_zlib`` supports memory levels smallest, small, medium, large and
  largest. These have been mapped to levels 1, 2-3, 4-6, 7-8 and 9. So
  ``isal_zlib`` can be used with zlib compatible memory levels.
+ ``isal_zlib`` only supports ``FLUSH``, ``SYNC_FLUSH`` and ``FULL_FLUSH``
  ``FINISH`` is aliased to ``FULL_FLUSH`` (and works correctly as such).
+ ``isal_zlib`` has a ``compressobj`` and ``decompressobj`` implementation.
  However, the unused_data and unconsumed_tail for the Decompress object, only
  work properly when using gzip compatible compression. (25 <= wbits <= 31).
+ The flush implementation for the Compress object behavious differently from
  the zlib equivalent.

Contributing
------------
Please make a PR or issue if you feel anything can be improved. Bug reports
are also very welcome. Please report them on the `github issue tracker
<https://github.com/rhpvorderman/python-isal/issues>`_.
