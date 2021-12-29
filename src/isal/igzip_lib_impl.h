#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <isa-l/igzip_lib.h>
#include <stdint.h>

/* Initial buffer size. */
#define DEF_BUF_SIZE (16*1024)

enum MemLevel {
    MEM_DEFAULT
    MEM_MIN
    MEM_SMALL
    MEM_MEDIUM
    MEM_LARGE
    MEM_EXTRA_LARGE
}

static int mem_level_to_bufsize(int compression_level, int mem_level,
                                uint32_t * bufsize)
{
    if (compression_level == 0){
        switch(mem_level){
            case MEM_DEFAULT: *bufsize = ISAL_DEF_LVL0_DEFAULT;
            case MEM_MIN: *bufsize = ISAL_DEF_LVL0_MIN;
            case MEM_SMALL: *bufsize = ISAL_DEF_LVL0_SMALL;
            case MEM_MEDIUM: *bufsize = ISAL_DEF_LVL0_MEDIUM;
            case MEM_LARGE: *bufsize = ISAL_DEF_LVL0_LARGE;
            case MEM_EXTRA_LARGE: *bufsize = ISAL_DEF_LVL0_EXTRA_LARGE;
            default: *bufsize = 0; return -1;
        }
    }
    else if (compression_level == 1){
        switch(mem_level){
            case MEM_DEFAULT: *bufsize = ISAL_DEF_LVL1_DEFAULT;
            case MEM_MIN: *bufsize = ISAL_DEF_LVL1_MIN;
            case MEM_SMALL: *bufsize = ISAL_DEF_LVL1_SMALL;
            case MEM_MEDIUM: *bufsize = ISAL_DEF_LVL1_MEDIUM;
            case MEM_LARGE: *bufsize = ISAL_DEF_LVL1_LARGE;
            case MEM_EXTRA_LARGE: *bufsize = ISAL_DEF_LVL1_EXTRA_LARGE;
            default: *bufsize = 0; return -1;
        }
    }
    else if (compression_level == 2){
        switch(mem_level){
            case MEM_DEFAULT: *bufsize = ISAL_DEF_LVL2_DEFAULT;
            case MEM_MIN: *bufsize = ISAL_DEF_LVL2_MIN;
            case MEM_SMALL: *bufsize = ISAL_DEF_LVL2_SMALL;
            case MEM_MEDIUM: *bufsize = ISAL_DEF_LVL2_MEDIUM;
            case MEM_LARGE: *bufsize = ISAL_DEF_LVL2_LARGE;
            case MEM_EXTRA_LARGE: *bufsize = ISAL_DEF_LVL2_EXTRA_LARGE;
            default: *bufsize = 0; return -1;
        }
    }
    else if (compression_level == 3){
        switch(mem_level){
            case MEM_DEFAULT: *bufsize = ISAL_DEF_LVL3_DEFAULT;
            case MEM_MIN: *bufsize = ISAL_DEF_LVL3_MIN;
            case MEM_SMALL: *bufsize = ISAL_DEF_LVL3_SMALL;
            case MEM_MEDIUM: *bufsize = ISAL_DEF_LVL3_MEDIUM;
            case MEM_LARGE: *bufsize = ISAL_DEF_LVL3_LARGE;
            case MEM_EXTRA_LARGE: *bufsize = ISAL_DEF_LVL3_EXTRA_LARGE;
            default: *bufsize = 0; return -1;
        }
    }
    else {
        *bufsize = 0; return -1;
    }
    return 0
}

static void
arrange_input_buffer(uint32_t *avail_in, Py_ssize_t *remains)
{
    *avail_in = (uint32_t)Py_MIN((size_t)*remains, UINT32_MAX);
    *remains -= *avail_in;
}

static Py_ssize_t
arrange_output_buffer_with_maximum(uint32_t *avail_out,
                                   uint8_t *next_out,
                                   PyObject **buffer,
                                   Py_ssize_t length,
                                   Py_ssize_t max_length)
{
    Py_ssize_t occupied;

    if (*buffer == NULL) {
        if (!(*buffer = PyBytes_FromStringAndSize(NULL, length)))
            return -1;
        occupied = 0;
    }
    else {
        occupied = *next_out - (uint8_t *)PyBytes_AS_STRING(*buffer);

        if (length == occupied) {
            Py_ssize_t new_length;
            assert(length <= max_length);
            /* can not scale the buffer over max_length */
            if (length == max_length)
                return -2;
            if (length <= (max_length >> 1))
                new_length = length << 1;
            else
                new_length = max_length;
            if (_PyBytes_Resize(buffer, new_length) < 0)
                return -1;
            length = new_length;
        }
    }

    *avail_out = (uint32_t)Py_MIN((size_t)(length - occupied), UINT32_MAX);
    *next_out = (uint8_t *)PyBytes_AS_STRING(*buffer) + occupied;

    return length;
}

static Py_ssize_t
arrange_output_buffer(uint32_t *avail_out,
                      uint8_t *next_out,
                      PyObject **buffer,
                      Py_ssize_t length)
{
    Py_ssize_t ret;

    ret = arrange_output_buffer_with_maximum(avail_out, next_out, buffer,
                                             length,
                                             PY_SSIZE_T_MAX);
    if (ret == -2)
        PyErr_NoMemory();
    return ret;
}

