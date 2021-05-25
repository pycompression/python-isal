# Copyright (c) 2020 Leiden University Medical Center
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

# cython: language_level=3
cdef extern from "<Python.h>":
    cdef struct PyObject
#     const Py_ssize_t PY_SSIZE_T_MAX
    cdef char* PyBytes_AS_STRING(PyObject * string)
    cdef PyObject * PyBytes_FromStringAndSize(char *v, Py_ssize_t len)
    cdef void PyList_SET_ITEM(PyObject * op, Py_ssize_t i, PyObject * v)
    cdef void Py_DECREF(PyObject * op)
#     cdef void PyErr_NoMemory()
#     cdef int _PyBytes_Resize(PyObject **bytes, Py_ssize_t newsize)
    cdef PyObject * PyList_New(Py_ssize_t size)

cdef struct _BlocksOutputBuffer:
    PyObject * list
    Py_ssize_t allocated
    Py_ssize_t max_length

unable_allocate_msg = "Unable to allocate output buffer."
DEF OUTPUT_BUFFER_MAX_BLOCK_SIZE = (256 * 1024 * 1024)
DEF KB = 1024
DEF MB = 1024 * 1024
cdef const Py_ssize_t[:] BUFFER_BLOCK_SIZE = {32*KB, 64*KB, 256*KB, 1*MB, 4*MB,
                                             8*MB, 16*MB, 16*MB, 32*MB, 32*MB,
                                             32*MB, 32*MB, 64*MB, 64*MB,
                                             128*MB, 128*MB,
                                             OUTPUT_BUFFER_MAX_BLOCK_SIZE}
cdef inline Py_ssize_t _BlocksOutputBuffer_InitAndGrow(
    _BlocksOutputBuffer *buffer,
    const Py_ssize_t max_length,
    void **next_out):
    cdef PyObject * b
    cdef Py_ssize_t block_size

    assert buffer.list == NULL
    if 0 <= max_length and max_length < BUFFER_BLOCK_SIZE[0]:
        block_size = max_length
    else:
        block_size = BUFFER_BLOCK_SIZE[0]

    b = PyBytes_FromStringAndSize(NULL, block_size)
    if b == NULL:
        return -1
    if b == NULL:
        return -1
    buffer.list = PyList_New(1)
    if buffer.list == NULL:
        Py_DECREF(b)
        return -1
    PyList_SET_ITEM(buffer.list, 0, b)
    buffer.allocated = block_size
    buffer.max_length = max_length
    next_out[0] = PyBytes_AS_STRING(b)
    return block_size

cdef inline Py_ssize_t _BlocksOutputBuffer_InitWithSize(
    _BlocksOutputBuffer *buffer,
    const Py_ssize_t init_size,
                            void **next_out):

    cdef PyObject *b

    assert buffer.list  == NULL
    b = PyBytes_FromStringAndSize(NULL, init_size)
    if b == NULL:
        raise MemoryError(unable_allocate_msg)
    buffer.list = PyList_New(1)
    if buffer.list == NULL:
        Py_DECREF(b)
        return -1
    PyList_SET_ITEM(buffer.list, 0, b)
    buffer.allocated = init_size
    buffer.max_length = -1
    next_out[0] = PyBytes_AS_STRING(b)
    return init_size

cdef inline Py_ssize_t _BlocksOutputBuffer_Grow(_BlocksOutputBuffer *buffer,
                     void **next_out,
                     const Py_ssize_t avail_out):



# cdef inline Py_ssize_t _BlocksOutputBuffer_GetDataSize(_BlocksOutputBuffer *buffer,
#                             const Py_ssize_t avail_out)
# cdef inline PyObject * _BlocksOutputBuffer_Finish(_BlocksOutputBuffer *buffer,
#                            const Py_ssize_t avail_out)
# cdef inline void _BlocksOutputBuffer_OnError(_BlocksOutputBuffer *buffer)