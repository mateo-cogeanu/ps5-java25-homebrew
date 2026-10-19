# Checked PS5 kernel entropy

Patch0096 fixes the concrete failure captured in consumer072. Its saved SIGSEGV
has PC0. The stack top, adjusted using the matching signal-handler anchor, is
exactly the return address after the direct sceRandomGetRandomNumber call in the
seed JNI function. The matching ELF GLOB_DAT identifies that import. This proves
an unresolved service import was invoked, rather than Java heap exhaustion.
The earlier071failure remains unproven;072introduced the direct dependency.

The runtime now obtains entropy from the PS5 kernel kern.rng_pseudo interface
through sysctlbyname, already used elsewhere in the runtime. Fixed64-byte stack
storage bounds each request. It validates the return code and actual byte count
before transferring only the requested bytes to Java. The kernel API pointer is
checked too; an unresolved import becomes a Java error instead of a null call. Errors, insufficient
responses and oversized counts throw ProviderException; there is no substitute
seed or threaded fallback. Scratch storage is cleared through volatile writes.
Other Unix platforms retain URL seeding. No optional service import/module load
is needed, and the standalone/embedded direct libSceRandom dependency is removed.

The kernel interface is also used by the independently maintained
[OpenNOW PS5 entropy implementation](https://github.com/Portablelle/OpenNOW-PS5/blob/main/src/random.cpp).
Our JNI implementation is independent; no code from that file is incorporated.

The actual Java/JNI host regression covers concurrent requests, batching, DRBG,
first/later OS errors, kernel-query failure, insufficient responses and oversized
response counts, an injected null kernel API, plus the desktop URL control. It runs with JNI checking and
UBSan using a mocked kernel boundary backed by host entropy. Target native
rebuild passes. These do not establish PS5 kernel-query availability or entropy
quality, successful TLS/server startup, or the earlier071cause. Those remain
console checks. No server-JAR transformations are added by this repair.
