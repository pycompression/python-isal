//  Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
// 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
// Python Software Foundation; All Rights Reserved

// This file is part of python-isal which is distributed under the 
// PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

// This file was modified from Cpython Modules/bz2module.c file from the 3.9
// branch.

// Changes compared to CPython:
// - The BZ2Decompressor has been used as a basis for IgzipDecompressor.
//   Functionality is almost the same. IgzipDecompressor does have a more
//   elaborate __init__ to set settings. It also implements decompress_buf more
//   akin to how decompression is implemented in isal_shared.h
// - Constants were added that are particular to igzip_lib.
// - Argument parsers were written using th CPython API rather than argument
//   clinic.

#include "isal_shared.h"

typedef struct {
    PyObject_HEAD
    struct inflate_state state;
    char eof;           /* T_BOOL expects a char */
    PyObject *unused_data;
    PyObject *zdict;
    char needs_input;
    uint8_t *input_buffer;
    Py_ssize_t input_buffer_size;

    /* inflate_state>avail_in is only 32 bit, so we store the true length
       separately. Conversion and looping is encapsulated in
       decompress_buf() */
    Py_ssize_t avail_in_real;
} IgzipDecompressor;

static void
IgzipDecompressor_dealloc(IgzipDecompressor *self)
{
    if(self->input_buffer != NULL)
        PyMem_Free(self->input_buffer);
    Py_CLEAR(self->unused_data);
    Py_CLEAR(self->zdict);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

/* Decompress data of length d->bzs_avail_in_real in d->state.next_in.  The output
   buffer is allocated dynamically and returned.  At most max_length bytes are
   returned, so some of the input may not be consumed. d->state.next_in and
   d->bzs_avail_in_real are updated to reflect the consumed input. */
static PyObject*
decompress_buf(IgzipDecompressor *self, Py_ssize_t max_length)
{
    /* data_size is strictly positive, but because we repeatedly have to
       compare against max_length and PyBytes_GET_SIZE we declare it as
       signed */
    PyObject * RetVal = NULL;
    Py_ssize_t hard_limit;
    
    Py_ssize_t obuflen;
    
    int err;

    // In Python 3.10 sometimes sys.maxsize is passed by default. In those cases
    // we do want to use DEF_BUF_SIZE as start buffer.
    if ((max_length < 0) || max_length == PY_SSIZE_T_MAX) {
        hard_limit = PY_SSIZE_T_MAX;
        obuflen = DEF_BUF_SIZE;
    } else {
        // Assume that decompressor is used in file decompression with a fixed
        // block size of max_length. In that case we will reach max_length almost
        // always (except at the end of the file). So it makes sense to allocate
        // max_length.
        hard_limit = max_length;
        obuflen = max_length;
        if (obuflen > DEF_MAX_INITIAL_BUF_SIZE){
            // Safeguard against memory overflow.
            obuflen = DEF_MAX_INITIAL_BUF_SIZE;
        }
    }

    do {
        arrange_input_buffer(&(self->state.avail_in), &(self->avail_in_real));

        do {
            obuflen = arrange_output_buffer_with_maximum(&(self->state.avail_out), 
                                                        &(self->state.next_out),
                                                        &RetVal,
                                                        obuflen,
                                                        hard_limit);
            if (obuflen == -1){
                PyErr_SetString(PyExc_MemoryError, 
                                "Unsufficient memory for buffer allocation");
                goto error;
            }
            else if (obuflen == -2)
                break;
        
            err = isal_inflate(&(self->state));
            if (err != ISAL_DECOMP_OK){
                isal_inflate_error(err);
                goto error;
            }
        } while (self->state.avail_out == 0 && self->state.block_state != ISAL_BLOCK_FINISH);
    } while(self->avail_in_real != 0 && self->state.block_state != ISAL_BLOCK_FINISH);

    if (self->state.block_state == ISAL_BLOCK_FINISH)
        self->eof = 1;

    self->avail_in_real += self->state.avail_in;

    if (_PyBytes_Resize(&RetVal, self->state.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) != 0)
        goto error;

    return RetVal;

error:
    Py_CLEAR(RetVal);
    return NULL;
}


static PyObject *
decompress(IgzipDecompressor *self, uint8_t *data, size_t len, Py_ssize_t max_length)
{
    char input_buffer_in_use;
    PyObject *result;

    /* Prepend unconsumed input if necessary */
    if (self->state.next_in != NULL) {
        size_t avail_now, avail_total;

        /* Number of bytes we can append to input buffer */
        avail_now = (self->input_buffer + self->input_buffer_size)
            - (self->state.next_in + self->avail_in_real);

        /* Number of bytes we can append if we move existing
           contents to beginning of buffer (overwriting
           consumed input) */
        avail_total = self->input_buffer_size - self->avail_in_real;

        if (avail_total < len) {
            size_t offset = self->state.next_in - self->input_buffer;
            uint8_t *tmp;
            size_t new_size = self->input_buffer_size + len - avail_now;

            /* Assign to temporary variable first, so we don't
               lose address of allocated buffer if realloc fails */
            tmp = PyMem_Realloc(self->input_buffer, new_size);
            if (tmp == NULL) {
                PyErr_SetNone(PyExc_MemoryError);
                return NULL;
            }
            self->input_buffer = tmp;
            self->input_buffer_size = new_size;

            self->state.next_in = self->input_buffer + offset;
        }
        else if (avail_now < len) {
            memmove(self->input_buffer, self->state.next_in,
                    self->avail_in_real);
            self->state.next_in = self->input_buffer;
        }
        memcpy((void*)(self->state.next_in + self->avail_in_real), data, len);
        self->avail_in_real += len;
        input_buffer_in_use = 1;
    }
    else {
        self->state.next_in = data;
        self->avail_in_real = len;
        input_buffer_in_use = 0;
    }

    result = decompress_buf(self, max_length);
    if(result == NULL) {
        self->state.next_in = NULL;
        return NULL;
    }

    if (self->eof) {
        self->needs_input = 0;
        Py_ssize_t bytes_in_bitbuffer = bitbuffer_size(&(self->state));
        if (self->avail_in_real + bytes_in_bitbuffer > 0) {
            PyObject * new_data = PyBytes_FromStringAndSize(
                NULL, self->avail_in_real + bytes_in_bitbuffer);
            if (new_data == NULL)
                goto error;
            char * new_data_ptr = PyBytes_AS_STRING(new_data);
            bitbuffer_copy(&(self->state), new_data_ptr, bytes_in_bitbuffer);
            memcpy(new_data_ptr + bytes_in_bitbuffer, self->state.next_in, self->avail_in_real);
            Py_XSETREF(self->unused_data, new_data);
        }
    }
    else if (self->avail_in_real == 0) {
        self->state.next_in = NULL;
        self->needs_input = 1;
    }
    else {
        self->needs_input = 0;

        /* If we did not use the input buffer, we now have
           to copy the tail from the caller's buffer into the
           input buffer */
        if (!input_buffer_in_use) {

            /* Discard buffer if it's too small
               (resizing it may needlessly copy the current contents) */
            if (self->input_buffer != NULL &&
                self->input_buffer_size < self->avail_in_real) {
                PyMem_Free(self->input_buffer);
                self->input_buffer = NULL;
            }

            /* Allocate if necessary */
            if (self->input_buffer == NULL) {
                self->input_buffer = PyMem_Malloc(self->avail_in_real);
                if (self->input_buffer == NULL) {
                    PyErr_SetNone(PyExc_MemoryError);
                    goto error;
                }
                self->input_buffer_size = self->avail_in_real;
            }

            /* Copy tail */
            memcpy(self->input_buffer, self->state.next_in, self->avail_in_real);
            self->state.next_in = self->input_buffer;
        }
    }
    return result;

error:
    Py_XDECREF(result);
    return NULL;
}

PyDoc_STRVAR(igzip_lib_compress__doc__,
"compress($module, data, /, level=ISAL_DEFAULT_COMPRESSION, flag=COMP_DEFLATE,\n"
"         mem_level=MEM_LEVEL_DEFAULT, hist_bits=MAX_HIST_BITS)\n"
"--\n"
"\n"
"Returns a bytes object containing compressed data.\n"
"\n"
"  data\n"
"    Binary data to be compressed.\n"
"  level\n"
"    Compression level, in 0-3.\n"
"  flag\n"
"    Controls which header and trailer are used.\n"
"  mem_level\n"
"    Sets the memory level for the memory buffer. \n"
"    Larger buffers improve performance.\n"
"  hist_bits\n"
"    Sets the size of the view window. The size equals \n"
"    2^hist_bits. Similar to zlib wbits value except that \n"
"    the header and trailer are controlled by the flag parameter.");

#define IGZIP_LIB_COMPRESS_METHODDEF    \
    {"compress", (PyCFunction)(void(*)(void))igzip_lib_compress, METH_VARARGS|METH_KEYWORDS, igzip_lib_compress__doc__}

static PyObject *
igzip_lib_compress(PyObject *module, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"", "level", "flag", "mem_level", "hist_bits", NULL};
    char *format ="y*|iiii:compress";
    Py_buffer data = {NULL, NULL};
    int level = ISAL_DEFAULT_COMPRESSION;
    int flag = COMP_DEFLATE;
    int mem_level = MEM_LEVEL_DEFAULT;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords, 
            &data, &level, &flag, &mem_level, &hist_bits)) {
        return NULL;
    }
    PyObject *return_value = igzip_lib_compress_impl(
        &data, level, flag, mem_level, hist_bits);
    PyBuffer_Release(&data);
    return return_value;
}

