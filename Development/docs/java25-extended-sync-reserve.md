# Optional extended native synchronization reserve, patch0131

Consumer141's fatal report identifies checked `monitor mutex_init` returning
ENOMEM12 while Controlify's FFM initialization generates a hidden Java class.
The retained VM trace records all4096 configured mutexes both initialized and
leased, with a matching attribute pointer and configured state2. This establishes
reserve exhaustion followed by failed native initialization; it does not establish
a leak or a universal JVM monitor demand. Consumer reports stay in ProsperoCraft.

Patch0131 adds `JVM_PS5SetExtendedSyncReserveEnabled(int)` as an explicit bootstrap
policy. The default still initializes4096 mutexes,4096 relative-clock conditions
and2048 absolute-clock conditions. Enabling before initialization requests8192
mutexes and8192 relative conditions; absolute conditions stay2048. The setter
returns EBUSY once priming starts. It must be called on the bootstrap thread
before JVM startup, not concurrently with initialization. Fixed metadata arrays
have room for the larger maximum in both modes; native extra objects are created
only when explicitly enabled. There is no change to Java heap/GC, lock ownership,
attribute domains, native wait/deadline operations or process-wide pthread calls.

Existing native priming success counts remain authoritative: requesting8192 does
not prove the platform initialized every object. Leases use only initialized
entries. Once a selected pool is exhausted, the original native initialization
fallback and checked failure reporting remain; no failed lock is treated as
successful. Returning leases does not destroy the process-lifetime native pool.
The capacity remains bounded. No automatic growth or arbitrary allocator fallback
is introduced. Frozen milestone source/binaries remain unchanged.

Host ASan/UBSan tests run actual pooled native mutex/condition objects in separate
default and extended processes. They deny late native initialization and verify
full capacity/exhaustion/reuse, exact attributes and clock domains, locked destroy,
real wait/signal/timeout,8,000 concurrent lease lifetimes and final native cleanup.
They also reject post-prime policy changes. Target IR checks continue to exclude
heap allocation, compiler TLS and lazy guards from lease metadata. The actual
HotSpot rebuild/export/object hash checks are recorded separately; host checks
are not PS5 FFM/mod compatibility or startup acceptance.

PS5 priming counts, late class/monitor creation, consumer Fabric startup/world/
save/endurance and regression remain pending. Consumer142 owns the pin, explicit
policy and package audit. Store/publication decisions remain separate.
