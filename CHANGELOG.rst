==========
Changelog
==========

.. Newest changes should be on top.

.. This document is user facing. Please word the changes in such a way
.. that users understand how the changes affect the new version.

version 0.3.1-dev
-----------------
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