PyDoc_STRVAR(igzip_lib_decompress__doc__,
"decompress($module, data, /, flag=DECOMP_DEFLATE, hist_bits=MAX_HIST_BITS,\n"
"           bufsize=DEF_BUF_SIZE)\n"
"--\n"
"\n"
"Returns a bytes object containing the uncompressed data.\n"
"\n"
"  data\n"
"    Compressed data.\n"
"  flag\n"
"    The container format.\n"
"  hist_bits\n"
"    The window buffer size.\n"
"  bufsize\n"
"    The initial output buffer size.");

#define IGZIP_LIB_DECOMPRESS_METHODDEF    \
    {"decompress", (PyCFunction)(void(*)(void))igzip_lib_decompress, METH_VARARGS|METH_KEYWORDS, igzip_lib_decompress__doc__}

static PyObject *
igzip_lib_decompress(PyObject *module, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"", "flag", "hist_bits", "bufsize", NULL};
    char *format ="y*|iin:decompress";
    Py_buffer data = {NULL, NULL};
    int flag = DECOMP_DEFLATE;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;
    Py_ssize_t bufsize = DEF_BUF_SIZE;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords, 
            &data, &flag, &hist_bits, &bufsize)) {
        return NULL;
    }
    PyObject * return_value = igzip_lib_decompress_impl(&data, flag, hist_bits, bufsize);
    PyBuffer_Release(&data);
    return return_value;
}

