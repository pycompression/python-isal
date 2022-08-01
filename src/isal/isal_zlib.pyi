# Copyright (c) 2001, 2002, 2003, 2004, 2005, 2006, 2007, 2008, 2009, 2010,
# 2011, 2012, 2013, 2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022
# Python Software Foundation; All Rights Reserved

# This file is part of python-isal which is distributed under the
# PYTHON SOFTWARE FOUNDATION LICENSE VERSION 2.

ISAL_BEST_SPEED: int
ISAL_BEST_COMPRESSION: int
ISAL_DEFAULT_COMPRESSION: int
Z_BEST_SPEED: int
Z_BEST_COMPRESSION: int
Z_DEFAULT_COMPRESSION: int

DEF_BUF_SIZE: int
DEF_MEM_LEVEL: int
MAX_WBITS: int

DEFLATED: int

Z_DEFAULT_STRATEGY: int
Z_RLE: int
Z_HUFFMAN_ONLY: int
Z_FILTERED: int
Z_FIXED: int

Z_NO_FLUSH: int
Z_SYNC_FLUSH: int
Z_FULL_FLUSH: int
Z_FINISH: int

error: Exception
IsalError: Exception

def adler32(__data, __value: int = 1) -> int: ...
def crc32(__data, __value: int = 0) -> int: ...

def compress(__data,
             level: int = ISAL_DEFAULT_COMPRESSION,
             wbits: int = MAX_WBITS) -> bytes: ...
def decompress(__data,
               wbits: int = MAX_WBITS,
               bufsize: int = DEF_BUF_SIZE) -> bytes: ...

class Compress:
    def compress(self, __data) -> bytes: ...
    def flush(self, mode: int = Z_FINISH) -> bytes: ...

class Decompress:
    unused_data: bytes
    unconsumed_tail: bytes
    eof: bool

    def decompress(self, __data, max_length: int = 0) -> bytes: ...
    def flush(self, length: int = DEF_BUF_SIZE) -> bytes: ...

def compressobj(level: int = ISAL_DEFAULT_COMPRESSION,
                method: int = DEFLATED,
                wbits: int = MAX_WBITS,
                memLevel: int = DEF_MEM_LEVEL,
                strategy: int = Z_DEFAULT_STRATEGY,
                zdict = None) -> Compress: ...
def decompressobj(wbits: int = MAX_WBITS, zdict = None) -> Decompress: ...
