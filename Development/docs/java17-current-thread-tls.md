# Java 17 current-thread storage on PS5

Consumer builds 028 and 029 reach the original Minecraft 1.20 Main and
then raise SIGABRT during row 3. The PS5 context's saved RBX in both
reports matches HotSpot's compiler TLS descriptor for Thread::_thr_current
after applying the independently measured image load offset. Disassembly
of the linked SDK emulated TLS routine shows that it holds this descriptor
in RBX. The saved R12, R13 and R15 values match the abort branch after the
initial 128-byte per-thread address array allocation. They differ from
the branch that allocates the current-thread pointer's individual slot.
The reason the platform allocator refused the small request is unresolved.

Patch 0014 makes the existing HotSpot POSIX thread key the sole current-thread
provider on PS5. The port already maintained that key for signal-safe lookup.
This removes compiler-emulated allocation for this pointer when a new worker
initializes or accesses its current thread. Other compiler TLS variables
retain their existing behavior. Thread attach, detach and JNI destructor
restoration retain their native key semantics. The port reuses Java 25's
bounded current-thread fallback for failed native key updates, verifies
readback and handles a refused clear without restoring a deleted thread.
Other platforms retain the existing JDK 17 path.

The source-replay checks and the actual HotSpot method and POSIX backend
fixture passed. The fixture exercises native refusal, false-success
readback, detach, JNI destructor restoration, signal lookup and fallback
capacity. Target fixture IR uses the native key without compiler TLS.

Consumer 030 recorded a native key update returning ENOMEM and its
allocation-free fallback storing the thread pointer. It then aborted
at a different emulated TLS descriptor during row 3. See
[compiler TLS for the Java 17 consumer](java17-compiler-tls.md).
