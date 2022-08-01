//  Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
// 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
// Python Software Foundation; All Rights Reserved

// This file is part of python-isal which is distributed under the 
// PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

// This file was modified from Cpython's Modules/zlibmodule.c file.
// Changes compared to CPython:
// - All zlib naming changed to isal_zlib
// - Including a few constants that are more specific to the ISA-L library
//   (ISAL_DEFAULT_COMPRESSION etc).
// - Zlib to ISA-L conversion functions were included.
// - All compression and checksum functions from zlib replaced with ISA-L
//   compatible functions.
// - No locks in Compress and Decompress objects. These were deemed unnecessary
//   as the ISA-L functions do not allocate memory, unlike the zlib
//   counterparts.
// - zlib.compress also has a 'wbits' argument. This change was included in
//   Python 3.11. It allows for faster gzip compression by using
//   isal_zlib.compress(data, wbits=31).
// - Argument parsers were written using th CPython API rather than argument
//   clinic.


#include "isal_shared.h"

#include <isa-l/crc.h>

#define Z_DEFAULT_STRATEGY    0
#define Z_FILTERED            1
#define Z_HUFFMAN_ONLY        2
#define Z_RLE                 3
#define Z_FIXED               4

#define Z_DEFLATED 8

// Flush modes copied from zlib.h
#define Z_NO_FLUSH      0
#define Z_PARTIAL_FLUSH 1
#define Z_SYNC_FLUSH    2
#define Z_FULL_FLUSH    3
#define Z_FINISH        4
#define Z_BLOCK         5
#define Z_TREES         6

#define DEF_MEM_LEVEL 8

static PyTypeObject IsalZlibCompType;
static PyTypeObject IsalZlibDecompType;

static int 
wbits_to_flag_and_hist_bits_deflate(int wbits, int *hist_bits, int *flag) 
{
    if (wbits >= 9 && wbits <= 15){
        *hist_bits = wbits;
        *flag = IGZIP_ZLIB;
    }
    else if (wbits >= 25  && wbits <= 31) {
        *hist_bits = wbits - 16;
        *flag = IGZIP_GZIP;
    }
    else if (wbits >=-15 && wbits <= -9) {
        *hist_bits = -wbits;
        *flag = IGZIP_DEFLATE;
    }
    else {
        PyErr_Format(IsalError, "Invalid wbits value: %d", wbits);
        return -1;
    }
    return 0;
}

static int 
wbits_to_flag_and_hist_bits_inflate(int wbits, int *hist_bits, int *flag) 
{
    if (wbits == 0) {
        *hist_bits = 0;
        *flag = ISAL_ZLIB;
    }
    else if (wbits >= 8 && wbits <= 15){
        *hist_bits = wbits;
        *flag = ISAL_ZLIB;
    }
    else if (wbits >= 24  && wbits <= 31) {
        *hist_bits = wbits - 16;
        *flag = ISAL_GZIP;
    }
    else if (wbits >=-15 && wbits <= -8) {
        *hist_bits = -wbits;
        *flag = ISAL_DEFLATE;
    }
    else if (wbits >=40 && wbits <= 47) {
        *hist_bits = wbits - 32;
        return 1;
    }
    else {
        PyErr_Format(IsalError, "Invalid wbits value: %d", wbits);
        return -1;
    }
    return 0;
}

static const int ZLIB_MEM_LEVEL_TO_ISAL[10] = {
    0, // 0 Is an invalid mem_level in zlib,
    MEM_LEVEL_MIN, // 1 -> min
    MEM_LEVEL_SMALL, // 2-3 -> SMALL
    MEM_LEVEL_SMALL,
    MEM_LEVEL_MEDIUM, // 4-6 -> MEDIUM
    MEM_LEVEL_MEDIUM, 
    MEM_LEVEL_MEDIUM,
    MEM_LEVEL_LARGE, // 7-8 LARGE. The zlib module default = 8. Large is the ISA-L default value.
    MEM_LEVEL_LARGE,
    MEM_LEVEL_EXTRA_LARGE, // 9 -> EXTRA_LARGE. 
};


