# IO_Probe — first passing Java file I/O milestone

Frozen PS5 console milestone **PPSA99866 01.000.004**, confirmed ALL PASS by
the user on 2026-10-13, firmware 13.60.

The four passing rows initialize the embedded runtime, create the real Java 25
VM, run FileIO25, and destroy the VM. FileIO25 verifies relative path resolution,
exclusive private-file creation (0600), UTF-8 write/read equality, file size,
deletion and absence. It uses real Java Files APIs and native OS operations.

[Download the passing native app folder ZIP and validation assets](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/IO_Probe-v01.000.004).
Extract the ZIP and copy the entire PPSA99866 folder into your existing
ShadowLoader homebrew scan location.

## Reproduce

Run from this folder with the pinned toolchain/dependencies prepared:

```sh
python3 tools/java25_source.py --bootstrap --build-hotspot --build-base
python3 tools/package_java25_jni.py --fileio
```

The build uses java25/probe/fileio.cpp and fileio-param.json. The source pin
and 29 patches are retained here. Generated binaries/dependencies are excluded
from Git. See validation.json for results, policies and the package SHA-256.

This snapshot stays frozen; later work goes into ../Development. Default-0666
creation, directory listing, ZIP/JAR class loading, sockets, JIT stability and
Minecraft remain separate tests. Keep all upstream source/license notices.