PyDoc_STRVAR(igzip_lib_IgzipDecompressor_decompress__doc__,
"decompress($self, data, /, max_length=-1)\n"
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
    {"decompress", (PyCFunction)(void(*)(void))igzip_lib_IgzipDecompressor_decompress, METH_VARARGS|METH_KEYWORDS, igzip_lib_IgzipDecompressor_decompress__doc__}

static PyObject *
igzip_lib_IgzipDecompressor_decompress(IgzipDecompressor *self, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"", "max_length", NULL};
    char *format = "y*|n:decompress";
    Py_buffer data = {NULL, NULL};
    Py_ssize_t max_length = -1;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords, &data, &max_length)) {
        return NULL;
    }
    PyObject *result = NULL;
    if (self->eof)
        PyErr_SetString(PyExc_EOFError, "End of stream already reached");
    else
        result = decompress(self, data.buf, data.len, max_length);
    PyBuffer_Release(&data);
    return result;
}

PyDoc_STRVAR(igzip_lib_IgzipDecompressor___init____doc__,
"IgzipDecompressor(flag=0, hist_bits=15, zdict=b\'\')\n"
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

static PyObject *
igzip_lib_IgzipDecompressor__new__(PyTypeObject *type, 
                                   PyObject *args, 
                                   PyObject *kwargs)
{
    char *keywords[] = {"flag", "hist_bits", "zdict", NULL};
    char *format = "|iiO:IgzipDecompressor";
    int flag = ISAL_DEFLATE;
    int hist_bits = ISAL_DEF_MAX_HIST_BITS;
    PyObject *zdict = NULL;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords, &flag, &hist_bits, &zdict)) {
        return NULL;
    }
    IgzipDecompressor *self = PyObject_New(IgzipDecompressor, type); 
    int err;
    self->eof = 0;
    self->needs_input = 1;
    self->avail_in_real = 0;
    self->input_buffer = NULL;
    self->input_buffer_size = 0;
    self->zdict = zdict;
    self->unused_data = PyBytes_FromStringAndSize(NULL, 0);
    if (self->unused_data == NULL) {
        Py_CLEAR(self);
        return NULL;
    }
    isal_inflate_init(&(self->state));
    self->state.hist_bits = hist_bits;
    self->state.crc_flag = flag;
    if (self->zdict != NULL){
        Py_buffer zdict_buf;
        if (PyObject_GetBuffer(self->zdict, &zdict_buf, PyBUF_SIMPLE) == -1) {
                Py_CLEAR(self);
                return NULL;
        }
        if ((size_t)zdict_buf.len > UINT32_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                           "zdict length does not fit in an unsigned 32-bits int");
            PyBuffer_Release(&zdict_buf);
            Py_CLEAR(self);
            return NULL;
        }
        err = isal_inflate_set_dict(&(self->state), zdict_buf.buf, 
                                    (uint32_t)zdict_buf.len);
        PyBuffer_Release(&zdict_buf);
        if (err != ISAL_DECOMP_OK) {
            isal_inflate_error(err);
            Py_CLEAR(self);
            return NULL;
        }        
    }
    return (PyObject *)self;
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

