#define PY_SSIZE_T_CLEAN
#include <Python.h>

typedef struct {
    PyTypeObject *Comptype;
    PyTypeObject *Decomptype;
    PyObject *ZlibError;
} isal_zlib_state;


static struct PyModuleDef isal_zlib_module {
    PyModuleDef_HEAD_INIT,
    "isal_zlib",   /* name of module */
    NULL, /* module documentation, may be NULL */
    sizeof(isal_zlib_state),
    IsalZlibMethods
}

PyMODINIT_FUNC
PyInit_isal_zlib(void)
{
    PyObject *m;
    PyObject *IsalError;

    m = PyModule_Create(&isal_zlib_module);
    if (m == NULL)
        return NULL;

    IsalError = PyErr_NewException("isal_zlib.error", NULL, NULL);
    Py_XINCREF(IsalError);
    if (PyModule_AddObject(m, "error", IsalError) < 0) {
        Py_XDECREF(IsalError);
        Py_CLEAR(IsalError);
        Py_DECREF(m);
        return NULL;
    }

    return m;
}
