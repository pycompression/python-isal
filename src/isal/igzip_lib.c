#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include "structmember.h"         // PyMemberDef
#include "igzip_lib_impl.h"

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

PyDoc_STRVAR(igzip_lib_IgzipDecompressor_decompress__doc__,
"decompress($self, /, data, max_length=-1)\n"
"--\n"
"\n"
"Decompress *data*, returning uncompressed data as bytes.\n"
"\n"
"If *max_length* is nonnegative, returns at most *max_length* bytes of\n"
"decompressed data. If this limit is reached and further output can be\n"
"produced, *self.needs_input* will be set to ``False``. In this case, the next\n"
"call to *decompress()* may provide *data* as b\'\' to obtain more of the output.\n"
"\n"
"If all of the input data was decompressed and returned (either because this\n"
"was less than *max_length* bytes, or because *max_length* was negative),\n"
"*self.needs_input* will be set to True.\n"
"\n"
"Attempting to decompress data after the end of stream is reached raises an\n"
"EOFError.  Any data found after the end of the stream is ignored and saved in\n"
"the unused_data attribute.");

#define IGZIP_LIB_IGZIPDECOMPRESSOR_DECOMPRESS_METHODDEF    \
    {"decompress", (PyCFunction)(void(*)(void))igzip_lib_IgzipDecompressor_decompress, METH_FASTCALL|METH_KEYWORDS, igzip_lib_IgzipDecompressor_decompress__doc__}

static PyObject *
igzip_lib_IgzipDecompressor_decompress(IgzipDecompressor *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"data", "max_length", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "decompress", 0};
    PyObject *argsbuf[2];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 1;
    Py_buffer data = {NULL, NULL};
    Py_ssize_t max_length = -1;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 1, 2, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&data, 'C')) {
        _PyArg_BadArgument("decompress", "argument 'data'", "contiguous buffer", args[0]);
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (PyFloat_Check(args[1])) {
        PyErr_SetString(PyExc_TypeError,
                        "integer argument expected, got float" );
        goto exit;
    }
    {
        Py_ssize_t ival = -1;
        PyObject *iobj = PyNumber_Index(args[1]);
        if (iobj != NULL) {
            ival = PyLong_AsSsize_t(iobj);
            Py_DECREF(iobj);
        }
        if (ival == -1 && PyErr_Occurred()) {
            goto exit;
        }
        max_length = ival;
    }
skip_optional_pos:
    return_value = igzip_lib_IgzipDecompressor_decompress_impl(self, &data, max_length);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}
PyDoc_STRVAR(igzip_lib_IgzipDecompressor___init____doc__,
"IgzipDecompressor(flag=DECOMP_DEFLATE, hist_bits=MAX_HIST_BITS, zdict=b\'\')\n"
"--\n"
"\n"
"Create a decompressor object for decompressing data incrementally.\n"
"\n"
"  flag\n"
"    Flag signifying which headers and trailers the stream has.\n"
"  hist_bits\n"
"    The lookback distance is 2 ^ hist_bits.\n"
"  zdict\n"
"    Dictionary used for decompressing the data\n"
"\n"
"For one-shot decompression, use the decompress() function instead.");

