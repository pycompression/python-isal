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
from cpython.ref cimport PyObject
cdef extern from "pycore_blocks_output_buffer.h":
    cdef struct _BlocksOutputBuffer
    cdef Py_ssize_t _BlocksOutputBuffer_InitAndGrow(_BlocksOutputBuffer *buffer,
                                    const Py_ssize_t max_length,
                                    void **next_out)
    cdef Py_ssize_t _BlocksOutputBuffer_InitWithSize(_BlocksOutputBuffer *buffer,
                                 const Py_ssize_t init_size,
                                 void **next_out)
    cdef Py_ssize_t _BlocksOutputBuffer_Grow(_BlocksOutputBuffer *buffer,
                         void **next_out,
                         const Py_ssize_t avail_out)
    cdef Py_ssize_t _BlocksOutputBuffer_GetDataSize(_BlocksOutputBuffer *buffer,
                                const Py_ssize_t avail_out)
    cdef PyObject * _BlocksOutputBuffer_Finish(_BlocksOutputBuffer *buffer,
                           const Py_ssize_t avail_out)
    cdef void _BlocksOutputBuffer_OnError(_BlocksOutputBuffer *buffer)
