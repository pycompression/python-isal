/*
Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
Python Software Foundation; All Rights Reserved

This file is part of python-isal which is distributed under the 
PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

This file is not originally from the CPython distribution. But it does 
contain mostly example code from the Python docs. Also dual licensing just 
for this one file seemed silly.
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <isa-l.h>

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
    PyObject *m = PyModule_Create(&_isal_module);
    if (m == NULL) {
        return NULL;
    }

#ifdef Py_GIL_DISABLED
    PyUnstable_Module_SetGIL(m, Py_MOD_GIL_NOT_USED);
#endif

    if (PyModule_AddIntMacro(m, ISAL_MAJOR_VERSION) < 0 ||
            PyModule_AddIntMacro(m, ISAL_MINOR_VERSION) < 0 ||
            PyModule_AddIntMacro(m, ISAL_PATCH_VERSION) < 0)
        goto error;

    PyObject *isal_version = PyUnicode_FromFormat(
        "%d.%d.%d", ISAL_MAJOR_VERSION, ISAL_MINOR_VERSION, ISAL_PATCH_VERSION);  
    if (isal_version == NULL) {
        goto error;
    }
    int ret = PyModule_AddObjectRef(m, "ISAL_VERSION", isal_version);
    Py_DECREF(isal_version);
    if (ret < 0)
        goto error;
    return m;

error:
    Py_DECREF(m);
    return NULL;
}
