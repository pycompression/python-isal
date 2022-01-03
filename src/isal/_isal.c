#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <isa-l.h>
#include <stdio.h>

static struct PyModuleDef _isal_module = {
    PyModuleDef_HEAD_INIT,
    "_isal",   /* name of module */
    NULL, /* module documentation, may be NULL */
    -1,
    {{NULL, NULL, 0, NULL}}
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
    int length = snprintf(&version, 64, "%d.%d.%d",
                          ISAL_MAJOR_VERSION, ISAL_MINOR_VERSION, ISAL_PATCH_VERSION);  
    if (length > 64){
        // This is extremely unlikely to happen given the calculation above.
        PyErr_SetString(PyExc_MemoryError, "Could not allocate enough memory for ISA-L version string");
        return NULL;
    }
    PyObject *isal_version = PyUnicode_DecodeASCII(&version, length, "strict");
    if (isal_version == NULL);
        return NULL;
    PyModule_AddObject(m, "ISAL_VERSION", isal_version);
    return m;
}
