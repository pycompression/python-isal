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
    PyObject *ErrorClass = get_igzip_lib_state(module)->IsalError;
    Py_buffer data = {NULL, NULL};
    int level = ISAL_DEFAULT_COMPRESSION;
    int flag = COMP_DEFLATE;
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
        level = _PyLong_AsInt(args[1]);
        if (level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[2]) {
        flag = _PyLong_AsInt(args[2]);
        if (flag == -1 && PyErr_Occurred()) {
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
        ErrorClass, &data, level, flag, mem_level, hist_bits);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}


static PyObject *
igzip_lib_decompress(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "flag", "hist_bits" "bufsize", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "decompress", 0};
    PyObject *argsbuf[4];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    PyObject *ErrorClass = get_igzip_lib_state(module)->IsalError;
    Py_buffer data = {NULL, NULL};
    int flag = DECOMP_DEFLATE;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;
    Py_ssize_t bufsize = DEF_BUF_SIZE;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 4, 0, argsbuf);
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
        flag = _PyLong_AsInt(args[1]);
        if (flag == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[2]) {
        hist_bits = _PyLong_AsInt(args[2]);
        if (hist_bits == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[2]) {
        flag = _PyLong_AsInt(args[2]);
        if (flag == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    {
        Py_ssize_t ival = -1;
        PyObject *iobj = PyNumber_Index(args[3]);
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
    return_value = igzip_lib_decompress_impl(ErrorClass, &data, flag, hist_bits, bufsize);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}


static PyMethodDef IgzipLibMethods[] = {
    {"compress", (PyCFunction)(void(*)(void))igzip_lib_compress, METH_FASTCALL|METH_KEYWORDS, NULL},
    {"decompress", (PyCFunction)(void(*)(void))igzip_lib_decompress, METH_FASTCALL|METH_KEYWORDS, NULL},
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

    PyModule_AddIntConstant(m, "ISAL_BEST_SPEED", ISAL_DEF_MIN_LEVEL);
    PyModule_AddIntConstant(m, "ISAL_BEST_COMPRESSION", ISAL_DEF_MAX_LEVEL);
    PyModule_AddIntMacro(m, ISAL_DEFAULT_COMPRESSION);

    PyModule_AddIntMacro(m, DEF_BUF_SIZE);
    PyModule_AddIntConstant(m, "MAX_HIST_BITS", ISAL_DEF_MAX_HIST_BITS);
    
    PyModule_AddIntConstant(m, "ISAL_NO_FLUSH", NO_FLUSH);
    PyModule_AddIntConstant(m, "ISAL_SYNC_FLUSH", SYNC_FLUSH);
    PyModule_AddIntConstant(m, "ISAL_FULL_FLUSH", FULL_FLUSH);

    PyModule_AddIntConstant(m, "COMP_DEFLATE", IGZIP_DEFLATE);
    PyModule_AddIntConstant(m, "COMP_GZIP", IGZIP_GZIP);
    PyModule_AddIntConstant(m, "COMP_GZIP_NO_HDR", IGZIP_GZIP_NO_HDR);
    PyModule_AddIntConstant(m, "COMP_ZLIB", IGZIP_ZLIB);
    PyModule_AddIntConstant(m, "COMP_ZLIB_NO_HDR", IGZIP_ZLIB_NO_HDR);

    PyModule_AddIntConstant(m, "DECOMP_DEFLATE", ISAL_DEFLATE);
    PyModule_AddIntConstant(m, "DECOMP_GZIP", ISAL_GZIP);
    PyModule_AddIntConstant(m, "DECOMP_GZIP_NO_HDR", DECOMP_GZIP_NO_HDR);
    PyModule_AddIntConstant(m, "DECOMP_ZLIB", ISAL_ZLIB);
    PyModule_AddIntConstant(m, "DECOMP_ZLIB_NO_HDR", ISAL_ZLIB_NO_HDR);
    PyModule_AddIntConstant(m, "DECOMP_ZLIB_NO_HDR_VER", ISAL_ZLIB_NO_HDR_VER);
    PyModule_AddIntConstant(m, "DECOMP_GZIP_NO_HDR_VER", ISAL_GZIP_NO_HDR_VER);

    PyModule_AddIntMacro(m, MEM_LEVEL_DEFAULT);
    PyModule_AddIntMacro(m, MEM_LEVEL_MIN);
    PyModule_AddIntMacro(m, MEM_LEVEL_SMALL);
    PyModule_AddIntMacro(m, MEM_LEVEL_MEDIUM);
    PyModule_AddIntMacro(m, MEM_LEVEL_LARGE);
    PyModule_AddIntMacro(m, MEM_LEVEL_EXTRA_LARGE);

    return m;
}
