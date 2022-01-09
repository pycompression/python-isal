import os
import sys

from isal import igzip

with open(sys.argv[1], "rb") as in_file:
    with igzip.open(os.devnull, "wb") as out_gzip:
        for line in in_file:
            out_gzip.write(line)
