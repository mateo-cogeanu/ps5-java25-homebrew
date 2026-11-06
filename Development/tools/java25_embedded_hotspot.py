#!/usr/bin/env python3
"""Merge target HotSpot objects while retaining staged constructor sections."""
import argparse
from pathlib import Path
import re
import subprocess


def embed_hotspot(objects, output, llvm, lld):
    if not objects:
        raise ValueError("No target HotSpot objects")
    response = output.with_suffix(".rsp")
    response.write_text("\n".join(
        '"' + str(path.resolve()).replace("\\", "\\\\").replace('"', '\\"') + '"'
        for path in objects
    ) + "\n")
    subprocess.run([str(lld), "-r", "@" + str(response), "-o", str(output)], check=True)
    sections = subprocess.check_output([str(llvm / "llvm-readelf"), "-SW", str(output)], text=True)
    names = sorted(set(re.findall(r"\]\s+(\.(?:init_array|ctors)\S*)\s", sections)))
    if not names:
        raise ValueError("No staged HotSpot constructors found")
    renames = []
    for name in names:
        renames.extend(["--rename-section", name + "=.data.rel.ro.jvm_init_array" + name])
    subprocess.run([str(llvm / "llvm-objcopy"), *renames, str(output)], check=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("objects", "output", "llvm-bin", "lld"):
        parser.add_argument("--" + option, type=Path, required=True)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    embed_hotspot(sorted(args.objects.glob("*.o")), args.output, args.llvm_bin, args.lld)


if __name__ == "__main__":
    main()
