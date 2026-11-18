"""Cross-library checks for dictionary headers and compressor lifecycle."""
import random
import zlib

from isal import isal_zlib

import pytest


@pytest.mark.parametrize('level', range(4))
@pytest.mark.parametrize('wbits', [9, 15, -15])
@pytest.mark.parametrize('dictionary_size', [11, 32768, 40000])
@pytest.mark.parametrize(
    'first_operation', ['compress', 'empty', 'sync', 'finish'])
def test_dictionary_cross_decode(level, wbits, dictionary_size,
                                 first_operation):
    dictionary = random.Random(21).randbytes(dictionary_size)
    data = dictionary[-256:] * 5 + random.Random(22).randbytes(4096)
    compressor = isal_zlib.compressobj(level, wbits=wbits, zdict=dictionary)
    packed = b''
    if first_operation == 'empty':
        packed += compressor.compress(b'')
    elif first_operation == 'sync':
        packed += compressor.flush(isal_zlib.Z_SYNC_FLUSH)
    elif first_operation == 'finish':
        data = b''
    for pos in range(0, len(data), 17):
        packed += compressor.compress(data[pos:pos+17])
    packed += compressor.flush()
    if wbits > 0:
        assert packed[0] >> 4 == wbits - 8
        assert packed[1] & 32
        assert int.from_bytes(packed[2:6], 'big') == zlib.adler32(dictionary)
        assert int.from_bytes(packed[:2], 'big') % 31 == 0
    decompressor = zlib.decompressobj(wbits, zdict=dictionary)
    assert decompressor.decompress(packed) + decompressor.flush() == data
    assert decompressor.eof
    assert decompressor.unused_data == b''


@pytest.mark.parametrize('level', range(4))
@pytest.mark.parametrize(
    'flush_mode', [isal_zlib.Z_SYNC_FLUSH, isal_zlib.Z_FULL_FLUSH])
def test_dictionary_multiple_flushes(level, flush_mode):
    dictionary = b'hello world'
    compressor = isal_zlib.compressobj(level, zdict=dictionary)
    data = dictionary * 1000
    packed = compressor.compress(data[:5500]) + compressor.flush(flush_mode)
    packed += compressor.compress(data[5500:]) + compressor.flush()
    for module in (zlib, isal_zlib):
        decompressor = module.decompressobj(zdict=dictionary)
        assert decompressor.decompress(packed) + decompressor.flush() == data


@pytest.mark.parametrize('dictionary', [None, b''])
def test_no_dictionary_header(dictionary):
    kwargs = {} if dictionary is None else {'zdict': dictionary}
    compressor = isal_zlib.compressobj(**kwargs)
    data = b'hello world' * 100
    packed = compressor.compress(data) + compressor.flush()
    assert not packed[1] & 32
    assert zlib.decompress(packed) == data


def test_wrong_dictionary_rejected_by_zlib():
    compressor = isal_zlib.compressobj(zdict=b'hello world')
    packed = compressor.compress(b'hello world' * 10) + compressor.flush()
    decompressor = zlib.decompressobj(zdict=b'wrong dictionary')
    with pytest.raises(zlib.error):
        decompressor.decompress(packed)
