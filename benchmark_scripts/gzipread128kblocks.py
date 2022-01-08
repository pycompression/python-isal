import sys

from isal import igzip

with igzip.open(sys.argv[1], "rb") as gzip_file:
    while True:
        block = gzip_file.read(128 * 1024)
        if not block:
            break

