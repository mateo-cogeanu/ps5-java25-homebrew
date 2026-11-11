# Java 17 compiler TLS on PS5

In consumer 030, HotSpot's native current-thread key returned ENOMEM and
its allocation-free fallback stored the current thread. The subsequent
SIGABRT's saved registers resolve to the compiler TLS descriptor for
HotSpot's `_lookup_shared_first` symbol lookup flag. As with 028 and 029,
the remaining registers match the SDK's failed first 128-byte address
array allocation. The underlying libc allocation pressure remains unresolved.

The LTS packager's explicit `--compiler-tls` option for a Java 17 consumer
reuses the existing PS5 compiler-TLS adapter. It validates the SDK object
hash, then rebinds six allocator and native key references only in a copy
of that object. The Java 17 backend pairs allocation, growth and release
through HotSpot's existing libc-first heap with mapped-slab fallback.
The shared bounded registry retains compiler TLS when a native key update
fails, verifies readback and reclaims state after a native destructor,
successful join or proven thread identity reuse. The target SDK archive,
ordinary allocator calls and standalone LTS defaults retain their current
behavior.

Host fixtures cover a forced 128-byte libc allocation refusal, failed
growth with both routes denied, bytes preserved across successful growth,
native key refusal and stale native values, 800 thread lifecycles and
cleanup. The signed build 031 includes the rebound SDK member, target
backend and matching source. Exact PS5 row 3 and title-screen checks remain
pending.
