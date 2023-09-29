from isal.isal_zlib import _IGzipReader

import sys

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        reader = _IGzipReader(f, 512 * 1024)
        while True:
            block = reader.read(128 * 1024)
            if not block:
                break
