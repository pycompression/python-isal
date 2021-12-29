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
