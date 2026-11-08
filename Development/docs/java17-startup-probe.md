# Java 17 standalone startup probe 01.000.002

This is the first local hardware candidate for the separate Java 17 port. It uses
title **PPSA99876**, distinct from ProsperoCraft, and has no Minecraft, account,
world, shader, mod or NAS operations. It does not replace the Java 25 launcher.
No physical-console result or release approval has been recorded.

The signed local package is `dist/PPSA99876.zip` (about 25 MiB), SHA-256
`c2241e10bb8c0cb895c7fc02a8490cdd50b2be670e54bc561c90e98c43776c29`.
The [build record](validation/java17-startup-002-build-2026-11-08.json) identifies
its matching symbols, source/patches, native object groups and scoped checks.
Compiled packages and raw reports remain local; no GitHub release or Store action.

## Console check

Install the separate **Java17 Startup - DEV TEST** title with the normal native
title-folder workflow. Run the four rows in order with D-pad and X, one at a time:

1. Initialize the embedded Java 17 core constructors.
2. Create the genuine VM in interpreter mode with a 128 MiB maximum test heap.
3. Run Java arithmetic, UTF-16 strings, original StrictMath, a caught Java
   exception, registered JNI calls and a joined Java worker thread.
4. Destroy the VM cleanly.

Report the first failed or hanging row, or all four results for this exact build.
If it crashes, reopen this same probe and leave it open when retrieving its
private reports. The title writes `java17-startup.log` and
`java17-vm-trace.log` to its own mounted `download0`; HotSpot fatal errors use
`java17-hs-error-%p.log`. It has no inbound server, fixed console address or
client-IP filter. A failed VM creation is not retried within the same process.

The probe deliberately uses `-Xint`, Serial GC, two active processors and a small
heap. This establishes a bootstrap test boundary, not production game settings.
C2 is present in the target VM but is not exercised. No Java 17 performance or
collector advantage is inferred. Java 21 still has only the earlier cross-build
baseline; it has not received this startup integration.

## Startup adaptations

The reviewed Java 17 patch now includes:

- Actual packaged runtime home/library paths under `/app0/assets/java17`, and
  explicit native launcher options rather than desktop VM-option environment files.
- OS-visible processor query and the actual direct-memory-size query. The latter
  is not advertised as a title's free-memory quota. Commit changes protections on
  an owned reservation rather than replacing it with another fixed mapping.
- The existing runtime-owned PS5 register-context view, including the floating-point
  save area. The original kernel context pointer remains intact. With explicit
  AVX disablement the generated CPU probe skips its deliberate SIMD fault test.
- Native PS5 identity, UTF-8/default locale and sandbox user/tmp properties, with
  Java property overrides still supported. Unsupported OS version stays unknown.
- Immutable packaged core-image identity after opening the real JIMAGE file,
  descriptor-based length, bounded/retried reads and anonymous read-only image
  copies with checked page rounding and paired cleanup.
- A minimal allocation-free VM checkpoint writer preserving errno.

All other platforms retain their original branches. The working Java 25 source,
objects, renderer defaults and resident registry remain unchanged. The existing
signal regression runner gains an explicit `--source-major 17`; its default25
fixture/target IR still passes.

The new resident builder merges only matching Java 17 objects and its original
fdlibm implementation, stages real native constructors and generates exports from
actual symbols. JNI load functions remain library-owned; no arbitrary ELF loader
or implementation stubs are added. `dladdr` accepts only the linker-bounded actual
VM code range. The copied SDK libc omits its payload-side memory object; original
SDK archives are preserved. Optional weak callbacks retain absent/null semantics.

## Reproduction and scoped tests

Build the reviewed target and class image as described in
[the LTS runtime guide](java-lts-runtimes.md). An existing class image can be reused
when its audit matches. The probe packages matching compiled natives separately.
Use explicit paths to LLVM and a runnable host Java 17 JDK:

```sh
python3 tools/java_lts.py --major 17 --llvm-home /path/to/llvm --build
python3 tools/test_java_lts.py
python3 tools/test_java_lts_startup.py --llvm-home /path/to/llvm --boot-jdk /path/to/jdk17
python3 tools/test_java_lts_image_io.py --llvm-home /path/to/llvm --boot-jdk /path/to/jdk17
python3 tools/test_java_lts_resident.py --llvm-home /path/to/llvm
python3 tools/test_java25_signal_context.py --source-major 17
python3 tools/test_java25_signal_context.py
python3 tools/package_java_lts_probe.py --llvm-home /path/to/llvm --lld /path/to/ld.lld --boot-jdk /path/to/jdk17 --work-dir build/java-lts/new-probe-work
```

The package builder preserves an existing signed candidate and refuses an existing
asset snapshot. Increment the probe version before replacing a completed package.
It verifies core image bytes, metadata, CRC, actual JNI functions, VM text-range
ownership and constructor staging, then records checksums and preserved symbols.
Native conversion/signature integrity checks also pass for the app and companion.

The exact JNI/Java check runs successfully on an actual host Java 17 VM with
`-Xint`/`-Xcheck:jni` and native UBSan. The JIMAGE OS implementation is tested under
ASan/UBSan with short reads, EINTR, offset/size bounds, failed mapping/protection/
reads and truncation cleanup. Generated registry code passes real export lookup,
scope/error/load/close, address-range and 16-thread/16,000-lookup controls under
ASan/UBSan. Its source-only outside-root fixture needs no SDK/JDK/game cache.
Register fixtures check pinned SDK/captured offsets, restricted RIP writes and
target IR. These tests do not execute the PS5 kernel, a target VM or graphics.

Local untested 001 remains retained as superseded. A final audit found its one
remaining SDK-offset floating-point context member before hardware testing;002
routes that member through the actual PS5 view too. The first handoff is002.
No frozen milestone is created until exact-build console acceptance.
