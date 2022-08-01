import cProfile
import os
import sys

from isal import igzip


def main():
    with open(sys.argv[1], mode="rb") as in_file:
        with igzip.open(os.devnull, mode="wb") as gzip_h:
            for line in in_file:
                gzip_h.write(line)


if __name__ == "__main__":
    cProfile.run("main()")
