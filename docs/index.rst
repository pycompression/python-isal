.. python-isal documentation master file, created by
   sphinx-quickstart on Fri Sep 11 15:42:56 2020.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

=======================================
Welcome to python-isal's documentation!
=======================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

============
Introduction
============

.. include:: includes/README.rst
   :start-after: .. introduction start
   :end-before: .. introduction end

==========
Quickstart
==========

Python-isal has faster versions of the stdlib's ``zlib`` and ``gzip`` module
these are called ``isal_zlib`` and ``igzip`` respectively.

They can be imported as follows

.. code-block:: python

    from isal import isal_zlib
    from isal import igzip

``isal_zlib`` and ``igzip`` are meant to be used as drop in replacements so
their api and functions are the same as the stdlib's modules. Except where
ISA-L does not support the same calls as zlib (See differences below).

A full API documentation can be found below.

``python -m isal.igzip`` implements a simple gzip-like command line
application (just like ``python -m gzip``). Full usage documentation can be
found below.


.. include:: includes/Installation.rst

======================================
Differences with zlib and gzip modules
======================================

.. include:: includes/README.rst
   :start-after: .. differences start
   :end-before: .. differences end

============================
API Documentation: igzip_lib
============================

.. automodule:: isal.igzip_lib
   :members:

============================
API Documentation: isal_zlib
============================

.. automodule:: isal.isal_zlib
   :members:

========================
API-documentation: igzip
========================

.. automodule:: isal.igzip
   :members: compress, decompress, open

   .. autoclass:: IGzipFile
      :members:
      :special-members: __init__

==========================
python -m isal.igzip usage
==========================

.. argparse::
   :module: isal.igzip
   :func: _argument_parser
   :prog: python -m isal.igzip


============
Contributing
============
.. include:: includes/README.rst
   :start-after: .. contributing start
   :end-before: .. contributing end

================
Acknowledgements
================
.. include:: includes/README.rst
   :start-after: .. acknowledgements start
   :end-before: .. acknowledgements end

.. include:: includes/CHANGELOG.rst
