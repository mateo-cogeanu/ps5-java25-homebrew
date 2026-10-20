# Shared direct-memory fallback for native ZIP and image buffers (0102)

The raw allocator's0101direct-memory backend is confirmed in a consumer's PS5
run:2064mappings/2000releases at the last trace sample,3309568held bytes,
10059776peak observed held bytes and zero reported direct failures. This is
mapping/release evidence for that run, not a universal capacity/cache/stability
claim. The consumer still stops after native Deflater.init raises OutOfMemoryError
while creating a compressed chunk-save stream. Shutdown then fails to decode the
cold java/nio/file/Path$1.class image resource and reports player-save failures.
The harness correctly fails; a client observes server closure and refused reconnect.
Raw reports and personal/account/address details remain local.

## Scope and ownership

0102 exposes two PS5-only C ABI functions from the VM: JVM_PS5MapNativeMemory
and JVM_PS5UnmapNativeMemory. Native ZIP and temporary image-resource allocation
now retry anonymous-map ENOMEM through these functions. They use the SAME0101
ledger,2048slots and128MiB held-byte budget as raw HotSpot allocations, rather
than creating independent pools per translation unit or library. No JavaThread,
JNI transition, safepoint or VM heap allocation is required by these functions;
image loading can use them during early startup.

Successful libc and anonymous allocation paths remain unchanged. Each native
buffer retains its existing aligned ownership prefix, with an otherwise-unused
low bit tagging direct-backed storage. Release clears the tag to recover the
exact mapping length and invokes the shared owner. libc/page/direct frees are
never mixed. ZIP calloc retains overflow checks, zeroing and caller errno; image
buffers retain exact checked decoding and do not publish bytes after failure.
VM helpers preserve errno on success, report real failure otherwise and report
shared direct counters outside the ledger lock. API/budget/cleanup refusal
retains0101's ownership/failure contract, including leaked ownership on failed
kernel cleanup until process exit.

The change covers z_stream ownership, zlib private Inflater/Deflater allocations,
image compressed-input/intermediate decode buffers and existing image ZIP paths
using those callbacks. Java heap/metaspace/code-cache mapping, compiler settings,
Java library classes and game artifacts do not change. Other native-library
allocators remain outside this repair; no universal OOM or persistence guarantee.

## Verification

The host JNI test registers the complete actual Inflater/Deflater natives. With
libc and anonymous mapping forcibly refused, it executes the actual exported VM
bridge and actual shared ledger over a controlled kernel model using real aligned
storage. Raw/wrapped roundtrips and real compressed ZipFS create/read operations
pass. Refusing direct allocation at partial stream initialization still raises
genuine OOM and releases earlier allocations. This supplements unchanged normal
and page-backed controls; the kernel model is not actual PS5 execution.

ASan/UBSan covers actual allocation zeroing/alignment/overflow/errno and1024zlib
lifetimes. Actual JIMAGE/ZIP tests under ASan/UBSan cover simultaneous input/output/
zlib direct fallback, partial-budget refusal without publishing caller bytes,
cleanup, and exact extracted Path$1/HTTPS/DTLS bytes. Existing short/EINTR/EIO/EOF,
truncated/corrupt decode, index-only and desktop controls pass. Actual Java/native/
JNI image handoff retains the old MAP_ALL failure reproduction and passes corrected
PS5 and desktop modes. Exact0102forward patch application matches target source;
HotSpot/java.base native rebuilds and the two exported symbols are checked.

Pending PS5: native compression/image paths under joined-load pressure, shared
mapping/release/failure counters, actual player save/rejoin and world-save
completion, latency and sustained stability. Existing passing milestones are
preserved. The consumer will test a short session before later endurance.
