# Java21 startup probe 01.000.001

The standalone native test title is **PPSA99877**, separate from Java17 PPSA99876
and ProsperoCraft. Its four ordered rows initialize the matched native core,
create the genuine Java21 VM, execute Java/JNI/worker-thread checks, then destroy
the VM. Use D-pad and X to run each row in order. Report ALL PASS or the first
failed/hanging row. The maintainer reported **ALL PASS** for this exact build on 2026-11-08. See the [console record](validation/java21-startup-001-console-2026-11-08.json).

The local signed package is `dist/PPSA99877.zip`, SHA256
`33598afb949733eedfc328695d4fffcc81091ed46d1ff92654dc3611cc5d2260`.
See the [build record](validation/java21-startup-001-build-2026-11-08.json).
The [passing release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Java21_Startup-v01.000.001) preserves the unchanged package, complete source archive and verified checksums. The [frozen source](https://github.com/mateo-cogeanu/ps5-homebrew-history/tree/2468e3d5034b4c5122e14bf5a461fdc0db27ce0a/runtime/Java21_Startup) records original source commit051cbf7e22583d7c11010710d854685f3fb1e731. No Store publication is involved.

This independently pinned Java21 generation rebases the Java17 bootstrap boundary:
matched core classes/native exports, bounded VM text identity, staged constructors,
PS5 signal context, image paths/properties, interpreter memory/thread/signal
services, disabled unavailable attach/JIT-permission probes, and checked class
image reads. Other-platform defaults and working Java25 integration stay intact.
The probe selects `-Xint`, SerialGC, 128MiB maximum heap and two processors.
C1/C2 are compiled but not exercised; no game, performance, virtual-thread, FFM,
collector, shader or endurance compatibility follows from this startup test.

Actual host Java21 executes the exact probe class/JNI helper with `-Xcheck:jni`
and UBSan, including wrong-class rejection, exceptions and the joined native-call
worker. Actual target JIMAGE code passes ASan/UBSan failure-injection controls;
21's signal accessor matches the SDK layout and target IR. Generated21 registry
checks cover real exports, JNI load errors, scope, VM address bounds and concurrent
error isolation. Target build, ELF ownership, package CRC, matching image bytes,
and native signed-container integrity pass. Host tests do not execute a PS5 VM.

Reproduce with explicit matching dependencies:

```sh
python3 tools/java_lts.py --major 21 --llvm-home /path/to/llvm --build
python3 tools/test_java_lts.py
python3 tools/test_java_lts_startup.py --major 21 --llvm-home /path/to/llvm --boot-jdk /path/to/jdk21
python3 tools/test_java_lts_image_io.py --major 21 --llvm-home /path/to/llvm --boot-jdk /path/to/jdk21
python3 tools/test_java_lts_resident.py --major 21 --llvm-home /path/to/llvm
python3 tools/test_java25_signal_context.py --source-major 21
python3 tools/package_java_lts_probe.py --major 21 --llvm-home /path/to/llvm --lld /path/to/ld.lld --boot-jdk /path/to/jdk21 --work-dir build/java-lts/fresh21
```

Existing package/asset snapshots are preserved rather than overwritten. A matching
class-only image and its adjacent audit must already exist. Java17 remains the
default of the shared tools; explicit21 selects its own pins, cache, class major,
JNI headers, registry identity and title. No runtime generation is mixed.

Private logs use this probe's mounted `download0/java21-startup.log`,
`java21-vm-trace.log`, and `java21-hs-error-%p.log`. It has no inbound server or
preset device address. If a row crashes, reopen this probe once for retained logs.
It performs no Minecraft, account, world or NAS operations.
