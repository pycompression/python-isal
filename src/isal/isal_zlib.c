#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "isal_zlib_impl.h"


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

static PyObject *
isal_zlib_crc32(PyObject *module, PyObject *const *args, Py_ssize_t nargs)
{
    PyObject *return_value = NULL;
    Py_buffer data = {NULL, NULL};
    uint32_t value = 0;

    if (!_PyArg_CheckPositional("crc32", nargs, 1, 2)) {
        goto exit;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&data, 'C')) {
        _PyArg_BadArgument("crc32", "argument 1", "contiguous buffer", args[0]);
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
    return_value = isal_zlib_crc32_impl(module, &data, value);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }
    return return_value;
}

static PyObject *
isal_zlib_compress(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "level", "wbits", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "compress", 0};
    PyObject *argsbuf[3];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    PyObject *ErrorClass = get_isal_zlib_state(module)->IsalError;
    Py_buffer data = {NULL, NULL};
    int level = ISAL_DEFAULT_COMPRESSION;
    int wbits = ISAL_DEF_MAX_HIST_BITS;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 3, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&data, 'C')) {
        _PyArg_BadArgument("compress", "argument 1", "contiguous buffer", args[0]);
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (args[1]) {
        level = _PyLong_AsInt(args[1]);
        if (level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    wbits = _PyLong_AsInt(args[2]);
    if (wbits == -1 && PyErr_Occurred()) {
        goto exit;
    }
skip_optional_pos:
    return_value = isal_zlib_compress_impl(ErrorClass, &data, level, wbits);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}


static PyObject *
isal_zlib_decompress(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "wbits", "bufsize", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "decompress", 0};
    PyObject *argsbuf[3];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    PyObject *ErrorClass = get_isal_zlib_state(module)->IsalError;
    Py_buffer data = {NULL, NULL};
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    Py_ssize_t bufsize = DEF_BUF_SIZE;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 3, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&data, 'C')) {
        _PyArg_BadArgument("decompress", "argument 1", "contiguous buffer", args[0]);
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (args[1]) {
        wbits = _PyLong_AsInt(args[1]);
        if (wbits == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    {
        Py_ssize_t ival = -1;
        PyObject *iobj = PyNumber_Index(args[2]);
        if (iobj != NULL) {
            ival = PyLong_AsSsize_t(iobj);
            Py_DECREF(iobj);
        }
        if (ival == -1 && PyErr_Occurred()) {
            goto exit;
        }
        bufsize = ival;
    }
skip_optional_pos:
    return_value = isal_zlib_decompress_impl(ErrorClass, &data, wbits, bufsize);

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
    {"crc32", (PyCFunction)(void(*)(void))isal_zlib_crc32, METH_FASTCALL, NULL},
    {"compress", (PyCFunction)(void(*)(void))isal_zlib_compress, METH_FASTCALL|METH_KEYWORDS, NULL},
    {"decompress", (PyCFunction)(void(*)(void))isal_zlib_decompress, METH_FASTCALL|METH_KEYWORDS, NULL},
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
    get_isal_zlib_state(m)->IsalError = IsalError;

    return m;
}
