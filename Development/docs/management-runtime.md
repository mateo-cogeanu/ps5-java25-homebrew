# Embedded JVM management

Consumer probe specifications that request `java.management` now build its real
OpenJDK `libmanagement` and embed its native object files alongside the other
resident core libraries. Packaging also includes the matching target ELF library
at `assets/java25/lib/libmanagement.so`. No desktop library is substituted.

The generated resident lookup exposes `JNI_OnLoad_management` and the library's
actual `Java_sun_management_*` functions. Its original JNI load hook obtains the
real `JVM_GetManagement` interface from the embedded HotSpot VM. Heap/non-heap
usage, VM input arguments and the other standard management natives therefore
use HotSpot's implementation; no fabricated management values are introduced.
The default integration remains `java.management` only. Optional `jdk.management` support is described below; its presence does not validate OS telemetry.

Relevant host checks:

```sh
python3 tools/test_java25_management.py
python3 tools/test_java25_builtin_lookup.py
```

The first compiles the actual management C sources for the host, loads their JNI
hook into a real JVM, and checks heap/non-heap usage and the real `-Xint` flag via
the JMM interface. The second checks generated resident-library discovery, hook
execution, JNI versions, function lookup and isolation from other library handles.
These checks do not execute the target ELF on PS5. Console management queries
must pass before this integration is considered console-validated.

## Opt-in genuine JDK management extensions —2026-11-02

`java25_builtin_runtime.py --management-extensions` includes the separately built
OpenJDK `management_ext` resident group and implies `--management`. Defaults and
base library tables remain unchanged when the option is absent. The reserved
runtime-owned group has its original JNI load hook, native flags/diagnostic/GC
functions and separate symbol scope; no arbitrary loader or replacement MBean.
`package_java25_jni.py` recognizes explicit `jdk.management` in a consumer module
specification, builds the target native library, selects the option and copies the
matching target ELF. `java25_boot_image.py --modules ...jdk.management` already
builds target Java classes; include the module explicitly and retain the other
consumer modules. Adding a class name alone is insufficient: the provider loads
`management_ext`, whose genuine JNI hook obtains HotSpot's JMM interface.

Build prerequisites:

```sh
gmake -C .tools/java25/openjdk CONF=ps5-bootstrap jdk.management-java jdk.management-libs
python3 tools/java25_builtin_runtime.py --management-extensions
```

All eight target native translation units and original Java/module provider are
used. Native `Flag.getFlags` returns the real VM option values, origins and
writability. There is no fabricated UseFMA value or VM-flag mutation. The existing
VM/allocator/GC policies are unchanged. OS extensions retain upstream BSD behavior,
including unvalidated sysctl/procfs support and historical fallback values; this
addition does not establish truthful complete PS5 OS telemetry, heap/thread dump,
diagnostic-command, collector-listener or writable-flag coverage. These need
separate checks. The runtime offers the generic API; consumer image/module pins,
original application dependencies and release validation belong to the consumer.

`test_java25_management_extensions.py --java-home <JDK25> --cc <clang>` is a manual
macOS test. It compiles genuine OpenJDK extension sources, links a disposable host
image, replaces only that image's management_ext, and patches in target-built
jdk.management Java classes. Traces must bind Flag initialization/getFlags to the
rebuilt library. Fresh child JVMs force UseFMA=false/true and test real option
values, unknown-option and readonly-setter refusal with Xcheck:jni. Removing the
custom library must fail instead of falling back to an installed stock extension.
The host's java.management core is intentionally retained. Installed JDKs are not
changed. Optional explicit consumer classpath/initializer/static-boolean inputs
allow the owning consumer to check its original code against those real values.
No consumer JAR is bundled or transformed. Other host platforms and physical PS5
API behavior remain separate validation.

The generated lookup test covers original hook execution, extension native-symbol
visibility and isolation from management/java handles. Console API behavior remains
pending until independently recorded; host compilation or a linked image is not
physical acceptance. Existing frozen milestones and release gates remain intact.

## PS5 small native flag queries —0136

PS5 builds now use a per-call stack array for up to16 jmmVMGlobal records in the
original Flag.getFlags native routine. No shared reserve, loader/VM-flag spoof,
heap/GC change or new JNI implementation is added. Larger requests retain the
original malloc/refusal behavior; every cleanup path distinguishes stack from
heap ownership. Other platforms keep the original allocation. The genuine JMM
query, Java values/origins/writability and original error handling remain.
This avoids a small native allocation under PS5 libc refusal; Java object or
underlying VM allocations can still fail. Native allocator root cause is open.

The forced extension test's --deny-flag-malloc option compiles the actual PS5
branch while denying only Flag.c malloc. It checks1and16record queries,17record
and full-list malloc refusal, unknown/readonly controls,8concurrent workers making
1000real UseFMA queries each, false/true flags, Xcheck:jni and no stock extension
fallback. The consumer also exercises its original initializer with that option.
Target jdk.management-libs rebuild passes. Actual PS5 small-query behavior and
consumer shader rendering remain pending; this does not establish broad native
allocation or OS-management compatibility.
