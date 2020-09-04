from typing import Dict
import timeit
from isal import isal_zlib
import zlib
pangram = b"The quick brown fox jumps over the lazy dog. "
data = pangram * 23 * 1024  # Approx 1 MB
sizes: Dict[str, bytes] = {
    "0b": b"",
    "8b": data[:8],
    "128b": data[:128],
    "1kb": data[:1024],
    "8kb": data[:8 * 1024],
    "16kb": data[:16 * 1024],
    "64kb": data[:64 * 1024],
    #"512kb": data[:512*1024]
}
compressed_sizes = {name: zlib.compress(data_block)
                    for name, data_block in sizes.items()}


def benchmark(name: str,
              names_and_data: Dict[str, bytes],
              isal_string: str,
              zlib_string: str,
              number: int = 10_000):
    print(name)
    print("name\tisal\tzlib\tratio")
    for name, data_block in names_and_data.items():
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


benchmark("Compression", sizes,
          "isal_zlib.compress(data_block)",
          "zlib.compress(data_block, 1)")

benchmark("Decompression", compressed_sizes,
          "isal_zlib.decompress(data_block)",
          "zlib.decompress(data_block)")
