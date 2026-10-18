# Native library lookup scratch allocation

Consumer 066 creates a C1 VM and compiles about 800 methods, then reports a bare
OutOfMemoryError at the combined management preflight. No JIT warmup success,
server readiness or timed phase is recorded. Class loading stops before the
management implementation classes appear. The startup log shows platform-string
fallback for 17 bytes immediately after that stage, consistent with the
libmanagement.so path. This narrows the failure to management initialization;
the exact allocating instruction is not captured, so the cause remains a
candidate until the console retest.

NativeLibraries.c still allocated its library-name copy and JNI_OnLoad/OnUnload
symbol buffer directly with malloc. Both produce a message-less native OOM on
refusal. Patch0090 gives only those temporary names a PS5 libc-first, mapped
fallback, with explicit backend ownership, overflow/page rounding checks,
matching cleanup and preserved successful errno. Both-backend failures remain
real errors. Prefix/suffix behavior, actual symbol lookup, JNI version checks,
OnLoad/OnUnload calls, unknown-library results and desktop behavior stay intact.
There is no global allocation replacement or library-discovery bypass.

`python3 tools/test_java25_native_library_names.py` compiles the actual lookup
and symbol-construction JNI bodies in isolated mixed-mode host JVMs. It checks
libc success, fallback for either/both buffers, first/second mapping denial,
Java-string allocation failure, unknown/short/oversized/null names, load/unload
symbol construction and 512 repeated lifetimes with no live allocations/maps.
The unchanged desktop body reproduces the bare OOM when malloc is denied.
The symbol resolver is an explicit host fixture; console ABI and real resident
library discovery still need validation. Tests run with -Xcheck:jni and UBSan.
The target java.base-libs rebuild and consumer package are checked separately.
Frozen passing snapshots remain unchanged.
