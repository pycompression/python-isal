"""Compare installed baseline/candidate wheels in separate Python environments.

Example: python benchmark_scripts/benchmark_abi3.py --library isal \
    --baseline /tmp/before/bin/python --candidate /tmp/after/bin/python \
    --output /tmp/abi3-results.json
"""
import argparse
import gc
import gzip
import hashlib
import importlib
import io
import json
import math
import os
import platform
import random
import statistics
import subprocess
import sys
import sysconfig
import tempfile
import time
import zlib
from pathlib import Path


SIZES = (1024, 65536, 1048713, 16777353)


def prepare_data(directory):
    fixture = Path(__file__).resolve().parents[1] / "tests/data/test.fastq.gz"
    stdlib = Path(sysconfig.get_path("stdlib"))
    source = b"\n".join(
        (stdlib / name).read_bytes()
        for name in ("gzip.py", "tarfile.py", "typing.py", "json/encoder.py",
                     "zipfile.py", "zipfile/__init__.py")
        if (stdlib / name).is_file()
    )
    seeds = {"fastq": gzip.decompress(fixture.read_bytes()),
             "python": source,
             "random": random.Random(240).randbytes(max(SIZES)),
             "zeros": bytes(1024)}
    hashes = {}
    for kind, seed in seeds.items():
        for size in SIZES:
            data = (seed * ((size + len(seed) - 1) // len(seed)))[:size]
            prefix = directory / f"{kind}-{size}"
            prefix.with_suffix(".bin").write_bytes(data)
            hashes[f"{kind}/{size}"] = hashlib.sha256(data).hexdigest()
            for suffix, wbits in ((".zlib", 15), (".raw", -15), (".gz", 31)):
                prefix.with_suffix(suffix).write_bytes(
                    zlib.compress(data, 6, wbits=wbits))
    return hashes


def cases(library, directory):
    if library == "isal":
        gz = importlib.import_module("isal.igzip")
        igzip_lib = importlib.import_module("isal.igzip_lib")
        codec = importlib.import_module("isal.isal_zlib")
        decoder = igzip_lib.IgzipDecompressor
        raw_decompress = igzip_lib.decompress
    else:
        gz = importlib.import_module("zlib_ng.gzip_ng")
        codec = importlib.import_module("zlib_ng.zlib_ng")

        def decoder():
            return codec._ZlibDecompressor(wbits=-15)

        def raw_decompress(data):
            return codec.decompress(data, wbits=-15)
    for kind in ("fastq", "python", "random", "zeros"):
        for size in SIZES:
            prefix = directory / f"{kind}-{size}"
            data = prefix.with_suffix(".bin").read_bytes()
            packed = prefix.with_suffix(".zlib").read_bytes()
            raw = prefix.with_suffix(".raw").read_bytes()
            gzipped = prefix.with_suffix(".gz").read_bytes()

            def stream(packed=packed):
                obj = codec.decompressobj()
                return obj.decompress(packed) + obj.flush()

            def bounded(raw=raw):
                obj = decoder()
                chunks = [obj.decompress(raw, 65536)]
                while not obj.eof:
                    chunks.append(obj.decompress(b"", 65536))
                return b"".join(chunks)

            def read(gzipped=gzipped):
                chunks = []
                with gz.open(io.BytesIO(gzipped), "rb") as handle:
                    while chunk := handle.read(131072):
                        chunks.append(chunk)
                return b"".join(chunks)

            def readinto(verify=False, gzipped=gzipped):
                buffer = bytearray(131072)
                count, chunks = 0, []
                with gz.open(io.BytesIO(gzipped), "rb") as handle:
                    while length := handle.readinto(buffer):
                        count += length
                        if verify:
                            chunks.append(bytes(buffer[:length]))
                return b"".join(chunks) if verify else count

            assert readinto(verify=True) == data
            operations = (
                ("compress1", lambda data=data: codec.compress(data, 1),
                 "zlib"),
                ("decompress", lambda packed=packed: codec.decompress(packed),
                 "bytes"),
                ("raw-decompress", lambda raw=raw: raw_decompress(raw),
                 "bytes"),
                ("stream-decompress", stream, "bytes"),
                ("bounded-decompress", bounded, "bytes"),
                ("gzip-read128k", read, "bytes"),
                ("gzip-readinto128k", readinto, "size"),
                ("crc32", lambda data=data: codec.crc32(data), "crc"),
            )
            for name, function, check in operations:
                yield f"{kind}/{size}/{name}", function, data, check


def worker(args):
    if hasattr(os, "sched_setaffinity"):
        os.sched_setaffinity(0, {args.cpu})
    module = importlib.import_module(args.library)
    extension = importlib.import_module(
        "isal.isal_zlib" if args.library == "isal" else "zlib_ng.zlib_ng")
    calibration = (json.loads(args.calibration.read_text())
                   if args.calibration else {})
    gc.disable()
    result = {}
    for name, function, expected, check in cases(args.library, args.data):
        start = time.thread_time_ns()
        actual = function()
        first = time.thread_time_ns() - start
        if check == "zlib":
            assert zlib.decompress(actual) == expected, name
        elif check == "bytes":
            assert actual == expected, name
        elif check == "size":
            assert actual == len(expected), name
        else:
            assert actual == zlib.crc32(expected), name
        del actual
        count = calibration.get(name, max(1, min(
            10000, math.ceil(20_000_000 / max(first, 1)))))
        start_cpu, start_wall = time.thread_time_ns(), time.perf_counter_ns()
        for _ in range(count):
            function()
        result[name] = {"cpu_ns": time.thread_time_ns() - start_cpu,
                        "wall_ns": time.perf_counter_ns() - start_wall,
                        "count": count}
    return {"cases": result, "python": sys.version,
            "module": module.__file__, "platform": platform.platform(),
            "extension": extension.__file__,
            "version": getattr(module, "__version__", None),
            "gil_enabled": getattr(sys, "_is_gil_enabled", lambda: True)(),
            "free_threaded": bool(sysconfig.get_config_var("Py_GIL_DISABLED"))}


def paired_ratios(rows):
    """Return {case: {variant: median ratio}} against each round's baseline."""
    grouped = {(r["round"], r["variant"]): r["cases"] for r in rows}
    rounds = sorted({r["round"] for r in rows})
    medians = {}
    for name in rows[0]["cases"]:
        medians[name] = {}
        for variant in ("candidate", "control"):
            values = []
            for repeat in rounds:
                a = grouped[repeat, variant][name]
                b = grouped[repeat, "baseline"][name]
                values.append((a["cpu_ns"] / a["count"]) /
                              (b["cpu_ns"] / b["count"]))
            medians[name][variant] = statistics.median(values)
    return medians


def summarize(rows):
    """Print per-case medians, then the summaries the reports quote."""
    medians = paired_ratios(rows)
    print("case,candidate_time_ratio,control_time_ratio")
    for name, ratio in medians.items():
        print(f"{name},{ratio['candidate']:.6f},{ratio['control']:.6f}")
    control = [abs(r["control"] - 1) for r in medians.values()]
    p95 = statistics.quantiles(control, n=100, method="inclusive")[94]
    print(f"\ncontrol |ratio - 1|: p95 (inclusive) {p95:.3%}, "
          f"max {max(control):.3%}")
    operations = {}
    for name, ratio in medians.items():
        operations.setdefault(name.split("/")[2], []).append(
            ratio["candidate"])
    print("\noperation,median,min,max")
    for operation, values in operations.items():
        print(f"{operation},{statistics.median(values):.3f},"
              f"{min(values):.3f},{max(values):.3f}")
    largest = str(max(SIZES))
    kinds = sorted({name.split("/")[0] for name in medians})
    print(f"\nsize {largest}: operation," + ",".join(kinds))
    for operation in operations:
        print(operation + "," + ",".join(
            f"{medians[f'{kind}/{largest}/{operation}']['candidate']:.3f}"
            for kind in kinds))
    ranked = sorted(medians.items(), key=lambda item: item[1]["candidate"])
    print("\nslowest cases")
    for name, ratio in reversed(ranked[-10:]):
        print(f"{name},{ratio['candidate']:.3f}")
    print("\nfastest cases")
    for name, ratio in ranked[:10]:
        print(f"{name},{ratio['candidate']:.3f}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--library", choices=("isal", "zlib_ng"),
                        required=True)
    parser.add_argument("--baseline", type=Path)
    parser.add_argument("--candidate", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--rounds", type=int, default=9)
    parser.add_argument("--cpu", type=int, default=1)
    parser.add_argument("--worker", action="store_true",
                        help=argparse.SUPPRESS)
    parser.add_argument("--data", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--calibration", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--summarize", type=Path, metavar="RESULTS",
                        help="print the summaries of an existing --output "
                             "file instead of running a benchmark")
    args = parser.parse_args()
    if args.summarize:
        summarize(json.loads(args.summarize.read_text())["runs"])
        return
    if args.worker:
        print(json.dumps(worker(args)))
        return
    if not (args.baseline and args.candidate and args.output):
        parser.error("--baseline, --candidate and --output are required")
    if args.rounds < 1:
        parser.error("--rounds must be positive")
    if (hasattr(os, "sched_getaffinity")
            and args.cpu not in os.sched_getaffinity(0)):
        parser.error(f"--cpu {args.cpu} is not available; choose one of "
                     f"{sorted(os.sched_getaffinity(0))}")
    # Resolving a venv's interpreter symlink would bypass that environment.
    args.baseline = args.baseline.absolute()
    args.candidate = args.candidate.absolute()
    args.output = args.output.resolve()
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env["PYTHONNOUSERSITE"] = "1"
    rows = []
    with tempfile.TemporaryDirectory() as temporary:
        directory = Path(temporary)
        hashes = prepare_data(directory)
        common = [str(Path(__file__).resolve()), "--worker", "--library",
                  args.library, "--data", str(directory),
                  "--cpu", str(args.cpu)]

        def run(interpreter, extra=()):
            return json.loads(subprocess.check_output(
                [str(interpreter), *common, *extra], cwd=directory, env=env))

        initial = run(args.baseline)
        calibration = directory / "calibration.json"
        calibration.write_text(json.dumps({
            name: case["count"] for name, case in initial["cases"].items()}))
        interpreters = {"baseline": args.baseline, "control": args.baseline,
                        "candidate": args.candidate}
        rng = random.Random(240)
        for repeat in range(args.rounds):
            order = list(interpreters)
            rng.shuffle(order)
            for variant in order:
                result = run(interpreters[variant],
                             ("--calibration", str(calibration)))
                rows.append({"round": repeat, "variant": variant, **result})
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_text(json.dumps({
                    "library": args.library, "cpu": args.cpu,
                    "data_sha256": hashes, "planned_rounds": args.rounds,
                    "runs": rows}, separators=(",", ":")))
            print(f"Round {repeat + 1}/{args.rounds}", flush=True)
    summarize(rows)


if __name__ == "__main__":
    main()
