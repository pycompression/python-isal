//  Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
// 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
// Python Software Foundation; All Rights Reserved

// This file is part of python-isal which is distributed under the 
// PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

// This file was modified from Cpython's Modules/clinic/zlibmodule.c.h and
// Modules/zlibmodule.c files.
// Changes compared to CPython:
// - All zlib naming changed to isal_zlib
// - Including a few constants that are more specific to the ISA-L library
//   (ISAL_DEFAULT_COMPRESSION etc).


#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "isal_zlib_impl.h"
#include "structmember.h"  
#ifndef _PyArg_CheckPositional
#include "python_args.h"
#endif

PyDoc_STRVAR(isal_zlib_adler32__doc__,
"adler32($module, data, value=1, /)\n"
"--\n"
"\n"
"Compute an Adler-32 checksum of data.\n"
"\n"
"  value\n"
"    Starting value of the checksum.\n"
"\n"
"The returned checksum is an integer.");

#define ISAL_ZLIB_ADLER32_METHODDEF    \
    {"adler32", (PyCFunction)(void(*)(void))isal_zlib_adler32, METH_FASTCALL, isal_zlib_adler32__doc__}

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

PyDoc_STRVAR(zlib_crc32__doc__,
"crc32($module, data, value=0, /)\n"
"--\n"
"\n"
"Compute a CRC-32 checksum of data.\n"
"\n"
"  value\n"
"    Starting value of the checksum.\n"
"\n"
"The returned checksum is an integer.");

#define ISAL_ZLIB_CRC32_METHODDEF    \
    {"crc32", (PyCFunction)(void(*)(void))isal_zlib_crc32, METH_FASTCALL, zlib_crc32__doc__}

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
PyDoc_STRVAR(zlib_compress__doc__,
"compress($module, data, /, level=ISAL_DEFAULT_COMPRESSION, wbits=MAX_WBITS)\n"
"--\n"
"\n"
"Returns a bytes object containing compressed data.\n"
"\n"
"  data\n"
"    Binary data to be compressed.\n"
"  level\n"
"    Compression level, in 0-3.\n"
"  wbits\n"
"    The window buffer size and container format.");

#define ISAL_ZLIB_COMPRESS_METHODDEF    \
    {"compress", (PyCFunction)(void(*)(void))isal_zlib_compress, METH_FASTCALL|METH_KEYWORDS, zlib_compress__doc__}

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

PyDoc_STRVAR(zlib_decompress__doc__,
"decompress($module, data, /, wbits=MAX_WBITS, bufsize=DEF_BUF_SIZE)\n"
"--\n"
"\n"
"Returns a bytes object containing the uncompressed data.\n"
"\n"
"  data\n"
"    Compressed data.\n"
"  wbits\n"
"    The window buffer size and container format.\n"
"  bufsize\n"
"    The initial output buffer size.");

#define ISAL_ZLIB_DECOMPRESS_METHODDEF    \
    {"decompress", (PyCFunction)(void(*)(void))isal_zlib_decompress, METH_FASTCALL|METH_KEYWORDS, zlib_decompress__doc__}


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

PyDoc_STRVAR(isal_zlib_compressobj__doc__,
"compressobj($module, /, level=ISAL_DEFAULT_COMPRESSION, method=DEFLATED,\n"
"            wbits=MAX_WBITS, memLevel=DEF_MEM_LEVEL,\n"
"            strategy=Z_DEFAULT_STRATEGY, zdict=None)\n"
"--\n"
"\n"
"Return a compressor object.\n"
"\n"
"  level\n"
"    The compression level (an integer in the range 0-3; default is\n"
"    currently equivalent to 2).  Higher compression levels are slower,\n"
"    but produce smaller results.\n"
"  method\n"
"    The compression algorithm.  If given, this must be DEFLATED.\n"
"  wbits\n"
"    * +9 to +15: The base-two logarithm of the window size.  Include a zlib\n"
"      container.\n"
"    * -9 to -15: Generate a raw stream.\n"
"    * +25 to +31: Include a gzip container.\n"
"  memLevel\n"
"    Controls the amount of memory used for internal compression state.\n"
"    Valid values range from 1 to 9.  Higher values result in higher memory\n"
"    usage, faster compression, and smaller output.\n"
"  strategy\n"
"    Used to tune the compression algorithm. Not supported by ISA-L.\n"
"    Only a default strategy is used.\n"
"  zdict\n"
"    The predefined compression dictionary - a sequence of bytes\n"
"    containing subsequences that are likely to occur in the input data.");

