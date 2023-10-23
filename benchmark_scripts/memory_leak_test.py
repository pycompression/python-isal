import sys
from isal import igzip
from pathlib import Path
import resource
import gc

README = Path(__file__).parent.parent / "README.rst"
GZIPPED_DATA = igzip.compress(README.read_bytes())

for _ in range(10):
    for _ in range(1000):
        a = igzip.decompress(GZIPPED_DATA)
    memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    memory_usage_mb = memory_usage / 1024
    print(f"Maximum memory usage: {memory_usage_mb:.2f} MiB")


for _ in range(10):
    with igzip.open(sys.argv[1], "rb") as reader:
        a = reader.read()
        print(len(a))
        gc.collect()
        memory_usage = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_usage_mb = memory_usage / 1024
        print(f"Maximum memory usage: {memory_usage_mb:.2f} MiB")
        del(a)


objects_and_size = [(sys.getsizeof(obj), type(obj)) for obj in
                    gc.get_objects()]
objects_and_size.sort(key=lambda x: x[0], reverse=True)
print(objects_and_size[:10])
