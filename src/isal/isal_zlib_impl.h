#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "igzip_lib_impl.h"

#include <isa-l/crc.h>

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

static PyModuleDef isal_zlibmodule;
#define _isal_zlibstate_global ((_isal_zlibstate *)PyModule_GetState(PyState_FindModule(&isal_zlibmodule)))


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
    if (wbits >= 8 && wbits <= 15){
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
    if (mem_level < 1 || mem_level > 9) 
        PyErr_Format(PyExc_ValueError, 
        "Invalid mem level: %d. Mem level should be between 1 and 9");
        return -1;
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
    int hist_bits;
    int flag;
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
    PyObject *unused_data;
    PyObject *unconsumed_tail;
    char eof;
    int is_initialised;
    PyObject *zdict;
    PyThread_type_lock lock;
} compobject;

static compobject *
newcompobject(PyTypeObject *type)
{
    compobject *self;
    self = PyObject_New(compobject, type);
    if (self == NULL)
        return NULL;
    self->eof = 0;
    self->is_initialised = 0;
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
    self->lock = PyThread_allocate_lock();
    if (self->lock == NULL) {
        Py_DECREF(self);
        PyErr_SetString(PyExc_MemoryError, "Unable to allocate lock");
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
    uint8_t * level_buf = NULL;
    int flag;
    int hist_bits;

    if (zdict->buf != NULL && (size_t)zdict->len > UINT32_MAX) {
        PyErr_SetString(PyExc_OverflowError,
                        "zdict length does not fit in an unsigned 32-bit int");
        goto error;
    }
    int isal_mem_level = zlib_mem_level_to_isal(memLevel);
    if (isal_mem_level == -1)
        goto error;
    if (wbits_to_flag_and_hist_bits_deflate(wbits, &hist_bits, &flag) == -1)
        goto error;
    if (mem_level_to_bufsize(
        level, isal_mem_level, &level_buf_size) == -1) {
        PyErr_Format(PyExc_ValueError, "Invalid compression level: %d. Compression level should be between 0 and 3", level)
        goto error;
    }   

    self = newcompobject(_isal_zlibstate_global->Comptype);
    if (self == NULL)
        goto error;
    level_buf = (uint8_t *)PyMem_Malloc(level_buf_size);
    if (level_buf == NULL){
        PyErr_NoMemory;
        goto error;
    }
    isal_deflate_init(&(self->zst));
    self->zst.next_in = NULL;
    self->zst.avail_in = 0;
    self->zst.level_buf_size = level_buf_size;
    self->zst.level_buf = level_buf;
    self->zst.level = level;
    self->zst.hist_bits = (uint16_t)hist_bits;
    self->zst.gzip_flag = (uint16_t)flag;

    self->is_initialised = 1;
    if (zdict->buf == NULL) {
        goto success;
    } else {
        err = isal_deflate_set_dict(&(self->zst),
                                    zdict->buf, (uint32_t)zdict->len);
        if (err = COMP_OK)
            goto success;
        PyErr_SetString(PyExc_ValueError, "Invalid dictionary");
        goto error;
        }
 error:
    Py_CLEAR(self);
    PyMem_Free(level_buf);
 success:
    return (PyObject *)self;
}