static PyObject *
igzip_lib_compress_impl(PyObject *module, Py_buffer *data, int level,
                        uint16_t flag,
                        int mem_level
                        uint16_t hist_bits)
{
    PyObject *RetVal = NULL;
    uint8_t *ibuf;
    uint8_t *level_buf
    uint32_t level_buf_size
    Py_ssize_t ibuflen, obuflen = DEF_BUF_SIZE;
    int err, flush;
    isal_zstream zst;
    zst.level = level
    zst.level_buf = level_buf
    zst.level_buf_size = level_buf_size

    ibuf = data->buf;
    ibuflen = data->len;

    zst.opaque = NULL;
    zst.zalloc = PyZlib_Malloc;
    zst.zfree = PyZlib_Free;
    zst.next_in = ibuf;
    err = deflateInit(&zst, level);

    switch (err) {
    case Z_OK:
        break;
    case Z_MEM_ERROR:
        PyErr_SetString(PyExc_MemoryError,
                        "Out of memory while compressing data");
        goto error;
    case Z_STREAM_ERROR:
        PyErr_SetString(_zlibstate_global->ZlibError, "Bad compression level");
        goto error;
    default:
        deflateEnd(&zst);
        zlib_error(zst, err, "while compressing data");
        goto error;
    }

    do {
        arrange_input_buffer(&zst, &ibuflen);
        flush = ibuflen == 0 ? Z_FINISH : Z_NO_FLUSH;

        do {
            obuflen = arrange_output_buffer(&zst, &RetVal, obuflen);
            if (obuflen < 0) {
                deflateEnd(&zst);
                goto error;
            }

            Py_BEGIN_ALLOW_THREADS
            err = deflate(&zst, flush);
            Py_END_ALLOW_THREADS

            if (err == Z_STREAM_ERROR) {
                deflateEnd(&zst);
                zlib_error(zst, err, "while compressing data");
                goto error;
            }

        } while (zst.avail_out == 0);
        assert(zst.avail_in == 0);

    } while (flush != Z_FINISH);
    assert(err == Z_STREAM_END);

    err = deflateEnd(&zst);
    if (err == Z_OK) {
        if (_PyBytes_Resize(&RetVal, zst.next_out -
                            (Byte *)PyBytes_AS_STRING(RetVal)) < 0)
            goto error;
        return RetVal;
    }
    else
        zlib_error(zst, err, "while finishing compression");
 error:
    Py_XDECREF(RetVal);
    return NULL;
}

static PyObject *
zlib_decompress_impl(PyObject *module, Py_buffer *data, int wbits,
                     Py_ssize_t bufsize)
/*[clinic end generated code: output=77c7e35111dc8c42 input=21960936208e9a5b]*/
{
    PyObject *RetVal = NULL;
    Byte *ibuf;
    Py_ssize_t ibuflen;
    int err, flush;
    z_stream zst;

    if (bufsize < 0) {
        PyErr_SetString(PyExc_ValueError, "bufsize must be non-negative");
        return NULL;
    } else if (bufsize == 0) {
        bufsize = 1;
    }

    ibuf = data->buf;
    ibuflen = data->len;

    zst.opaque = NULL;
    zst.zalloc = PyZlib_Malloc;
    zst.zfree = PyZlib_Free;
    zst.avail_in = 0;
    zst.next_in = ibuf;
    err = inflateInit2(&zst, wbits);

    switch (err) {
    case Z_OK:
        break;
    case Z_MEM_ERROR:
        PyErr_SetString(PyExc_MemoryError,
                        "Out of memory while decompressing data");
        goto error;
    default:
        inflateEnd(&zst);
        zlib_error(zst, err, "while preparing to decompress data");
        goto error;
    }

    do {
        arrange_input_buffer(&zst, &ibuflen);
        flush = ibuflen == 0 ? Z_FINISH : Z_NO_FLUSH;

        do {
            bufsize = arrange_output_buffer(&zst, &RetVal, bufsize);
            if (bufsize < 0) {
                inflateEnd(&zst);
                goto error;
            }

            Py_BEGIN_ALLOW_THREADS
            err = inflate(&zst, flush);
            Py_END_ALLOW_THREADS

            switch (err) {
            case Z_OK:            /* fall through */
            case Z_BUF_ERROR:     /* fall through */
            case Z_STREAM_END:
                break;
            case Z_MEM_ERROR:
                inflateEnd(&zst);
                PyErr_SetString(PyExc_MemoryError,
                                "Out of memory while decompressing data");
                goto error;
            default:
                inflateEnd(&zst);
                zlib_error(zst, err, "while decompressing data");
                goto error;
            }

        } while (zst.avail_out == 0);

    } while (err != Z_STREAM_END && ibuflen != 0);


    if (err != Z_STREAM_END) {
        inflateEnd(&zst);
        zlib_error(zst, err, "while decompressing data");
        goto error;
    }

    err = inflateEnd(&zst);
    if (err != Z_OK) {
        zlib_error(zst, err, "while finishing decompression");
        goto error;
    }

    if (_PyBytes_Resize(&RetVal, zst.next_out -
                        (Byte *)PyBytes_AS_STRING(RetVal)) < 0)
        goto error;

    return RetVal;

 error:
    Py_XDECREF(RetVal);
    return NULL;
}