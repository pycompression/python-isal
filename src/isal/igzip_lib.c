#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "igzip_lib_impl.h"


typedef struct {
    PyTypeObject *Decomptype;
    PyObject *IsalError;
} _igzip_lib_state;

static inline _igzip_lib_state*
get_igzip_lib_state(PyObject *module)
{
    void *state = PyModule_GetState(module);
    assert(state != NULL);
    return (_igzip_lib_state*)state;
}
static PyObject *
igzip_lib_compress(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "level", "flag", "mem_level" "hist_bits", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "compress", 0};
    PyObject *argsbuf[5];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    Py_buffer data = {NULL, NULL};
    int level = ISAL_DEFAULT_COMPRESSION;
    int flag = DECOMP_DEFLATE;
    int mem_level = MEM_LEVEL_DEFAULT;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 5, 0, argsbuf);
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
        level = (uint32_t)_PyLong_AsInt(args[1]);
        if (level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[2]) {
        flag = (uint16_t)_PyLong_AsInt(args[2]);
        if (level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[3]) {
        mem_level = _PyLong_AsInt(args[3]);
        if (mem_level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    hist_bits = _PyLong_AsInt(args[4]);
    if (hist_bits == -1 && PyErr_Occurred()) {
        goto exit;
    }
skip_optional_pos:
    return_value = igzip_lib_compress_impl(
        get_igzip_lib_state(module)->IsalError,
        &data, level, flag, mem_level, hist_bits);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}

static PyMethodDef IgzipLibMethods[] = {
    {"compress", (PyCFunction)(void(*)(void))igzip_lib_compress, METH_FASTCALL|METH_KEYWORDS, NULL},
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static struct PyModuleDef igzip_lib_module = {
    PyModuleDef_HEAD_INIT,
    "igzip_lib",   /* name of module */
    NULL, /* module documentation, may be NULL */
    sizeof(_igzip_lib_state),
    IgzipLibMethods
};

PyMODINIT_FUNC
PyInit_igzip_lib(void)
{
    PyObject *m;
    PyObject *IsalError;

    m = PyModule_Create(&igzip_lib_module);
    if (m == NULL)
        return NULL;

    IsalError = PyErr_NewException("igzip_lib.error", NULL, NULL);
    Py_XINCREF(IsalError);
    if (PyModule_AddObject(m, "error", IsalError) < 0) {
        Py_XDECREF(IsalError);
        Py_CLEAR(IsalError);
        Py_DECREF(m);
        return NULL;
    }
    get_igzip_lib_state(m)->IsalError = IsalError;

    return m;
}
