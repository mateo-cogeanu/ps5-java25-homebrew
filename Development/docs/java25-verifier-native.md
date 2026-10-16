# Remaining verifier native allocations and thread-failure evidence

Patch 0043 routes all malloc/calloc/free calls local to legacy check_code.c
through a PS5 libc-first, anonymous-RW-page fallback with an aligned backend
header. This includes class-hash arrays/rows/names, constants, superclass and
exception tables, bytecode copies, the longjmp cleanup stack, and CCpool blocks.
calloc retains zeroing with overflow checks; cleanup matches free/munmap and
preserves errno. Method-pool lifetime fixes remain. VM-owned UTF strings still
use JVM_ReleaseUTF, never the local allocator. No bytecode checks are bypassed.
Other platforms retain their original allocation calls.

Build 018's server log identifies verifier site 506 in initialize_class_hash
for org/joml/Matrix3fc: either class-hash calloc returned NULL. The previous
fallback covered only CCpool blocks. It also reports a separate SeedGenerator
native thread failure. Successful file-I/O and platform-string fallbacks are
recorded in this run. No signal record/abort was captured; no server readiness
or world save/stop is established.

Patch 0044 adds allocation-free native trace lines for OSThread allocation,
pthread_attr_init, stack-attribute setup and failed pthread_create attempts.
The current thread warning does not distinguish these paths, so its cause
remains unresolved pending a target log. No security seed substitution,
verification bypass or unsafe thread-attribute fabrication is introduced.

Checks: test_java25_verifier_pool.py runs actual allocator/pool reset and
cleanup under ASan/UBSan, forced heap/mapping failures, zeroing/overflow and
constrained budget. test_java25_verifier_native.py runs the full real legacy
verifier through host JNI with UBSan, all libc allocations refused, real mapped
storage, and mapping refusal during root/class-hash/constants initialization.
Every invocation checks mapped-allocation cleanup. Matrix3fc, Matrix3f,
Matrix4f and MemUtil$MemUtilNIO are covered. Target HotSpot/libverify build and
package checks are separate from required PS5 console validation.
