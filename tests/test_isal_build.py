"""Check that the statically linked ISA-L uses its optimized code paths."""
import platform
from pathlib import Path

from isal import isal_zlib

import pytest

EXTENSION_BYTES = Path(isal_zlib.__file__).read_bytes()

# Function names from ISA-L's portable C code. The extension binary contains
# them only when ISA-L is linked statically and the symbols are not stripped.
STATIC_ISAL = b"decode_huffman_code_block_stateless_base" in EXTENSION_BYTES


@pytest.mark.skipif(platform.machine().lower() not in ("aarch64", "arm64"),
                    reason="Only applies to aarch64 builds")
@pytest.mark.skipif(not STATIC_ISAL,
                    reason="ISA-L is linked dynamically or stripped")
@pytest.mark.parametrize("symbol", [
    b"decode_huffman_code_block_stateless_aarch64",  # Inflate
    b"isal_deflate_body_aarch64",  # Deflate
    b"crc32_gzip_refl_pmull",  # CRC-32
    b"adler32_neon",  # Adler-32
])
def test_aarch64_build_includes_optimized_functions(symbol):
    # Without these functions, ISA-L falls back to its portable C code,
    # which is several times slower.
    assert symbol in EXTENSION_BYTES
