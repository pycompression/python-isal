from typing import Dict
import timeit
from isal import isal_zlib
import zlib

import argparse
pangram = b"The quick brown fox jumps over the lazy dog. "
data = pangram * 23 * 1024  # Approx 1 MB
sizes: Dict[str, bytes] = {
    "0b": b"",
    "8b": data[:8],
    "128b": data[:128],
    "1kb": data[:1024],
    "8kb": data[:8 * 1024],
    "16kb": data[:16 * 1024],
    "32kb": data[:32 * 1024],
    "64kb": data[:64 * 1024],
    "128kb": data[:128*1024],
    #"512kb": data[:512*1024]
}
compressed_sizes = {name: zlib.compress(data_block)
                    for name, data_block in sizes.items()}


def show_sizes():
    print("zlib sizes")
    print("name\t" + "\t".join(str(level) for level in range(-1,10)))
    for name, data_block in sizes.items():
        orig_size = max(len(data_block), 1)
        rel_sizes = (
            str(round(len(zlib.compress(data_block, level)) / orig_size, 3))
            for level in range(-1, 10))
        print(name + "\t" + "\t".join(rel_sizes))

    print("isal sizes")
    print("name\t" + "\t".join(str(level) for level in range(0, 4)))
    for name, data_block in sizes.items():
        orig_size = max(len(data_block), 1)
        rel_sizes = (
            str(round(len(isal_zlib.compress(data_block, level)) / orig_size, 3))
            for level in range(0, 4))
        print(name + "\t" + "\t".join(rel_sizes))


def benchmark(name: str,
              names_and_data: Dict[str, bytes],
              isal_string: str,
              zlib_string: str,
              number: int = 10_000):
    print(name)
    print("name\tisal\tzlib\tratio")
    for name, data_block in names_and_data.items():
        isal_compressobj = isal_zlib.compressobj(level=1,wbits=-15)
        zlib_compressobj = zlib.compressobj(level=1, wbits=-15)
        timeit_kwargs = dict(globals=dict(**globals(), **locals()),
                             number=number)
        isal_time = timeit.timeit(isal_string, **timeit_kwargs)
        zlib_time = timeit.timeit(zlib_string, **timeit_kwargs)
        isal_nanosecs = round(isal_time * (1_000_000 / number), 2)
        zlib_nanosecs = round(zlib_time * (1_000_000 / number), 2)
        ratio = round(isal_time / zlib_time, 2)
        print("{0}\t{1}\t{2}\t{3}".format(name,
                                          isal_nanosecs,
                                          zlib_nanosecs,
                                          ratio))
# show_sizes()

def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--checksums", action="store_true")
    parser.add_argument("--functions", action="store_true")
    parser.add_argument("--objects", action="store_true")
    return parser

if __name__ == "__main__":
    args = argument_parser().parse_args()
    if args.checksums or args.all:
        benchmark("CRC32", sizes,
                  "isal_zlib.crc32(data_block)",
                  "zlib.crc32(data_block)")

        benchmark("Adler32", sizes,
                  "isal_zlib.adler32(data_block)",
                  "zlib.adler32(data_block)")
    if args.functions or args.all:
        benchmark("Compression", sizes,
                  "isal_zlib.compress(data_block, 1)",
                  "zlib.compress(data_block, 1)")

        benchmark("Decompression", compressed_sizes,
                  "isal_zlib.decompress(data_block)",
                  "zlib.decompress(data_block)")

    if args.objects or args.all:
        benchmark("Object compression", sizes,
                  "isal_compressobj.compress(data_block)",
                  "zlib_compressobj.compress(data_block)")

        benchmark("Object decompression", compressed_sizes,
                  "isal_compressobj.decompress(data_block)",
                  "zlib_compressobj.decompress(data_block)")