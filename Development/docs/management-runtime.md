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
The optional `jdk.management` OS extensions are not part of this integration.

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
