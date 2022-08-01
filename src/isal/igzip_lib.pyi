# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the 
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

ISAL_BEST_SPEED: int
ISAL_BEST_COMPRESSION: int
ISAL_DEFAULT_COMPRESSION: int
DEF_BUF_SIZE: int
MAX_HIST_BITS: int
ISAL_NO_FLUSH: int
ISAL_SYNC_FLUSH: int
ISAL_FULL_FLUSH: int
COMP_DEFLATE: int
COMP_GZIP: int
COMP_GZIP_NO_HDR: int
COMP_ZLIB: int
COMP_ZLIB_NO_HDR: int
DECOMP_DEFLATE: int
DECOMP_ZLIB: int
DECOMP_GZIP: int
DECOMP_GZIP_NO_HDR: int
DECOMP_ZLIB_NO_HDR: int
DECOMP_ZLIB_NO_HDR_VER: int
DECOMP_GZIP_NO_HDR_VER: int
MEM_LEVEL_DEFAULT: int
MEM_LEVEL_MIN: int
MEM_LEVEL_SMALL: int
MEM_LEVEL_MEDIUM: int
MEM_LEVEL_LARGE: int
MEM_LEVEL_EXTRA_LARGE: int

IsalError: Exception
error: Exception

def compress(__data,
             level: int = ISAL_DEFAULT_COMPRESSION,
             flag: int = COMP_DEFLATE,
             mem_level: int = MEM_LEVEL_DEFAULT,
             hist_bits: int = MAX_HIST_BITS) -> bytes: ...
def decompress(__data,
               flag: int = DECOMP_DEFLATE,
               hist_bits: int = MAX_HIST_BITS,
               bufsize: int = DEF_BUF_SIZE) -> bytes: ...

class IgzipDecompressor:
    unused_data: bytes
    needs_input: bool
    eof: bool
    crc: int

    def __init__(self,
                 flag: int = DECOMP_DEFLATE,
                 hist_bits: int = MAX_HIST_BITS,
                 zdict = None): ...

    def decompress(self, __data, max_length = -1) -> bytes: ...
