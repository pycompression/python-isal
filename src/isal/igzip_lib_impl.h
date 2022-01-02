#define PY_SSIZE_T_CLEAN
#include <Python.h>

#include <isa-l/igzip_lib.h>
#include <stdint.h>

/* Initial buffer size. */
#define DEF_BUF_SIZE (16*1024)
#define ISAL_BEST_SPEED ISAL_DEF_MIN_LEVEL
#define ISAL_BEST_COMPRESSION ISAL_DEF_MAX_LEVEL
#define ISAL_DEFAULT_COMPRESSION 2
#define COMP_DEFLATE IGZIP_DEFLATE
#define COMP_GZIP = IGZIP_GZIP
#define COMP_GZIP_NO_HDR IGZIP_GZIP_NO_HDR
#define COMP_ZLIB IGZIP_ZLIB
#define COMP_ZLIB_NO_HDR IGZIP_ZLIB_NO_HDR
#define DECOMP_DEFLATE ISAL_DEFLATE
#define DECOMP_GZIP ISAL_GZIP
#define DECOMP_GZIP_NO_HDR ISAL_GZIP_NO_HDR
#define DECOMP_ZLIB ISAL_ZLIB
#define DECOMP_ZLIB_NO_HDR ISAL_ZLIB_NO_HDR
#define DECOMP_ZLIB_NO_HDR_VER ISAL_ZLIB_NO_HDR_VER
#define DECOMP_GZIP_NO_HDR_VER ISAL_GZIP_NO_HDR_VER

static enum MemLevel {
    MEM_LEVEL_DEFAULT,
    MEM_LEVEL_MIN,
    MEM_LEVEL_SMALL,
    MEM_LEVEL_MEDIUM,
    MEM_LEVEL_LARGE,
    MEM_LEVEL_EXTRA_LARGE
};

static const uint32_t LEVEL_BUF_SIZES[24] = {
    ISAL_DEF_LVL0_DEFAULT,
    ISAL_DEF_LVL0_MIN,
    ISAL_DEF_LVL0_SMALL,
    ISAL_DEF_LVL0_MEDIUM,
    ISAL_DEF_LVL0_LARGE,
    ISAL_DEF_LVL0_EXTRA_LARGE,
    ISAL_DEF_LVL1_DEFAULT,
    ISAL_DEF_LVL1_MIN,
    ISAL_DEF_LVL1_SMALL,
    ISAL_DEF_LVL1_MEDIUM,
    ISAL_DEF_LVL1_LARGE,
    ISAL_DEF_LVL1_EXTRA_LARGE,
    ISAL_DEF_LVL2_DEFAULT,
    ISAL_DEF_LVL2_MIN,
    ISAL_DEF_LVL2_SMALL,
    ISAL_DEF_LVL2_MEDIUM,
    ISAL_DEF_LVL2_LARGE,
    ISAL_DEF_LVL2_EXTRA_LARGE,
    ISAL_DEF_LVL3_DEFAULT,
    ISAL_DEF_LVL3_MIN,
    ISAL_DEF_LVL3_SMALL,
    ISAL_DEF_LVL3_MEDIUM,
    ISAL_DEF_LVL3_LARGE,
    ISAL_DEF_LVL3_EXTRA_LARGE
};

static int mem_level_to_bufsize(int compression_level, int mem_level,
                                uint32_t * bufsize)
{
    if (compression_level < 0 || compression_level > 3 || mem_level < MEM_LEVEL_DEFAULT || mem_level > MEM_LEVEL_EXTRA_LARGE) {
        *bufsize = 0; return -1;
    }
    *bufsize = LEVEL_BUF_SIZES[compression_level * 6 + mem_level];
    return 0;
}

static void isal_deflate_error(int err, PyObject *ErrorClass)
{
    const char * msg = NULL;
    if (err == COMP_OK) return;
    else if (err == INVALID_FLUSH) msg = "Invalid flush type";
    else if (err == INVALID_PARAM) msg = "Invalid parameter";
    else if (err == STATELESS_OVERFLOW) msg = "Not enough room in output buffer";
    else if (err == ISAL_INVALID_OPERATION) msg = "Invalid operation";
    else if (err == ISAL_INVALID_STATE) msg = "Invalid state";
    else if (err == ISAL_INVALID_LEVEL) msg = "Invalid compression level.";
    else if (err == ISAL_INVALID_LEVEL_BUF) msg = "Level buffer too small.";
    else msg = "Unknown Error";

    PyErr_Format(ErrorClass, "Error %d %s", err, msg);
}

static void isal_inflate_error(int err, PyObject *ErrorClass){
    const char * msg = NULL;
    if (err == ISAL_DECOMP_OK) return;
    else if (err == ISAL_END_INPUT) msg = "End of input reached";
    else if (err == ISAL_OUT_OVERFLOW) msg = "End of output reached";
    else if (err == ISAL_NAME_OVERFLOW) msg = "End of gzip name buffer reached";
    else if (err == ISAL_COMMENT_OVERFLOW) msg = "End of gzip comment buffer reached";
    else if (err == ISAL_EXTRA_OVERFLOW) msg = "End of extra buffer reached";
    else if (err == ISAL_NEED_DICT) msg = "Dictionary needed to continue";
    else if (err == ISAL_INVALID_BLOCK) msg = "Invalid deflate block found";
    else if (err == ISAL_INVALID_SYMBOL) msg = "Invalid deflate symbol found";
    else if (err == ISAL_INVALID_LOOKBACK) msg = "Invalid lookback distance found";
    else if (err == ISAL_INVALID_WRAPPER) msg = "Invalid gzip/zlib wrapper found";
    else if (err == ISAL_UNSUPPORTED_METHOD) msg = "Gzip/zlib wrapper specifies unsupported compress method";
    else if (err == ISAL_INCORRECT_CHECKSUM) msg = "Incorrect checksum found";
    else msg = "Unknown error";

    PyErr_Format(ErrorClass, "Error %d %s", err, msg);
}

