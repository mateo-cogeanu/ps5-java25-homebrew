# Isolated Java 17 and 21 runtime work

The maintainer prioritizes a genuine Java 17 runtime before the Vanilla 1.20
candidate, and requests a Java 21 comparison for 1.21.x. These are new ports with
matching VM/class-library generations. Existing Java 25 defaults and frozen
milestones remain unchanged.

## Current build result

Both version-pinned FreeBSD/OpenJDK trees cross-build the genuine HotSpot server
VM (C1 and C2), `java.base` classes and native libraries for PS5 x86-64. Target
classfile majors are 61 and 65 respectively. Genuine JNI VM creation symbols and
Java 17's bundled fdlibm archive exports were checked. The class-only core images
are 12,593,381 and 14,350,852 bytes; these sizes exclude native runtime/application
code and do not establish game memory use or a performance improvement.

The original build record describes **initial cross-build baselines**. Subsequently Java17 startup002 received ALL PASS on the physical PS5; Java21 startup001 subsequently received ALL PASS too. Neither establishes Minecraft compatibility.
Some SDK-linked shared libraries produce `llvm-readelf` warnings about nonstandard
PT_DYNAMIC sizes. These are recorded in local audits; a header check does not
validate dynamic loading. Separate startup packages use matched statically resident native objects, not arbitrary shared-library loading.

The [build record](validation/java-lts-build-2026-11-08.json) includes exact
commits, patch hashes, target artifact hashes, image checks and limitations.
Downloads, target binaries, host bootstrap JDKs and raw logs stay local.

## Source and ownership

The [FreeBSD Java 17 port](https://github.com/freebsd/freebsd-ports/blob/main/java/openjdk17/Makefile)
and [Java 21 port](https://github.com/freebsd/freebsd-ports/blob/main/java/openjdk21/Makefile)
identify battleblow's maintained BSD source trees. Immutable commits and tags are
pinned in `java25/lts/upstream.json`, with separate source caches under
`.tools/java17` and `.tools/java21`. Verified Temurin macOS ARM64 bootstrap archives
are pinned independently; an explicit matching host JDK can be supplied instead.

Initial patches rebase our existing PS5 build boundaries onto each source
generation: explicit headless bootstrap mode, separate macOS host/target sysroots,
SDK math imports, no FreeBSD elfctl call for the explicit PS5 build, unavailable
uptime/module-enumeration diagnostics, credential-dependent attach refusal,
unsupported nonreaping process wait and the line-length portability fallback.
Non-PS5 defaults are retained. No comparison-project implementation was copied.

Reusable runtime source and tooling belong here. Launcher selection, original
Minecraft inputs, native graphics/mod dependencies and consumer validation belong
in [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft).

## Reproduce

The new provisioning entrypoint requires Python 3.12+ for safe archive extraction,
Git, GNU make, the prepared pinned PS5 SDK and an explicit LLVM installation.
It does not discover private game caches, reset modified source or overwrite an
existing class image. `--fetch-deps` is required to provision missing sources or
bootstrap archives. A source commit mismatch or patch conflict stops the command.

From this runtime workspace (or `Development` in its public checkout):

```sh
python3 tools/java_lts.py --major 17 --llvm-home /path/to/llvm --fetch-deps --build --image
python3 tools/java_lts.py --major 21 --llvm-home /path/to/llvm --fetch-deps --build --image
```

For another host, supply a matching runnable JDK with `--boot-jdk /path/to/jdk17`
or `/path/to/jdk21`. Both `java` and `javac` must match the selected major, with
`jmod` and `jlink` present. Source/build/class outputs remain version-separated.
`--cache-dir` and `--output-dir` are explicit alternatives. Use a fresh output
directory to create another image; existing images are preserved.

Subsequent offline checks of prepared inputs:

```sh
python3 tools/java_lts.py --major 17 --llvm-home /path/to/llvm --audit
python3 tools/java_lts.py --major 21 --llvm-home /path/to/llvm --audit
python3 tools/test_java_lts.py
```

The image step runs target data generation for security configuration, certificates
and timezones. Host `jmod`/`jlink` encode only the target-built class/configuration
data. Their temporary JMOD uses a supported Linux transport tag, as our existing
class-image builder does; no Linux/host native binary enters the image. It contains
no native launcher or libraries. The original target `Object`, `Runtime` and
`StrictMath` class bytes are independently extracted and rehashed from each image.
This does not replace matching native-image/resident-registry integration.

## Work required before a hardware candidate

1. Rebase and validate PS5 VM bootstrap services: image paths/resident native
   lookup, sandbox properties, CPU/signal context, direct-memory ownership,
   thread/TLS/synchronization and native allocation behavior. Compilation alone
   does not establish any of these sandbox contracts.
2. Package an isolated native startup probe using matching headers, class image,
   VM and core native libraries. Validate VM creation, arithmetic, exceptions,
   JNI, Java threads and clean destruction on the physical console.
3. Integrate a selectable consumer test path. The current launcher is compiled
   for Java 25 and uses finalized FFM. It cannot simply execute unchanged on 17
   or 21; keep its working path and design the matching game bootstrap explicitly.
   Do not mix Java-major class/native/management/JNI-table generations.
4. Validate Vanilla 1.20 on Java 17 and the intended 1.21.x versions on Java 21.
   Original game/mod JARs stay intact. Matched graphics, input/audio, dependencies,
   world generation/save/rejoin, quit and shaders all need scoped PS5 tests.
5. Compare repeatable cold/warm workloads with the working Java 25 runtime,
   controlling heap, compiler/collector policy, seed, distances, workers and mods.
   Preserve test results before deciding default selection or claiming less
   overhead. No older Java collector support is inferred from a build feature list.

Existing exact-build console, shader and publication gates remain in force.

## Startup milestones —2026-11-08

[Java17 startup002](java17-startup-probe.md), PPSA99876, received exact-build
**ALL PASS** for interpreter startup, Java/JNI/worker checks and destruction.
The signed package and complete source are released with checksums; frozen source
lives in the separate history archive. No C2/game/performance claim follows.

[Java21 startup001](java21-startup-probe.md), PPSA99877, uses an independently
rebased bootstrap boundary and its own matching class image/core objects. Host
checks and packaging pass; the maintainer also reported exact-build ALL PASS for its four interpreter startup rows. The working
Java25 consumer remains unchanged. Consumer launchers require separate integration.


## Explicit consumer bootstrap image —2026-11-09

The [opt-in integration guide](java-lts-bootstrap-integration.md) covers extended
class modules, genuine management natives, explicit linked resident groups and a
consumer-supplied probe directory. Current17target build/host/bootstrap/package
checks pass; exact consumer PS5 execution remains pending. The frozen startup
packages and default Java25 consumer are preserved. Native desktop support and
playable game/shader/performance acceptance are not implied.
