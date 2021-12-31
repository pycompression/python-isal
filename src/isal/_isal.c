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

    char *version = NULL;
    asprintf(&version, "%d.%d.%d",
                ISAL_MAJOR_VERSION, ISAL_MINOR_VERSION, ISAL_PATCH_VERSION);
    PyObject *isal_version = PyUnicode_FromString(version);
    free(version); //asprintf allocates memory to the pointer.
    PyModule_AddObject(m, "ISAL_VERSION", isal_version);
    return m;
}

