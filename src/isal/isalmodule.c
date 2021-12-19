#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <isa-l/crc.h>
#include <isa-l/igzip_lib.h>
#include <stdint.h>

static PyObject *
isal_zlib_adler32_impl(PyObject *module, Py_buffer *data, uint32_t value)
{
    value = isal_adler32(value, data->buf, (uint64_t)data->len);
    return PyLong_FromUnsignedLong(value & 0xffffffffU);
}

static PyObject *
isal_zlib_adler32(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    PyObject *return_value = NULL;
    Py_buffer data = {NULL, NULL};
    uint32_t value = 1;

    if (!_PyArg_CheckPositional("adler32", nargs, 1, 2)) {
        goto exit;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&data, 'C')) {
        _PyArg_BadArgument("adler32", "argument 1", "contiguous buffer", args[0]);
        goto exit;
    }
    if (nargs < 2) {
        goto skip_optional;
    }
    value = (uint32_t)PyLong_AsUnsignedLongMask(args[1]);
    if (value == (uint32_t)-1 && PyErr_Occurred()) {
        goto exit;
    }
skip_optional:
    return_value = isal_zlib_adler32_impl(module, &data, value);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }
    return return_value;
}


typedef struct {
    PyTypeObject *Comptype;
    PyTypeObject *Decomptype;
    PyObject *IsalError;
} isal_zlib_state;

static PyMethodDef IsalZlibMethods[] = {
    {"adler32", (PyCFunction)(void(*)(void))isal_zlib_adler32, METH_FASTCALL, NULL},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef isal_zlib_module = {
    PyModuleDef_HEAD_INIT,
    "isal_zlib",   /* name of module */
    NULL, /* module documentation, may be NULL */
    sizeof(isal_zlib_state),
    IsalZlibMethods
};

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
