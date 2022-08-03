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
  :target: https://github.com/pycompression/python-isal/blob/main/LICENSE
  :alt:

.. image:: https://img.shields.io/conda/pn/conda-forge/python-isal.svg
  :target: https://github.com/conda-forge/python-isal-feedstock
  :alt:

.. image:: https://github.com/pycompression/python-isal//actions/workflows/ci.yml/badge.svg
  :target: https://github.com/pycompression/python-isal/actions
  :alt:

.. image:: https://codecov.io/gh/pycompression/python-isal/branch/develop/graph/badge.svg
  :target: https://codecov.io/gh/pycompression/python-isal
  :alt:

.. image:: https://readthedocs.org/projects/python-isal/badge
   :target: https://python-isal.readthedocs.io
   :alt:


python-isal
===========

.. introduction start

Faster zlib and gzip compatible compression and decompression
by providing Python bindings for the ISA-L library.

This package provides Python bindings for the `ISA-L
<https://github.com/intel/isa-l>`_ library. The Intel(R) Intelligent Storage
Acceleration Library (ISA-L) implements several key algorithms in `assembly
language <https://en.wikipedia.org/wiki/Assembly_language>`_. This includes
a variety of functions to provide zlib/gzip-compatible compression.

``python-isal`` provides the bindings by offering three modules:

+ ``isal_zlib``: A drop-in replacement for the zlib module that uses ISA-L to
  accelerate its performance.
+ ``igzip``: A drop-in replacement for the gzip module that uses ``isal_zlib``
  instead of ``zlib`` to perform its compression and checksum tasks, which
  improves performance.
+ ``igzip_lib``: Provides compression functions which have full access to the
  API of ISA-L's compression functions.

``isal_zlib`` and ``igzip`` are almost fully compatible with ``zlib`` and
``gzip`` from the Python standard library. There are some minor differences
see: differences-with-zlib-and-gzip-modules_.

.. introduction end

Quickstart
----------

.. quickstart start

The python-isal modules can be imported as follows

.. code-block:: python

    from isal import isal_zlib
    from isal import igzip
    from isal import igzip_lib

``isal_zlib`` and ``igzip`` are meant to be used as drop in replacements so
their api and functions are the same as the stdlib's modules. Except where
ISA-L does not support the same calls as zlib (See differences below).

A full API documentation can be found on `our readthedocs page
<https://python-isal.readthedocs.io>`_.

``python -m isal.igzip`` implements a simple gzip-like command line
application (just like ``python -m gzip``). Full usage documentation can be
found on `our readthedocs page <https://python-isal.readthedocs.io>`_.


.. quickstart end

Installation
------------
- with pip: ``pip install isal``
- with conda: ``conda install python-isal``

Installation is supported on Linux, Windows and MacOS. For more advanced
installation options check the `documentation
<https://python-isal.readthedocs.io/en/stable/index.html#installation>`_.

.. _differences-with-zlib-and-gzip-modules:

python-isal as a dependency in your project
-------------------------------------------

.. dependency start

Python-isal supports a limited amount of platforms for which wheels have been
made available. To prevent your users from running into issues when installing
your project please list a python-isal dependency as follows.

``setup.cfg``::

    install_requires =
        isal; platform.machine == "x86_64" or platform.machine == "AMD64"

``setup.py``::

    extras_require={
        ":platform.machine == 'x86_64' or platform.machine == 'AMD64'": ['isal']
    },

.. dependency end

Differences with zlib and gzip modules
--------------------------------------

.. differences start

+ Compression level 0 in ``zlib`` and ``gzip`` means **no compression**, while
  in ``isal_zlib`` and ``igzip`` this is the **lowest compression level**.
  This is a design choice that was inherited from the ISA-L library.
+ Compression levels range from 0 to 3, not 1 to 9. ``isal_zlib.Z_DEFAULT_COMPRESSION``
  has been aliased to ``isal_zlib.ISAL_DEFAULT_COMPRESSION`` (2).
+ ``isal_zlib`` only supports ``NO_FLUSH``, ``SYNC_FLUSH``, ``FULL_FLUSH`` and
  ``FINISH_FLUSH``. Other flush modes are not supported and will raise errors.
+ ``zlib.Z_DEFAULT_STRATEGY``, ``zlib.Z_RLE`` etc. are exposed as
  ``isal_zlib.Z_DEFAULT_STRATEGY``, ``isal_zlib.Z_RLE`` etc. for compatibility
  reasons. However, ``isal_zlib`` only supports a default strategy and will
  give warnings when other strategies are used.
+ ``zlib`` supports different memory levels from 1 to 9 (with 8 default).
  ``isal_zlib`` supports memory levels smallest, small, medium, large and
  largest. These have been mapped to levels 1, 2-3, 4-6, 7-8 and 9. So
  ``isal_zlib`` can be used with zlib compatible memory levels.
+ ``igzip.open`` returns a class ``IGzipFile`` instead of ``GzipFile``. Since
  the compression levels are not compatible, a difference in naming was chosen
  to reflect this. ``igzip.GzipFile`` does exist as an alias of
  ``igzip.IGzipFile`` for compatibility reasons.

.. differences end

Contributing
------------
.. contributing start

Please make a PR or issue if you feel anything can be improved. Bug reports
are also very welcome. Please report them on the `github issue tracker
<https://github.com/rhpvorderman/python-isal/issues>`_.

.. contributing end

Acknowledgements
----------------

.. acknowledgements start

This project builds upon the software and experience of many.  Many thanks to:

+ The `ISA-L contributors
  <https://github.com/intel/isa-l/graphs/contributors>`_ for making ISA-L.
  Special thanks to @gbtucker for always being especially helpful and
  responsive.
+ The `Cython contributors
  <https://github.com/cython/cython/graphs/contributors>`_ for making it easy
  to create an extension and helping a novice get start with pointer addresses.
+ The `CPython contributors
  <https://github.com/python/cpython/graphs/contributors>`_.
  Python-isal mimicks ``zlibmodule.c`` and ``gzip.py`` from the standard
  library to make it easier for python users to adopt it.
+ `@marcelm <https://github.com/marcelm>`_ for taking a chance on this project
  and make it a dependency for his `xopen
  <https://github.com/pycompression/xopen>`_ and by extension `cutadapt
  <https://github.com/marcelm/cutadapt>`_ projects. This gave python-isal its
  first users who used python-isal in production.
+ The `github actions team <https://github.com/orgs/actions/people>`_ for
  creating the actions CI service that enables building and testing on all
  three major operating systems.
+ `@animalize <https://github.com/animalize>`_ for explaining how to test and
  build python-isal for ARM 64-bit platforms.
+ And last but not least: everyone who submitted a bug report or a feature
  request. These make the project better!

Python-isal would not have been possible without you!

.. acknowledgements end
