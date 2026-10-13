# Java 25 on native PS5 homebrew

Target: Minecraft Java Edition, Minecraft server, Fabric/Forge compatibility,
and eventually accelerated OpenGL or Vulkan rendering. The user has confirmed
that the native Interface Lab 01.001.002 works on firmware 13.60 with their
existing loader. This is a separate port project; a working menu does not
establish that a JVM or Minecraft can run.

## Current deliverable

`dist/PPSA99862.zip` contains a separate **Java 25 Platform Probe** title folder.
Extract it and register `PPSA99862` through the same folder workflow as Interface
Lab. Its title ID differs from Interface Lab's `PPSA99861`.

Use D-pad up/down to select a test and X to run it. Run from top to bottom,
one at a time. Each test runs once per launch. Photograph the results, including
the hexadecimal failure codes. If the console crashes, report which test was
selected and whether its RUN status appeared. Exit using the PS menu.

| Probe | What PASS establishes | What remains untested |
| --- | --- | --- |
| Clock | Monotonic clock advances after a short sleep | Timing accuracy under load |
| Memory | Reserve 64 MiB, commit/write 16 KiB, release | JVM-sized heaps, decommit, protection faults |
| Thread | Create/join one thread, mutex, thread-local storage | Signals, safepoints, condition variables, many threads |
| Socket | TCP socket can bind/listen on loopback | Accept/connect, LAN reachability, Minecraft protocol |
| Files | Exclusive temporary file write/read/delete in `/download0` | World saves, durability, other mount permissions |
| Executable page | Change one mapping from RW to RX | Execution, JIT allocation policy, dual mappings |

The last test executes no generated code. A PASS does not prove HotSpot JIT
support. The filesystem probe will not overwrite an existing file; if a crash
leaves `/download0/.java25-platform-probe.tmp`, remove that probe file before
retesting. A thread timeout retains its resources until the application exits
so a late worker cannot access destroyed synchronization objects.

Build with `make java25-probe`. The native package tool checks its container
and clean-room runtime integrity. The actual probe interface was also rendered
on the host with the large-allocation regression guard. These are host checks;
The user reported **all six tests PASS on PS5 firmware 13.60 on 2026-10-11**.
The reported results and their limits are recorded in `console-results.json`.

## Source and bootstrap build

