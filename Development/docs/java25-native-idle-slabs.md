# Bounded idle native slabs and sampled success traces

A consumer 063 console run reaches authenticated world entry, then its measured
game-time progress falls to 330 ticks per 30 seconds (about 11 TPS). The captured
native trace contains 1,894 slab-creation messages and over 33,000 ENTER/DONE
phase messages. These counts establish avoidable allocation/diagnostic work;
they do not establish its share of total tick time. The consumer still uses
`-Xint`, and no JIT or overall performance pass is claimed. Raw reports remain local.

Patch 0087 keeps at most one empty mapped slab in each of the eight existing
size classes. All storage comes from the same real allocator; size/alignment,
headers, realloc and NMT contracts remain unchanged. No reserve is allocated
in advance. Retained idle capacity is bounded by 512 KiB, and excess empty slabs
are unmapped. Large mapping failure trims all idle slabs and retries the real
mapping once. Small mapping refusal trims idle slabs before the existing
minimal-page retry. Live slabs are preserved, including borrowed larger slots;
genuine failures remain failures. Locking covers ownership and cache lifetime.

The actual-header ASan/UBSan regression executes 10,000 allocation/free cycles
of the observed 4,088-byte size using one mapping. It checks one idle slab after
multiple slabs empty, pressure reclamation, all eight size classes, concurrent
lifetimes, compatible borrowing, failed realloc preservation, full explicit
trim, overflow and errno. The existing exact os.cpp entry-point fixture retains
its narrow NMT accounting model; this is not native host JMM validation.

Patch 0088 extends the existing configured successful-phase sampling to all
ENTER/DONE phase labels. Default tracing remains unchanged when sampling is
disabled. Last-stage context is updated before sampling, and signal-active
context, failure and thread messages remain unsampled. The actual trace-helper
test checks sampling, current context, signal override, partial/interrupted
writes, denied open and errno; target IR still checks no emulated TLS or
allocation in crash-context lookup. No failure signal or error is silenced.

Console allocator safety, native headroom and gameplay TPS improvement remain
pending. Consumer gameplay diagnostics separately record observed TPS, real GC
counter deltas and read-only hunger fields to distinguish lag from food-state
issues; they do not change hunger rules or food consumption.
