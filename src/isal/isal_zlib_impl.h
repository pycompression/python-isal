#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include "igzip_lib_impl.h"

#include <isa-l/crc.h>

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
wbits_to_flag_and_hist_bits_deflate(PyObject * ErrorClass, 
                                    int wbits, int *hist_bits, int *flag) 
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
        PyErr_Format(ErrorClass, "Invalid wbits value: %d", wbits);
        return -1;
    }
    return 0;
}

static int 
wbits_to_flag_and_hist_bits_inflate(PyObject * ErrorClass, 
                                    int wbits, int *hist_bits, int *flag) 
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
        PyErr_Format(ErrorClass, "Invalid wbits value: %d", wbits);
        return -1;
    }
    return 0;
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
    if (wbits_to_flag_and_hist_bits_deflate(ErrorClass, wbits, &hist_bits, &flag) != 0)
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
    int convert_result = wbits_to_flag_and_hist_bits_inflate(ErrorClass, wbits, 
                                                             &hist_bits, &flag);
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
