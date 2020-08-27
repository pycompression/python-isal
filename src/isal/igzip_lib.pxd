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

cdef extern from "<isa-l/igzip_lib.h>":
    # Deflate compression standard defines
    int ISAL_DEF_MAX_HDR_SIZE
    int ISAL_DEF_MAX_CODE_LEN
    int ISAL_DEF_HIST_SIZE  # Window size
    int ISAL_DEF_MAX_HIST_BITS
    int ISAL_DEF_MAX_MATCH
    int ISAL_DEF_MIN_MATCH

    int ISAL_DEF_LIT_SYMBOLS
    int ISAL_DEF_LEN_SYMBOLS
    int ISAL_DEF_DIST_SYMBOLS
    int ISAL_DEF_LIT_LEN_SYMBOLS

    # Max repeat length
    int ISAL_LOOK_AHEAD

    # Flush flags
    int NO_FLUSH  # Defaults
    int SYNC_FLUSH
    int FULL_FLUSH

    # Gzip flags
    int IGZIP_DEFLATE  # Default
    int IGZIP_GZIP
    int IGZIP_GZIP_NO_HDR
    int IGZIP_ZLIB
    int IGZIP_ZLIB_NO_HDR

    # Compression return values
    int COMP_OK 
    int INVALID_FLUSH
    int INVALID_PARAM
    int STATELESS_OVERFLOW
    int ISAL_INVALID_OPERATION
    int ISAL_INVALID_STATE 
    int ISAL_INVALID_LEVEL 
    int ISAL_INVALID_LEVEL_BUFF 

    cdef enum isal_zstate_state:
        ZSTATE_NEW_HDR  #!< Header to be written
        ZSTATE_HDR,	#!< Header state
        ZSTATE_CREATE_HDR  #!< Header to be created
        ZSTATE_BODY,	#!< Body state
        ZSTATE_FLUSH_READ_BUFFER  #!< Flush buffer
        ZSTATE_FLUSH_ICF_BUFFER
        ZSTATE_TYPE0_HDR  #! Type0 block header to be written
        ZSTATE_TYPE0_BODY  #!< Type0 block body to be written
        ZSTATE_SYNC_FLUSH  #!< Write sync flush block
        ZSTATE_FLUSH_WRITE_BUFFER  #!< Flush bitbuf
        ZSTATE_TRL,	#!< Trailer state
        ZSTATE_END,	#!< End state
        ZSTATE_TMP_NEW_HDR  #!< Temporary Header to be written
        ZSTATE_TMP_HDR,	#!< Temporary Header state
        ZSTATE_TMP_CREATE_HDR  #!< Temporary Header to be created state
        ZSTATE_TMP_BODY  #!< Temporary Body state
        ZSTATE_TMP_FLUSH_READ_BUFFER  #!< Flush buffer
        ZSTATE_TMP_FLUSH_ICF_BUFFER
        ZSTATE_TMP_TYPE0_HDR  #! Temporary Type0 block header to be written
        ZSTATE_TMP_TYPE0_BODY  #!< Temporary Type0 block body to be written
        ZSTATE_TMP_SYNC_FLUSH  #!< Write sync flush block
        ZSTATE_TMP_FLUSH_WRITE_BUFFER  #!< Flush bitbuf
        ZSTATE_TMP_TRL 	#!< Temporary Trailer state
        ZSTATE_TMP_END	#!< Temporary End state

    cdef enum isal_block_state:
        ISAL_BLOCK_NEW_HDR,	# Just starting a new block */
        ISAL_BLOCK_HDR,		# In the middle of reading in a block header */
        ISAL_BLOCK_TYPE0,	# Decoding a type 0 block */
        ISAL_BLOCK_CODED,	# Decoding a huffman coded block */
        ISAL_BLOCK_INPUT_DONE,	# Decompression of input is completed */
        ISAL_BLOCK_FINISH,	# Decompression of input is completed and all data has been flushed to output */
        ISAL_GZIP_EXTRA_LEN,
        ISAL_GZIP_EXTRA,
        ISAL_GZIP_NAME,
        ISAL_GZIP_COMMENT,
        ISAL_GZIP_HCRC,
        ISAL_ZLIB_DICT,
        ISAL_CHECKSUM_CHECK,
    
    # Inflate flags
    int ISAL_DEFLATE 
    int ISAL_GZIP 
    int ISAL_GZIP_NO_HDR
    int ISAL_ZLIB
    int ISAL_ZLIB_NO_HDR
    int ISAL_ZLIB_NO_HDR_VER
    int ISAL_GZIP_NO_HDR_VER

    # Inflate return values
    int ISAL_DECOMP_OK
    int ISAL_END_INPUT
    int ISAL_OUT_OVERFLOW
    int ISAL_NAME_OVERFLOW
    int ISAL_COMMENT_OVERFLOW
    int ISAL_EXTRA_OVERFLOW
    int ISAL_NEED_DICT
    int ISAL_INVALID_BLOCK
    int ISAL_INVALID_LOOKBACK
    int ISAL_INVALID_WRAPPER
    int ISAL_UNSOPPERTED_METHOD
    int ISAL_INCORRECT_CHECKSUM

    # Compression structures
    int ISAL_DEF_MIN_LEVEL
    int ISAL_DEF_MAX_LEVEL

    int ISAL_DEF_LVL0_MIN
    int ISAL_DEF_LVL0_SMALL
    int ISAL_DEF_LVL0_MEDIUM
    int ISAL_DEF_LVL0_LARGE
    int ISAL_DEF_LVL0_EXTRA_LARGE
    int ISAL_DEF_LVL0_DEFAULT

    int ISAL_DEF_LVL1_MIN
    int ISAL_DEF_LVL1_SMALL
    int ISAL_DEF_LVL1_MEDIUM
    int ISAL_DEF_LVL1_LARGE
    int ISAL_DEF_LVL1_EXTRA_LARGE
    int ISAL_DEF_LVL1_DEFAULT

    int ISAL_DEF_LVL2_MIN
    int ISAL_DEF_LVL2_SMALL
    int ISAL_DEF_LVL2_MEDIUM
    int ISAL_DEF_LVL2_LARGE
    int ISAL_DEF_LVL2_EXTRA_LARGE
    int ISAL_DEF_LVL2_DEFAULT

    int ISAL_DEF_LVL3_MIN
    int ISAL_DEF_LVL3_SMALL
    int ISAL_DEF_LVL3_MEDIUM
    int ISAL_DEF_LVL3_LARGE
    int ISAL_DEF_LVL3_EXTRA_LARGE
    int ISAL_DEF_LVL3_DEFAULT
    
    cdef struct isal_zstream:
        pass

    # Compression functions