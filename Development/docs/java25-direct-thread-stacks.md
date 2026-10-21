# Owned Java thread stacks (0105)

A PS5 startup capture gets past the4MiB non-class metadata reservation using0104,
then ordinary pthread_create refuses512KiB Java thread stacks with EAGAIN and
errnoENOMEM.0105adds an ownership-safe fallback for this specific refusal.
The exact SDK internal allocation is still unknown; supplying a stack does not
guarantee that the SDK can allocate its remaining thread metadata.

Ordinary creation/retries stay first. Only Java threads with final EAGAIN and
errnoENOMEM can use this fallback. A native reaper and64separate attribute objects
are prepared early in os::init. The reaper uses an ordinary128KiB stack. If it
cannot start, fallback stays unavailable; original failure is propagated.

Fallback stacks use the existing shared direct-memory ledger, with an additional
32MiB stack-held budget and64owner slots. Stack size is unchanged and backing is
zeroed. Separate persistent attributes carry the explicit stack, zero SDK guard
size and joinable state; normal attribute leases are not modified. HotSpot's
normal Java guard/protection/stack registration remains. Stack ranges have their
own ledger purpose tag; logical guard uncommit zeroes/protects the owned pages
instead of replacing part of a physical direct mapping with MAP_FIXED.

The wrapper only marks that its entry returned. A process-lifetime native reaper
joins that thread before releasing the mapping and physical memory, so native
TLS/C++ destructors finish first. No stack is freed by its own thread. The reaper
skips entries that have not returned. A join/cleanup failure retains ownership,
slot and budget; creation/allocation failures roll back when safe. Non-returning
entry paths such as pthread_exit/cancellation cannot publish completion and
retain their bounded slot/backing until process exit. No attempt is made to
infer thread death from an entry return or a failed join. This fallback is
internal to HotSpot-created Java threads, not a generic pthread replacement.

Validation: actual owner/helpers over real512KiB custom-stack pthreads and
controlled kernel storage under ASan/UBSan. Gated TLS destructors prove no unmap
before join completes;220lifetimes reclaim fully. Allocation/attribute/create/
join/physical-release faults, slot/stack budgets and stack-purpose/guard uncommit
are checked. Existing metadata lifecycle, attribute-domain/800thread, pthread
release-check, raw direct fault/concurrency and historical-prefix controls pass.
Exact0105patch application and targetHotSpot build pass. Host tests control reaper
scheduling; they do not run the full target VM or prove PS5 SDK guard/TLS/NMT/
join behavior. Actual SDK success, native headroom, GC and stability are pending.