PyDoc_STRVAR(IgzipDecompressor_crc_doc,
"The checksum that is saved if DECOMP_ZLIB* or DECOMP_GZIP* flags are used.");

static PyMemberDef IgzipDecompressor_members[] = {
    {"eof", T_BOOL, offsetof(IgzipDecompressor, eof),
     READONLY, IgzipDecompressor_eof__doc__},
    {"unused_data", T_OBJECT_EX, offsetof(IgzipDecompressor, unused_data),
     READONLY, IgzipDecompressor_unused_data__doc__},
    {"needs_input", T_BOOL, offsetof(IgzipDecompressor, needs_input), READONLY,
     IgzipDecompressor_needs_input_doc},
    {"crc", T_UINT, offsetof(IgzipDecompressor, state) + offsetof(struct inflate_state, crc), READONLY,
     IgzipDecompressor_crc_doc},
    {NULL}
};

static PyTypeObject IgzipDecompressor_Type = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "igzip_lib.IgzipDecompressor",
    .tp_basicsize = sizeof(IgzipDecompressor),
    .tp_dealloc = (destructor)IgzipDecompressor_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_doc = igzip_lib_IgzipDecompressor___init____doc__,
    .tp_methods = IgzipDecompressor_methods,
    .tp_members =  IgzipDecompressor_members,
    .tp_new = igzip_lib_IgzipDecompressor__new__,
};

static PyMethodDef IgzipLibMethods[] = {
    IGZIP_LIB_COMPRESS_METHODDEF,
    IGZIP_LIB_DECOMPRESS_METHODDEF,
    {NULL, NULL, 0, NULL}        /* Sentinel */
};

