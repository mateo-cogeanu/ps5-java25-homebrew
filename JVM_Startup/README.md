# JVM Startup — first passing PS5 Java 25 build

**PPSA99865 · 01.000.023 · all four tests passed on PS5 firmware 13.60 on 2026-10-12.**

1. Initialize the embedded core runtime.
2. Create the real Java 25 VM in interpreter mode.
3. Execute Hello25: Java 25 version, arithmetic and a Java worker thread.
4. Destroy the VM cleanly.

The application reads the packaged class bytes and defines them through JNI into the actual system class loader. This snapshot establishes application-bytecode execution; filesystem class-path discovery, JIT, Minecraft and mods remain unverified.

## Run

Download the ZIP from [the milestone release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/JVM_Startup-v01.000.023), extract it, and register the `PPSA99865` title folder in the existing ShadowLoader/native-title workflow. Run the four rows in order. The release retains menu music at 35% and disabled selection effects.

See [validation.json](validation.json) for the reported result and package checksum.

## Rebuild

The scripts use the original macOS/Homebrew build environment: Python with Pillow, host JDK 25, LLVM 22 plus lld, GNU make and ffmpeg. Native SDK and native-app dependencies are pinned; OpenJDK source is pinned in java25/upstream.json and adapted through the patches directory.

From this folder on a fresh checkout:

```sh
python3 tools/package_native.py --source java25/probe/main.cpp --param java25/probe/param.json
python3 tools/java25_source.py --bootstrap --build-hotspot --build-base
python3 tools/package_java25_jni.py --startup
```

The first command prepares the pinned native SDK/tooling using the prerequisite platform probe. The final package is generated at `dist/PPSA99865.zip`. Cached dependencies and generated build outputs are excluded from Git.

This is a frozen milestone. Current changes belong in ../Development; preserve this snapshot's tested behaviour and validation record.