[FreeBSD's OpenJDK fork](https://github.com/freebsd/openjdk) is pinned in
`upstream.json` to `jdk-25.0.4+7-freebsd-1`, commit
`b219cdec88ca2e165711f63b8158ab78303facc8`. Source is cached in
`.tools/java25/openjdk`, approximately 1 GiB. Preserve its upstream license
and per-file notices when distributing a port.

```sh
python3 tools/java25_source.py
python3 tools/java25_source.py --configure
python3 tools/java25_source.py --build-hotspot
python3 tools/java25_source.py --build-base
```

The second command retains the original diagnostic and exits with an error. It uses
the FreeBSD configure target with the community PS5 compiler, a macOS host
boot JDK, and the server VM configuration. Compiler checks pass; configure
stops because ALSA headers are absent. Headless mode still configures desktop
audio dependencies.

The bootstrap commands apply seventeen tracked patches under `patches/` and use an
explicit `--enable-ps5-bootstrap` configuration. This excludes desktop library
requirements; the script builds only the scoped HotSpot and java.base targets,
it is not suitable for building a full desktop JDK image. Host Mac SDK paths
are kept separate from PS5 paths. The C-driver wrapper routes C++ compilations
through the SDK C++ driver to preserve libc++ header ordering. DTrace is disabled.

**HotSpot now compiles and links successfully**: all 1,135 source objects built
for the PS5 target, producing a roughly 31 MiB `libjvm.so` with
`JNI_CreateJavaVM`, `JNI_GetCreatedJavaVMs`, and `JNI_GetDefaultJavaVMInitArgs`
exports. JVMTI remains enabled. Unsupported system-uptime and loaded-module
diagnostics report unavailable; external attach sockets are disabled because
the SDK lacks `getpeereid`. These restrictions avoid fake implementations of
absent APIs.

This is a build artifact, **not a runnable PS5 Java distribution**. Its SDK
linker uses a payload-oriented ELF layout and imports `libkernel_web.sprx`,
`libSceLibcInternal.sprx`, and `libSceNet.sprx`. Native module conversion,
dynamic loading hooks, initialization, writable/executable mappings, and OS
startup assumptions still need adaptation and console validation.

`java.base-java java.base-libs` also builds successfully: the core classes
have Java 25 class-file major version 69, and nine supporting native libraries
link alongside HotSpot. The missing SDK `getline` dependency is replaced by
length-only stream reading for the NIO helper. A non-reaping child-process wait
throws `UnsupportedOperationException` instead of calling the unavailable
`waitid` API; process spawning and waiting are not validated on the console.
Run `python3 tools/java25_audit.py` to record library hashes, JNI exports,
class format, dependencies and ELF inspection warnings in
`build/java25/artifact-audit.json`. Passing this audit establishes build
properties, not runtime functionality.

## Second console probe

`make java25-runtime-probe` builds **Java 25 Runtime Probe**, a new `PPSA99863`
folder in `dist/PPSA99863.zip`. It uses the same native interface and leaves
both earlier titles available. D-pad selects; X runs one test per launch.

1. Report the OS page size (include the value in your results).
2. Wake a timed condition-variable wait from a worker, then join it.
3. Install an `SA_SIGINFO` handler, send SIGUSR1 to this process and restore
   the previous signal handler/mask. A timeout retains the harmless handler
   in case delivery is delayed. This does not test SIGSEGV recovery or safepoints.
4. Allocate RW memory, write six x86-64 bytes (`mov eax,25; ret`), change the
   mapping to RX, call it, check the return value and release it. This tests
   actual generated-code execution, not a complete Java JIT.

Run from top to bottom and report the result screen and any crash at RUN.
The package's container/runtime integrity passes. All four tests also pass in
the x86 macOS host fixture `tools/test_java25_runtime.cpp`, including executing
the tiny generated function. The actual interface was previewed with the
large-allocation guard. **The user reported all four second-probe tests PASS
on PS5 on 2026-10-11.** The numeric page size was not supplied, so it remains
unspecified in the results record. This confirms the tiny generated function
executed; HotSpot JIT, fault recovery and safepoints remain untested.

## Embedded HotSpot setup probe

`make java25-jni-probe` builds **Java 25 Embedded HotSpot**, `PPSA99864`, using
the real compiled JVM object files. `dist/PPSA99864.zip` is a separate native
application folder. Its executable is about 21 MiB; this is materially larger
than the OS probes because it contains HotSpot code.

The native converter currently does not publish application exports, which
prevents using it directly for a dynamically loaded `libjvm` module. This
probe instead embeds all 1,135 HotSpot objects in the native executable,
links the SDK support archives, and uses the proven native app startup.
HotSpot's 358 constructors are relocated into a separate RELRO range and run
only on the first selected test, after RUN appears. Application startup runs
zero static constructors. SDK optional weak callbacks are explicitly bound
to their normal absent/NULL state; dynamic loading is not implemented by
this probe. Strong imports still must resolve through the public SDK stubs.

Run the three tests in order with D-pad and X:

1. Initialize the real embedded HotSpot static constructors.
2. Call the real `JNI_GetDefaultJavaVMInitArgs` function. The latest JNI API
   constant in this pinned JDK 25 is `JNI_VERSION_24`; JNI API numbering does
   not advance for every Java release.
3. Call `JNI_GetCreatedJavaVMs` and require zero VMs, since this probe does not
   call `JNI_CreateJavaVM`.

Report the results, including any crash before the UI or at a RUN stage.
Passing this probe establishes embedded runtime initialization and setup API
calls, **not VM startup or Java execution**. Its container integrity, actual
JNI definitions, delayed constructor range and absent callbacks are checked
on the host. The host image preview uses synthetic JNI stubs only for layout,
and is not evidence that the real PS5 JVM works. Build evidence is saved in
`build/java25/jni-package-audit.json`. Upstream OpenJDK license and source
notices are included in the package. **The user reported all three embedded
HotSpot setup tests PASS on PS5 on 2026-10-11.** VM creation and Java bytecode
execution were not attempted by that probe.

## First VM creation / Hello25 attempt

`make java25-startup` builds **Java 25 VM Startup**, a separate `PPSA99865`
title in `dist/PPSA99865.zip`. This app attempts real VM creation and Java
execution. Both are **pending console validation**, not reported as working.

It embeds the target-built HotSpot and five core native libraries (`java`,
`zip`, `jimage`, `net`, `nio`). A generated lookup table binds 932 names to
their actual compiled function addresses. The SDK's optional `__dlopen`,
`__dlsym`, `__dladdr`, `__dlclose`, and `__dlerror` callbacks now have real
embedded-library adapters instead of NULL. This dispatch is specific to the
resident core libraries; arbitrary ELF modules and external JNI mods remain
unsupported. Library-specific JNI load/unload entry points and libjava's
formatting helpers are renamed during object merging to preserve their
separate desktop-library identities. Core-library constructors remain delayed
until the first on-screen stage (359 entries in this build).

`tools/java25_boot_image.py` generates a classes/resources-only image from
the cross-built FreeBSD/PS5 `java.base`. Stock host jlink rejects the BSD
target tag, so its temporary JMOD uses an accepted `linux-amd64` transport
tag. The input classes/resources are still the PS5 build, and **no Linux or
host native binaries enter this image**. Target-native code is packaged
separately. The final release metadata identifies the experimental FreeBSD
PS5 runtime. This workaround and its limits are recorded in the packaged
`boot-image-audit.json`; the image has not been verified by a running PS5 VM.

Use D-pad and X to run these stages in order, once per launch:

1. Initialize the embedded runtime and open the persistent diagnostic log.
2. Call the real `JNI_CreateJavaVM`: interpreter mode (`-Xint`), Serial GC,
   16 MiB initial / 128 MiB maximum heap, CDS and performance data disabled.
3. Find and invoke `Hello25.main`. It requires runtime version 25, verifies
   the arithmetic result, and starts/joins a Java worker thread. A PASS means
   the Java method returned without throwing an exception.
4. Call the real `DestroyJavaVM` and return to the native UI.

Startup diagnostics are appended and flushed to
`/download0/java25-startup.log`; fatal-error files use
`/download0/hs_err_java25_%p.log`. If the app closes or crashes, relaunch it and
photograph the previous log line displayed on the interface, plus identify
the selected stage. If it hangs at RUN, report that stage. A failed stage
cannot be retried within that launch. Java's normal stdout/stderr may still
go to the platform's console streams; the startup log hook captures VM
diagnostics and explicit stage records.

The package passes container integrity, delayed-constructor, actual JNI/core
symbol, core-image-content and ZIP checks on the host. The library lookup
contracts were exercised with synthetic host addresses; those checks do not
run the target JVM. The UI was rendered with synthetic JNI stubs for layout
only. Host build evidence is in `build/java25/startup-package-audit.json`.

### Startup 01.000.001: distinguish file checks from VM failure

The user reported PASS / FAIL / FAIL / FAIL on 01.000.000, with code
`00000001` for the failed creation stage. The exact message/log was not
supplied. The original preflight `access(R_OK)` could return this positive
errno before `JNI_CreateJavaVM` is called; the source's normal JNI errors
are negative. A file-permission preflight failure is therefore suspected,
not confirmed.

Version 01.000.001 replaces `access()` with opening and reading the packaged
core image and checking its JIMAGE magic. It distinguishes fopen/read/header
errors with "Before JVM" messages and persistent log entries. This checks
actual readability rather than bypassing a failed file operation. If VM
creation cannot proceed or fails, the two dependent stages automatically
show SKIP. The current log's last line is refreshed on screen immediately.
The JVM itself is unchanged in this update. Retest stages 1 and 2 and report
the complete creation-stage message and code if it fails.

### Startup 01.000.002: checkpoints inside HotSpot

The user reported a stage-2 crash in 01.000.001. After relaunch, the last
startup log was `STAGE: Calling real JNI_CreateJavaVM`. This establishes that
the packaged image open/read/header check completed and the application
entered the JVM call. The exact failing internal operation is still unknown.

Patch `0009-ps5-vm-startup-breadcrumbs.patch` records checkpoints inside the
real JNI entry and VM initialization. It brackets CPU initialization, TLS,
output streams, BSD/OS setup, core library paths, JDK version lookup, argument
parsing, signals, safepoints, stack discovery/guards, heap/global setup and
Java system initialization. It also records the stdout/stderr flushes before
returning from the JNI startup call. No initialization step is bypassed.

Checkpoints append directly using open/write/close to
`/download0/java25-vm-trace.log`, avoiding stdio and JVM allocation/locks.
The app verifies that this raw trace file can be opened and written before
calling JNI. The trace is reset at each actual startup attempt; on relaunch,
its final nonempty line takes precedence over the broader startup log.
Tracing failure inside the JVM is best-effort and does not change its return
value. The checkpoint helper passes host tests for interrupted/partial writes,
append behavior and a denied open; this is not PS5 execution evidence.

Replace the PPSA99865 folder with version 01.000.002, run stages 1 and 2,
then relaunch after a crash and report **Last startup checkpoint**. An ENTER
line identifies the next operation attempted; a DONE line means that operation
returned, not that all later VM initialization succeeded. This release is a
diagnostic build; it does not claim to fix the crash.

### Startup 01.000.003: explicit embedded runtime paths

The user reported the checkpoint matching `ENTER: System properties and core
library paths` in 01.000.002. VM startup therefore reached
`Arguments::init_system_properties`; it did not reach the following DONE
checkpoint. The failing operation inside that stage is not yet established.

Patch `0010-ps5-embedded-runtime-paths.patch` gives the native PS5 build its
explicit packaged Java home (`/app0/assets/java25`) and core/library directory
(`/app0/assets/java25/lib`). It keeps the normal boot-image stat/path
validation and reports failure rather than skipping it. The legacy desktop
extension path is empty. `os::jvm_path` also identifies the actual packaged
library directly for this embedded build, without desktop shared-object
discovery or a `realpath` call using a NULL output buffer. This is an embedded
port adaptation; it does not establish which old call triggered the crash.

Additional checkpoints distinguish boot-path allocation, VM identity/property
construction, the property list, PS5 core-library directory, Java home and
boot-image validation. HotSpot and the native package rebuild successfully.
Console validation of this change is pending. Run stages 1 and 2; after any
crash, relaunch and report the last checkpoint again.

### Startup 01.000.004: launcher options and image-loading checkpoints

The user reported `ENTER: VM argument parsing` after the path adaptation.
System-property initialization, JDK core-library version lookup and logging
initialization therefore returned. The failing operation within argument
parsing remains unknown.

Patch `0011-ps5-explicit-launcher-options.patch` makes the native bootstrap's
option sources explicit: the JNI launcher's options and any options resource
inside the core image. Desktop `JAVA_TOOL_OPTIONS`, `_JAVA_OPTIONS` and
`JDK_AOT_VM_OPTIONS` injection is disabled for PS5. This is a bootstrap
configuration restriction, not proof that getenv caused the crash. Supplied
JNI options are still parsed normally, with unknown options rejected.

New checkpoints cover flag declarations, option sources, loading/binding
libjimage, `JIMAGE_Open`, the embedded options-resource lookup, option
expansion, settings-file checks and applying each individual option. This
distinguishes parser failure from image-loading/native-binding failure.
The existing heap, interpreter and GC options also run Hello25 successfully
on the host JDK 25; that validates the option syntax, not PS5 compatibility.
Console validation of 01.000.004 remains pending. Retry stages 1 and 2 and
report the checkpoint after relaunch if it crashes.

### Startup 01.000.005: module image reader and mapping fallback

The user reported `ENTER: Real JIMAGE_Open on packaged modules`. The native
binding step returned; the current failure is inside the actual image reader.
It has not yet been localized to its mutex, allocation, file operations or
mapping code.

Patch `0012-ps5-jimage-mapping-and-checkpoints.patch` adds checkpoints around
the reader cache/mutex, reader allocation, file open/size, header validation,
memory mapping, module metadata and reader-table insertion. A mapping failure
now returns an explicit open failure rather than relying solely on an assertion
that is disabled in the release build. A failed reader-table allocation also
has an explicit diagnostic before terminating rather than a NULL write.

If file-backed mapping is rejected on PS5, the reader now tries anonymous RW
memory, copies the requested image range with bounded pread calls (handling
EINTR/partial reads), then changes it to read-only. Mapping ownership and
munmap cleanup remain unchanged. Any anonymous allocation, copy or protection
failure is reported and cleaned up; none is treated as success. Direct file
mapping is still attempted first. File mapping has not been proven to be the
current console failure.

`python3 tools/test_jimage_host.py` compiles the actual patched reader on the
Mac and exercises direct mapping, forced anonymous fallback and rejection of
both mapping methods. Both successful paths read the real packaged
`java/lang/Object.class` and verify Java 25 major version 69. These host
component tests pass; the PS5 target library also rebuilds successfully.
They do not establish console JVM startup. Retry stages 1 and 2 in 01.000.005
and report the checkpoint after relaunch if it crashes.

### Startup 01.000.006: direct anonymous image copy on PS5

The user reported `ENTER: JIMAGE memory mapping`. File opening, size retrieval
and header validation had returned. The reader had entered its mapping path,
whose first operation was file-backed mmap; it did not return to the DONE
checkpoint. The exact fault inside that operation remains unverified.

Patch `0013-ps5-jimage-direct-anonymous-copy.patch` removes the file-backed
mapping attempt from the PS5 image reader. It now allocates anonymous RW
memory directly, reads the image into it and changes the range to read-only.
The same length/offset, read, protection and cleanup checks from the fallback
are retained. Other platforms retain their file-backed mapping behavior.
New checkpoints separate anonymous allocation, the copy and read-only
protection so a subsequent failure is identifiable.

The actual patched reader passes host tests reopening the packaged image,
reading Java 25 Object.class and rejecting failed anonymous allocation.
The harness explicitly verifies **zero file-backed mmap calls** for this
PS5 branch. The target core library and native package also build successfully.
Console startup remains pending; retry stages 1 and 2 and send the last
checkpoint after relaunch if it crashes.

### Startup 01.000.007: native memory imports and aligned image allocation

The user reported `ENTER: JIMAGE anonymous allocation`. Inspection of the
actual SDK archive and linked executable found a significant binding mismatch:
`libc.a(mman.o)` defines mmap using a raw syscall and mprotect using the SDK's
kernel_mprotect callback. The early successful OS probes did not link this
archive; they called imported platform memory functions. This is a confirmed
source/link difference, not a console crash-stack diagnosis.

The packager now copies the SDK libc archive into build/java25/native-libc.a
and removes only mman.o from that copy. The installed SDK remains intact.
All embedded memory callers now resolve mmap/mprotect through public platform
imports, consistent with the tested native probes. The package audit requires
both functions to remain undefined dynamic imports and rejects an embedded
payload implementation.

Patch `0014-ps5-jimage-native-allocation-size.patch` also obtains the readable
image length through open/lseek/close, avoiding dependence on stat field
layout for sizing. Anonymous allocation, mprotect and cleanup use a length
rounded to the runtime page size with overflow checks. Only the exact image
bytes are read. The trace records the requested/aligned lengths before the
native allocation call. Host tests of the actual reader still pass; console
validation of the changed memory binding remains pending. Retest stages 1
and 2 in 01.000.007 and report the checkpoint after any crash.

### Startup 01.000.008: global initialization and memory diagnostics

The user reported `ENTER: VM stubs heap and globals`. The creation path had
returned from image loading, argument parsing, early JavaThread/stack setup
and guard-page setup before entering `init_globals`. The failing operation
inside that function is not yet established; Java execution remains unproven.

Patch `0015-ps5-global-init-and-memory-checkpoints.patch` brackets each global
initialization subsystem: management/JVMTI storage, bytecode/class loading,
code cache, CPU version probing, initial machine-code and stack-overflow stubs,
the universe/heap, GC and continuation stubs, interpreter entries and runtime
adapters. Native reserve/commit checkpoints report addresses, byte counts,
permission/flag values and errno on failure. No memory operation or protection
policy is bypassed by this diagnostic patch.

The trace helper now preserves errno across successful and failed diagnostic
IO, including stack-only memory-detail formatting. Its host tests pass for
interrupted/partial writes, append, denied open, numeric memory fields and
errno preservation. The actual image-reader tests still pass, and the target
HotSpot/core libraries and native package build successfully. Console testing
of this diagnostic release remains pending. Retry stages 1 and 2 and report
the last checkpoint after relaunch if startup fails.

### Startup 01.000.009: bootstrap image identity and phase-one diagnostics

The user reported the checkpoint matching `ENTER: Class loader phase 1`.
Management/JVMTI storage and bytecode table initialization returned; code cache,
CPU executable probing and universe/heap initialization had not been reached.
The exact failing operation in class-loader phase one remains unknown.

Patch `0016-ps5-bootstrap-image-path-identity.patch` adds checkpoints around
the exception/thread context, ClassLoader body, Java path-helper binding,
bootstrap ResourceMark/path-stream construction, image stat, path identity
and ClassPathImageEntry allocation. For the exact fixed packaged
`/app0/assets/java25/lib/modules` path, whose file was already opened and
validated by JIMAGE_Open, the reader retains that absolute identity rather
than calling desktop realpath-based canonicalization again. Other paths
still use normal canonicalization. A missing canonical identity now fails
explicitly instead of relying on a release-disabled assertion.

The target JVM and package build successfully. This adaptation has not been
confirmed as the cause or fix for the phase-one crash. Retry stages 1 and 2
in 01.000.009 and report the final checkpoint after relaunch if it fails.

### Startup 01.000.010: conservative CPU bootstrap and stub checkpoints

The user reported the checkpoint for `CPU version and executable detection
stubs`. Class-loader phase one, compilation policy and code-cache
initialization returned. CPU version initialization entered; its exact failing
operation has not yet been established.

The x86 CPU-info stub contains a deliberate null-reference SIGSEGV test for
AVX register restoration after signal handling. Ordinary SIGUSR1 delivery was
validated by the earlier console probe, but fault recovery and vector-state
restoration were not. This test is a suspected failure point, not a crash-stack
diagnosis.

The launcher now explicitly requests `-XX:UseAVX=0 -XX:UseSSE=2` alongside
interpreter mode. Patch `0017-ps5-conservative-cpu-bootstrap.patch` emits a
jump around the deliberate SIMD fault probe on PS5 only when AVX is explicitly
disabled. CPUID feature discovery still runs. The existing feature-selection
logic clears AVX/AVX2/AVX512 from the VM's usable feature set in this mode; the
port does not claim those vector features or signal recovery work. AVX-enabled
modes retain the original probe and remain unvalidated. This is a conservative
bootstrap configuration, not the intended final Minecraft performance profile.

Checkpoints now separate CPU ResourceMark, code-blob allocation, assembler
setup, CPU-info code generation, helper-stub generation, generated-stub
execution, feature processing and virtualization checks. The target JVM and
native package rebuild successfully. The new x86-specific options are not
validated by the ARM host JVM smoke test. Console validation remains pending;
retry stages 1 and 2 in 01.000.010 and report the last checkpoint on failure.

### Startup 01.000.011: smaller class-space reservation

The console photograph from 01.000.010 shows:
`FAIL: Native memory reserve addr=ffffffffffffffff bytes=1090519040 mode=4098 errno=12`.
This is a failed 1 GiB + 16 MiB reservation. HotSpot defaults
`CompressedClassSpaceSize` to 1 GiB, and its aligned reservation fallback
allocates the requested size plus alignment. The size matches class-space
reservation, although the checkpoint does not identify the allocation tag.
It does not establish that the console has exhausted physical RAM.

The launcher now requests `-XX:CompressedClassSpaceSize=32m`. This limits the
reserved range for compressed class metadata while retaining `-Xms16m
-Xmx128m`, Serial GC and the conservative CPU settings. This is a bootstrap
test budget; Minecraft and large mod sets need separate memory sizing tests.
No HotSpot source change is needed for this option. The native package builds
and passes integrity, ZIP, version and embedded-option checks. Host Java 25
runs Hello25 successfully with the 32 MiB class-space and 128 MiB heap limits;
this does not validate PS5 execution or the x86-specific CPU options.
VM startup and Java bytecode
execution still require console validation. Retry stages 1 and 2; if VM creation
passes, continue with Hello25 and VM shutdown.

### Startup 01.000.012: heap and commit context

The console photo from 01.000.011 ends with a successful native RW commit:
`DONE: Native RW memory commit addr=207170000 bytes=65536 mode=3 errno=0`.
This identifies a completed 64 KiB commit call, not the subsequent failing
operation or successful VM startup. The retained 32 MiB class-space option
avoids repeating the default 1 GiB reservation request.

Patch `0018-ps5-heap-and-commit-checkpoints.patch` adds checkpoints around
commit tracking, collector heap creation, TLAB setup, metaspace initialization,
commit counters and masks, bootstrap loader data, and symbol/string tables.
These diagnostics do not change allocation behaviour. The launcher now shows
the last three nonempty trace lines, oldest first, so a successful nested call
has context in a console photograph. Retry stages 1 and 2 in 01.000.012.
Console VM startup and Hello25 remain pending.

### Startup 01.000.013: preserve reservations and add menu audio

The user reports `ENTER: Metaspace commit mask` followed by two
`DONE: Metaspace commit mask` lines. The duplicate is recorded as reported;
this does not locate the later fault. VM creation is still unestablished.

Patch `0019-ps5-preserve-native-reservations.patch` changes PS5 RW commitment
from `mmap(MAP_FIXED)` to `mprotect` on the existing anonymous reservation.
This uses the protection-change mechanism previously exercised by the console
platform probe and avoids replacing the owned mapping. Other platforms retain
the original mmap commit path. Decommit retains its fresh anonymous PROT_NONE
mapping, so subsequent recommit does not retain the discarded data. This is a
candidate platform adaptation, not a confirmed explanation of the crash.
Chunk commit-boundary traces and signal number/PC/fault-address checkpoints
preserve more context without changing HotSpot signal recovery decisions.
Fault tracing uses fixed stack formatting and raw file writes; fault-handler
execution on this console still needs validation.

The startup title now plays `sounds/menu_music.wav` in a loop at 50% PCM
amplitude, mixing `sounds/sel.wav` at full amplitude on navigation or test
activation. Packaging converts both original 44.1 kHz stereo WAVs to 48 kHz
stereo signed 16-bit PCM using ffmpeg, preserving the supplied originals.
`desel.wav` remains unused. A dedicated pthread streams and mixes 256-frame
grains through the native AudioOut imports. Read/decode work does not run on
the controller thread. Selection effects restart on a new selection; the mixed
output saturates at the signed 16-bit limits. Audio errors do not prevent VM
testing, and an error code appears on screen. Normal UI shutdown stops and
joins the audio worker and closes its files and port. Forced console closure
is handled by the OS.

The real audio worker passes a host test with a synthetic AudioOut sink:
stereo format/grain settings, music gain, looping, effect mixing, clipping and
shutdown. This is not evidence of PS5 audio playback. Retry tests 1 and 2;
photograph the last three checkpoints after any crash. If VM creation passes,
continue with Hello25 and controlled VM destruction.

### Startup 01.000.014: audio setup and usable fault context

The console photo from 01.000.013 reports audio error `80260011` and
signal 11 at PC `0x8000751d0`, fault address `0x100026c946`.
That version did not record which audio call failed or the app load address.
Subtracting an assumed base from the PC does not give a trustworthy symbol;
the PC could also be in generated code. No JVM crash fix is established.

Audio now initializes and opens on the main thread, before its streaming
worker, and opens for SYSTEM user `0xff`. This follows the
[PS5 SDL audio backend](https://github.com/ps5-payload-dev/SDL/blob/release-2.30.x-ps5/src/audio/ps5/SDL_ps5audio.c),
which initializes before its output thread and opens the SYSTEM MAIN port.
Music still loops at 50% amplitude; navigation/test activation still plays
sel.wav; desel.wav remains unused. On failure the UI names the failing call.
`/download0/java25-audio.log` records init/open/output results independently
of the VM trace. The synthetic host sink verifies the setup thread and system
user, distinguishes init/open failures, and verifies streaming/mixing/shutdown.
Console sound playback still requires a retest.

Patch `0020-ps5-fault-stage-and-image-anchor.patch` remembers the latest
non-signal startup milestone and re-emits it immediately before fault details.
It also logs the loaded address of the actual HotSpot signal-handler function.
The UI shows five lines: preceding stage, handler anchor, signal, PC and fault
address. The anchor can be compared to the retained ELF symbol file to locate
faults in the app image; generated code faults still need further inspection.
Fault recovery behaviour is unchanged. Target build and trace-helper tests
pass, including preservation of the stage through signal hex logging.

Retry tests 1 and 2 in 01.000.014 and photograph all five trace lines on failure.
The full startup and VM trace logs remain useful for locating the stage.

### Startup 01.000.015: quieter mix and metadata context

The user confirms menu audio works on the PS5 in 01.000.014. At their request,
01.000.015 reduces music from 50% to 35% PCM amplitude and selection effects
from 100% to 70%. The streaming/mixing host test now checks the quieter gains
and still passes system-user setup, error stages, looping and shutdown.

The photographed VM stage is `DONE: Metachunk commit boundary`, followed by
signal 11, PC `0x8000751d0` and fault address `0x100026c946`.
The handler anchor reads `0xded450`; the retained 01.000.014 symbol is
`0x9ed450`, consistent with an app load base of `0x400000`. On that inference,
the fault PC is outside the app text and could belong to a platform module
or generated code. It does not identify a specific failing function.

Patch `0021-ps5-metadata-allocation-context.patch` records the outer metadata
allocation, its returned pointer and requested byte count, then traces the
zero-initialization call. Allocation behaviour and signal recovery are
unchanged. This build adds diagnostics, not a confirmed JVM crash fix.
Console VM creation and Hello25 still require validation.

### Startup 01.000.016: sound effects disabled

At the user's request, selection effects are disabled until replacement sounds
are ready. Navigation and activation remain silent; music stays at 35%.
The audio worker no longer opens the selection file, so disabled effects cannot
prevent music playback. The supplied WAV files remain available for later use.
VM behaviour and metadata diagnostics are retained from 01.000.015.

### Startup 01.000.017: address searches must preserve existing mappings

IMG_0409.JPG shows `DONE: Metadata zeroing` followed by the same signal 11
at PC `0x8000751d0`, fault address `0x100026c946`. This confirms a zeroing
call returned, not VM creation. The header version is cropped; the latest
supplied title was 01.000.016.

The BSD reservation helper adds `MAP_FIXED | MAP_EXCL` when given a hint,
expecting the kernel to reject overlap. The SDK exposes MAP_EXCL, but the
console's handling of that flag has not been established. If it is ignored,
a compressed heap/class-space address search can replace an earlier JIMAGE,
heap or other mapping with PROT_NONE memory. This is a concrete source risk,
not proof that it caused this fault or that the console ignores MAP_EXCL.

Patch `0022-ps5-nondestructive-address-hints.patch` excludes PS5 from the
MAP_FIXED/MAP_EXCL optimization. Hints now retain only non-fixed anonymous
mapping flags. If the kernel returns a different location, the existing BSD
caller releases that new mapping and treats the attempt as unsuccessful;
it never releases the preexisting occupied range. Normal reservation fallbacks
remain available. Deliberate commits/decommits of owned memory are unchanged.

`tools/test_java25_address_hints.py` extracts the actual patched anon_mmap
function and runs it on the host with a shim that ignores MAP_EXCL. It checks
that an occupied RW mapping retains every marker byte and that the request
never uses MAP_FIXED. This host regression, the actual patched JIMAGE reader
(Object.class major 69), and target HotSpot build pass. Console VM startup
still needs a retry of tests 1 and 2; continue through Hello25 and DestroyJavaVM
only after creation succeeds. Music remains 35%; effects remain disabled.

### Startup 01.000.018: identify the native call at the fault

IMG_0410.JPG repeats `DONE: Metadata zeroing`, signal 11 at
`0x8000751d0`, fault address `0x100026c946`. The nondestructive reservation
change did not resolve the fault. MAP_EXCL remains an unverified console
capability; its removal is not evidence of the crash's root cause.

Patch `0023-ps5-native-fault-call-context.patch` adds the saved RDI, RSI and RDX
registers and three words at the saved stack pointer. Stack reads occur only
when the JavaThread is available and the whole range falls inside its recorded
stack bounds, with integer overflow checked. They are stack candidates, not
an asserted backtrace. Saved argument registers can have been modified inside
a native function; their values must be interpreted alongside the instruction
and a candidate caller. No allocation or stdio formatting is used for the new
context lines, and signal recovery decisions are unchanged.

The launcher displays seven trace lines so the stage, image anchor, signal,
PC, fault address, register values and stack candidates fit one photo. Target
HotSpot builds and the host formatter test passes under AddressSanitizer,
including exact three-value output, preservation of the earlier stage through
signal logging, bounded long labels and preserved errno. Console fault-handler
execution and VM startup remain pending. Retry 1 and 2; after a crash, relaunch
and photograph all seven lines. The retained per-version symbol file can be
used to resolve stack candidates that lie inside the app text.

### Startup 01.000.019: capture native call sites before a fault

IMG_0411.JPG repeats the fault after metadata zeroing; saved RDI/RSI/RDX
and stack candidates all display zero. The stack guard can also produce zero
candidates when no valid JavaThread stack range is available. This is not
proof of bad arguments or of an incorrect signal-context structure.

The startup package now links wrappers for memcpy, memmove, memcmp, strcmp
and strlen. `probe/native_trace.hpp` records the original call site's return
address, input/output pointers and size, then forwards to the original native
function and returns its result. It does not replace those operations with
fake implementations. Tracing runs only on the VM-creation thread while the
actual JNI_CreateJavaVM call is in progress. A recursion guard excludes calls
made by the tracing helper itself. Raw trace writes can make this diagnostic
build slower during startup; it is not a performance configuration.

Patch `0024-ps5-native-call-trace-signal-guard.patch` marks signal-handler
execution so logging does not replace the pending native call's evidence.
The guard restores its earlier value on return. Caller/pointer logging uses
fixed stack formatting and does not depend on the saved signal registers.
The existing signal report and seven-line UI remain available. A host ASan
test exercises all five forwarding operations, exact results, caller/pointer
log fields, and the signal guard. Target HotSpot builds successfully.

Retry 1 and 2 in 01.000.019 and photograph all seven checkpoint lines after
relaunch. A pending CALL line will identify a wrapped native operation;
if no pending CALL is shown, the failure lies elsewhere or after a completed
wrapped call. Only a subsequent console test can establish a JVM startup fix.

### Startup 01.000.020: retain completed-call evidence separately

IMG_0412.JPG still reports the same fault, but the first line is the generic
`DONE: Traced native memory/string call`. The previous diagnostic design
replaced the semantic VM checkpoint with tracing events and did not retain
the caller after a wrapped function returned. This obscured useful evidence.

Patch `0025-ps5-retain-native-call-evidence.patch` adds a separate retained
record: operation label, caller, source/destination pointers, byte count and
whether the function returned. Trace events no longer replace the semantic
startup checkpoint. Diagnostic IO and fault reporting exclude their own
native string/memory calls from capture. The signal report keeps seven lines:
VM stage, handler anchor, signal, PC, fault address, retained call context and
byte-count/completion state. `completed=1` means the retained call returned;
it does not prove that call caused the subsequent fault. `completed=0` is a
pending captured call, subject to the usual limits of asynchronous capture.

The launcher additionally wraps memset, strncmp, strncpy, strchr and memchr,
for ten original forwarding operations. Java execution behaviour is not
replaced with stubs. The same creation-thread and recursion guards apply.
Host ASan tests pass all ten operation results, retained caller/pointer/count
and completion fields, VM-stage preservation, and signal/IO capture exclusion.
Target HotSpot builds successfully. This is a diagnostic repair, not a
confirmed JVM crash fix. Retry tests 1 and 2 and photograph all seven lines.

### Startup 01.000.021: native locale bootstrap adaptation

IMG_0413.JPG retains a completed strlen call, return address `0x116dbb6`,
source `0x8801d3083`, and the same fault. With the inferred `0x400000` app
load base, return offset `0xd6dbb6` resolves to **ParseLocale** in the retained
01.000.020 ELF. Disassembly shows strlen returning, then malloc and strcpy.
The report establishes the locale path; it does not prove which later call
faulted, or that locale parsing is the underlying memory-corruption cause.

Patch `0026-ps5-explicit-bootstrap-locale.patch` makes native PS5 bootstrap
locale defaults explicit: format/display language en, country US, empty script
and variant, UTF-8 encoding. The existing sun.jnu.encoding assignment uses that
UTF-8 value. This avoids desktop BSD setlocale/ParseLocale/native locale tables
on the PS5 path. Other platforms retain their existing parser. These are native
platform defaults, not a stubbed VM; standard Java property overrides remain
available. Console language/region detection is not implemented by this branch.

Target java.base-libs rebuilds successfully. Its compiled properties object
has no ParseLocale or setlocale reference. Host Hello25 passes with en/US and
UTF-8 property overrides, though that host run is not PS5 execution evidence.
Native-call diagnostics now additionally forward/trace strcpy and malloc,
including the allocator's returned pointer. The host ASan test passes all twelve
forwarding operations and record retention. Console VM creation and Hello25
remain pending. Retry tests 1 and 2, then 3 and 4 only if creation succeeds;
on failure, relaunch and photograph all seven lines.

### Startup 01.000.022: explicit native sandbox properties

IMG_0415.JPG reports a completed 11-byte memcpy, return address `0x9cf4b9`,
source `0x203c480e0`, destination `0x203c4b603`. With app base `0x400000`,
offset `0x5cf4b9` resolves to SignatureHandlerLibrary::add after copying JNI
signature-handler bytes. The following operations publish/flush that handler
before native invocation. The same external PC/fault address remains; this
completed copy is not evidence that memcpy failed. Removing ParseLocale did
not resolve the fault.

GetJavaProperties still used desktop BSD uname/passwd structs, tzset and
getcwd/strdup. Patch `0027-ps5-native-sandbox-properties.patch` gives the PS5
bootstrap title explicit native defaults: os.name PS5, os.version unknown,
os.arch from the actual target build, user.name ps5, user.home/java.io.tmpdir
/download0, user.dir /app0. It avoids those unverified desktop discovery
interfaces on PS5; other platforms remain unchanged. These paths reflect the
tested title sandbox. Version unknown is deliberate, rather than an invented
firmware value. User identity/firmware detection is not implemented by this
bootstrap branch. Normal Java property overrides remain available.

The launcher selects user.timezone UTC; native props no longer calls tzset
during early bootstrap. Locale defaults stay en/US/UTF-8. This does not prove
that any of the removed APIs caused the crash. The target java.base build
passes, and the compiled property object has no uname/getpwuid/getcwd/tzset
or strdup dependency. strdup now has a forwarding trace wrapper in case a
later native path fails inside its string allocation. All thirteen wrappers
pass host ASan semantics and retention tests. VM startup still needs console
validation. Retry tests 1 and 2; photograph all seven lines on failure.

### Startup 01.000.023: VM startup passes; define the acceptance class directly

The user reports **PASS PASS FAIL PASS** for 01.000.022: constructor setup,
real JNI_CreateJavaVM and DestroyJavaVM succeed on the console. Hello25 fails
with `FFFFFAE8`, our -1304 FindClass error. This establishes the VM lifecycle;
it does not establish application-class loading, arithmetic or a Java worker
thread. The packaged Hello25.class is present with Java 25 class major 69.
The original Java exception behind FindClass was not supplied.

The bootstrap probe now reads Hello25.class with the already exercised native
fopen path, checks its magic/major format and size (64 KiB probe limit), obtains
the actual Java system class loader, and calls JNI DefineClass with those real
bytes. It then performs the unchanged main/version/arithmetic/thread checks.
This tests application bytecode execution independently of desktop filesystem
class-path discovery. It does not fix ordinary directory/JAR class-path loading;
that remains necessary for Minecraft and mod loaders.

Failure rows now report phase, Java exception.toString text and the numeric
code. The original exception is retained while extracting its text, then its
stack trace is described to the startup log. Extraction failures clear their
secondary exception so the original remains diagnosable. The display truncates
long exception text; the log retains a longer prefix. No Java pass is inferred
from a successful native setup alone.

`tools/test_java25_define_class.cpp` passes against a real host JDK 25 JVM:
FindClass first fails with an intentionally unavailable class path; DefineClass
loads the packaged fixture into the real system loader; main prints THREAD_OK
and HELLO_JAVA_25 49995000; DestroyJavaVM succeeds. This is host integration,
not console execution. Retry tests 1 through 4 in 01.000.023, stopping after a
failed creation. If Hello25 fails, report its row's exception text and code.

### Console milestone: all four tests PASS on 01.000.023

The user reports **ALL PASS** on the PS5: native core setup, real VM creation,
Hello25 Java 25/version/arithmetic/worker-thread checks, and real VM destruction.
The first passing package is preserved at
`dist/PPSA99865-first-java-pass-01.000.023.zip`; the original PPSA99865 title
folder remains intact. This establishes real application-bytecode execution
through JNI DefineClass. It does not establish ordinary directory/JAR discovery,
JIT stability, Minecraft or mod compatibility.

The next separate title is **Java 25 File I/O**, PPSA99866 01.000.000,
built with `python3 tools/package_java25_jni.py --fileio`. It uses the same
VM lifecycle and direct-definition route for FileIO25. Run all four rows;
row three creates a unique file in java.io.tmpdir (/download0), writes and
reads UTF-8 bytes containing accented text, Japanese and an emoji, verifies
byte equality and size, deletes the file, and confirms it is absent. It uses
Java Files APIs, not a native substitute. CREATE_NEW prevents overwriting an
existing file. After an error or console crash, a uniquely named probe file
may remain for diagnosis.

FileIO25 passes on the host interpreter with the same fixture and a workspace
temporary directory, printing JAVA_FILE_IO_OK. Target packaging/integrity is
verified; its console result is pending. Java filesystem support is the next
server prerequisite; ZIP/JAR operations, sockets and normal class-path loading
remain later checks. Report the file-test row's exception text/code on failure.

The SDK identifies its ABI as x86-64, PROSPERO, FreeBSD 9. The BSD HotSpot source
also expects platform facilities such as `pthread_np.h` and `sysctl`. These
interfaces, signal handling, page size, module loading, and native linking
need to be audited against the actual PS5 environment. A desktop FreeBSD Java
binary cannot be assumed to run in the native application sandbox.

`tests/Hello25.java` is the first Java acceptance fixture. It requires Java 25,
checks an arithmetic result, and creates/joins a Java thread. It has compiled
with `javac --release 25` and run on the **Mac only**, printing `THREAD_OK` and
`HELLO_JAVA_25 49995000`. It has not run on PS5.

## Milestones and acceptance

1. Establish console OS capabilities using the probe, then add condition
   variable, signal and dynamic-library tests where the port requires them.
2. Build a minimal VM plus `java.base`; run Hello25 on PS5, initially using
   interpreter execution if feasible. Interpreter-only mode is a bootstrap
   option, not the performance target for Minecraft.
3. Add reliable JIT, garbage collection, native library loading, sockets and
   file handling. Exercise repeated launches and controlled shutdown.
4. Run a chosen Minecraft server version, create/reload a world, connect from
   another device, and verify sustained ticking and save integrity.
5. Port client dependencies: JNI bindings, LWJGL/window/input/audio interfaces,
   and graphics. Test a vanilla client before individual Fabric/Forge builds.
6. Validate each loader and mod set against a specific game and Java version;
   native desktop dependencies in mods need their own PS5 adaptation.

[ps5-opengl](https://github.com/blackbearreloaded/ps5-opengl) is an experimental
native OpenGL candidate. It has not been built or tested in this project.
[LWJGL](https://github.com/LWJGL/lwjgl3) exposes native bindings, so bringing
up Java alone will not supply the client's platform libraries. Vulkan support
and Vulkan renderer mods are separate feasibility work; there is no verified
Vulkan backend here yet. Neither graphics route nor Fabric/Forge compatibility
is promised by the current probe.

### File I/O 01.000.001: resident library discovery

The console reports PASS / PASS / FAIL / PASS for File I/O 01.000.000.
FileIO25.main throws UnsatisfiedLinkError with code FFFFFAE5 (-1307).
The row truncated the native method signature after `int sun.nio.fs...`,
so its exact name is not established by that report.

The Unix filesystem natives, including UnixNativeDispatcher.init, are already
compiled and included in the resident libnio table. OpenJDK's Unix loader
checks File.exists/canonical paths for ordinary libraries; a missing library
returns null from BootLoader.loadLibrary and the following native invocation
can fail. The adapter now exposes JNI_OnLoad_java/zip/jimage/net/nio so
OpenJDK recognizes these libraries as built in before checking their files.
The adapters invoke each original load hook when present, preserve negative
failures, and advertise JNI 1.8 or later as required for built-in libraries.
External libraries still require a separate loader implementation.

PPSA99866 **01.000.001** contains this change and a seven-line full exception
panel. `python3 tools/test_java25_builtin_lookup.py` tests the actual generated
lookup implementation with mocked function bodies: built-in discovery, original
hooks, JNI version handling, real filesystem symbol entries and handle scope.
The native build, signed binary integrity, ZIP CRC and version checks pass.
Console file I/O remains pending; the original passing JVM_Startup is preserved.

### File I/O 01.000.002: sandbox path resolution and current tracing

The user confirms the 01.000.001 crash occurs in row three, the Java file test.
IMG_0417 shows SIGSEGV at native PC 0x8000751d0. The handler anchor matches
the supplied ELF at image base 0x400000. The retained caller 0x10965e6 is
after memset in ThreadsSMRSupport::free_list, with 0x203c bytes completed.
Tracing had stopped after VM creation, so that retained call and metadata
stage cannot identify the subsequent Java file-test fault.

The UnixFileSystem constructor calls UnixNativeDispatcher.getcwd unless
`sun.nio.fs.chdirAllowed=true`. Native desktop getcwd had already been
excluded from PS5 system-property initialization. The new probe explicitly
sets `user.dir=/app0` and enables that standard resolution policy: all relative
paths resolve against the supplied user.dir, without querying process cwd.
This is a targeted workaround for a suspected sandbox path; the photograph
does not prove getcwd caused the crash. Java Files operations remain real.

Row three and VM destruction now each enable/reset native-call tracing with
a scope that disables tracing on every return. Application stage messages
also update the persistent signal-handler checkpoint, so future faults will
identify the active Java operation instead of the old metadata checkpoint.
The fixture now verifies relative-path resolution as well as UTF-8 file I/O.

Native packaging, signature integrity, ZIP CRC/version, generated built-in
lookup tests and AddressSanitizer native-trace tests pass. The real host JDK
interpreter fixture passes with `/app0` as user.dir, chdirAllowed=true and an
actual writable host temporary directory. PS5 01.000.002 validation is pending.

### File I/O 01.000.003: private file permissions and operation diagnostics

IMG_0418 shows successful VM creation and destruction around a managed Java
FileSystemException: the /download0 probe file reports Operation not permitted.
The old fixture did not identify which operation failed. This report confirms
progress beyond the earlier crash, but does not prove the native error number
or that file creation itself failed.

Java's prior default create mode was 0666; the passing native platform probe
uses 0600. The new fixture calls real Files.createFile with explicit POSIX
`rw-------` permissions and exclusive creation, then real Files.write/read/size/
delete on that uniquely owned file. Each IOException now names its operation.
This tests private-file creation; ordinary default-0666 creation remains
unvalidated. No native replacement supplies the Java fixture's file results.

The File I/O package alone wraps open for diagnostics. It forwards unchanged
flags/mode to the real native platform function. For failed /download0 opens
on the traced test thread, the TV panel shows flags, mode, return value and
numeric errno. The diagnostic writer's own open is guarded against recursion
and errno is preserved. tools/test_java25_open_trace.py exercises the actual
wrapper with mocked platform calls under AddressSanitizer.

The actual host Java interpreter fixture, wrapper test, target native build,
signed integrity, ZIP CRC and 01.000.003 metadata checks pass. PS5 validation
is pending. The original JVM_Startup milestone is unchanged.

### File I/O 01.000.004: sandbox metadata and deletion

IMG_0420 reports `File I/O stage delete` / Operation not permitted. Exclusive
Java creation completed, but the old finally block could replace a preceding
write/read/size exception with the delete failure. The fixture now retains the
first failure and adds failed cleanup as a suppressed exception. No new console
PASS milestone is established by this photograph.

The pinned native boilerplate's docs/SANDBOX_ELEVATION.md describes native-title
files opening/writing while directory listing and lstat are denied with EPERM.
UnixFileSystemProvider normally calls lstat before deletion. Patch 0028 adds an
explicit `sun.nio.fs.ps5Sandbox=true` policy for this probe: try real unlink,
then real rmdir if unlink indicates a directory/permission error. A regular-file
EPERM stays the unlink error when rmdir returns ENOTDIR. Missing paths and
nonempty directories keep their Java exception semantics. Unlink does not
follow symlinks. The normal provider path remains unchanged without the flag.

Patch 0029 adapts stat0 only under __PROSPERO__: when real stat returns EPERM,
it attempts read-only/nonblocking open, real fstat and close. Success requires
real descriptor metadata; denied opens and failed fstat remain errors. This
retains stat's link-following policy and never substitutes for lstat. Files
without read access may still lack pathname metadata support in this sandbox.
Directory listing and wider filesystem privileges remain separate work.

Target java.base classes/native libraries rebuilt successfully. The actual
patched provider class passes host file, directory, nonempty directory, link,
dangling-link and missing-path tests, plus the real FileIO25 fixture. The actual
stat0 function (C parameter renamed for the C++ host harness) passes ASan tests
with mocked platform results, including descriptor data and errno/close handling.
The target native package, signed integrity, ZIP CRC and 01.000.004 metadata
checks pass. Host tests are not PS5 proof; console validation is pending.

### Console milestone: File I/O 01.000.004 ALL PASS

On 2026-10-13 the user reports ALL PASS on PS5 firmware 13.60 for the supplied
PPSA99866 build: embedded initialization, real VM creation, FileIO25 and VM
destruction. The fixture validates relative paths, exclusive private 0600
file creation, UTF-8 write/read equality, actual size, deletion and absence.
The passing package is preserved as dist/PPSA99866-file-io-pass-01.000.004.zip.
IO_Probe is the frozen source milestone; its release includes the matching
package, SHA-256 checksum and validation record. Wider filesystem permissions,
ZIP/JAR loading, sockets, JIT stability and Minecraft remain unvalidated.
