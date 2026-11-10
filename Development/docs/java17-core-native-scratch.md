# Java 17 class loader and image scratch

Consumer 019 recorded successful native fallback mappings during Minecraft
startup, then a libjava out-of-memory request and SIGILL. The retained PS5
address resolves to the deliberate trap in the linked application array
allocator after a null return. The exact caller and the libjava allocation
site remain unconfirmed.

The active PS5 Java 17 runtime now uses the paired native scratch allocator
for libjava ClassLoader-owned temporary buffers and libjimage-owned arrays.
The same allocator continues to serve the legacy verifier. The Java heap,
bytecode validation and JIMAGE format are unaffected. Exhaustion retains
the respective Java exception and resident C++ failure behavior.
Consumer 020 requires physical row 3 and title-screen validation.
