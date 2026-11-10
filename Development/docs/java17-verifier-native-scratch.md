# Java 17 legacy verifier native scratch

Consumer 018 reproduced the class initializer OutOfMemoryError with no
HotSpot OOM, memory commit refusal or libjava OOM markers. The legacy
verifier can produce a contextual message while bypassing those paths.
That makes verifier scratch allocation a candidate, with the exact
failure still unconfirmed.

The PS5 Java 17 verifier now uses the existing native heap allocator
for allocations owned by check_code.c, including calloc zeroing and
the paired frees during normal completion and longjmp cleanup.
The allocator tries libc first and falls back to its existing native
mappings. Foreign buffers still use their original JNI cleanup.
The verifier's OOM return emits a fixed trace before the original throw.
The Java heap limits, verification rules and other runtimes are unchanged.
Physical test build 019 remains pending.
