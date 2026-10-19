# PS5 index-only module image

## Confirmed077fatal allocation

The current077session is VM ABORT. At97.573seconds JVM elapsed time the C1
CompilerThread0 fails to allocate32664native bytes for Chunk::new(arena.cpp219)
while compiling SerializableChunkData.read(808byte method). The PS5 trace shows
the32768byte raw fallback mapping fails with ENOMEM, including the pool-prune
retry. This is native allocation failure, not a captured Java heap OOM or
network failure. The recorded maxrss_raw520448 and generic JVM memory summary
must not be interpreted as proof of the host's memory limit.

The user reports nearly perfect speeds before the crash, with some mob/damage
lag. Consumer077health samples stay near20TPS but full-GC pauses remain. Its
vanilla NBT SYNC/replacement/backup/readback check passes; that does not prove
actual player serialization or save/rejoin persistence. Raw reports remain local.

## Runtime repair0099

The PS5 reader previously used the64bit default of keeping the entire image
resident. Because file-backed mapping had crashed earlier, it copied the whole
compressed image into anonymous memory.0099sets memory_map_image=false only
for PS5, using the upstream index-only/resource-read path instead. The lookup
index retains the existing anonymous/read-only copy; no file-backed mmap is
reintroduced. Compressed resource bytes are read on demand into0098scoped
buffers, inflated through0097checked zlib allocation, and released. All modules,
image compression, bytecode checks and native ownership remain.

Current image:28085766bytes. Lookup index:1000498bytes. With16KiBtargetpages,
the old resident copy is28098560bytes and the new index1015808bytes, saving
27082752bytes(25.828125MiB). This is a reduction in this persistent copy, not
a proven reduction in total peak RSS or a guarantee against all native OOM.
Per-resource buffers add transient allocations and resource file reads.

The PS5 osSupport::read path completes partial pread results, retries EINTR,
rejects negative/overflowing offset/length and propagates EOF/real errors.
Concurrent reads use explicit offsets; there is no shared seek position.
Desktop behavior is unchanged.

## Checks and remaining validation

Actual release-mode native reader/inflater pass ASan/UBSan: real mapped index
under2MiB, zero file-backed mappings, exact Object/String/HTTPSverifier/delegate/
SSL/DTLS/JFR/desktop resource bytes, short reads/EINTR, EIO/EOF with no published
compressed-resource bytes, independent input/output allocation refusal,
cleanup/recovery, tiny terminal output and existing zlib failure controls.
0099applies exactly to recorded077source. HotSpot/java.base native target build
passes. Host checks are not PS5 execution.

Consumer078retains176MiBheap,NewRatio15,guardedC1/2MiBcompilationbudget,world/view/
simulation/player/OP/security/timer settings and the existing game derivative.
PS5startup, class/resource read latency, actual native headroom under joined
play, player-save persistence, mob/damage lag and two-hour stability are pending.
The compiler still has the existing fatal behavior if native allocation is
exhausted; this repair reduces a known resident cost rather than introducing
a compiler bailout mechanism. Frozen passing milestones remain unchanged.