PyDoc_STRVAR(igizp_lib_module_documentation,
"Pythonic interface to ISA-L's igzip_lib.\n"
"\n"
"This module comes with the following constants:\n"
"\n"
".. list-table::\n"
"   :widths: 20 60\n"
"   :header-rows: 0\n"
"\n"
"   *  - ``ISAL_BEST_SPEED``\n"
"      - The lowest compression level (0)\n"
"   *  - ``ISAL_BEST_COMPRESSION``\n"
"      - The highest compression level (3)\n"
"   *  -  ``ISAL_DEFAULT_COMPRESSION``\n"
"      - The compromise compression level (2)\n"
"   *  - ``DEF_BUF_SIZE``\n"
"      - Default size for the starting buffer (16K)\n"
"   *  - ``MAX_HIST_BITS``\n"
"      - Maximum window size bits (15).\n"
"   *  - ``COMP_DEFLATE``\n"
"      - Flag to compress to a raw deflate block\n"
"   *  - ``COMP_GZIP``\n"
"      - | Flag to compress a gzip block, consisting of a gzip header, a raw\n"
"        | deflate block and a gzip trailer.\n"
"   *  - ``COMP_GZIP_NO_HDR``\n"
"      - Flag to compress a gzip block without a header.\n"
"   *  - ``COMP_ZLIB``\n"
"      - | Flag to compress a zlib block, consisting of a zlib header, a raw\n"
"        | deflate block and a zlib trailer.\n"
"   *  - ``COMP_ZLIB_NO_HDR``\n"
"      - Flag to compress a zlib block without a header.\n"
"   *  - ``DECOMP_DEFLATE``\n"
"      - Flag to decompress a raw deflate block.\n"
"   *  - ``DECOMP_GZIP``\n"
"      - | Flag to decompress a gzip block including header and verify the\n"
"        |  checksums in the trailer.\n"
"   *  - ``DECOMP_GZIP_NO_HDR``\n"
"      - | Decompresses a raw deflate block (no header, no trailer) and \n"
"        | updates the crc member on the IgzipDecompressor object with a \n"
"        | crc32 checksum.\n"
"   *  - ``DECOMP_GZIP_NO_HDR_VER``\n"
"      - | Like DECOMP_GZIP_NO_HDR but reads the trailer and verifies the \n"
"        | crc32 checksum.\n"
"   *  - ``DECOMP_ZLIB``\n"
"      - | Flag to decompress a zlib block including header and verify the\n"
"        | checksums in the trailer.\n"
"   *  - ``DECOMP_ZLIB_NO_HDR``\n"
"      - | Decompresses a raw deflate block (no header, no trailer) and \n"
"        | updates the crc member on the IgzipDecompressor object with an \n"
"        | adler32 checksum.\n"
"   *  - ``DECOMP_ZLIB_NO_HDR_VER``\n"
"      - | Like DECOMP_ZLIB_NO_HDR but reads the trailer and verifies the \n"
"        | adler32 checksum.\n"
"   *  - ``MEM_LEVEL_DEFAULT``\n"
"      - | The default memory level for the internal level buffer. \n"
"        | (Equivalent to MEM_LEVEL_LARGE.)\n"
"   *  - ``MEM_LEVEL_MIN``\n"
"      -  The minimum memory level.\n"
"   *  - ``MEM_LEVEL_SMALL``\n"
"      - \n"
"   *  - ``MEM_LEVEL_MEDIUM``\n"
"      - \n"
"   *  - ``MEM_LEVEL_LARGE``\n"
"      - \n"
"   *  - ``MEM_LEVEL_EXTRA_LARGE``\n"
"      - The largest memory level.\n"
);

static struct PyModuleDef igzip_lib_module = {
    PyModuleDef_HEAD_INIT,
    "igzip_lib",   /* name of module */
    igizp_lib_module_documentation, /* module documentation, may be NULL */
    0,
    IgzipLibMethods
};


PyMODINIT_FUNC
PyInit_igzip_lib(void)
{
    PyObject *m;

    m = PyModule_Create(&igzip_lib_module);
    if (m == NULL)
        return NULL;

    IsalError = PyErr_NewException("igzip_lib.IsalError", NULL, NULL);
    if (IsalError == NULL) {
        return NULL;
    }
    Py_INCREF(IsalError);
    if (PyModule_AddObject(m, "error", IsalError) < 0) {
        return NULL;
    }
    Py_INCREF(IsalError);
    if (PyModule_AddObject(m, "IsalError", IsalError) < 0) {
        return NULL;
    }

    if (PyType_Ready(&IgzipDecompressor_Type) != 0)
        return NULL;
    Py_INCREF(&IgzipDecompressor_Type);
    if (PyModule_AddObject(m, "IgzipDecompressor",  (PyObject *)&IgzipDecompressor_Type) < 0) {
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