static void
arrange_input_buffer(uint32_t *avail_in, Py_ssize_t *remains)
{
    *avail_in = (uint32_t)Py_MIN((size_t)*remains, UINT32_MAX);
    *remains -= *avail_in;
}

static Py_ssize_t
arrange_output_buffer_with_maximum(uint32_t *avail_out,
                                   uint8_t **next_out,
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
                      uint8_t **next_out,
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
igzip_lib_compress_impl(PyObject *ErrorClass, Py_buffer *data,
                        int level,
                        int flag,
                        int mem_level,
                        int hist_bits)
{
    PyObject *RetVal = NULL;
    uint8_t *ibuf;
    uint8_t *level_buf = NULL;
    uint32_t level_buf_size;
    if (mem_level_to_bufsize(level, mem_level, &level_buf_size) != 0){
        PyErr_SetString(ErrorClass, "Invalid memory level or compression level");
        goto error;
    }
    level_buf = (uint8_t *)PyMem_Malloc(level_buf_size);
    if (level_buf == NULL){
        PyErr_NoMemory();
        goto error;
    }
    Py_ssize_t ibuflen, obuflen = DEF_BUF_SIZE;
    int err;
    struct isal_zstream zst;
    isal_deflate_init(&zst);
    zst.level = (uint32_t)level;
    zst.level_buf = level_buf;
    zst.level_buf_size = level_buf_size;
    zst.hist_bits = (uint16_t)hist_bits;
    zst.gzip_flag = (uint16_t)flag ;

    ibuf = (uint8_t *)data->buf;
    ibuflen = data->len;

    zst.next_in = ibuf;

    do {
        arrange_input_buffer(&(zst.avail_in), &ibuflen);
        if (ibuflen == 0){
            zst.flush = FULL_FLUSH;
            zst.end_of_stream = 1;
        }
        else zst.flush = NO_FLUSH;

        do {
            obuflen = arrange_output_buffer(&(zst.avail_out), &(zst.next_out), &RetVal, obuflen);
            if (obuflen < 0) {
                PyErr_SetString(PyExc_MemoryError,
                        "Unsufficient memory for buffer allocation");
                goto error;
            }
            err = isal_deflate(&zst);

            if (err != COMP_OK) {
                isal_deflate_error(err, ErrorClass);
                goto error;
            }

        } while (zst.avail_out == 0);
        assert(zst.avail_in == 0);

    } while (zst.end_of_stream != 1);
    assert(zst.internal_state.state == ZSTATE_END);
    if (_PyBytes_Resize(&RetVal, zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) < 0)
        goto error;
    PyMem_Free(level_buf);
    return RetVal;
 error:
    PyMem_Free(level_buf);
    Py_XDECREF(RetVal);
    return NULL;
}

static PyObject *
igzip_lib_decompress_impl(PyObject *ErrorClass, Py_buffer *data, int flag,
                          int hist_bits, Py_ssize_t bufsize)
{
    PyObject *RetVal = NULL;
    uint8_t *ibuf;
    Py_ssize_t ibuflen;
    int err;
    struct inflate_state zst;
    isal_inflate_init(&zst);

    if (bufsize < 0) {
        PyErr_SetString(PyExc_ValueError, "bufsize must be non-negative");
        return NULL;
    } else if (bufsize == 0) {
        bufsize = 1;
    }

    ibuf = (uint8_t *)data->buf;
    ibuflen = data->len;

    zst.hist_bits = (uint32_t)hist_bits;
    zst.crc_flag = (uint32_t)flag;
    zst.avail_in = 0;
    zst.next_in = ibuf;

    do {
        arrange_input_buffer(&(zst.avail_in), &ibuflen);

        do {
            bufsize = arrange_output_buffer(&(zst.avail_out), &(zst.next_out),
                                            &RetVal, bufsize);
            if (bufsize < 0) {
                goto error;
            }

            err = isal_inflate(&zst);
            if (err != ISAL_DECOMP_OK) {
                isal_inflate_error(err, ErrorClass);
                goto error;
            }
        } while (zst.avail_out == 0);

    } while (zst.block_state != ISAL_BLOCK_FINISH && ibuflen != 0);

    if (zst.block_state != ISAL_BLOCK_FINISH) {
         PyErr_SetString(ErrorClass,
                         "incomplete or truncated stream");
        goto error;
    }

    if (_PyBytes_Resize(&RetVal, zst.next_out -
                        (uint8_t *)PyBytes_AS_STRING(RetVal)) < 0)
        goto error;

    return RetVal;

 error:
    Py_XDECREF(RetVal);
    return NULL;
}