static int
igzip_lib_IgzipDecompressor___init__(PyObject *self, PyObject *args, PyObject *kwargs)
{
    int return_value = -1;
    static const char * const _keywords[] = {"flag", "hist_bits", "zdict", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "IgzipDecompressor", 0};
    PyObject *argsbuf[3];
    PyObject * const *fastargs;
    Py_ssize_t nargs = PyTuple_GET_SIZE(args);
    Py_ssize_t noptargs = nargs + (kwargs ? PyDict_GET_SIZE(kwargs) : 0) - 0;
    int flag = ISAL_DEFLATE;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;
    PyObject *zdict = NULL;

    fastargs = _PyArg_UnpackKeywords(_PyTuple_CAST(args)->ob_item, nargs, kwargs, NULL, &_parser, 0, 3, 0, argsbuf);
    if (!fastargs) {
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (fastargs[0]) {
        if (PyFloat_Check(fastargs[0])) {
            PyErr_SetString(PyExc_TypeError,
                            "integer argument expected, got float" );
            goto exit;
        }
        flag = _PyLong_AsInt(fastargs[0]);
        if (flag == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (fastargs[1]) {
        if (PyFloat_Check(fastargs[1])) {
            PyErr_SetString(PyExc_TypeError,
                            "integer argument expected, got float" );
            goto exit;
        }
        hist_bits = _PyLong_AsInt(fastargs[1]);
        if (hist_bits == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    zdict = fastargs[2];
skip_optional_pos:
    return_value = igzip_lib_IgzipDecompressor___init___impl((IgzipDecompressor *)self, flag, hist_bits, zdict);

exit:
    return return_value;
}

static PyMethodDef IgzipDecompressor_methods[] = {
    IGZIP_LIB_IGZIPDECOMPRESSOR_DECOMPRESS_METHODDEF,
    {NULL}
};

PyDoc_STRVAR(IgzipDecompressor_eof__doc__,
"True if the end-of-stream marker has been reached.");

PyDoc_STRVAR(IgzipDecompressor_unused_data__doc__,
"Data found after the end of the compressed stream.");

PyDoc_STRVAR(IgzipDecompressor_needs_input_doc,
"True if more input is needed before more decompressed data can be produced.");

#define offsetof(TYPE, MEMBER) __builtin_offsetof (TYPE, MEMBER)

static PyMemberDef IgzipDecompressor_members[] = {
    {"eof", T_BOOL, offsetof(IgzipDecompressor, eof),
     READONLY, IgzipDecompressor_eof__doc__},
    {"unused_data", T_OBJECT_EX, offsetof(IgzipDecompressor, unused_data),
     READONLY, IgzipDecompressor_unused_data__doc__},
    {"needs_input", T_BOOL, offsetof(IgzipDecompressor, needs_input), READONLY,
     IgzipDecompressor_needs_input_doc},
    {NULL}
};

static PyTypeObject IgzipDecompressor_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    "igzip_lib.IgzipDecompressor",      /* tp_name */
    sizeof(IgzipDecompressor),          /* tp_basicsize */
    0,                                  /* tp_itemsize */
    (destructor)IgzipDecompressor_dealloc,/* tp_dealloc */
    0,                                  /* tp_vectorcall_offset */
    0,                                  /* tp_getattr */
    0,                                  /* tp_setattr */
    0,                                  /* tp_as_async */
    0,                                  /* tp_repr */
    0,                                  /* tp_as_number */
    0,                                  /* tp_as_sequence */
    0,                                  /* tp_as_mapping */
    0,                                  /* tp_hash  */
    0,                                  /* tp_call */
    0,                                  /* tp_str */
    0,                                  /* tp_getattro */
    0,                                  /* tp_setattro */
    0,                                  /* tp_as_buffer */
    Py_TPFLAGS_DEFAULT,                 /* tp_flags */
    igzip_lib_IgzipDecompressor___init____doc__,  /* tp_doc */
    0,                                  /* tp_traverse */
    0,                                  /* tp_clear */
    0,                                  /* tp_richcompare */
    0,                                  /* tp_weaklistoffset */
    0,                                  /* tp_iter */
    0,                                  /* tp_iternext */
    IgzipDecompressor_methods,            /* tp_methods */
    IgzipDecompressor_members,            /* tp_members */
    0,                                  /* tp_getset */
    0,                                  /* tp_base */
    0,                                  /* tp_dict */
    0,                                  /* tp_descr_get */
    0,                                  /* tp_descr_set */
    0,                                  /* tp_dictoffset */
    igzip_lib_IgzipDecompressor___init__,      /* tp_init */
    0,                                  /* tp_alloc */
    PyType_GenericNew,                  /* tp_new */
};

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

    IsalError = PyErr_NewException("IsalError", NULL, NULL);
    Py_XINCREF(IsalError);
    if (PyModule_AddObject(m, "error", IsalError) < 0) {
        Py_XDECREF(IsalError);
        Py_CLEAR(IsalError);
        Py_DECREF(m);
        return NULL;
    }
    get_igzip_lib_state(m)->IsalError = IsalError;

    if (PyModule_AddType(m, &IgzipDecompressor_Type) < 0) {
        return NULL;
    }

    PyModule_AddIntConstant(m, "ISAL_BEST_SPEED", ISAL_DEF_MIN_LEVEL);
    PyModule_AddIntConstant(m, "ISAL_BEST_COMPRESSION", ISAL_DEF_MAX_LEVEL);
    PyModule_AddIntMacro(m, ISAL_DEFAULT_COMPRESSION);

    PyModule_AddIntMacro(m, DEF_BUF_SIZE);
    PyModule_AddIntConstant(m, "MAX_HIST_BITS", ISAL_DEF_MAX_HIST_BITS);
    
    PyModule_AddIntConstant(m, "ISAL_NO_FLUSH", NO_FLUSH);
    PyModule_AddIntConstant(m, "ISAL_SYNC_FLUSH", SYNC_FLUSH);
    PyModule_AddIntConstant(m, "ISAL_FULL_FLUSH", FULL_FLUSH);

    PyModule_AddIntMacro(m, COMP_DEFLATE);
    PyModule_AddIntMacro(m, COMP_GZIP);
    PyModule_AddIntMacro(m, COMP_GZIP_NO_HDR);
    PyModule_AddIntMacro(m, COMP_ZLIB);
    PyModule_AddIntMacro(m, COMP_ZLIB_NO_HDR);

    PyModule_AddIntMacro(m, DECOMP_DEFLATE);
    PyModule_AddIntMacro(m, DECOMP_GZIP);
    PyModule_AddIntMacro(m, DECOMP_GZIP_NO_HDR);
    PyModule_AddIntMacro(m, DECOMP_ZLIB);
    PyModule_AddIntMacro(m, DECOMP_ZLIB_NO_HDR);
    PyModule_AddIntMacro(m, DECOMP_ZLIB_NO_HDR_VER);
    PyModule_AddIntMacro(m, DECOMP_GZIP_NO_HDR_VER);

    PyModule_AddIntMacro(m, MEM_LEVEL_DEFAULT);
    PyModule_AddIntMacro(m, MEM_LEVEL_MIN);
    PyModule_AddIntMacro(m, MEM_LEVEL_SMALL);
    PyModule_AddIntMacro(m, MEM_LEVEL_MEDIUM);
    PyModule_AddIntMacro(m, MEM_LEVEL_LARGE);
    PyModule_AddIntMacro(m, MEM_LEVEL_EXTRA_LARGE);

    return m;
}
