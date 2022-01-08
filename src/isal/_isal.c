//  Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
// 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
// Python Software Foundation; All Rights Reserved

// This file is part of python-isal which is distributed under the 
// PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

// This file is not originally from the CPython distribution. But it does contain mostly example code
// from the Python docs. Also dual licensing just for this one file seemed silly.

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <isa-l.h>
#include <stdio.h>

static struct PyModuleDef _isal_module = {
    PyModuleDef_HEAD_INIT,
    "_isal",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,
    NULL
};


PyMODINIT_FUNC
PyInit__isal(void)
{
    PyObject *m;

    m = PyModule_Create(&_isal_module);
    if (m == NULL)
        return NULL;

    PyModule_AddIntMacro(m, ISAL_MAJOR_VERSION);
    PyModule_AddIntMacro(m, ISAL_MINOR_VERSION);
    PyModule_AddIntMacro(m, ISAL_PATCH_VERSION);
    // UINT64_MAX is 20 characters long. A version contains:
    // 3 numbers, 2 dots, one null byte. So the maximum size
    // in charcters is 3x20+2+1=63. Round up to the nearest 
    // power of 2 is 64.
    char version[64];
    int length = snprintf(version, 64, "%d.%d.%d",
                          ISAL_MAJOR_VERSION, ISAL_MINOR_VERSION, ISAL_PATCH_VERSION);  
    if (length > 64){
        // This is extremely unlikely to happen given the calculation above.
        PyErr_SetString(PyExc_MemoryError, "Could not allocate enough memory for ISA-L version string");
        return NULL;
    }
    PyObject *isal_version = PyUnicode_DecodeASCII(version, length, "strict");
    if (isal_version == NULL)
        return NULL;
    PyModule_AddObject(m, "ISAL_VERSION", isal_version);
    return m;
}
