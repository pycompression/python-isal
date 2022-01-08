import argparse
import gzip
import io  # noqa: F401 used in timeit strings
import timeit
import zlib
from pathlib import Path
from typing import Dict

from isal import igzip, isal_zlib  # noqa: F401 used in timeit strings

DATA_DIR = Path(__file__).parent.parent / "tests" / "data"
COMPRESSED_FILE = DATA_DIR / "test.fastq.gz"
with gzip.open(str(COMPRESSED_FILE), mode="rb") as file_h:
    data = file_h.read()

sizes: Dict[str, bytes] = {
    "0b": b"",
    "8b": data[:8],
    "128b": data[:128],
    "1kb": data[:1024],
    "8kb": data[:8 * 1024],
    "16kb": data[:16 * 1024],
    "32kb": data[:32 * 1024],
    "64kb": data[:64 * 1024],
    # "128kb": data[:128*1024],
    # "512kb": data[:512*1024]
}
compressed_sizes = {name: zlib.compress(data_block)
                    for name, data_block in sizes.items()}

compressed_sizes_gzip = {name: gzip.compress(data_block)
                         for name, data_block in sizes.items()}


def show_sizes():
    print("zlib sizes")
    print("name\t" + "\t".join(str(level) for level in range(-1, 10)))
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
            str(round(len(isal_zlib.compress(data_block, level)) / orig_size,
                      3))
            for level in range(0, 4))
        print(name + "\t" + "\t".join(rel_sizes))


def benchmark(name: str,
              names_and_data: Dict[str, bytes],
              isal_string: str,
              zlib_string: str,
              number: int = 10_000,
              **kwargs):
    print(name)
    print("name\tisal\tzlib\tratio")
    for name, data_block in names_and_data.items():
        timeit_kwargs = dict(globals=dict(**globals(), **locals()),
                             number=number, **kwargs)
        isal_time = timeit.timeit(isal_string, **timeit_kwargs)
        zlib_time = timeit.timeit(zlib_string, **timeit_kwargs)
        isal_microsecs = round(isal_time * (1_000_000 / number), 2)
        zlib_microsecs = round(zlib_time * (1_000_000 / number), 2)
        ratio = round(isal_time / zlib_time, 2)
        print("{0}\t{1}\t{2}\t{3}".format(name,
                                          isal_microsecs,
                                          zlib_microsecs,
                                          ratio))


# show_sizes()

def argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--checksums", action="store_true")
    parser.add_argument("--functions", action="store_true")
    parser.add_argument("--gzip", action="store_true")
    parser.add_argument("--sizes", action="store_true")
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
        benchmark("zlib compression", sizes,
                  "isal_zlib.compress(data_block, 1)",
                  "zlib.compress(data_block, 1)")

        benchmark("zlib decompression", compressed_sizes,
                  "isal_zlib.decompress(data_block)",
                  "zlib.decompress(data_block)")

    if args.gzip or args.all:
        benchmark("gzip compression", sizes,
                  "igzip.compress(data_block, 1)",
                  "gzip.compress(data_block, 1)")

        benchmark("gzip decompression", compressed_sizes_gzip,
                  "igzip.decompress(data_block)",
                  "gzip.decompress(data_block)")
    if args.objects or args.all:
        benchmark("zlib Compress instantiation", {"": b""},
                  "a = isal_zlib.compressobj()",
                  "a = zlib.compressobj()")
        benchmark("zlib Decompress instantiation", {"": b""},
                  "a = isal_zlib.decompressobj()",
                  "a = zlib.decompressobj()")
        benchmark("Gzip Writer instantiation", {"": b""},
                  "a = igzip.GzipFile(fileobj=io.BytesIO(), mode='wb' )",
                  "a = gzip.GzipFile(fileobj=io.BytesIO(), mode='wb')")
        benchmark("Gzip Reader instantiation", {"": b""},
                  "a = igzip.GzipFile(fileobj=io.BytesIO(), mode='rb' )",
                  "a = gzip.GzipFile(fileobj=io.BytesIO(), mode='rb')")
    if args.sizes or args.all:
        show_sizes()
