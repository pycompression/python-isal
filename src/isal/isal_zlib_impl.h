#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "igzip_lib_impl.h"

#include <isa-l/crc.h>

// Below values are copied from zlib.h
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

typedef struct {
    PyTypeObject *Comptype;
    PyTypeObject *Decomptype;
    PyObject *IsalError;
} _isal_zlibstate;

static inline _isal_zlibstate*
get_isal_zlib_state(PyObject *module)
{
    void *state = PyModule_GetState(module);
    assert(state != NULL);
    return (_isal_zlibstate *)state;
}

static PyModuleDef isal_zlib_module;
#define _isal_zlibstate_global ((_isal_zlibstate *)PyModule_GetState(PyState_FindModule(&isal_zlib_module)))


static PyObject *
isal_zlib_adler32_impl(PyObject *module, Py_buffer *data, uint32_t value)
{
    value = isal_adler32(value, data->buf, (uint64_t)data->len);
    return PyLong_FromUnsignedLong(value & 0xffffffffU);
}

static PyObject *
isal_zlib_crc32_impl(PyObject *module, Py_buffer *data, uint32_t value)
{
    value = crc32_gzip_refl(value, data->buf, (uint64_t)data->len);
    return PyLong_FromUnsignedLong(value & 0xffffffffU);
}


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
        PyErr_Format(_isal_zlibstate_global->IsalError, "Invalid wbits value: %d", wbits);
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
        PyErr_Format(_isal_zlibstate_global->IsalError, "Invalid wbits value: %d", wbits);
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
    if (buf[0] == 31 && buf[1] == 139)
        return 1;
    return 0;
}

static PyObject *
isal_zlib_compress_impl(PyObject *ErrorClass, Py_buffer *data, int level, int wbits)
{
    int hist_bits = -1;
    int flag = -1;
    if (wbits_to_flag_and_hist_bits_deflate(wbits, &hist_bits, &flag) != 0)
        return NULL;
    return igzip_lib_compress_impl(ErrorClass, data, level, 
                                   flag, MEM_LEVEL_DEFAULT, hist_bits);
}

static PyObject *
isal_zlib_decompress_impl(PyObject *ErrorClass, Py_buffer *data, int wbits,
                          Py_ssize_t bufsize)
{
    int hist_bits;
    int flag; 
    int convert_result = wbits_to_flag_and_hist_bits_inflate(wbits, &hist_bits, &flag);
    if (convert_result < 0)
        return NULL;
    if (convert_result > 0) {
        if (data_is_gzip(data)) 
            flag = ISAL_GZIP;
        else 
            flag = ISAL_ZLIB;
    }
    return igzip_lib_decompress_impl(ErrorClass, data, flag, hist_bits, bufsize);
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
    PyObject *type = (PyObject *)Py_TYPE(self);
    Py_XDECREF(self->zdict);
    PyObject_Del(self);
    Py_DECREF(type);
}

static compobject *
newcompobject(PyTypeObject *type)
{
    compobject *self;
    self = PyObject_New(compobject, type);
    if (self == NULL)
        return NULL;
    self->is_initialised = 0;
    self->zdict = NULL;
    self->level_buf = NULL;
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

    self = newcompobject(_isal_zlibstate_global->Comptype);
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
    PyObject *type = (PyObject *)Py_TYPE(self);
    Py_XDECREF(self->unused_data);
    Py_XDECREF(self->unconsumed_tail);
    Py_XDECREF(self->zdict);
    PyObject_Del(self);
    Py_DECREF(type);
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
        isal_inflate_error(err, _isal_zlibstate_global->IsalError);
        return -1;
    }
    return 0;
}

static decompobject *
newdecompobject(PyTypeObject *type)
{
    decompobject *self;
    self = PyObject_New(decompobject, type);
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
    self = newdecompobject(_isal_zlibstate_global->Decomptype);
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
    //Apparently zlibmodule.c only adds dicts for raw deflate streams.
    if (self->zdict != NULL && flag == ISAL_DEFLATE) {  
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
                isal_deflate_error(err, _isal_zlibstate_global->IsalError);
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
                isal_inflate_error(err, _isal_zlibstate_global->IsalError);
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
        PyErr_Format(_isal_zlibstate_global->IsalError, 
                     "Unsupported flush mode: %d", mode);
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
            isal_deflate_error(err, _isal_zlibstate_global->IsalError);
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
                isal_inflate_error(err, _isal_zlibstate_global->IsalError);
                goto abort;
            }

        } while (self->zst.avail_out == 0 && self->zst.block_state != ISAL_BLOCK_FINISH);

    } while (self->zst.block_state != ISAL_BLOCK_FINISH && ibuflen != 0);

 save:
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