static int zlib_mem_level_to_isal(int mem_level) {
    if (mem_level < 1 || mem_level > 9) {
        PyErr_Format(PyExc_ValueError, 
        "Invalid mem level: %d. Mem level should be between 1 and 9");
        return -1;}
    return ZLIB_MEM_LEVEL_TO_ISAL[mem_level];
}

static int
data_is_gzip(Py_buffer *data){
    if (data->len < 2) 
        return 0;
    uint8_t *buf = (uint8_t *)data->buf;
    return (buf[0] == 31 && buf[1] == 139);
}


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

    if (nargs < 1 || nargs > 2) {
        PyErr_Format(
            PyExc_TypeError, 
            "adler32 takes exactly 1 or 2 arguments, got %d", 
            nargs);
        return NULL;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    if (nargs > 1) {
        value = (uint32_t)PyLong_AsUnsignedLongMask(args[1]);
        if (value == (uint32_t)-1 && PyErr_Occurred()) {
            PyBuffer_Release(&data);
            return NULL;
        }
    }
    value = isal_adler32(value, data.buf, (uint64_t)data.len);
    return_value = PyLong_FromUnsignedLong(value & 0xffffffffU);
    PyBuffer_Release(&data);
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

    if (nargs < 1 || nargs > 2) {
        PyErr_Format(
            PyExc_TypeError, 
            "crc32 takes exactly 1 or 2 arguments, got %d", 
            nargs);
        return NULL;
    }
    if (PyObject_GetBuffer(args[0], &data, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    if (nargs > 1) {
        value = (uint32_t)PyLong_AsUnsignedLongMask(args[1]);
        if (value == (uint32_t)-1 && PyErr_Occurred()) {
            PyBuffer_Release(&data);
            return NULL;
        }
    }
    value = crc32_gzip_refl(value, data.buf, (uint64_t)data.len);
    return_value = PyLong_FromUnsignedLong(value & 0xffffffffU);
    PyBuffer_Release(&data);
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
    {"compress", (PyCFunction)(void(*)(void))isal_zlib_compress, METH_VARARGS|METH_KEYWORDS, zlib_compress__doc__}

static PyObject *
isal_zlib_compress(PyObject *module, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"", "level", "wbits", NULL};
    char *format ="y*|ii:isal_zlib.compress";
    Py_buffer data = {NULL, NULL};
    int level = ISAL_DEFAULT_COMPRESSION;
    int wbits = ISAL_DEF_MAX_HIST_BITS;

    if (!PyArg_ParseTupleAndKeywords(
        args, kwargs, format, keywords, &data, &level, &wbits)) {
        return NULL;
    }

    int hist_bits = -1;
    int flag = -1;

    if (wbits_to_flag_and_hist_bits_deflate(wbits, &hist_bits, &flag) != 0) {
        PyBuffer_Release(&data);
        return NULL;
    }
    PyObject *return_value = igzip_lib_compress_impl(
        &data, level, flag, MEM_LEVEL_DEFAULT, hist_bits);
    PyBuffer_Release(&data);
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
    {"decompress", (PyCFunction)(void(*)(void))isal_zlib_decompress, METH_VARARGS|METH_KEYWORDS, zlib_decompress__doc__}


static PyObject *
isal_zlib_decompress(PyObject *module, PyObject *args, PyObject *kwargs)
{
    PyObject *return_value = NULL;
    char *keywords[] = {"", "wbits", "bufsize", NULL};
    char *format ="y*|in:isal_zlib.decompress";
    Py_buffer data = {NULL, NULL};
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    Py_ssize_t bufsize = DEF_BUF_SIZE;

    if (!PyArg_ParseTupleAndKeywords(
        args, kwargs, format, keywords, &data, &wbits, &bufsize)) {
        return NULL;
    }
    int hist_bits;
    int flag; 
   
    int convert_result = wbits_to_flag_and_hist_bits_inflate(wbits, &hist_bits, &flag);
    if (convert_result < 0) {
        PyBuffer_Release(&data);
        return NULL;
    }
    if (convert_result > 0) {
        if (data_is_gzip(&data)) 
            flag = ISAL_GZIP;
        else 
            flag = ISAL_ZLIB;
    }
    return_value = igzip_lib_decompress_impl(&data, flag, hist_bits, bufsize);
    PyBuffer_Release(&data);
    return return_value;
}

typedef struct
{
    PyObject_HEAD
    struct isal_zstream zst;
    int is_initialised;
    uint8_t * level_buf;
    PyObject *zdict;
} compobject;

static void
Comp_dealloc(compobject *self)
{
    if (self->is_initialised && self->level_buf != NULL)
        PyMem_Free(self->level_buf);
    Py_XDECREF(self->zdict);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static compobject *
newcompobject()
{
    compobject *self;
    self = PyObject_New(compobject, &IsalZlibCompType);
    if (self == NULL)
        return NULL;
    self->is_initialised = 0;
    self->zdict = NULL;
    self->level_buf = NULL;
    return self;
}


typedef struct
{
    PyObject_HEAD
    struct inflate_state zst;
    PyObject *unused_data;
    PyObject *unconsumed_tail;
    char eof;
    int is_initialised;
    int method_set;
    PyObject *zdict;
} decompobject;

static void
Decomp_dealloc(decompobject *self)
{
    Py_XDECREF(self->unused_data);
    Py_XDECREF(self->unconsumed_tail);
    Py_XDECREF(self->zdict);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
set_inflate_zdict(decompobject *self)
{
    Py_buffer zdict_buf;
    int err;

    if (PyObject_GetBuffer(self->zdict, &zdict_buf, PyBUF_SIMPLE) == -1) {
        return -1;
    }
    if ((size_t)zdict_buf.len > UINT32_MAX) {
        PyErr_SetString(PyExc_OverflowError,
                        "zdict length does not fit in an unsigned 32-bits int");
        PyBuffer_Release(&zdict_buf);
        return -1;
    }
    err = isal_inflate_set_dict(&(self->zst),
                               zdict_buf.buf, (uint32_t)zdict_buf.len);
    PyBuffer_Release(&zdict_buf);
    if (err != ISAL_DECOMP_OK) {
        isal_inflate_error(err);
        return -1;
    }
    return 0;
}

static decompobject *
newdecompobject()
{
    decompobject *self;
    self = PyObject_New(decompobject, &IsalZlibDecompType);
    if (self == NULL)
        return NULL;
    self->eof = 0;
    self->is_initialised = 0;
    self->method_set = 0;
    self->zdict = NULL;
    self->unused_data = PyBytes_FromStringAndSize("", 0);
    if (self->unused_data == NULL) {
        Py_DECREF(self);
        return NULL;
    }
    self->unconsumed_tail = PyBytes_FromStringAndSize("", 0);
    if (self->unconsumed_tail == NULL) {
        Py_DECREF(self);
        return NULL;
    }
    return self;
}

static PyObject *
isal_zlib_compressobj_impl(PyObject *module, int level, int method, int wbits,
                           int memLevel, int strategy, Py_buffer *zdict)
{
    compobject *self = NULL;
    int err;
    uint32_t level_buf_size = 0;
    int flag = -1;
    int hist_bits = -1;

    if (method != Z_DEFLATED){
         PyErr_Format(PyExc_ValueError, 
                      "Unsupported method: %d. Only DEFLATED is supported.",
                      method);
         goto error; 
    }
    if (strategy != Z_DEFAULT_STRATEGY){
        err = PyErr_WarnEx(
            PyExc_UserWarning, 
            "Only one strategy is supported when using isal_zlib. Using the default strategy.",
            1);
        if (err == -1)
            // Warning was turned into an exception.
            goto error;
    }
    if (zdict->buf != NULL && (size_t)zdict->len > UINT32_MAX) {
        PyErr_SetString(PyExc_OverflowError,
                        "zdict length does not fit in an unsigned 32-bit int");
        goto error;
    }
    int isal_mem_level = zlib_mem_level_to_isal(memLevel);
    if (isal_mem_level == -1)
        goto error;
    if (wbits_to_flag_and_hist_bits_deflate(wbits, &hist_bits, &flag) == -1) {
        PyErr_Format(PyExc_ValueError, "Invalid wbits value: %d", wbits);
        goto error;
    }
    if (mem_level_to_bufsize(
        level, isal_mem_level, &level_buf_size) == -1) {
        PyErr_Format(PyExc_ValueError, 
                     "Invalid compression level: %d. Compression level should be between 0 and 3", 
                     level);
        goto error;
    }   

    self = newcompobject();
    if (self == NULL)
        goto error;
    self->level_buf = (uint8_t *)PyMem_Malloc(level_buf_size);
    if (self->level_buf == NULL){
        PyErr_NoMemory();
        goto error;
    }
    isal_deflate_init(&(self->zst));
    self->zst.next_in = NULL;
    self->zst.avail_in = 0;
    self->zst.level_buf_size = level_buf_size;
    self->zst.level_buf = self->level_buf;
    self->zst.level = level;
    self->zst.hist_bits = (uint16_t)hist_bits;
    self->zst.gzip_flag = (uint16_t)flag;

    self->is_initialised = 1;
    if (zdict->buf == NULL) {
        goto success;
    } else {
        err = isal_deflate_set_dict(&(self->zst),
                                    zdict->buf, (uint32_t)zdict->len);
        if (err == COMP_OK)
            goto success;
        PyErr_SetString(PyExc_ValueError, "Invalid dictionary");
        goto error;
        }
 error:
    if (self != NULL) {
        if (self->level_buf != NULL)
            PyMem_Free(self->level_buf);
        Py_CLEAR(self);
    }

 success:
    return (PyObject *)self;
}


static PyObject *
isal_zlib_decompressobj_impl(PyObject *module, int wbits, PyObject *zdict)
{
    int err;
    decompobject *self;
    int flag;
    int hist_bits; 
    if (zdict != NULL && !PyObject_CheckBuffer(zdict)) {
        PyErr_SetString(PyExc_TypeError,
                        "zdict argument must support the buffer protocol");
        return NULL;
    }
    self = newdecompobject();
    if (self == NULL)
        return NULL;

    isal_inflate_init(&(self->zst));
    err = wbits_to_flag_and_hist_bits_inflate(wbits, &hist_bits, &flag);
    if (err < 0) {
        PyErr_Format(PyExc_ValueError, "Invalid wbits value: %d", wbits);
        return NULL;
    }
    else if (err == 0) {
        self->zst.crc_flag = flag;
        self->method_set = 1;
    }
    self->zst.hist_bits = hist_bits;
    self->zst.next_in = NULL;
    self->zst.avail_in = 0;
    if (zdict != NULL) {
        Py_INCREF(zdict);
        self->zdict = zdict;
    }
    self->is_initialised = 1;

    if (self->zdict != NULL) {  
        if (set_inflate_zdict(self) < 0) {
            Py_DECREF(self);
            return NULL;
        }
    }
    return (PyObject *)self;
}

static PyObject *
isal_zlib_Compress_compress_impl(compobject *self, Py_buffer *data)
/*[clinic end generated code: output=5d5cd791cbc6a7f4 input=0d95908d6e64fab8]*/
{
    PyObject *RetVal = NULL;
    Py_ssize_t ibuflen, obuflen = DEF_BUF_SIZE;
    int err;

    self->zst.next_in = data->buf;
    ibuflen = data->len;

    do {
        arrange_input_buffer(&(self->zst.avail_in), &ibuflen);
        do {
            obuflen = arrange_output_buffer(&(self->zst.avail_out),
                                            &(self->zst.next_out), &RetVal, obuflen);
            if (obuflen < 0)
                goto error;

            err = isal_deflate(&self->zst);

            if (err != COMP_OK) {
                isal_deflate_error(err);
                goto error;
            }
        } while (self->zst.avail_out == 0);
        assert(self->zst.avail_in == 0);

    } while (ibuflen != 0);

    if (_PyBytes_Resize(&RetVal, self->zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) == 0)
        goto success;

 error:
    Py_CLEAR(RetVal);
 success:
    return RetVal;
}

/* Helper for objdecompress() and flush(). Saves any unconsumed input data in
   self->unused_data or self->unconsumed_tail, as appropriate. */
static int
save_unconsumed_input(decompobject *self, Py_buffer *data, int err)
{
    if (self->zst.block_state == ISAL_BLOCK_FINISH) {
        /* The end of the compressed data has been reached. Store the leftover
           input data in self->unused_data. */
        if (self->zst.avail_in > 0) {
            Py_ssize_t old_size = PyBytes_GET_SIZE(self->unused_data);
            Py_ssize_t new_size, left_size;
            PyObject *new_data;
            Py_ssize_t bytes_in_bitbuffer = bitbuffer_size(&(self->zst));
            left_size = (uint8_t *)data->buf + data->len - self->zst.next_in;
            if (left_size + bytes_in_bitbuffer > (PY_SSIZE_T_MAX - old_size)) {
                PyErr_NoMemory();
                return -1;
            }
            // There might also be data left in the bit_buffer.
            new_size = old_size + left_size + bytes_in_bitbuffer;
            new_data = PyBytes_FromStringAndSize(NULL, new_size);
            if (new_data == NULL)
                return -1;
            char * new_data_ptr = PyBytes_AS_STRING(new_data);
            memcpy(new_data_ptr,
                   PyBytes_AS_STRING(self->unused_data), old_size);
            bitbuffer_copy(&(self->zst), new_data_ptr + old_size, bytes_in_bitbuffer);
            memcpy(new_data_ptr + old_size + bytes_in_bitbuffer,
                   self->zst.next_in, left_size);       
            Py_SETREF(self->unused_data, new_data);
            self->zst.avail_in = 0;
        }
    }

    if (self->zst.avail_in > 0 || PyBytes_GET_SIZE(self->unconsumed_tail)) {
        /* This code handles two distinct cases:
           1. Output limit was reached. Save leftover input in unconsumed_tail.
           2. All input data was consumed. Clear unconsumed_tail. */
        Py_ssize_t left_size = (uint8_t *)data->buf + data->len - self->zst.next_in;
        PyObject *new_data = PyBytes_FromStringAndSize(
                (char *)self->zst.next_in, left_size);
        if (new_data == NULL)
            return -1;
        Py_SETREF(self->unconsumed_tail, new_data);
    }

    return 0;
}

static PyObject *
isal_zlib_Decompress_decompress_impl(decompobject *self, Py_buffer *data,
                                Py_ssize_t max_length)
{
    int err = ISAL_DECOMP_OK;
    Py_ssize_t ibuflen, obuflen = DEF_BUF_SIZE, hard_limit;
    PyObject *RetVal = NULL;

    if (max_length < 0) {
        PyErr_SetString(PyExc_ValueError, "max_length must be non-negative");
        return NULL;
    } else if (max_length == 0)
        hard_limit = PY_SSIZE_T_MAX;
    else
        hard_limit = max_length;

    if (!self->method_set) {
        if (data_is_gzip(data)){
            self->zst.crc_flag = ISAL_GZIP;
        }
        else {
            self->zst.crc_flag = ISAL_ZLIB;
        }
        self->method_set = 1;
    }
    self->zst.next_in = data->buf;
    ibuflen = data->len;

    /* limit amount of data allocated to max_length */
    if (max_length && obuflen > max_length)
        obuflen = max_length;

    do {
        arrange_input_buffer(&(self->zst.avail_in), &ibuflen);

        do {
            obuflen = arrange_output_buffer_with_maximum(&(self->zst.avail_out),
                                                         &(self->zst.next_out), 
                                                         &RetVal,
                                                         obuflen, hard_limit);
            if (obuflen == -2) {
                if (max_length > 0) {
                    goto save;
                }
                PyErr_NoMemory();
            }
            if (obuflen < 0) {
                goto abort;
            }

            err = isal_inflate(&self->zst);
            if (err != ISAL_DECOMP_OK){
                isal_inflate_error(err);
                goto abort;
            }

        } while (self->zst.avail_out == 0 && self->zst.block_state != ISAL_BLOCK_FINISH);

    } while (self->zst.block_state != ISAL_BLOCK_FINISH && ibuflen != 0);

 save:
    if (save_unconsumed_input(self, data, err) < 0)
        goto abort;

    if (self->zst.block_state == ISAL_BLOCK_FINISH) {
        self->eof = 1;
    }

    if (_PyBytes_Resize(&RetVal, self->zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) == 0)
        goto success;

 abort:
    Py_CLEAR(RetVal);
 success:
    return RetVal;
}

static PyObject *
isal_zlib_Compress_flush_impl(compobject *self, int mode)
{
    int err;
    Py_ssize_t length = DEF_BUF_SIZE;
    PyObject *RetVal = NULL;

    /* Flushing with Z_NO_FLUSH is a no-op, so there's no point in
       doing any work at all; just return an empty string. */
    if (mode == Z_NO_FLUSH) {
        return PyBytes_FromStringAndSize(NULL, 0);
    } else if (mode == Z_FINISH) {
        self->zst.flush = FULL_FLUSH;
        self->zst.end_of_stream = 1;
    } else if (mode == Z_FULL_FLUSH){
        self->zst.flush = FULL_FLUSH;
    } else if (mode == Z_SYNC_FLUSH) {
        self->zst.flush = SYNC_FLUSH;
    } else {
        PyErr_Format(IsalError, 
                     "Unsupported flush mode: %d", mode);
        return NULL;
    }

    self->zst.avail_in = 0;

    do {
        length = arrange_output_buffer(&(self->zst.avail_out), 
                                       &(self->zst.next_out), &RetVal, length);
        if (length < 0) {
            Py_CLEAR(RetVal);
            goto error;
        }

        err = isal_deflate(&self->zst);

        if (err != COMP_OK) {
            isal_deflate_error(err);
            Py_CLEAR(RetVal);
            goto error;
        }
    } while (self->zst.avail_out == 0);
    assert(self->zst.avail_in == 0);

    /* If mode is Z_FINISH, we free the level buffer. 
       Note we should only get ZSTATE_END when
       mode is Z_FINISH, but checking both for safety*/
    if (self->zst.internal_state.state == ZSTATE_END && mode == Z_FINISH) {
        PyMem_FREE(self->level_buf);
        self->zst.level_buf_size = 0;
        self->zst.level_buf = NULL;
        self->is_initialised = 0;
    } else {
        // reset the flush mode back so compressobject can be used again.
        self->zst.flush = NO_FLUSH;
    }

    if (_PyBytes_Resize(&RetVal, self->zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) < 0)
        Py_CLEAR(RetVal);

 error:
    return RetVal;
}

static PyObject *
isal_zlib_Decompress_flush_impl(decompobject *self, Py_ssize_t length)
{
    int err;
    Py_buffer data;
    PyObject *RetVal = NULL;
    Py_ssize_t ibuflen;

    if (length <= 0) {
        PyErr_SetString(PyExc_ValueError, "length must be greater than zero");
        return NULL;
    }

    if (PyObject_GetBuffer(self->unconsumed_tail, &data, PyBUF_SIMPLE) == -1) {
        return NULL;
    }

    self->zst.next_in = data.buf;
    ibuflen = data.len;

    do {
        arrange_input_buffer(&(self->zst.avail_in), &ibuflen);

        do {
            length = arrange_output_buffer(&(self->zst.avail_out),
                                           &(self->zst.next_out), &RetVal, length);
            if (length < 0)
                goto abort;

            err = isal_inflate(&self->zst);

            if (err != ISAL_DECOMP_OK) {
                isal_inflate_error(err);
                goto abort;
            }

        } while (self->zst.avail_out == 0 && self->zst.block_state != ISAL_BLOCK_FINISH);

    } while (self->zst.block_state != ISAL_BLOCK_FINISH && ibuflen != 0);

    if (save_unconsumed_input(self, &data, err) < 0)
        goto abort;

    /* If at end of stream, clean up any memory allocated by zlib. */
    if (self->zst.block_state == ISAL_BLOCK_FINISH) {
        self->eof = 1;
        self->is_initialised = 0;
    }

    if (_PyBytes_Resize(&RetVal, self->zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) == 0)
        goto success;

 abort:
    Py_CLEAR(RetVal);
 success:
    PyBuffer_Release(&data);
    return RetVal;
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
    {"compressobj", (PyCFunction)(void(*)(void))isal_zlib_compressobj, METH_VARARGS|METH_KEYWORDS, isal_zlib_compressobj__doc__}

static PyObject *
isal_zlib_compressobj(PyObject *module, PyObject *args, PyObject *kwargs)
{
    PyObject *return_value = NULL;
    char *keywords[] = {"level", "method", "wbits", "memLevel", "strategy", "zdict", NULL};
    char *format = "|iiiiiy*:compressobj";
    int level = ISAL_DEFAULT_COMPRESSION;
    int method = Z_DEFLATED;
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    int memLevel = DEF_MEM_LEVEL;
    int strategy = Z_DEFAULT_STRATEGY;
    Py_buffer zdict = {NULL, NULL};

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords,
            &level, &method, &wbits, &memLevel, &strategy, &zdict)) {
        return NULL;
    }
    return_value = isal_zlib_compressobj_impl(module, level, method, wbits, memLevel, strategy, &zdict);
    PyBuffer_Release(&zdict);
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
    {"decompressobj", (PyCFunction)(void(*)(void))isal_zlib_decompressobj, METH_VARARGS|METH_KEYWORDS, isal_zlib_decompressobj__doc__}

static PyObject *
isal_zlib_decompressobj(PyObject *module, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"wbits", "zdict", NULL};
    char *format = "|iO:decompressobj";
    int wbits = ISAL_DEF_MAX_HIST_BITS;
    PyObject *zdict = NULL;

    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords,
            &wbits, &zdict)) {
        return NULL;
    }
    return isal_zlib_decompressobj_impl(module, wbits, zdict);
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
    {"compress", (PyCFunction)(void(*)(void))isal_zlib_Compress_compress, METH_O, isal_zlib_Compress_compress__doc__}


static PyObject *
isal_zlib_Compress_compress(compobject *self, PyObject *data)
{
    Py_buffer data_buf;
    if (PyObject_GetBuffer(data, &data_buf, PyBUF_SIMPLE) < 0) {
        return NULL;
    }
    PyObject *return_value = isal_zlib_Compress_compress_impl(self, &data_buf);
    PyBuffer_Release(&data_buf);
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
    {"decompress", (PyCFunction)(void(*)(void))isal_zlib_Decompress_decompress, METH_VARARGS|METH_KEYWORDS, isal_zlib_Decompress_decompress__doc__}


static PyObject *
isal_zlib_Decompress_decompress(decompobject *self, PyObject *args, PyObject *kwargs)
{
    char *keywords[] = {"", "max_length", NULL};
    char *format = "y*|n:decompress";
   
    Py_buffer data = {NULL, NULL};
    Py_ssize_t max_length = 0;
    if (!PyArg_ParseTupleAndKeywords(
            args, kwargs, format, keywords, &data, &max_length)) {
        return NULL;
    }
    PyObject *return_value = isal_zlib_Decompress_decompress_impl(self, &data, max_length);
    PyBuffer_Release(&data);
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
    Py_ssize_t mode; 
    if (nargs == 0) {
        mode = Z_FINISH;
    }
    else if (nargs == 1) {
        PyObject *mode_arg = args[0];
        if (PyLong_Check(mode_arg)) {
            mode = PyLong_AsSsize_t(mode_arg);
        }
        else {
            mode = PyNumber_AsSsize_t(mode_arg, PyExc_OverflowError);
        }
        if (mode == -1 && PyErr_Occurred()) {
            return NULL;
        }
    }
    else {
        PyErr_Format(
            PyExc_TypeError,
            "flush() only takes 0 or 1 positional arguments got %d", 
            nargs
        );
        return NULL;
    }
    return isal_zlib_Compress_flush_impl(self, mode);
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
    {"flush", (PyCFunction)(void(*)(void))isal_zlib_Decompress_flush, METH_FASTCALL, isal_zlib_Decompress_flush__doc__}

static PyObject *
isal_zlib_Decompress_flush(decompobject *self, PyObject *const *args, Py_ssize_t nargs)
{
    Py_ssize_t length; 
    if (nargs == 0) {
        length = DEF_BUF_SIZE;
    }
    else if (nargs == 1) {
        PyObject *length_arg = args[0];
        if (PyLong_Check(length_arg)) {
            length = PyLong_AsSsize_t(length_arg);
        }
        else {
            length = PyNumber_AsSsize_t(length_arg, PyExc_OverflowError);
        }
        if (length == -1 && PyErr_Occurred()) {
            return NULL;
        }
    }
    else {
        PyErr_Format(
            PyExc_TypeError,
            "flush() only takes 0 or 1 positional arguments got %d", 
            nargs
        );
        return NULL;
    }
    return isal_zlib_Decompress_flush_impl(self, length);
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

static PyTypeObject IsalZlibCompType = {
    .tp_name = "isal_zlib.Compress", 
    .tp_doc = "Object returned by isal_zlib.compressobj",
    .tp_basicsize = sizeof(compobject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_dealloc = (destructor)Comp_dealloc,
    .tp_methods = comp_methods,
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

static PyTypeObject IsalZlibDecompType = {
    .tp_name = "isal_zlib.Decompress",
    .tp_doc = "Object returned by isal_zlib.compressobj.",
    .tp_basicsize = sizeof(decompobject),
    .tp_flags = Py_TPFLAGS_DEFAULT,
    .tp_dealloc = (destructor)Decomp_dealloc,
    .tp_methods = Decomp_methods,
    .tp_members = Decomp_members,
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

static struct PyModuleDef isal_zlib_module = {
    PyModuleDef_HEAD_INIT,
    "isal_zlib",   /* name of module */
    isal_zlib_module_documentation, /* module documentation, may be NULL */
    0,
    IsalZlibMethods,
};

PyMODINIT_FUNC
PyInit_isal_zlib(void)
{
    PyObject *m;

    m = PyModule_Create(&isal_zlib_module);
    if (m == NULL)
        return NULL;

    PyObject *igzip_lib_module = PyImport_ImportModule("isal.igzip_lib");
    if (igzip_lib_module == NULL) {
        return NULL;
    }

    IsalError = PyObject_GetAttrString(igzip_lib_module, "error");
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

    PyTypeObject *Comptype = (PyTypeObject *)&IsalZlibCompType;
    if (PyType_Ready(Comptype) != 0) { 
        return NULL;
    }

    Py_INCREF(Comptype);
    if (PyModule_AddObject(m, "Compress",  (PyObject *)Comptype) < 0) {
        return NULL;
    }

    PyTypeObject *Decomptype = (PyTypeObject *)&IsalZlibDecompType;
    if (PyType_Ready(Decomptype) != 0) {
        return NULL;
    }

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

    return m;
}
