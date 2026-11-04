/*
Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
Python Software Foundation; All Rights Reserved

This file is part of python-isal which is distributed under the
PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

This file is not originally from the CPython distribution. But it does
contain mostly example code from the Python docs. Also dual licensing just
for this one file seemed silly.
*/

#define PY_SSIZE_T_CLEAN
#include <Python.h>
#include <stdbool.h>

#define FEXTRA 4

static inline uint16_t load_u16_le(const void *address) {
    #if PY_BIG_ENDIAN
    uint8_t *mem = address;
    return mem[0] | (mem[1] << 8);
    #else
    return *(uint16_t *)address;
    #endif
}

static PyObject *find_last_bgzip_end(PyObject *module, PyObject *buffer_obj) {
    Py_buffer buf; 
    int ret = PyObject_GetBuffer(buffer_obj, &buf, PyBUF_SIMPLE);
    if (ret == -1) {
        return NULL;
    }
    const uint8_t *data = buf.buf;
    Py_ssize_t data_length = buf.len;
    const uint8_t *data_end = data + data_length;
    const uint8_t *cursor = data;

    while (true) {
        if (cursor + 18 > data_end) {
            break;
        }
        uint8_t magic1 = cursor[0];
        uint8_t magic2 = cursor[1];
        uint8_t method = cursor[2];
        uint8_t flags = cursor[3];
        uint16_t xlen = load_u16_le(cursor + 10);
        uint8_t si1 = cursor[12];
        uint8_t si2 = cursor[13];
        uint16_t subfield_length = load_u16_le(cursor + 14);        
        if (
            magic1 != 31 || 
            magic2 != 139 ||
            method != 8 ||
            flags != FEXTRA ||
            xlen != 6 ||
            si1 != 66 ||
            si2 != 67 ||
            subfield_length != 2
        ) {
            PyErr_Format(
                PyExc_ValueError, 
                "Incorrect bgzip header:\n"
                "magic: %x, %x\n" 
                "method: %x\n"  
                "flags: %x\n"
                "xlen: %d\n"
                "si1, si2: %d, %d \n"
                "subfield_length: %d",
                magic1, magic2, method, flags, xlen, si1, si2, subfield_length
            );
            return NULL;
        }
        uint16_t block_size = load_u16_le(cursor + 16);
        const uint8_t *new_start = cursor + block_size + 1;
        if (new_start > data_end) {
            break;
        }
        cursor = new_start;
    }
    return PyLong_FromSsize_t(cursor - data);
}

static PyMethodDef _bgzip_methods[] = {
    {"find_last_bgzip_end", find_last_bgzip_end, METH_O, NULL},
    {NULL},
};

static struct PyModuleDef _bgzip_module = {
    PyModuleDef_HEAD_INIT,
    .m_name = "_bgzip",
    .m_doc = NULL,
    .m_size = -1,
    .m_methods = _bgzip_methods,
};

PyMODINIT_FUNC
PyInit__bgzip(void)
{
    PyObject *m = PyModule_Create(&_bgzip_module);
    if (m == NULL) {
        return NULL;
    }
    return m;
}
