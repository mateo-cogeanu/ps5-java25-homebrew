# PS5 thread attributes and exact-size metaspace reservations

Build 019 identifies pthread_attr_init returning ENOMEM (12), with errno zero,
before pthread_create. Later it records a successful 16 MiB reserve followed
by two failed 32 MiB reserves and SIGSEGV. The aligned reservation path releases
an unaligned successful mapping, then normally over-reserves size+alignment.
The last completed call is a 21-byte memset in ConstantPool::allocate; it is
not the faulting instruction. The signal PC is outside the application image;
the later crash's causal chain is not proven.

Patch 0045 initializes a bounded pool of 32 real pthread_attr_t objects when
HotSpot first creates a thread, before server loading exhausts libc allocations.
A creator borrows one exclusively and passes its address without copying the
opaque object. Each create sets detach state and stack size as usual. It returns
the slot after pthread_create has consumed it. A lease returns it on early
failure too. Objects remain allocated for process lifetime; concurrent pool
exhaustion uses normal pthread_attr_init/destroy with real failure propagation.
Initial pool-creation failure does not fabricate an attribute. Stack allocation,
pthread creation and security seed behavior retain their actual OS semantics.
The existing failure-stage diagnostics remain.

Patch 0046 applies only to non-executable mtMetaspace reservations. After an
unaligned exact-size mapping is released, it tries up to eight nearby aligned
runtime-derived addresses through os::attempt_reserve_memory_at. The BSD API
uses mmap hints and releases unexpected-address results; no MAP_FIXED mapping
is added. Occupied mappings are preserved. The normal oversized reservation
remains if every hint fails. Size, alignment, ownership and NMT use existing
OS reservation APIs. A successful hint records bytes, alignment and address.
This addresses the observed size+alignment reservation pressure; neither this
host result nor the previous SIGSEGV proves a PS5 crash resolution.

Host checks: test_java25_thread_attributes.py uses the actual lease under
ASan/UBSan, forced late/initial attribute-init failure, all slots occupied,
local fallback cleanup, early-return reuse, stack-size reset and 800 actual
pthread creations from eight concurrent creators. test_java25_metaspace_hints.py
extracts the actual reservation decision function and uses real non-replacing
host mmap/munmap operations, simulating oversized-backend refusal. It checks
alignment, occupied-address contents, hint exhaustion and cleanup, plus the
unchanged initial-failure/executable/other-tag routes. The host setup arranges
an unaligned region; this is not a measurement of PS5 native-memory capacity.
Target compilation/package checks and actual PS5 validation are separate.
