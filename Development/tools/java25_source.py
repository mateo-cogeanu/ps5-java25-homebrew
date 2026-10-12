#!/usr/bin/env python3
"""Fetch the pinned BSD OpenJDK source; optionally reproduce configure diagnostics.

The bootstrap is experimental and does not produce a runnable PS5 JVM yet.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--configure", action="store_true")
    parser.add_argument("--bootstrap", action="store_true", help="Apply opt-in PS5 patches and configure HotSpot/java.base scope")
    parser.add_argument("--build-hotspot", action="store_true", help="Attempt the experimental HotSpot target after bootstrap configure")
    parser.add_argument("--build-base", action="store_true", help="Build java.base classes and native libraries after bootstrap configure")
    args = parser.parse_args()
    pin = json.loads((ROOT / "java25/upstream.json").read_text())
    source = ROOT / pin["cache"]
    source.parent.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        subprocess.run(["git", "clone", "--depth", "1", "--branch", pin["tag"],
                        pin["repository"], str(source)], check=True)
    actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
    if actual != pin["commit"]:
        raise SystemExit("Source differs from pinned commit; refusing to build it")
    print(f"Pinned OpenJDK source: {actual}", flush=True)
    if args.build_hotspot or args.build_base:
        args.bootstrap = True
    if args.bootstrap:
        for patch in sorted((ROOT / "java25/patches").glob("*.patch")):
            check = subprocess.run(["git", "apply", "--check", str(patch)], cwd=source, capture_output=True)
            if check.returncode == 0:
                subprocess.run(["git", "apply", str(patch)], cwd=source, check=True)
            else:
                applied = subprocess.run(["git", "apply", "--reverse", "--check", str(patch)], cwd=source, capture_output=True)
                if applied.returncode != 0:
                    raise SystemExit(f"Patch conflicts with local source: {patch.name}")
    if not (args.configure or args.bootstrap):
        return
    sdk = ROOT / ".tools/native-sdk/ps5-payload-sdk"
    if not sdk.exists():
        raise SystemExit("Build make java25-probe first to prepare the native SDK")
    boot = Path(os.environ.get("JAVA25_BOOT_JDK", "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"))
    if not (boot / "bin/javac").exists():
        raise SystemExit("Set JAVA25_BOOT_JDK to a host JDK 24 or 25 home")
    log = ROOT / "build/java25" / ("bootstrap-configure.log" if args.bootstrap else "configure.log")
    log.parent.mkdir(parents=True, exist_ok=True)
    command = ["bash", "configure", "--openjdk-target=x86_64-unknown-freebsd",
               "--with-jvm-variants=server", f"--with-boot-jdk={boot}",
               "--disable-warnings-as-errors", "--enable-headless-only",
               "--with-toolchain-type=clang", "--with-native-debug-symbols=none",
               "--with-freetype=bundled", f"CC={sdk / 'bin/prospero-clang'}",
               f"CXX={sdk / 'bin/prospero-clang++'}"]
    if args.bootstrap:
        wrapper = ROOT / "tools/java25_cc.py"
        wrapper.chmod(0o755)
        command = [arg if not arg.startswith("CC=") else f"CC={wrapper}" for arg in command]
        command += ["--enable-ps5-bootstrap", "--with-conf-name=ps5-bootstrap", "--with-jobs=4",
                    f"--with-sysroot={sdk}", "--with-stdc++lib=dynamic",
                    "--with-extra-cxxflags=-fno-stack-protector", "--with-jvm-features=-dtrace"]
    env = dict(os.environ)
    env.setdefault("LLVM_CONFIG", "/opt/homebrew/opt/llvm/bin/llvm-config")
    with log.open("w") as output:
        result = subprocess.run(command, cwd=source, env=env, stdout=output, stderr=subprocess.STDOUT)
    print(f"Configure exit {result.returncode}; diagnostics: {log}")
    print("This diagnostic uses BSD build rules with the PS5 compiler; it does not establish PS5 compatibility.")
    if result.returncode == 0 and args.build_hotspot:
        build_log = ROOT / "build/java25/hotspot-build.log"
        with build_log.open("w") as output:
            result = subprocess.run(["gmake", "CONF=ps5-bootstrap", "hotspot"], cwd=source, env=env,
                                    stdout=output, stderr=subprocess.STDOUT)
        print(f"HotSpot build exit {result.returncode}; diagnostics: {build_log}")
    if result.returncode == 0 and args.build_base:
        build_log = ROOT / "build/java25/base-build.log"
        with build_log.open("w") as output:
            result = subprocess.run(["gmake", "CONF=ps5-bootstrap", "java.base-java", "java.base-libs"],
                                    cwd=source, env=env, stdout=output, stderr=subprocess.STDOUT)
        print(f"java.base build exit {result.returncode}; diagnostics: {build_log}")
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
