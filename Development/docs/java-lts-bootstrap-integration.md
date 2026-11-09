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
hashes join the package audit. Native signatures, constructor/VM bounds, matching
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
