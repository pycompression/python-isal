# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

from ._isal import (ISAL_MAJOR_VERSION, ISAL_MINOR_VERSION, ISAL_PATCH_VERSION,
                    ISAL_VERSION)

__all__ = [
    "ISAL_MAJOR_VERSION",
    "ISAL_MINOR_VERSION",
    "ISAL_PATCH_VERSION",
    "ISAL_VERSION",
    "__version__"
]

__version__ = "1.6.1"
