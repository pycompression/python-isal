import sys

from isal import igzip

with igzip.open(sys.argv[1], "rb") as gzip_file:
    for line in gzip_file:
        pass
