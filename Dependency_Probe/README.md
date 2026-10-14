# Dependency_Probe — multi-JAR loading, system class path and JNI

Frozen **PPSA99873 01.000.001**, confirmed ALL PASS on 2026-10-14,
PS5 firmware 13.60. All six rows passed on the actual console.

[Download the matching app ZIP, checksum and validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Dependency_Probe-v01.000.001).

## Run

Install the entire PPSA99873 title folder through ShadowLoader. Close the
app before replacing files. No network or Mac helper is required. Run:

1. Initialize embedded runtime.
2. Create Java 25 interpreter VM.
3. Multi-JAR manifest dependencies, service providers and resources.
4. Actual VM system class-path loading and missing-class rejection.
5. Resident JNI library loading, array arithmetic, exception propagation
   and missing-library rejection.
6. Destroy VM.

Long exception messages wrap by actual font widths and use D-pad left/right
for additional pages. Application-view /download0 logs are not assumed to
be accessible through every FTP setup; photograph exception pages if needed.

## What passed

application.jar references dependency.jar and api.jar through its manifest.
The isolated URL loader and actual system loader both execute JAR-only
payload classes, a ServiceLoader provider and a UTF-8 resource. The isolated
loader also verifies resource enumeration order. NativeMath in native.jar
uses System.loadLibrary to discover a real embedded JNI fixture; its on-load
function queries the actual VM and native calls transfer byte arrays and
verify arithmetic/exception behavior. This is resident JNI loading, not
arbitrary external ELF support.

## Reproduce

With the pinned toolchain/dependencies prepared:

```sh
python3 tools/package_java25_jni.py --dependencies
python3 tools/test_java25_dependencies.py
python3 tools/test_java25_system_classpath.py
python3 tools/test_java25_builtin_lookup.py
```

The source retains 33 OpenJDK patches. See validation.json for the matching
ZIP SHA-256 and console scope. This snapshot stays frozen; future changes
belong in ../Development. Minecraft bootstrap, other application dependencies,
external native ELF loading and JIT stability remain unvalidated.
