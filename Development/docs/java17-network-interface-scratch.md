# Java 17 network interface allocations on PS5

Minecraft consumer build 031 returned `-1708` in row 3. Its retained
report shows a Java `OutOfMemoryError` from the native
`NetworkInterface.getAll` call during security provider initialization.
The Java heap held about 42 MB against a 195 MB maximum when the probe
reported the exception. The trace also records the successful compiler
TLS key fallback and a successful `DestroyJavaVM` return.

Patch 0015 routes allocations owned by `NetworkInterface.c` through
Java 17's paired native scratch allocator on PS5. It tries libc first,
then uses the existing mapped memory fallback. The platform's own
`getifaddrs` results still use `freeifaddrs`. If interface allocation
fails after allocating an address, the code releases the unlinked address
before propagating the existing error. Interface enumeration and address
conversion continue to use real platform data.

The target build and pinned patch checks passed. A host sanitizer fixture
exercised the actual node creation and cleanup code with the Java 17 heap,
including forced libc refusal, dual refusal, IPv4, IPv6 and partial
virtual interface allocation failures. Build 032 still needs a PS5
row 3 and title screen test. The original allocation site within
`getAll` and the underlying cause of libc pressure remain unconfirmed.