#define ISAL_ZLIB_COMPRESSOBJ_METHODDEF    \
    {"compressobj", (PyCFunction)(void(*)(void))isal_zlib_compressobj, METH_FASTCALL|METH_KEYWORDS, isal_zlib_compressobj__doc__}

static PyObject *
isal_zlib_compressobj(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"level", "method", "wbits", "memLevel", "strategy", "zdict", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "compressobj", 0};
    PyObject *argsbuf[6];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 0;
    int level = ISAL_DEFAULT_COMPRESSION;
    int method = Z_DEFLATED;
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    int memLevel = DEF_MEM_LEVEL;
    int strategy = Z_DEFAULT_STRATEGY;
    Py_buffer zdict = {NULL, NULL};

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 0, 6, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (args[0]) {
        level = _PyLong_AsInt(args[0]);
        if (level == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[1]) {
        method = _PyLong_AsInt(args[1]);
        if (method == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[2]) {
        wbits = _PyLong_AsInt(args[2]);
        if (wbits == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[3]) {
        memLevel = _PyLong_AsInt(args[3]);
        if (memLevel == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (args[4]) {
        strategy = _PyLong_AsInt(args[4]);
        if (strategy == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    if (PyObject_GetBuffer(args[5], &zdict, PyBUF_SIMPLE) != 0) {
        goto exit;
    }
    if (!PyBuffer_IsContiguous(&zdict, 'C')) {
        _PyArg_BadArgument("compressobj", "argument 'zdict'", "contiguous buffer", args[5]);
        goto exit;
    }
skip_optional_pos:
    return_value = isal_zlib_compressobj_impl(module, level, method, wbits, memLevel, strategy, &zdict);

exit:
    /* Cleanup for zdict */
    if (zdict.obj) {
       PyBuffer_Release(&zdict);
    }

    return return_value;
}

PyDoc_STRVAR(isal_zlib_decompressobj__doc__,
"decompressobj($module, /, wbits=MAX_WBITS, zdict=b\'\')\n"
"--\n"
"\n"
"Return a decompressor object.\n"
"\n"
"  wbits\n"
"    The window buffer size and container format.\n"
"  zdict\n"
"    The predefined compression dictionary.  This must be the same\n"
"    dictionary as used by the compressor that produced the input data.");

#define ISAL_ZLIB_DECOMPRESSOBJ_METHODDEF    \
    {"decompressobj", (PyCFunction)(void(*)(void))isal_zlib_decompressobj, METH_FASTCALL|METH_KEYWORDS, isal_zlib_decompressobj__doc__}

static PyObject *
isal_zlib_decompressobj(PyObject *module, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"wbits", "zdict", NULL};
    static _PyArg_Parser _parser = {NULL, _keywords, "decompressobj", 0};
    PyObject *argsbuf[2];
    Py_ssize_t noptargs = nargs + (kwnames ? PyTuple_GET_SIZE(kwnames) : 0) - 0;
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    PyObject *zdict = NULL;

    args = _PyArg_UnpackKeywords(args, nargs, NULL, kwnames, &_parser, 0, 2, 0, argsbuf);
    if (!args) {
        goto exit;
    }
    if (!noptargs) {
        goto skip_optional_pos;
    }
    if (args[0]) {
        wbits = _PyLong_AsInt(args[0]);
        if (wbits == -1 && PyErr_Occurred()) {
            goto exit;
        }
        if (!--noptargs) {
            goto skip_optional_pos;
        }
    }
    zdict = args[1];
skip_optional_pos:
    return_value = isal_zlib_decompressobj_impl(module, wbits, zdict);

exit:
    return return_value;
}

PyDoc_STRVAR(isal_zlib_Compress_compress__doc__,
"compress($self, data, /)\n"
"--\n"
"\n"
"Returns a bytes object containing compressed data.\n"
"\n"
"  data\n"
"    Binary data to be compressed.\n"
"\n"
"After calling this function, some of the input data may still\n"
"be stored in internal buffers for later processing.\n"
"Call the flush() method to clear these buffers.");

#define ISAL_ZLIB_COMPRESS_COMPRESS_METHODDEF    \
    {"compress", (PyCFunction)(void(*)(void))isal_zlib_Compress_compress, METH_FASTCALL|METH_KEYWORDS, isal_zlib_Compress_compress__doc__}


static PyObject *
isal_zlib_Compress_compress(compobject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", NULL};
    static _PyArg_Parser _parser = {"y*:compress", _keywords, 0};
    Py_buffer data = {NULL, NULL};

    if (!_PyArg_ParseStackAndKeywords(args, nargs, kwnames, &_parser,
        &data)) {
        goto exit;
    }
    return_value =isal_zlib_Compress_compress_impl(self, &data);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}

PyDoc_STRVAR(isal_zlib_Decompress_decompress__doc__,
"decompress($self, data, /, max_length=0)\n"
"--\n"
"\n"
"Return a bytes object containing the decompressed version of the data.\n"
"\n"
"  data\n"
"    The binary data to decompress.\n"
"  max_length\n"
"    The maximum allowable length of the decompressed data.\n"
"    Unconsumed input data will be stored in\n"
"    the unconsumed_tail attribute.\n"
"\n"
"After calling this function, some of the input data may still be stored in\n"
"internal buffers for later processing.\n"
"Call the flush() method to clear these buffers.");

#define ISAL_ZLIB_DECOMPRESS_DECOMPRESS_METHODDEF    \
    {"decompress", (PyCFunction)(void(*)(void))isal_zlib_Decompress_decompress, METH_FASTCALL|METH_KEYWORDS, isal_zlib_Decompress_decompress__doc__}


static PyObject *
isal_zlib_Decompress_decompress(decompobject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", "max_length", NULL};
    static _PyArg_Parser _parser = {"y*|n:decompress", _keywords, 0};
    Py_buffer data = {NULL, NULL};
    Py_ssize_t max_length = 0;

    if (!_PyArg_ParseStackAndKeywords(args, nargs, kwnames, &_parser,
        &data, &max_length)) {
        goto exit;
    }
    return_value = isal_zlib_Decompress_decompress_impl(self, &data, max_length);

exit:
    /* Cleanup for data */
    if (data.obj) {
       PyBuffer_Release(&data);
    }

    return return_value;
}

PyDoc_STRVAR(isal_zlib_Compress_flush__doc__,
"flush($self, mode=zlib.Z_FINISH, /)\n"
"--\n"
"\n"
"Return a bytes object containing any remaining compressed data.\n"
"\n"
"  mode\n"
"    One of the constants Z_SYNC_FLUSH, Z_FULL_FLUSH, Z_FINISH.\n"
"    If mode == Z_FINISH, the compressor object can no longer be\n"
"    used after calling the flush() method.  Otherwise, more data\n"
"    can still be compressed.");

#define ISAL_ZLIB_COMPRESS_FLUSH_METHODDEF    \
    {"flush", (PyCFunction)(void(*)(void))isal_zlib_Compress_flush, METH_FASTCALL|METH_KEYWORDS, isal_zlib_Compress_flush__doc__}


static PyObject *
isal_zlib_Compress_flush(compobject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", NULL};
    static _PyArg_Parser _parser = {"|i:flush", _keywords, 0};
    int mode = Z_FINISH;

    if (!_PyArg_ParseStackAndKeywords(args, nargs, kwnames, &_parser,
        &mode)) {
        goto exit;
    }
    return_value = isal_zlib_Compress_flush_impl(self, mode);

exit:
    return return_value;
}
PyDoc_STRVAR(isal_zlib_Decompress_flush__doc__,
"flush($self, length=zlib.DEF_BUF_SIZE, /)\n"
"--\n"
"\n"
"Return a bytes object containing any remaining decompressed data.\n"
"\n"
"  length\n"
"    the initial size of the output buffer.");


#define ISAL_ZLIB_DECOMPRESS_FLUSH_METHODDEF    \
    {"flush", (PyCFunction)(void(*)(void))isal_zlib_Decompress_flush, METH_FASTCALL|METH_KEYWORDS, isal_zlib_Decompress_flush__doc__}

static PyObject *
isal_zlib_Decompress_flush(decompobject *self, PyObject *const *args, Py_ssize_t nargs, PyObject *kwnames)
{
    PyObject *return_value = NULL;
    static const char * const _keywords[] = {"", NULL};
    static _PyArg_Parser _parser = {"|n:flush", _keywords, 0};
    Py_ssize_t length = DEF_BUF_SIZE;

    if (!_PyArg_ParseStackAndKeywords(args, nargs, kwnames, &_parser,
        &length)) {
        goto exit;
    }
    return_value = isal_zlib_Decompress_flush_impl(self, length);

exit:
    return return_value;
}


typedef struct {
    PyTypeObject *Comptype;
    PyTypeObject *Decomptype;
    PyObject *IsalError;
} isal_zlib_state;

static PyMethodDef IsalZlibMethods[] = {
    ISAL_ZLIB_ADLER32_METHODDEF,
    ISAL_ZLIB_CRC32_METHODDEF,
    ISAL_ZLIB_COMPRESS_METHODDEF,
    ISAL_ZLIB_DECOMPRESS_METHODDEF,
    ISAL_ZLIB_COMPRESSOBJ_METHODDEF,
    ISAL_ZLIB_DECOMPRESSOBJ_METHODDEF,
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

static PyMethodDef comp_methods[] = {
    ISAL_ZLIB_COMPRESS_COMPRESS_METHODDEF,
    ISAL_ZLIB_COMPRESS_FLUSH_METHODDEF,
    {NULL, NULL}
};
static PyMethodDef Decomp_methods[] =
{
    ISAL_ZLIB_DECOMPRESS_DECOMPRESS_METHODDEF,
    ISAL_ZLIB_DECOMPRESS_FLUSH_METHODDEF,
    {NULL, NULL}
};

static PyType_Slot Comptype_slots[] = {
    {Py_tp_dealloc, Comp_dealloc},
    {Py_tp_methods, comp_methods},
    {Py_tp_doc, "Object returned by isal_zlib.compressobj."},
    {0, 0},
};

static PyType_Spec Comptype_spec = {
    "isal_zlib.Compress",
    sizeof(compobject),
    0,
    Py_TPFLAGS_DEFAULT,
    Comptype_slots
};

#define COMP_OFF(x) offsetof(decompobject, x)

PyDoc_STRVAR(Decomp_unconsumed_tail,
"A bytes object that contains any data that was not consumed by the last\n"
"decompress() call because it exceeded the limit for the uncompressed data\n"
"buffer. This data has not yet been seen by the zlib machinery, so you must\n"
"feed it (possibly with further data concatenated to it) back to a \n"
"subsequent decompress() method call in order to get correct output.");

static PyMemberDef Decomp_members[] = {
    {"unused_data",     T_OBJECT, COMP_OFF(unused_data), READONLY,
    "Data found after the end of the compressed stream."},
    {"unconsumed_tail", T_OBJECT, COMP_OFF(unconsumed_tail), READONLY,
    Decomp_unconsumed_tail},
    {"eof",             T_BOOL,   COMP_OFF(eof), READONLY,
    "True if the end-of-stream marker has been reached."},
    {NULL},
};

static PyType_Slot Decomptype_slots[] = {
    {Py_tp_dealloc, Decomp_dealloc},
    {Py_tp_methods, Decomp_methods},
    {Py_tp_members, Decomp_members},
    {Py_tp_doc, "Object returned by isal_zlib.compressobj."},
    {0, 0},
};

static PyType_Spec Decomptype_spec = {
    "isal_zlib.Decompress",
    sizeof(decompobject),
    0,
    Py_TPFLAGS_DEFAULT,
    Decomptype_slots
};


PyDoc_STRVAR(isal_zlib_module_documentation,
"The functions in this module allow compression and decompression using the\n"
"zlib library, which is based on GNU zip.\n"
"\n"
"- adler32(string[, start]) -- Compute an Adler-32 checksum.\n"
"- compress(data[, level]) -- Compress data, with compression level 0-9 or -1.\n"
"- compressobj([level[, ...]]) -- Return a compressor object.\n"
"- crc32(string[, start]) -- Compute a CRC-32 checksum.\n"
"- decompress(string,[wbits],[bufsize]) -- Decompresses a compressed string.\n"
"- decompressobj([wbits[, zdict]]) -- Return a decompressor object.\n"
"\n"
"'wbits' is window buffer size and container format.\n"
"\n"
"Compressor objects support compress() and flush() methods; decompressor\n"
"objects support decompress() and flush().");

static int
isal_zlib_clear(PyObject *m)
{
    _isal_zlibstate *state = get_isal_zlib_state(m);
    Py_CLEAR(state->Comptype);
    Py_CLEAR(state->Decomptype);
    Py_CLEAR(state->IsalError);
    return 0;
}

static int
isal_zlib_traverse(PyObject *m, visitproc visit, void *arg)
{
    _isal_zlibstate *state = get_isal_zlib_state(m);
    Py_VISIT(state->Comptype);
    Py_VISIT(state->Decomptype);
    Py_VISIT(state->IsalError);
    return 0;
}

static void
isal_zlib_free(void *m)
{
    isal_zlib_clear((PyObject *)m);
}

static struct PyModuleDef isal_zlib_module = {
    PyModuleDef_HEAD_INIT,
    "isal_zlib",   /* name of module */
    isal_zlib_module_documentation, /* module documentation, may be NULL */
    sizeof(isal_zlib_state),
    IsalZlibMethods,
    NULL,
    isal_zlib_traverse,
    isal_zlib_clear,
    isal_zlib_free,
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

    PyTypeObject *Comptype = (PyTypeObject *)PyType_FromSpec(&Comptype_spec);
    if (Comptype == NULL)
        return NULL;
    get_isal_zlib_state(m)->Comptype = Comptype;

    PyTypeObject *Decomptype = (PyTypeObject *)PyType_FromSpec(&Decomptype_spec);
    if (Decomptype == NULL)
        return NULL;
    get_isal_zlib_state(m)->Decomptype = Decomptype;

    if (PyType_Ready(Comptype) != 0)
        return NULL;
    Py_INCREF(Comptype);
    if (PyModule_AddObject(m, "Compress",  (PyObject *)Comptype) < 0) {
        return NULL;
    }
    if (PyType_Ready(Decomptype) != 0)
        return NULL;
    Py_INCREF(Decomptype);
    if (PyModule_AddObject(m, "Decompress",  (PyObject *)Decomptype) < 0) {
        return NULL;
    }

    PyModule_AddIntConstant(m, "MAX_WBITS", ISAL_DEF_MAX_HIST_BITS);
    PyModule_AddIntConstant(m, "DEFLATED", Z_DEFLATED);
    PyModule_AddIntMacro(m, DEF_MEM_LEVEL);
    PyModule_AddIntMacro(m, DEF_BUF_SIZE);
    // compression levels
    // No compression is not supported by ISA-L. Throw an error if chosen.
    // PyModule_AddIntMacro(m, Z_NO_COMPRESSION);
    PyModule_AddIntConstant(m, "Z_BEST_SPEED", ISAL_DEF_MIN_LEVEL);
    PyModule_AddIntConstant(m, "Z_BEST_COMPRESSION", ISAL_DEF_MAX_LEVEL);
    PyModule_AddIntConstant(m, "Z_DEFAULT_COMPRESSION", ISAL_DEFAULT_COMPRESSION);
    PyModule_AddIntMacro(m, ISAL_DEFAULT_COMPRESSION);
    PyModule_AddIntConstant(m, "ISAL_BEST_SPEED", ISAL_DEF_MIN_LEVEL);
    PyModule_AddIntConstant(m, "ISAL_BEST_COMPRESSION", ISAL_DEF_MAX_LEVEL);

    // compression strategies
    PyModule_AddIntMacro(m, Z_DEFAULT_STRATEGY);
    PyModule_AddIntMacro(m, Z_FILTERED);
    PyModule_AddIntMacro(m, Z_HUFFMAN_ONLY);
    PyModule_AddIntMacro(m, Z_RLE);
    PyModule_AddIntMacro(m, Z_FIXED);
    
    // allowed flush values
    PyModule_AddIntMacro(m, Z_NO_FLUSH);
    PyModule_AddIntMacro(m, Z_PARTIAL_FLUSH);
    PyModule_AddIntMacro(m, Z_SYNC_FLUSH);
    PyModule_AddIntMacro(m, Z_FULL_FLUSH);
    PyModule_AddIntMacro(m, Z_FINISH);
    PyModule_AddIntMacro(m, Z_BLOCK);
    PyModule_AddIntMacro(m, Z_TREES);

    PyState_AddModule(m, &isal_zlib_module);
    return m;
}
