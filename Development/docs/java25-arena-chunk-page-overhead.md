# PS5 arena chunk page overhead

Patch0071 uses a128-byte PS5 sizing allowance for the default32KiB chunk,
instead of the desktop64-bit40-byte allowance.
The default payload becomes32640 bytes; the target24-byte Chunk plus32-byte
raw allocator prefix fits32768 bytes. Optional NMT header/footer also fits.
The old target request was32752 bytes; adding the raw prefix made32784 bytes,
which rounded to49152 on the PS5's16KiB pages. Native allocation refusal can
therefore occur for a third page that the arena payload does not need.

The tiny, initial and medium chunk sizes remain unchanged. Existing
arena growth/pooling/alignment and real OOM behavior are retained. It trades
88 bytes of arena payload per default chunk for avoiding a16KiB mapping spill
on the fallback backend. Libc-backed allocations may also use marginally
smaller chunks. This is not a claim that an arbitrary32KiB request will succeed
on an exhausted console. Non-PS5 constants remain unchanged.

A PS5 target static assertion checks the real Chunk/raw-prefix/NMT-header/footer
layouts against the allowance. The actual raw allocator and os.cpp API test
uses the exact arena size enum, a Chunk layout contract and NMT model with a
16KiB page-size model. Under forced libc failure and32KiB mapping cap the new
request succeeds with tracking modeled off/on; the old32752-byte request
fails. All existing allocation/realloc/concurrency cleanup checks run under
ASan/UBSan. Host fixtures do not execute actual target NMT or prove available
console memory. Target build and console validation are recorded separately.
