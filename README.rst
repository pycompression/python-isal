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

.. image:: https://img.shields.io/conda/pn/conda-forge/python-isal.svg
  :target: https://github.com/conda-forge/python-isal-feedstock
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
by providing Python bindings for the ISA-L library.

This package provides Python bindings for the `ISA-L
<https://github.com/intel/isa-l>`_ library. The Intel(R) Intelligent Storage
Acceleration Library (ISA-L) implements several key algorithms in `assembly
language <https://en.wikipedia.org/wiki/Assembly_language>`_. This includes
a variety of functions to provide zlib/gzip-compatible compression.

``python-isal`` provides the bindings by offering an ``isal_zlib`` and
``igzip`` module which are usable as drop-in replacements for the ``zlib``
and ``gzip`` modules from the stdlib (with some minor exceptions, see below).

Usage
-----

Python-isal has faster versions of the stdlib's ``zlib`` and ``gzip`` module
these are called ``isal_zlib`` and ``igzip`` respectively.

They can be imported as follows

.. code-block:: python

    from isal import isal_zlib
    from isal import igzip

``isal_zlib`` and ``igzip`` are meant to be used as drop in replacements so
their api and functions are the same as the stdlib's modules. Except where
ISA-L does not support the same calls as zlib (See differences below).

A full API documentation can be found on `our readthedocs page
<https://python-isal.readthedocs.io>`_.

``python -m isal.igzip`` implements a simple gzip-like command line
application (just like ``python -m gzip``).

Installation
------------
Installation with pip
.....................

::

    pip install isal

Installation is supported on Linux, MacOS and Windows. On x86-64 (amd64)
platforms wheels are provided, so installation should be almost instantaneous.
The installation will include a staticallly linked version of ISA-L.
If a wheel is not provided for your system the
installation will build ISA-L first in a temporary directory. Please check the
`ISA-L homepage <https://github.com/intel/isa-l>`_ for the build requirements.

The latest development version of python-isal can be installed with::

    pip install git+https://github.com/rhpvorderman/python-isal.git

This requires having the build requirements installed.
If you wish to link
dynamically against a version of libisal installed on your system use::

     PYTHON_ISAL_LINK_DYNAMIC=true pip install isal --no-binary isal

ISA-L is available in numerous Linux distro's as well as on conda via the
conda-forge channel. Checkout the `ports documentation
<https://github.com/intel/isa-l/wiki/Ports--Repos>`_ on the ISA-L project wiki
to find out how to install it. It is important that the development headers
are also installed.

On Debian and Ubuntu the ISA-L libraries (including the development headers)
can be installed with::

  sudo apt install libisal-dev

Installation via conda
..................................
Python-isal can be installed via conda, for example using
the `miniconda <https://docs.conda.io/en/latest/miniconda.html>`_ installer
with a properly setup `conda-forge 
<https://conda-forge.org/docs/user/introduction.html#how-can-i-install-packages-from-conda-forge>`_
channel. When used with bioinformatics tools setting up `bioconda 
<http://bioconda.github.io/user/install.html#install-conda>`_
provides a clear set of installation instructions for conda.

python-isal is available on conda-forge and can be installed with::

  conda install python-isal

This will automatically install the ISA-L library dependency as well, since
it is available on conda-forge.

Differences with zlib and gzip modules
--------------------------------------

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
+ ``isal_zlib`` methods have a ``data`` argument which is positional only. In
  isal_zlib this is not enforced and it can also called as keyword argument.
  This is due to implementing ``isal_zlib`` in cython and maintaining backwards
  compatibility with python 3.6.
+ ``igzip.open`` returns a class ``IGzipFile`` instead of ``GzipFile``. Since
  the compression levels are not compatible, a difference in naming was chosen
  to reflect this. ``igzip.GzipFile`` does exist as an alias of
  ``igzip.IGzipFile`` for compatibility reasons.

Contributing
------------
Please make a PR or issue if you feel anything can be improved. Bug reports
are also very welcome. Please report them on the `github issue tracker
<https://github.com/rhpvorderman/python-isal/issues>`_.
