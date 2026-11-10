# Opt-in LTS bootstrap integration

Java17/21 core startup milestones stay frozen. Active tooling now accepts explicit
additional target-built class modules and statically linked native groups so a
consumer can test its own bootstrap with a matching Java generation. Defaults
remain the core java.base image and original standalone startup probes.

## Target class modules

`tools/java_lts.py --major 17 --image --modules java.base,java.xml,java.prefs,java.datatransfer,java.desktop,java.logging,java.management,jdk.management,jdk.unsupported --llvm-home /path/to/llvm --output-dir /path/to/fresh-image-work`

The first module must be java.base. Only the reviewed explicit module names are
accepted. Upstream Java targets run their genuine source/resource generators;
using java-only targets directly can omit required generated X11 Java sources.
Temporary JMODs contain only target-built classes/configuration, using the same
host-jlink transport tag as the core builder. Matching target classfile majors,
original base-class image readback, generated security data and no native binaries
are checked. Images and audits are created in fresh directories; old images stay.
This adds Java desktop classes, **not** working AWT/fonts/GUI/printing/desktop
native libraries. Individual APIs/native modules require separate integration.

## Matching resident groups and consumer packaging

`tools/java_lts_resident.py` adds default-off `--management` for matching original
java.management/jdk.management native objects and explicit `--library name=object`.
Names must be safe and unique; missing inputs fail. Objects are linked into the
application at build time. There is no runtime arbitrary ELF loader. Every actual
export is discovered from its matched object; loader trampolines forward real
JNI_OnLoad arguments/version/errors, and scoped lookups retain group boundaries.
Separate libraries' JNI initializers and private management/LWJGL globals are
renamed with paired relocations, avoiding shared jvm/jmm/throw-helper ownership.
Their constructors are staged with the VM constructors; resident lifetime remains.
Consumers own native ABI correctness, matching headers, dependency/source pins and
coherent classloader ownership. Explicit input is not a compatibility assertion.

`tools/package_java_lts_probe.py` adds explicit `--probe-dir`, `--extra-assets`,
`--management`, `--library` and `--link-object`. The consumer directory supplies
startup.cpp, HelloLts.java and param.json; HelloLts retains the registered JNI
multiply and run()/major contract used by the shared test helper. Identity/content
ID and existing artifact checks run before packaging. The consumer probe sources
are included with the local runtime source record. Supplemental linked object
hashes join the package audit. Required native entry symbols, constructor/VM bounds, matching
image bytes, metadata and ZIP CRC are checked. No release is created by the tools.
`test_java_lts_startup.py --probe-dir ... --vm-option=...` can execute that exact
Java/JNI helper under a real matching host VM, with explicit host-only test options.

The [build record](validation/java17-extended-bootstrap-build-2026-11-09.json)
identifies the current17 extended image/native objects and scoped checks. Actual
management queries, consumer bindings and original application boot on PS5 remain
pending in the separate consumer. No Minecraft files or raw reports enter this
repository. See [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft) for
the local1.20 bootstrap candidate and physical-console results. Existing exact
hardware and shader/release gates remain; passing startup does not establish play.


The [early startup phase trace](java-lts-startup-phase-trace.md) follows an
extended-image consumer001 crash after native JIMAGE read-only setup. Active17
adds fixed phase markers; consumer002 supplies scoped fault capture. Cause and
exact console result remain pending, with original passing startup bytes retained.


## Consumer JNI-stage diagnostics —2026-11-09

The shared17/21 `jni_checks.hpp` accepts optional fixed-stage tracing and an
explicit on-class registration callback. Defaults preserve the original three-
argument path. Calls bracket loader lookup, DefineClass, native registration,
method lookup and run() entry/return; only fixed labels are emitted. The callback
can register a consumer-owned diagnostic native after the original multiply and
before run-method lookup. Callback failures preserve pending JNI exceptions and
release the local class reference. No game class or runtime API is replaced.

The host startup fixture accepts explicit `--register-stage` for the matching
consumer diagnostic native. Default standalone17/21 checks remain unchanged.
The consumer uses this for a native-side breadcrumb before its first Java file
operation, avoiding dependence on successful Java NIO initialization for evidence.
Exact PS5 consumer004results are pending;003only establishes VM creation with
that profile, not the complete row3/bootstrap or a proven512MiB failure cause.

Explicit class images can include the target-built `jdk.zipfs` module.
Its OpenJDK service declaration supplies the standard `jar` NIO provider
when the module is resolved. The default image selection remains `java.base`.
The Java 17 target image audit found `jdk.nio.zipfs.ZipFileSystemProvider`
in the generated image. Provider discovery and archive access on PS5
still require console validation.

An explicit consumer probe can supply additional target import stubs,
one named staged constructor section and an existing thread destructor
provider symbol. The native linker and PS5 converter receive the same
import stubs. The packager checks that the named constructor range is
present and nonempty. The caller owns the timing of constructor execution,
the provider ABI and the checks on the imported objects. Standalone probes
retain the default link and constructor configuration.

Consumer probes can repeat the staged constructor option to retain
independent native initialization ranges. The packager rejects duplicate
or overlapping stages and verifies every linked range is nonempty. The
Java 17 graphics and audio probe links separate GPU and OpenAL ranges.

Java 17's development HotSpot now carries the Java 25 port's original
malloc-first native heap fallback. Its paired allocation, reallocation and
free operations cover HotSpot and its NMT preinitialization paths. On native
allocator failure it can use anonymous page mappings or small slabs.
The first 32 mapping attempts are recorded in the VM trace. Java heap
policy and other JDK generations are outside this change.

A console report from the 1.20 demo test captured a fatal HotSpot malloc
failure for 9,232 bytes after the original Main initialized. The target
build passed, as did a host check using the same allocator with forced
malloc refusal, aligned payload checks, reallocation and cleanup.
Whether the PS5 can satisfy the failed allocation through this fallback
remains pending.
