import cProfile
import sys

from isal import igzip


def main():
    with igzip.open(sys.argv[1], mode="rb") as gzip_h:
        while True:
            block = gzip_h.read(128*1024)
            if block == b"":
                return


if __name__ == "__main__":
    cProfile.run("main()")
