# Java 25 on native PS5 homebrew

Scope: the native OpenJDK 25 runtime, PS5 platform adaptations and Java
acceptance probes. VM startup, Java file I/O and ZIP/JAR loading have passing
console milestones on firmware 13.60. Networking 01.000.001 awaits its test.
The sections below retain the port's build and diagnostic history.

Related application project: [ps5-minecraft-java](https://github.com/mateo-cogeanu/ps5-minecraft-java).

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
| Socket | TCP socket can bind/listen on loopback | Accept/connect, LAN reachability, application protocols |
| Files | Exclusive temporary file write/read/delete in `/download0` | Data durability, other mount permissions |
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

The bootstrap commands apply the tracked patches under `patches/` and use an
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
bootstrap configuration, not the final runtime performance target.

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
test budget; larger Java applications need separate memory sizing tests.
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
that remains necessary for general Java applications.

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
JIT stability or general application compatibility.

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

## Runtime acceptance roadmap

1. Verify console OS capabilities, VM initialization and Java thread behavior.
2. Execute Java 25 bytecode with interpreter-mode acceptance fixtures.
3. Test file I/O, ZIP/JAR loading, networking and class-path discovery.
4. Validate JIT, garbage collection, JNI/native-library loading and larger heaps.
5. Exercise repeated startup/shutdown, sustained workloads and API coverage.

Application-specific integration belongs in separate repositories.

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
ZIP/JAR loading, sockets and JIT stability remain unvalidated.

### Next probe: ZIP/JAR 01.000.000 (console pending)

`make java25-zipjar` / `python3 tools/package_java25_jni.py --zipjar` builds
PPSA99867 as a separate Java 25 ZIP / JAR title, version 01.000.000. Run the
four rows in order: runtime initialization, VM creation, ZIP/JAR test, shutdown.
The original PPSA99865/PPSA99866 titles and first-passing archives stay intact.

The test verifies five ZIP entries, an uncompressed text entry, a 65536-byte
deflated pattern through real ZipFile/Inflater code, and JarFile manifest
reading. It creates a URLClassLoader, loads ps5probe.JarHello25 only from the
packaged JAR, checks its defining loader, invokes its arithmetic/version check
and verifies its UTF-8 resource through the JAR class loader. JNI DefineClass
is used only to launch ZipJar25 itself, not to supply the JAR payload. The
payload is deliberately absent from the loose class path. This unsigned JAR
probe does not test signatures, complex dependency graphs or mods.

The packager gives this title a separate zipjar-assets staging directory and
uses the console-tested I/O sandbox policies. It supplies full stage-specific
Java exceptions and current native crash traces. The deterministic archive
fixture and Java 25 classes are generated from tracked source.

Host packaged-fixture tests pass under -Xint. Negative tests detect wrong
stored bytes, wrong JAR resource bytes and a missing payload class at the
expected stages. Native packaging, signed integrity, ZIP CRC, title/version
and JAR-only payload checks pass. PS5 results are pending: do not freeze a
ZIP/JAR milestone until the user reports ALL PASS for this exact package.

### Console milestone: ZIP/JAR 01.000.000 ALL PASS

On 2026-10-13 the user reports ALL PASS for PPSA99867 01.000.000 on the PS5.
This establishes stored and deflated ZIP reads, manifest parsing, real
URLClassLoader loading/execution of the JAR-only Java 25 payload, its UTF-8
resource, and successful VM lifecycle. ZIP_JAR_Probe preserves this source
snapshot; its release includes the exact passing package, checksum and record.
Signed archives, complex dependencies, network I/O and JIT stability
remain further work. The JNI-defined test harness is not proof of automatic
system application class-path discovery.

### Next probe: Java Networking 01.000.000 (console pending)

`make java25-network` / `python3 tools/package_java25_jni.py --network` builds
a separate PPSA99868 title, Java 25 Networking version 01.000.000. Run the
four rows in order: runtime initialization, VM creation, networking and
shutdown. Previously passing title folders and archives are preserved.

Network25 uses an explicitly constructed numeric IPv4 loopback address and
ephemeral ports. Its TCP test starts a Java echo worker, checks framed UTF-8
bytes in both directions, closes the listener and joins the worker. UDP
sends and checks both request and response datagrams and their source ports.
NIO uses nonblocking SocketChannels, a ServerSocketChannel and real Selector
connect/read readiness to exchange and check bytes. Socket reads, accepts
and connects have 4-second timeouts; nonblocking loops have a deadline.
Resources close through try-with-resources and the worker is daemonized as
a shutdown fallback. These are real Java APIs, not native socket substitutes.

Only a diagnostic checkpoint callback is registered with JNI. The probe
enables it to persist numeric-address/TCP/UDP/NIO stage names for crash
reports. Networking itself resolves through the real embedded net/nio
implementations. IPv4 preference and existing tested filesystem policies
are explicit VM options. Music remains at 35%; effects remain disabled.

The exact packaged bytecode passes four host interpreter runs in one VM,
with no remaining echo worker and descriptor count 5 before/after repeated
runs. A real host JNI test exercises the actual checkpoint callback and
RegisterNatives with all four expected markers. Native target packaging,
signed integrity, ZIP CRC, exact class bytes and title/version checks pass.
PS5 validation is pending; this establishes no LAN, DNS, IPv6, TLS, internet
or application-level protocol support yet. Freeze Network_Probe only after
the user's ALL PASS report for this actual build.

### Networking 01.000.001: package target runtime configuration

IMG_0421 shows a managed error before the socket exchanges: InetAddress
initialization raises InternalError loading java.security. The packaged
classes-only boot image lacked conf/security/java.security. VM destruction
still passes; TCP/UDP/NIO console support remains unverified.

The boot-image tool now runs the target java.base-gendata goal and passes
the generated java.base configuration directory to jmod --config. jlink
then preserves conf/security/java.security, crypto policies and net.properties.
The raw source security file is a template, so copying it directly would
leave provider/platform substitutions unresolved. The generated target
configuration is used; security checks are not disabled.

Network25 explicitly initializes Security configuration before numeric
InetAddress construction. Managed errors now include up to three nested
causes, and the native checkpoint records this new stage. Target packaging
passes ZIP CRC/version, exact generated-file and fixture-byte checks. Host
TCP/UDP/NIO tests pass with the packaged configuration as the Java security
override, with no descriptor or echo-worker leaks. The actual native trace
callback and five JNI checkpoints pass on the host. PS5 validation is pending.

Minecraft work has a separate public repository,
https://github.com/mateo-cogeanu/ps5-minecraft-java, intentionally empty for
now. Its description links to this runtime port; Java development remains
in ps5-java25-homebrew.

### Networking 01.000.002: bundled security master path policy

IMG_0422 shows FileSystemException /app0/assets/java25/conf/security/java.security:
Operation not permitted, before socket tests. The configuration is packaged;
the photograph does not identify whether pathname inspection or reading failed.
Security's regular-file loader calls toRealPath before opening its input stream.

Patch 0030 adds a narrow policy when sun.nio.fs.ps5Sandbox=true: the exact
normalized java.home/conf/security/java.security master path uses its bundled
absolute path instead of toRealPath. Regular-file checks, actual input reads,
property parsing and active-path cycle checks remain. Extra files and include
paths keep normal canonicalization unless they identify that exact master.
This is not a global realpath fallback or a replacement security configuration.
The native probe also tests fopen/read of the master header before executing
the Java fixture, to separate native read permission from Java path handling.

A real host JNI regression replaces realpath0 with an EPERM exception. The
actual patched Security class fails with the normal policy, loads SUN master
properties in PS5 sandbox mode, and still rejects denied extra-file resolution.
Host TCP/UDP/NIO passes with the patched Security class and packaged config.
Repeated fixture and JNI stage-callback tests pass. Rebuilt java.base, native
package integrity, ZIP CRC/version and exact config checks pass. Console
validation remains pending; no networking milestone is frozen.

### Networking 01.000.003: native socket blocking mode

IMG_0423 confirms setup, VM creation and shutdown pass; Java security and
numeric IPv4 construction advance to the TCP test. The worker reports an
IOException Permission denied. Its exact operation was not labeled, and the
fixture previously prioritized the worker error over a possible earlier
client error. TCP echo, UDP and NIO are still not console-validated.

The pinned native boilerplate's update-check/console_curl.c documents refused
socket fcntl and uses PS5 SO_NBIO (0x1200) through setsockopt. Patch 0031
adapts IOUtil.configureBlocking only on PS5: try normal fcntl; on EINVAL,
EPERM or EACCES, require a successful SO_TYPE socket check before changing
real nonblocking state through SO_NBIO. Failed socket checks retain the
original fcntl error, and failed setsockopt stays a failure. Files and pipes
receive no synthetic success. A failed F_GETFL no longer becomes a no-op
nonblocking success from comparing -1 flags.

The worker now labels accept/configure, request-header read, request-byte
read and response write. A shared atomic keeps the first client/worker
failure; later failures are suppressed and included in diagnostic text.
This fix tests a documented socket-control incompatibility; the photograph
alone does not establish fcntl as the actual cause.

The actual C blocking-mode function passes ASan host tests with controlled
platform results for both modes, GET/SET failures, socket identity and failed
SO_NBIO. Target java.base-libs and the native package rebuild successfully.
Actual packaged host TCP/UDP/NIO repeat tests and real JNI checkpoint tests
pass, with descriptor counts stable and workers terminated. ZIP CRC, version
and exact fixture checks pass. PS5 01.000.003 validation remains pending.

### Console milestone: Networking 01.000.003 ALL PASS

On 2026-10-13 the user confirms ALL PASS for PPSA99868 01.000.003. Native
setup, real Java VM creation, Network25 and VM destruction pass on PS5
firmware 13.60. The fixture validates bundled security initialization, numeric
IPv4 loopback, framed TCP echo with a Java worker, two-way UDP and source
ports, nonblocking NIO channel I/O and selector readiness. This validates the
combined accepted build; it does not isolate which adaptation resolved the
previous permission error.

Network_Probe freezes this source, with an exact passing package and checksum
in its release. LAN/remote connections, DNS, IPv6, TLS, concurrent/sustained
traffic and virtual-thread polling remain separate acceptance work.

### Next probe: LAN / DNS 01.000.000 (console pending)

PPSA99869 is a separate five-row title: runtime initialization, VM creation,
LAN TCP/UDP echo, DNS resolution and VM shutdown. LAN and DNS rows can be
tested independently after VM creation. The passing Network_Probe remains
frozen. Host fixtures pass; PS5 results are pending.

Start the local Python helper on the Mac's user-confirmed LAN address:

```sh
python3 tools/java25_lan_server.py --bind YOUR_MAC_IP --port 38025 --background
python3 tools/package_java25_jni.py --lan --lan-host YOUR_MAC_IP --lan-port 38025
python3 tools/test_java25_lan.py
```

The helper binds TCP and UDP to that address only, limits frames to 4096
bytes, echoes data, and uses bounded connection reads. Keep the Mac awake
and on the same network. Its log and PID are under build/java25. The user's
IP is stored only in the generated packaged assets, not tracked source.
Lan25 rejects loopback addresses by default and verifies framed UTF-8 TCP
bytes, UDP bytes and peer address/port against the external endpoint. Socket
connect/read waits have 4-second timeouts. Host self-address checks do not
prove communication between the PS5 and another device.

Dns25 resolves example.com using real InetAddress lookup. A daemon resolver
worker has an 8-second UI wait; timeout does not forcibly cancel the native
resolver. On timeout, close the app before retrying. DNS exchanges no web
request and asserts nonempty, non-local addresses. This checks forward DNS
only, not IPv6 reachability, TLS or an internet TCP connection.

The native probe registers stage callbacks for both fixtures, preserves
exception text and current crash checkpoints, and uses the tested runtime
security/socket policies. Local helper readiness, actual packaged host Java
fixtures, rejected-loopback guard, native packaging/signature, ZIP CRC,
metadata and exact class/config bytes all pass. No LAN/DNS milestone is
frozen until the user's console results pass.

### Console milestone: LAN/DNS 01.000.000 ALL PASS

The user reports ALL PASS on 2026-10-13 for PPSA99869 01.000.000. The
Mac helper additionally logged TCP and UDP exchanges from the PS5 peer,
distinct from host self-tests. This establishes Java outbound IPv4 LAN
TCP/UDP UTF-8 echo, peer checks, forward DNS lookup of example.com, and
VM lifecycle. The helper is stopped after the completed acceptance run.

LAN_DNS_Probe freezes the source and the exact package/checksum. The
passing package retains its tested endpoint in assets/java25/probe.properties;
other users must supply their own Mac helper address and port before running
the LAN row. Inbound LAN server acceptance, TLS, IPv6, DNS edge cases and
sustained/concurrent loads remain separate work.

### Next probe: Inbound LAN 01.000.000 (console pending)

PPSA99870 has five rows: initialize, create VM, inbound TCP, inbound UDP
and destroy VM. The Java app binds listeners by port on available interfaces,
with IPv4 preference. TCP uses 38026; UDP uses 38027. There are no preset
device addresses, packaged endpoint properties or client-address filters.
Replies go to the accepted connection or received datagram's actual peer.

```sh
python3 tools/package_java25_jni.py --inbound
python3 tools/java25_inbound_client.py --ps5-host YOUR_PS5_IP --background
python3 tools/test_java25_inbound.py
```

Only the external client helper takes a runtime destination. It uses normal
OS routing by default; --bind is optional. The helper retries while the app
is not listening, for up to 30 minutes, and exits after both protocol checks
pass. Keep the Mac awake. Readiness/results are in build/java25/inbound-client.log
and its PID is in inbound-client.pid; neither is tracked. Restart the helper
if its wait expires before testing.

The TCP fixture accepts a client, validates framed UTF-8 data, sends its
own acknowledgement and requires a client verification marker. UDP binds
a listener, validates a request, replies to its sender and checks a second
verification packet from that same peer. Accept/receive waits are bounded
to 25 seconds, with 5-second connected exchange/confirmation waits. Every
fixture uses real Java sockets and closes its resources. The native app
registers only diagnostic callbacks and persists active stage names.

The actual packaged Java listeners and Python protocol pass host tests,
including an invalid TCP frame that fails instead of reporting success.
Native build/signature, ZIP CRC/version, exact class bytes and package-wide
user-address checks pass. Packaging now replaces generated asset directories
rather than retaining removed files: the initial configured draft is superseded
and its stale properties are absent from the final ZIP. Console validation
remains pending; older passing milestones and archives are unchanged.


### Inbound LAN retry diagnostics — 2026-10-14

The first console run of 01.000.000 reached TCP accept and UDP receive,
but both timed out (FFFFFAE5). This does not establish successful inbound
networking or identify a Java socket defect. The background helper had hidden
all retry errors. It now prints its runtime destination, first/changed error,
a retry summary every 30 seconds, and successful handshake confirmations.

Run `tools/start_inbound_client.command` by double-clicking it in Finder.
It prompts for the current PS5 address in the user's Terminal; no device
address is stored in the launcher or console app. Keep the window open and
start the app's rows in order. A refused connection before the listener starts
is expected; persistent errors while a row is waiting need investigation.
The tool environment reported immediate No route to host during diagnostics;
the user reports LAN access works in their own environment and the app was
closed at that time. This result is not evidence of a PS5 routing failure.

The console package is unchanged. Host TCP/UDP handshakes and invalid-frame
rejection still pass. Retest the same package with the visible helper before
changing the runtime or freezing an inbound milestone.


### Inbound LAN console pass — 2026-10-14

The user reports ALL PASS for unchanged PPSA99870 01.000.000 after the
Terminal helper retry instructions. All five rows passed. The matching
package and source are frozen as Inbound_LAN_Probe; see inbound-validation.json.
Earlier timeout evidence is retained separately. TLS, IPv6 and sustained
inbound workloads remain unvalidated.


### Advanced Network 01.000.000 — awaiting PS5 tests

PPSA99871 adds six rows: initialize, create VM, HTTPS, IPv6 loopback,
network load and destroy VM. No preset device addresses or Mac helper.
Run all six in order, even if an individual test reports FAIL.

```sh
python3 tools/package_java25_jni.py --advanced-network
python3 tools/test_java25_advanced_network.py
```

HTTPS uses HttpsURLConnection to https://example.com/, with 10-second
connect/read timeouts and a 64-KiB body limit. The exact pinned target
OpenJDK build's generated CA store is bundled at lib/security/cacerts and
loaded through the already-tested Files read API. TrustManagerFactory
and SSLContext use standard providers; hostname verification remains
enabled. No accept-all trust manager, certificate override or insecure
randomness fallback is used. The PS5 needs Internet access and a correct
system clock for certificate validity. Host tests use a temporary local
TLS server and demonstrate trusted success, untrusted-chain rejection and
wrong-hostname rejection. Certificates/keys from that harness are temporary
and are not packaged or published. Public endpoint behavior remains a
console-time dependency.

This probe enables IPv6 sockets (preferIPv4Stack=false). The IPv6 row
explicitly binds/connects ::1 for TCP and UDP, checks the actual IPv6 peer
and verifies replies. This establishes IPv6 loopback only, not LAN IPv6
routing, external reachability or interface discovery.

Load uses four concurrent client workers with separate TCP echo workers,
128 verified 4096-byte frames each (2 MiB each direction overall), followed
by 256 verified 512-byte UDP round trips. Sockets have five-second timeouts;
client-worker joins share a 60-second deadline. This tests bounded concurrent
and repeated loopback traffic, not prolonged LAN endurance.

Host protocols and negative TLS checks pass. Native signature/integrity,
ZIP CRC, Java 25 fixture bytes, CA-store bytes and absence of preset device
IPs pass. No console pass is inferred. Passing snapshots are unchanged.


### Advanced Network 01.000.001 — IPv6 lookup and cause diagnostics

The user's 01.000.000 photos show three failed rows: HTTPS throws
ExceptionInInitializerError while initializing trust managers/TLS; IPv6
reports protocol family unavailable; load wraps an unreported TCP worker
cause. VM creation passed; shutdown results were not shown.

OpenJDK IPv6_supported first creates a real AF_INET6 socket, then looks
up inet_pton through JVM_FindLibraryEntry(RTLD_DEFAULT). The embedded
lookup searched only the resident Java library exports and omitted that
platform function. The lookup now exposes the existing SDK/platform
inet_pton for global/process scope, without changing library-scoped symbol
resolution. An actual IPv6 socket failure still returns unsupported; this
is not forced capability detection. Host lookup tests execute ::1 parsing,
invalid-input rejection and library-scope isolation. Native socket creation
also records its actual fd/errno before the Java IPv6 row.

TLS initialization now records separate trust-factory, trust initialization,
TLS-context creation and secure-random initialization phases. Each fixture
includes a bounded nested cause chain in its visible exception text. Load
errors identify the client/echo worker and bind, accept, connect or frame
phase. The exception buffer is larger to retain those details. No certificate
validation, entropy source or load assertions are relaxed. The TLS and load
causes still need actual console evidence before a targeted runtime fix.

Native build/signature and host TLS positive/negative, IPv6, concurrent load
and embedded lookup checks pass. The new package still needs all six console
rows tested. No passing snapshot was altered.


### Advanced Network 01.000.002 — bundled cryptographic policy reads

The user reports all 01.000.001 rows pass except HTTPS. Its visible nested
cause is JCE initialization failing to inspect the unlimited cryptographic
policy directory, before any HTTPS connection. IPv6 loopback and bounded
concurrent TCP/repeated UDP therefore have console evidence, while this
combined milestone remains unfrozen until every row passes.

Patch 0032 adapts JceSecurity.java.template under sun.nio.fs.ps5Sandbox
only for the exact built-in limited/unlimited policy names. Existing
single-directory name and normalized-parent checks remain. Instead of
directory stat/access/enumeration, it directly reads the two mandatory
standard default policy files; limited also reads exempt_local.policy.
Normal CryptoPermissions parsing/intersection and mandatory-default checks
remain. Missing/unreadable or invalid files reject initialization. Custom
policy directories and non-PS5 operation retain the original loading path.
No permission is invented, no trust manager accepts all certificates, and
no weak entropy substitute is added. This tailored path assumes the pinned
bundled policy filenames; custom policy filenames require normal loading.

```sh
python3 tools/test_java25_crypto_policy.py
python3 tools/test_java25_advanced_network.py --crypto-patch build/java25/crypto-policy-test/patch
python3 tools/package_java25_jni.py --advanced-network
```

Real host JNI hooks deny metadata/enumeration only on policy paths. Actual
unlimited parsing permits the expected maximum AES size, limited remains
128 bits, missing required files fail, and custom-policy metadata denial
still fails. TLS trusted success and untrusted/hostname rejection also pass
with the patched JCE class. The target core classes were rebuilt; packaged
JIMAGE inspection confirms the patch and all bundled policy files match
the target-generated configuration. All six rows still need PS5 retesting.


### Advanced Network console pass — 2026-10-14

The user reports ALL PASS for PPSA99871 01.000.002. All six rows passed,
including verified HTTPS to example.com after patch 0032, IPv6 ::1 TCP/UDP,
four concurrent TCP workers and 256 UDP round trips. The matching source
and package are frozen as Advanced_Network_Probe. See
advanced-network-validation.json for the exact checksum and limits.
TLS negative cases remain host-tested; IPv6 LAN and prolonged network
endurance are separate unvalidated scopes. No next probe has been chosen.


### LAN Endurance 01.000.000 — IPv6 discovery and external load

PPSA99872 has six rows: initialize, create VM, actual IPv6 LAN TCP/UDP,
four concurrent external TCP clients for 60 seconds, repeated external UDP
for 60 seconds, destroy VM. It contains no device addresses or client-IP
filters. IPv6 binds :: on TCP 38028 and UDP 38029; load binds IPv4 wildcard
on TCP 38030 and UDP 38031. IPv6/IPv4 load peers must be external; loopback
is rejected unless an explicit host-test property is supplied.

```sh
python3 tools/package_java25_jni.py --lan-endurance
python3 tools/test_java25_lan_endurance.py
# Or double-click tools/start_lan_endurance.command in Finder:
python3 tools/java25_lan_endurance_client.py --ps5-ipv4 YOUR_PS5_IPV4 --discover
# A confirmed IPv6 address can also be supplied at runtime:
python3 tools/java25_lan_endurance_client.py --ps5-ipv4 YOUR_PS5_IPV4 --ps5-ipv6 YOUR_PS5_IPV6
```

Discovery uses the route interface and IPv4 ARP neighbor MAC, sends bounded
IPv6 all-nodes probes on that interface, and matches NDP entries by MAC.
It retains the scope interface for link-local addresses. It never derives
or guesses an IPv6 address from IPv4. The Mac has IPv6 configured, but
no PS5 IPv6 neighbor was established by tool-environment probes. The user
requested local discovery; the Terminal launcher tries it in their own
environment. If no IPv6 destination is found, skip row 3 for now and test
rows 1,2,4,5,6; this is a partial result, not an ALL PASS milestone. Local
::1 support does not prove the PS5 has a routable LAN IPv6 address.

Each TCP worker verifies monotonic sequence numbers and 4096-byte payloads
for at least 60 seconds and 128 frames, returns actual frame/time counters
and requires client confirmation. Four external clients run concurrently.
UDP verifies sequenced 512-byte payloads for at least 60 seconds/128 round
trips, handles a retransmitted last sequence without double-counting, returns
counters and requires final confirmation. The helper runs approximately
61 seconds per load row to allow clock/startup margin, with bounded retries
and visible connection errors. This is bounded LAN endurance, not an
hours-long soak test. TCP and UDP load rows run separately.

Host tests use explicit loopback opt-in and a two-second duration override
to verify the real Java fixtures, framing, counters, confirmations and
minimum-duration rejection. The production IPv6 fixture rejects ::1.
Discovery regression checks match MAC addresses, preserve scope and reject
missing neighbor evidence. No host result is claimed as a console pass.
Target signatures/integrity, ZIP CRC/title/version, exact fixture bytes and
absence of device endpoint data pass. Older milestones remain frozen.


### LAN Endurance first console results — 2026-10-14

IMG_0433.JPG shows PPSA99872 01.000.000 initialization/VM creation and both
60-second external LAN load rows passing. Their assertions require actual
non-loopback peers, sequence/payload checks, minimum duration/traffic counts
and final helper confirmations. These are real IPv4 LAN endurance results;
exact throughput counters were not supplied.

IPv6 reached TCP accept and timed out; its UDP stage was not reached.
This does not establish an IPv6 routing failure or a Java socket defect.
The external helper may not have discovered a PS5 IPv6 destination; its
Terminal discovery result is requested. VM destruction remains unreported
in this photo. The source/package are unchanged and the partial build is
not frozen as a passing milestone. Existing seven snapshots remain intact.


### Retain IPv6 discovery evidence — 2026-10-14

The user confirms every LAN Endurance row except IPv6 passed, including
DestroyJavaVM. The helper's Terminal window closed before its discovery
output could be read, so a discovery failure cannot yet be distinguished
from a failed connection to a discovered address.

Both Terminal launchers now save stdout/stderr under build/java25, show
the exit status and wait for Enter before closing. Double-click
tools/check_lan_ipv6.command for discovery only, with the PS5 awake and
connected. No need to repeat load rows or transfer a new console build.
The result is in build/java25/lan-ipv6-discovery.log; the full helper output
is in build/java25/lan-endurance-terminal.log. Logs and runtime addresses
are excluded from publication.

Discovery prints route/ARP absence or command errors, and the hardware
address/interface used for NDP matching. Failure to observe a neighbor
does not prove the PS5 lacks IPv6 configuration. No device address is
guessed. All older passing snapshots stay frozen; this combined IPv6/load
package still has a failed row and is not a passing milestone.


### IPv4 neighbor lookup blocked IPv6 discovery — 2026-10-14

The user supplied the retained discovery log: arp returned 1 and no IPv4
hardware address was found, so discovery stopped before IPv6 NDP matching.
They confirm the entered address is the PS5's fixed IPv4 address used for
the passing TCP/UDP load tests. This is not evidence of missing IPv6 support.

The helper now checks existing ARP evidence before ICMP probing. If the
single-address query fails, it searches the full ARP table for the exact
IPv4 address on the route interface. Only when both lack an entry does it
try priming and rechecking. Logs now show the entered address, route
interface, tunnel-route notice when applicable, command failure output
and whether ARP or NDP matching was missing. No device address is embedded.

A direct local ARP query observed a valid PS5 entry, while a subsequent
helper invocation reported no entry; tool-environment ICMP access also
reports No route to host. No IPv6 address is inferred from that inconsistency.
Retry tools/check_lan_ipv6.command in the user's Terminal; no PS5 package
change or repetition of the passing load rows is needed.

Focused host discovery checks are now in tools/test_java25_ipv6_discovery.py.
They cover MAC/scope matching, exact full-table fallback and rejection of
unrelated destination evidence; the full protocol suite still invokes them.


### Manually supplied PS5 IPv6 link-local address

The user found a link-local address in PS5 settings. The LAN endurance
launcher now prompts for an optional IPv6 address; supplying one bypasses
ARP/NDP discovery. No address is stored in the app or launcher. Enter a
valid compressed address (including its double colon). For a link-local
address lacking %interface, the helper selects the route interface for the
runtime IPv4 destination. Explicit scopes are preserved, and automatic
tunnel scopes, loopback, unspecified and multicast destinations are rejected.
Host checks cover those cases. The console package remains 01.000.000
and IPv6 LAN exchange still needs actual PS5 verification.


### LAN Endurance console pass — 2026-10-14

The user reports ALL PASS for unchanged PPSA99872 01.000.000 after entering
the PS5 IPv6 link-local address at runtime. All six rows passed. The matching
package and current source/helper are frozen as LAN_Endurance_Probe; see
lan-endurance-validation.json for the checksum and console scope. Earlier
accept timeout and discovery failure evidence remain recorded separately.
This establishes link-local IPv6 LAN traffic and separate 60-second external
IPv4 TCP/UDP workloads, not global IPv6 routing or hours-long endurance.


### Dependency loading 01.000.000 — next application prerequisite

The user deferred hours-long endurance until a useful application exists.
The existing network milestones remain valid; further networking scope is
not a gate for this next probe. PPSA99873 has six rows: initialize, create
VM, multi-JAR dependencies, actual system class path, JNI library, destroy VM.
No external endpoint or Mac helper is needed.

```sh
python3 tools/package_java25_jni.py --dependencies
python3 tools/test_java25_dependencies.py
python3 tools/test_java25_builtin_lookup.py
```

Four deterministic unsigned JARs hold every payload class. application.jar
has manifest Class-Path: dependency.jar api.jar; it calls cross-JAR classes,
loads a ServiceLoader provider from META-INF/services, verifies a UTF-8
resource and computes a known result. MultiJar25 supplies only application.jar
to an isolated URLClassLoader with the platform parent, then verifies
transitive loading and the order of three same-name resources.

The native VM options now put application.jar on java.class.path alongside
the fixture entrypoint directory. SystemClasspath25 uses the actual system
class loader to resolve the JAR-only application, confirms its defining
loader, invokes transitive code and requires ClassNotFoundException for a
missing class. JNI DefineClass is used only for the probe entrypoint as in
earlier builds; it never supplies the payload/dependency bytecode.

NativeDeps25 loads ps5deps.NativeMath from native.jar. Its static initializer
calls System.loadLibrary("ps5probe"). The dependency package includes an
opt-in real target-compiled resident JNI fixture in the existing embedded
lookup tables, exposing its actual JNI_OnLoad and native method addresses.
The on-load function calls GetEnv on the real VM. The method copies byte
arrays through GetByteArrayRegion and computes weighted sums. Eight calls
verify the arithmetic; a null input verifies native-to-Java exception
propagation, and a missing library must throw UnsatisfiedLinkError.
This is a test of resident JNI discovery, not arbitrary external ELF loading.
Other probe packages omit the fixture; no host native binaries are packaged.

Host tests compile the same JNI source as a temporary host dynamic library,
then exercise actual Java loading and calls. They also reject missing
transitive JARs, a missing application system-classpath entry, and a missing
JNI library. The generated embedded lookup test covers opt-in discovery and
library symbol isolation. Package integrity/CRC, Java 25 bytes, JAR-only
payload placement and real target JNI definitions pass. Console execution
remains pending; no ninth milestone or application compatibility is claimed.


### Dependency loading 01.000.001 — system paths and visible diagnostics

The user reports only the system class-path row failed in version 000.
Its shortened message identifies the initial system class resolution stage,
but hides the cause. The isolated manifest/multi-JAR and native JNI rows
passed; these must not be conflated with the system loader row.

URLClassPath.toFileURL canonicalizes each class-path entry and returns null
on IOException, silently excluding the entry. Patch 0033, under the existing
PS5 sandbox property, constructs the file URL directly only for absolute
/app0/assets/java25/jars/*.jar paths without dot/parent segments. Other
paths retain canonicalization. Actual JarFile opening, header validation,
manifest/dependency resolution and class definition remain unchanged.
This is a candidate fix consistent with sandbox behavior, not a claim that
the unseen console cause has been established. Target core classes were
rebuilt and the patch is verified in packaged JIMAGE bytecode.

```sh
python3 tools/test_java25_system_classpath.py
python3 tools/test_java25_dependencies.py
python3 tools/package_java25_jni.py --dependencies
```

The host JNI regression denies java.io.UnixFileSystem.canonicalize0.
Bundled JAR URLs survive under the opt-in property, while normal behavior,
outside paths, parent traversal and relative paths retain failure. Standard
real JAR/service/JNI positive and missing-dependency tests pass.

The error panel now wraps by Canvas::text_width using baked 20px glyphs,
respects explicit newlines and supports seven lines per page with D-pad
left/right. Requested 16/18px fonts previously fell back to 24px; fixed
character chunks could therefore exceed the screen width. A synthetic host
layout preview confirms the diagnostic stays on screen. Preview results
are layout evidence only. No source snapshot is frozen yet.

The /download0 log paths are from the application's filesystem view.
The user's FTP setup does not expose that folder, and its mapping is not
established. Earlier advice that the user could retrieve those logs there
was too definite. On-screen full-cause photos/pages are the current supported
reporting route; no FTP-visible log export is claimed.


### Dependencies console pass — 2026-10-14

The user reports ALL PASS for PPSA99873 01.000.001. All six rows passed:
real VM lifecycle, manifest-linked multi-JAR classes/services/resources,
actual system class-path resolution and resident JNI discovery/calls.
The matching package and source are frozen as Dependency_Probe; see
dependency-validation.json for its checksum and scope. Earlier failure
evidence is retained. This establishes the controlled dependency fixture,
not Minecraft bootstrap or arbitrary external native-library support.


### External consumer probes and optional target modules

The runtime packaging tool now accepts --probe-spec JSON with source,
param, asset_dir, java_sources, modules and include_dirs. Consumer app
source/assets remain in their own repository; the Java project owns the
reusable native runtime/image tooling. All required paths must exist.
The native builder accepts additional include directories. External asset
staging is fresh for each build, and real module names are retained in
the release metadata. Related application work lives in
https://github.com/mateo-cogeanu/ps5-minecraft-java.

java25_boot_image.py --modules accepts optional target-built Java modules,
builds their Java targets, creates classes/config-only JMODs and uses jlink
to include the dependency closure. It rejects missing target modules and
checks the image did not borrow a host module. Default builds still include
only java.base. Optional modules currently cover compiler, desktop, XML,
logging, management, naming, RMI, scripting, SQL, HTTP server, JFR and
unsupported APIs with their dependencies. Their optional native services
are not implied to work by packaging their Java classes.

Target-generated tzdb.dat and security/cacerts are now always copied into
the core image: class/config-only JMODs previously omitted these data files.
Exact source/output bytes and default-module isolation were checked.
No host native library is included. An external consumer package passes
assembly/signature/CRC/content checks and awaits its own console test.
Existing nine frozen runtime milestones remain unchanged.

`probe/vm_diagnostics.hpp` provides bounded native formatted-output capture
for the JVM vfprintf callback, including failures before JNI_CreateJavaVM
returns. Consumers own persistence and display of the captured error. The
ASan/UBSan test checks formatting, retention of the recent output and reset.
Target compilation passes; console diagnostic capture remains pending.

The embedded core now includes the target-built legacy bytecode verifier
(`libverify`, `VerifyClassForMajorVersion`). Older class versions require
this in addition to HotSpot’s modern stack-map verifier. Its omission caused
“Could not link verifier” for an external consumer. Verification remains
enabled; real upstream verifier code is linked and its target library is
packaged. Lookup/scope and target packaging checks pass. An external consumer’s
bootstrap/help and VM lifecycle now pass on PS5 (01.000.002, human
ALL PASS on 2026-10-14).

### Incremental non-class metaspace reservations

Patch `0034-ps5-incremental-metaspace-reservations.patch` starts each PS5
non-class metaspace node with one 16 MiB root chunk instead of the desktop
64 MiB node. Existing node-list growth, chunk alignment, commit granules
and allocation failure checks remain intact. Non-PS5 defaults are unchanged.
The 64 MiB node can need an 80 MiB transient alignment reservation; those
sizes match consumer startup ENOMEM reports at larger Java heap budgets.
That match supports this adaptation but does not establish the complete
cause of the subsequent platform signal.

ASan/UBSan checks compile the real Settings header, verify both platform
branches and model constrained reservation pressure. The target HotSpot
build and embedded 16 MiB node argument pass inspection. Consumer console
validation is pending; frozen passing milestones remain unchanged.

The consumer 01.000.005 console result confirms real 192 MiB VM creation,
artifact preflight and VM destruction with the smaller metaspace nodes.
Application startup now reaches a separate helper-class lookup failure.
This result does not establish a ready application server.

### Legacy verifier allocation failure context

Patch `0035-ps5-verifier-allocation-failure-context.patch` appends the failing
source line, saved errno and pending-JNI-exception state to PS5 legacy
verifier allocation errors. A class/method/signature-only OutOfMemoryError
is emitted by this native verifier path; it should not automatically be
treated as Java heap exhaustion. The original failure result, cleanup and
longjmp remain in place. No verification checks are disabled.

Target libverify rebuild and package inspection pass. ASan/UBSan tests run
the actual error formatter with bounded context/JNI stubs, check preserved
errno even if the JNI callback changes it, and confirm the desktop message
is unchanged. Console diagnostic validation is pending.

### Quiet native crash context

Patch `0039-ps5-thread-local-crash-context.patch` isolates diagnostic state by thread. Shared stage, call and recursion guards could race between runtime threads; disabling verbose native tracing also discarded the call evidence needed when a consumer crashed. This is a diagnostic defect, not an established cause of that crash.

The probe now offers `ps5_native_trace::quiet()`: it retains caller, pointers, byte count and completion state in memory, with no per-call file writes. Added calloc/realloc/free wrappers call the original allocator functions unchanged. Explicit JVM stages and fatal signal output still reach the trace file. A completed record describes an earlier call; an incomplete record indicates interruption before its wrapper returned. Neither alone is a stack backtrace.

Contexts live in a preallocated 1024-slot table with lock-free claiming by pthread identity. No C++ `thread_local` is used for capture: the target emulates TLS using allocation, which could recurse into these wrappers during first access. Exhaustion suppresses new call capture, reports context unavailable and preserves existing slots. This table is process-lifetime diagnostic storage; thread identities may be reused by the platform.

The native-wrapper ASan/UBSan test covers quiet IO suppression, signal-time evidence, independent thread state, allocator semantics and bounded-table exhaustion. `python3 tools/test_java25_trace_storage.py` compiles context access for the PS5 target and checks its LLVM IR for allocation, emulated TLS and initializer-guard dependencies. The trace IO regression retains partial-write/errno checks. Host and target package checks pass; the original consumer SIGSEGV still requires PS5 diagnosis.

### HotSpot native heap fallback

Consumer build 015 records a completed native `malloc(128)` returning null from HotSpot `os::malloc`, followed by a signal outside the app image. This establishes a native allocation failure, without identifying why libc refused it or which subsequent instruction faulted.

Patch `0040-ps5-hotspot-native-heap-page-fallback.patch` adds a PS5-only storage backend below `os::malloc`, `os::realloc`, `os::free` and the matching NMT pre-init raw functions. Libc is attempted first. Failed small allocations share 64 KiB anonymous RW mappings through eight size classes, avoiding a whole console page per tiny block. Larger allocations fall back to page-rounded anonymous mappings. A uniform aligned prefix stores size and backend; cleanup uses the original libc free or matching unmap. Empty slabs are removed under the allocator lock, then unmapped after unlocking. Diagnostic IO also occurs outside the lock.

The same prefix is used before NMT initialization, including allocations that survive into NMT-off operation. Existing NMT admission limits, headers, logical-size accounting and failed-resize header revival remain. Backend headers and unused slab capacity are allocator overhead, outside those logical NMT sizes. Failed growth leaves the original allocation and bytes intact; failure of both storage backends remains a real allocation failure. Other platforms retain their original allocator paths. No Java heap-size increase or reserved-address overwrite is involved.

Run `python3 tools/test_java25_native_heap.py`. It executes the actual backend with forced failures under ASan/UBSan, checks pooling/alignment/reallocation/cleanup, and stresses concurrent callers. It also compiles the actual `os.cpp` API bodies with a narrow NMT contract model and the actual pre-init raw bridges to check accounting, limits and cross-initialization compatibility. These modeled checks are distinct from real target execution. The target HotSpot build and matching package checks pass. Console validation remains pending; the later native crash is not claimed fixed until retested.

## Native synchronization allocation

A console capture now confirms pthread mutex initialization returns ENOMEM. [Patch 0054 and its host regression](../docs/java25-native-synchronization-pools.md) add bounded early pools of real mutexes/conditions with exclusive stable-address leases, exact clock attributes and genuine failure propagation. Console validation remains pending.

Patch 0055 expands the early mutex reserve to 4096 for generated-class workloads and records exact failed native-init pool occupancy, attribute matching and caller; event/parker/monitor checks have distinct labels. The next capture confirms the former pools all initialized, but later ENOMEM persists; pool exhaustion remains an inference until occupancy is captured. Console validation remains pending.

Patch 0056 expands the relative/absolute condition reserves to 4096/2048 and adds failed native-condition occupancy/domain/caller diagnostics and constructor labels. The next console capture reaches later class loading but fails native condition init with ENOMEM; exact pool occupancy and consumer completion remain unvalidated.

## Nofollow metadata

[Patch 0057](../docs/java25-nofollow-metadata.md) adds genuine descriptor metadata after PS5 lstat EPERM, with O_NOFOLLOW leaf protection and real missing-path/error propagation. Final symlinks remain errors when native lstat cannot describe them; no link validation is disabled. Report notes now avoid allocating a new FILE. Console validation remains pending.

## Signal recovery and canonical paths

[Patches 0058/0059 and their regressions](../docs/java25-signal-context-and-realpath.md) correct the PS5 machine-context offset used for register reads and signal continuation writes, and verify every non-link path component through descriptors after native realpath EPERM. Host replay, actual JNI/ZipFS checks and target rebuilds pass. PS5 recovery and consumer readiness/save/stop remain pending.

Patch0060 excludes desktop FreeBSD stack-gap kernel queries from PS5 signal recovery while keeping JVM stack guards. The actual triage regression covers both platform branches, and the target signal object no longer references those queries. Build034 confirms corrected PC reads but still crashes during null preflight; live continuation recovery remains pending. See the linked signal-context notes.

Build035 confirms live Java null continuation and progress through40 JAR checks. Patch0061 replaces the fallback canonicalizer's raw desktop openat dependency with verified component-prefix resident opens, and stops advertising unported optional directory-at operations on PS5. Host actual JNI/ZipFS tests and target rebuild pass; asset mounting and the remaining consumer crash require console retest. The signal-context notes describe semantics and limits.

## Resident directory streams and access

[Patches0062/0063 and regressions](../docs/java25-directory-access.md) enumerate real directories through libkernel with bounded native record parsing, and check denied read/write access queries through actual non-creating descriptor operations. Execute permissions are not inferred. Consumer036 now reports Java failures without a whole-app crash; build037 console filesystem/server validation remains pending.

Build037 confirms actual readable asset access and later datapack loading. Patch0064 adds a conservative initial directory-ABI fallback and native stream/zlib allocation ownership with libc-first mapped fallback. Full JNI/real ZipFS and sanitizer regressions pass; build038 PS5 validation and separate service-discovery DNS diagnosis remain pending. See directory/access notes.

Patch0065 moves directory bytes to a dedicated page-aligned64KiB mapping and adds bounded saved-stack/frame evidence for unhandled native signals. Build038 still fails directory enumeration and crashes during consumer startup; buffer layout is a hypothesis, and the external faulting address has no native caller yet. Host/target checks pass; build039 is diagnostic development awaiting PS5 validation.

## Native OOM reporting and small slab retry (0066)

Build039's saved native frame chain resolves to ConcurrentHashTable dictionary insertion, AllocateHeap, native out-of-memory reporting, core-dump prerequisites and os::get_core_path. The signal is therefore in fatal reporting, rather than evidence that the last completed malloc itself jumped to the bad PC. The raw trace records refused64KiB slabs for small allocations. It does not establish the process memory limit.

On PS5 get_core_path now returns unavailable without desktop current-directory/program-name queries. Small mapped native allocations retry one minimal page-rounded slab after a64KiB mapping failure; successful ownership/cleanup is unchanged and both failures still propagate real OOM. The host actual-body core-path test and allocator sanitizer tests include a64KiB refusal with smaller mappings accepted, and complete refusal. These repairs need PS5 validation; they do not claim server readiness or eliminate genuine native memory exhaustion. Heap remains192MiB in the consumer probe.

## Generated resources in optional module images

The image builder now runs target `-gendata` goals for requested modules with
resource generators, in addition to Java compilation. Java compilation alone
omitted `jdk.jfr/jdk/jfr/internal/types/metadata.bin`, causing JFR metadata
initialization to fail with a null resource stream in a console consumer.
The resource is generated from the pinned target metadata XML/XSD; no host
metadata is copied. The builder verifies SHA-256 identity across the target
resource, temporary JMOD and extracted linked-image resource, and records the
generator goals and resource hash in `boot-image-audit.json`. Java desktop's
requested font/HTML data generators also run.

`python3 tools/test_java25_jfr_image.py` extracts target JFR classes/resources
from the linked image, patches them into the host Java 25 module, confirms
resource bytes, and exercises actual `MetadataLoader.createTypes()`. This
passes on the host JVM; its native JFR remains host behavior. PS5 JFR
registration and downstream consumer startup still require console validation.

## Network interface failure diagnostics (0075)

A console consumer now reaches TCP listener setup but fails with an
OutOfMemoryError rooted in `NetworkInterface.getAll()`. The saved native trace
returns from the fixture without a captured VM abort or native fatal OOM. The
exception does not identify whether interface-list malloc or a Java allocation
failed; available heap after failure does not establish peak heap availability.

Patch0075 adds PS5-only bounded descriptor diagnostics for getAll entry,
enumeration result/pending exception, interface count, array allocation and
per-interface conversion, with exact failed conversion source lines. BSD IPv4/6
getifaddrs and addif errors, and checked native malloc failures with requested
size, are recorded. It preserves errno and pending exceptions and retains real
enumeration, allocation and failure behavior. It does not change allocation
backends or manufacture interfaces. This is diagnostic development, not a
confirmed OOM repair.

`python3 tools/test_java25_netif_trace.py` tests the actual writer with short
writes, EINTR, write/open failure, bounded formatting and errno preservation;
it also runs the actual getAll body with narrow JNI/enumeration stubs covering
success, enumeration/array/conversion failures, pending exceptions and cleanup.
ASan/UBSan and target HotSpot/java.base native builds pass. Console validation
and the underlying OOM cause remain pending.

## Mapped interface-query fallback (0076)

[Patch0076 and validation details](../docs/java25-interface-query-fallback.md)
retry resident `getifaddrs()` ENOMEM with a fresh bounded kernel route query
and mapped storage. Current interface/MAC data and explicit ownership are
retained; normal resident success and other errors remain unchanged. Actual
parser/fallback sanitizer checks and target native compilation pass. PS5
route ABI/permissions and downstream consumer readiness remain unvalidated.

Patch0077 adds precise route-query error stages, SDK/header sizes and bounded
rejected-input evidence after a console fallback returns EINVAL. Actual hex
capture/rejection diagnostics pass sanitizer tests. This diagnoses an unresolved
fallback failure; it does not claim a kernel-query or route-layout repair.
See the interface-query notes for current evidence and console limitations.

Patch0078 corrects a captured PS5 route layout mismatch: RTM_IFINFO addresses
start at byte192, while the SDK declares a168-byte header. The parser now
skips the actual opaque statistics and reads only stable prefix fields. Host
ASan/UBSan replay of the complete local1320-byte capture yields eight real
records and passes mapped ownership/cleanup. Console fallback completion and
downstream consumer readiness remain pending. Raw route data stays local.

Patch0079 follows confirmed live route parsing with a scoped interface-node
allocator: libc first, page-rounded anonymous mapping on refusal, explicit
ownership and matched recursive cleanup. A captured64-byte addif allocation
failed on console. Actual allocator/addif/freeif sanitizer regressions and
target build pass; console availability and downstream startup remain pending.
The new-parent allocation failure also releases its unlinked address node.

Patch0080 extends the real route-query retry to resident EACCES/errno-less
failure after a console IPv6 enumeration failure; ENOMEM remains covered.
It clears stale errno before resident queries/node malloc and preserves caller
errno on success. Actual kernel-query denials and other errors still fail.
Host regressions and target build pass; console startup remains pending.


Patch0081 adds a fresh route-snapshot fallback for denied interface flag ioctls,
preserves query errno and diagnoses flag-query/name-conversion failures. It also
avoids a native diagnostic malloc for short PS5 last-error suffixes, preserving
the underlying exception when libc refuses scratch memory. Build056 confirms
both address families and two Java interfaces now enumerate; the subsequent
isLoopback0 failure's exact substage remains unresolved. Actual flag/parser
sanitizer and real JNI error-formatter tests pass; target compilation passes.
Console flag resolution and consumer readiness remain pending. See the
[interface-query notes](../docs/java25-interface-query-fallback.md).


## PS5 stream paths and mount-query boundary (0082/0083)

A consumer057 run reaches real server readiness, then its native trace ends at
BsdNativeDispatcher.getfsstat; the linked implementation uses raw syscall395.
Patch0082 reports ENOSYS on PS5 instead of invoking the unvalidated desktop
mount ABI. Mount discovery/capacity remain unavailable. Patch0083 resolves
relative java.io stream opens through File.getAbsolutePath/user.dir, addressing
captured relative-open errors while preserving actual errors and absolute paths.
Actual native-body/real-JNI regression with UBSan and -Xcheck:jni plus target
compilation pass. Console save/stop and handling of unavailable mount queries
remain pending. [Evidence and limits](../docs/java25-ps5-filesystem-queries.md).


## Scoped SDK DNS results

The runtime packager now adapts only the pinned SDK netdb object's result
malloc/free/strdup ownership to the existing libc-first/mapped backend and adds
resolver-stage diagnostics. This addresses a concrete allocation dependency
while the exact cause of a consumer DNS failure remains unconfirmed. Native
network results and failures are retained; console DNS/online operation is
pending. [Evidence, tests and scope](../docs/java25-dns-result-allocation.md).


## java.io metadata for TLS stores (0085)

Patch0085 extends real descriptor metadata/access fallback to java.io after
PS5 desktop stat/access EPERM. This supports the standard JSSE trust-store
selection path, which still uses File rather than NIO. Host native/JNI tests
reproduce zero roots before the adaptation and111 roots after it, using the
same target cacerts, then complete real consumer HTTPS preflight. Certificate
verification is unchanged. [Evidence and limits](../docs/java25-file-metadata-trust.md).
Console TLS and consumer endurance remain pending.

The scoped SDK DNS adapter now retains one serialized16KiB pool/resolver pair
per app lifetime after consumer061 logs confirm late pool creation ENOMEM.
Real DNS answers/errors and result allocation ownership remain intact. See
[DNS allocation and resolver lifetime](../docs/java25-dns-result-allocation.md).
The400-query concurrent allocation-denial regression passes ASan/UBSan;
consumer062 console DNS/authentication/endurance validation remains pending.

The current native allocator retains at most one idle slab per size class
(512 KiB total bound) and trims idle storage on mapping pressure. Ten thousand
4,088-byte allocation/free lifetimes use one real mapping in the actual-header
sanitizer regression. Successful ENTER/DONE phase traces now use the configured
sampling interval while keeping current crash context and unsampled failures.
See [idle slabs and trace sampling](../docs/java25-native-idle-slabs.md).
Console gameplay performance remains pending; the consumer still uses `-Xint`.

Patch 0089 extends the established resident directory reader to java.io.File
listing, fixing the remaining desktop opendir dependency reached by a consumer's
legacy-player conversion. Empty and real failed listings remain distinct;
partial failures are rejected and all descriptors/mappings are released.
See [java.io directory listing](../docs/java25-file-directory-list.md).
Actual JNI/Java-list host regressions and target compilation pass; the next
consumer console startup and gameplay result remain pending.

### Guarded C1 candidate (console validation pending)

The reusable [C1 warmup gate](../docs/java25-c1-warmup.md) requires actual current-run
level-1 kernel compilation and checks deterministic results before consumers
start heavy work. An 8 MiB code-cache host run passes; interpreter, stale and
missing-log controls reject. Current/previous JIT logs are available through the
read-only report service. This is a development candidate, not a PS5 JIT pass;
compiled exceptions, native memory and sustained execution still need console
validation. Frozen passing interpreter milestones remain preserved.

### Native library name allocation candidate

[Patch0090](../docs/java25-native-library-name-allocation.md) adds a PS5 scoped
fallback for temporary native-library and JNI symbol names. A C1 consumer run
fails with bare OOM during management initialization; raw malloc denial in
these bodies reproduces that failure on host. Real JNI fault/cleanup controls
pass, but the precise console allocation site and resolution require retesting.
Library lookup and JNI load/version validation remain enabled.

### Bound reusable arena retention on PS5

[Patch0091](../docs/java25-arena-pool-bounds.md) limits each arena chunk cache to
eight unused chunks and reclaims unused pools before retrying an allocation
refusal. A C1 workload aborted on a real32KiB native mapping failure. Actual
pool-path ASan/UBSan tests and target rebuild pass; console pressure resolution
and sustained execution are pending. Live arena storage remains protected.

### Four MiB PS5 metadata growth steps

[Patch0092](../docs/java25-metaspace-four-mib-roots.md) uses a PS5-only4MiB root
and13 buddy levels down to1KiB. A real join path aborts while reserving another
16MiB non-class metadata node. Actual level-fitting/settings tests and target
rebuild pass. Single metadata allocations are now bounded by the4MiB root;
total metadata can grow across nodes. Console growth, join and native budget
remain pending. Other platforms and frozen passing snapshots are unchanged.


### Development: compact allocator prefix and compressed resident image

Patches0093–0094 reduce per-allocation overhead and enable ZIP-compressed module
images using the resident ZIP decoder. See the [implementation and checks](../docs/java25-compact-prefix-and-resident-image.md). Host allocator, reader/resource identity and target builds pass; PS5 memory headroom, decode and sustained stability remain pending.


### Development: PS5 OS entropy seeding

[Patch0095](../docs/java25-os-entropy-seeding.md) connects Unix NativeSeedGenerator
to the actual PS5 system random service instead of the unavailable device-file
path and expensive threaded fallback. Host actual-Java/JNI/DRBG/failure tests
pass; PS5 service/ABI/TLS startup and the original process-crash cause remain
unvalidated. This does not alter consumer game classes or TLS verification.


### Development: checked PS5 kernel entropy

[Patch0096](../docs/java25-checked-entropy-resolution.md) fixes the captured null
service-import call using the checked kern.rng_pseudo interface. Actual Java/JNI
concurrency/batch/DRBG/kernel-error/short/oversized-response and desktop-control
tests pass; target native rebuild passes. PS5 kernel availability, TLS/server
startup and earlier071crash resolution remain pending.


### Development: native image inflater allocation and errors

[Patch 0097](../docs/java25-image-inflater-allocation-and-errors.md) applies the
existing PS5 zlib storage adapter to native image decoding and propagates decode
failures into checked resource errors. It also initializes image-reader ownership.
Actual native inflater and release-mode reader tests pass under ASan/UBSan,
including DTLS bytes and forced storage refusal. PS5 TLS startup remains pending.
