import sys

from isal.isal_zlib import _GzipReader

if __name__ == "__main__":
    with open(sys.argv[1], "rb") as f:
        reader = _GzipReader(f, 512 * 1024)
        while True:
            block = reader.read(128 * 1024)
            if not block:
                break
