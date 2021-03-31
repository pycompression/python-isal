============
Installation
============
Installation with pip
---------------------

::

    pip install isal

Installation is supported on Linux, MacOS and Windows. On most platforms
wheels are provided.
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
----------------------
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
