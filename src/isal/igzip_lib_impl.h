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
#define COMP_GZIP IGZIP_GZIP
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

typedef struct {
    PyTypeObject *Decomptype;
    PyObject *IsalError;
} _igzip_lib_state;

static inline _igzip_lib_state*
get_igzip_lib_state(PyObject *module)
{
    void *state = PyModule_GetState(module);
    assert(state != NULL);
    return (_igzip_lib_state*)state;
}
static PyModuleDef igzip_lib_module;
#define _igzip_lib_state_global ((_igzip_lib_state *)PyModule_GetState(PyState_FindModule(&igzip_lib_module)))


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

/**
 * @brief Returns the length in number of bytes of the bitbuffer read_in of an
 *        inflate state.
 * 
 * @param state An inflate_state
 * @return size_t 
 */
static size_t bitbuffer_size(struct inflate_state *state){
    return state->read_in_length / 8;
}

/**
 * @brief Copy n bytes in state->read_in to to. 
 * 
 * @param state ISA-L inflate_state
 * @param to the destination pointer
 * @param n the number of bytes to copy. Must be 8 or lower.
 * @return int Returns -1 if n > 8, 0 otherwise.
 */
static int bitbuffer_copy(struct inflate_state *state, char *to, size_t n){
    if (n > 8){
        // Size should not be greater than 8 as there are 8 bytes in a uint64_t
        PyErr_BadInternalCall();
        return -1;
    }
    int bits_in_buffer = state->read_in_length;
    int remainder = bits_in_buffer % 8;
    // Shift the 8-byte bitbuffer read_in so that the bytes are aligned.
    uint64_t remaining_bytes = state->read_in >> remainder;
    char * remaining_bytes_ptr = (char *)(&remaining_bytes);
    memcpy(to, remaining_bytes_ptr, n);
    return 0;
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

typedef struct {
    PyObject_HEAD
    struct inflate_state state;
    char eof;           /* T_BOOL expects a char */
    PyObject *unused_data;
    PyObject *zdict;
    char needs_input;
    uint8_t *input_buffer;
    Py_ssize_t input_buffer_size;

    /* inflate_state>avail_in is only 32 bit, so we store the true length
       separately. Conversion and looping is encapsulated in
       decompress_buf() */
    Py_ssize_t avail_in_real;
} IgzipDecompressor;

static void
IgzipDecompressor_dealloc(IgzipDecompressor *self)
{
    if(self->input_buffer != NULL)
        PyMem_Free(self->input_buffer);
    Py_CLEAR(self->unused_data);
    Py_CLEAR(self->zdict);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static int
igzip_lib_IgzipDecompressor___init___impl(IgzipDecompressor *self,
                                           int flag,
                                           int hist_bits,
                                           PyObject *zdict)
{
    int err;
    self->needs_input = 1;
    self->avail_in_real = 0;
    self->input_buffer = NULL;
    self->input_buffer_size = 0;
    self->zdict = zdict;
    Py_XSETREF(self->unused_data, PyBytes_FromStringAndSize(NULL, 0));
    if (self->unused_data == NULL)
        goto error;
    isal_inflate_init(&(self->state));
    self->state.hist_bits = hist_bits;
    self->state.crc_flag = flag;
    if (self->zdict != NULL){
        Py_buffer zdict_buf;
        if (PyObject_GetBuffer(self->zdict, &zdict_buf, PyBUF_SIMPLE) == -1) {
            goto error;
        }
        if ((size_t)zdict_buf.len > UINT32_MAX) {
            PyErr_SetString(PyExc_OverflowError,
                           "zdict length does not fit in an unsigned 32-bits int");
            PyBuffer_Release(&zdict_buf);
        }
        err = isal_inflate_set_dict(&(self->state), zdict_buf.buf, 
                                    (uint32_t)zdict_buf.len);
        PyBuffer_Release(&zdict_buf);
        if (err != ISAL_DECOMP_OK) {
            isal_inflate_error(err, _igzip_lib_state_global->IsalError);
            goto error;
        }        
    }
    return 0;

error:
    Py_CLEAR(self->unused_data);
    Py_CLEAR(self->zdict);
    return -1;
}

/* Decompress data of length d->bzs_avail_in_real in d->state.next_in.  The output
   buffer is allocated dynamically and returned.  At most max_length bytes are
   returned, so some of the input may not be consumed. d->state.next_in and
   d->bzs_avail_in_real are updated to reflect the consumed input. */
static PyObject*
decompress_buf(IgzipDecompressor *self, Py_ssize_t max_length)
{
    /* data_size is strictly positive, but because we repeatedly have to
       compare against max_length and PyBytes_GET_SIZE we declare it as
       signed */
    PyObject * RetVal = NULL;
    Py_ssize_t obuflen = DEF_BUF_SIZE;

    if (obuflen > max_length)
        obuflen = max_length;


    do {
        int err;

        obuflen = arrange_output_buffer_with_maximum(&(self->state.avail_out), 
                                                     &(self->state.next_out),
                                                     &RetVal,
                                                     obuflen,
                                                     max_length);
        if (obuflen == -1){
            PyErr_SetString(PyExc_MemoryError, 
                            "Unsufficient memory for buffer allocation");
            goto error;
        }
        else if (obuflen == -2)
            break;
        arrange_input_buffer(&(self->state.avail_in), &(self->avail_in_real));
        err = isal_inflate(&(self->state));
        if (err != ISAL_DECOMP_OK){
            isal_inflate_error(err, _igzip_lib_state_global->IsalError);
            goto error;
        }
        self->avail_in_real += self->state.avail_in;
        if (self->state.block_state == ISAL_BLOCK_FINISH){
            self->eof = 1;
            break;
        }
    } while(self->avail_in_real != 0);

    return RetVal;

error:
    Py_XDECREF(RetVal);
    return NULL;
}


static PyObject *
decompress(IgzipDecompressor *self, uint8_t *data, size_t len, Py_ssize_t max_length)
{
    char input_buffer_in_use;
    PyObject *result;

    Py_ssize_t hard_limit;
    if (max_length < 0) {
        hard_limit = PY_SSIZE_T_MAX;
    } else {
        hard_limit = max_length;
    }
    /* Prepend unconsumed input if necessary */
    if (self->state.next_in != NULL) {
        size_t avail_now, avail_total;

        /* Number of bytes we can append to input buffer */
        avail_now = (self->input_buffer + self->input_buffer_size)
            - (self->state.next_in + self->avail_in_real);

        /* Number of bytes we can append if we move existing
           contents to beginning of buffer (overwriting
           consumed input) */
        avail_total = self->input_buffer_size - self->avail_in_real;

        if (avail_total < len) {
            size_t offset = self->state.next_in - self->input_buffer;
            uint8_t *tmp;
            size_t new_size = self->input_buffer_size + len - avail_now;

            /* Assign to temporary variable first, so we don't
               lose address of allocated buffer if realloc fails */
            tmp = PyMem_Realloc(self->input_buffer, new_size);
            if (tmp == NULL) {
                PyErr_SetNone(PyExc_MemoryError);
                return NULL;
            }
            self->input_buffer = tmp;
            self->input_buffer_size = new_size;

            self->state.next_in = self->input_buffer + offset;
        }
        else if (avail_now < len) {
            memmove(self->input_buffer, self->state.next_in,
                    self->avail_in_real);
            self->state.next_in = self->input_buffer;
        }
        memcpy((void*)(self->state.next_in + self->avail_in_real), data, len);
        self->avail_in_real += len;
        input_buffer_in_use = 1;
    }
    else {
        self->state.next_in = data;
        self->avail_in_real = len;
        input_buffer_in_use = 0;
    }

    result = decompress_buf(self, hard_limit);
    if(result == NULL) {
        self->state.next_in = NULL;
        return NULL;
    }

    if (self->eof) {
        self->needs_input = 0;
        if (self->avail_in_real > 0) {
            Py_ssize_t bytes_in_bitbuffer = bitbuffer_size(&(self->state));
            PyObject * new_data = PyBytes_FromStringAndSize(
                NULL, self->avail_in_real + bytes_in_bitbuffer);
            if (new_data == NULL)
                goto error;
            char * new_data_ptr = PyBytes_AS_STRING(new_data);
            bitbuffer_copy(&(self->state), new_data_ptr, bytes_in_bitbuffer);
            memcpy(new_data_ptr + bytes_in_bitbuffer, self->state.next_in, self->avail_in_real);
            Py_XSETREF(self->unused_data, new_data);
        }
    }
    else if (self->avail_in_real == 0) {
        self->state.next_in = NULL;
        self->needs_input = 1;
    }
    else {
        self->needs_input = 0;

        /* If we did not use the input buffer, we now have
           to copy the tail from the caller's buffer into the
           input buffer */
        if (!input_buffer_in_use) {

            /* Discard buffer if it's too small
               (resizing it may needlessly copy the current contents) */
            if (self->input_buffer != NULL &&
                self->input_buffer_size < self->avail_in_real) {
                PyMem_Free(self->input_buffer);
                self->input_buffer = NULL;
            }

            /* Allocate if necessary */
            if (self->input_buffer == NULL) {
                self->input_buffer = PyMem_Malloc(self->avail_in_real);
                if (self->input_buffer == NULL) {
                    PyErr_SetNone(PyExc_MemoryError);
                    goto error;
                }
                self->input_buffer_size = self->avail_in_real;
            }

            /* Copy tail */
            memcpy(self->input_buffer, self->state.next_in, self->avail_in_real);
            self->state.next_in = self->input_buffer;
        }
    }
    return result;

error:
    Py_XDECREF(result);
    return NULL;
}

static PyObject *
igzip_lib_IgzipDecompressor_decompress_impl(IgzipDecompressor *self, Py_buffer *data,
                                             Py_ssize_t max_length)
{
    PyObject *result = NULL;
    if (self->eof)
        PyErr_SetString(PyExc_EOFError, "End of stream already reached");
    else
        result = decompress(self, data->buf, data->len, max_length);
    return result;
}

