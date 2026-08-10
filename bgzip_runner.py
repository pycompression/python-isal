#!/usr/bin/env python3
import io
import sys

from isal.igzip_threaded import _ThreadedGzipReader, _ThreadedBGzipReader

def main():
    file = sys.argv[1]
    with io.BufferedReader(
        _ThreadedBGzipReader(file, threads=8)
    ) as f:
        while True:
            block = f.read(128 * 1024)
            if block == b"":
                return


if __name__ == "__main__":
    main()