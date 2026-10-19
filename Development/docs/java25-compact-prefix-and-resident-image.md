# Native allocation prefix and resident module image

Development patches0093–0094 address native-memory pressure. They are candidates;
console validation remains pending. Frozen passing snapshots remain unchanged.

The current consumer crash report records a VM-thread native malloc failure for
4088bytes during SerialCollectForAllocation. Both ordinary allocation and the
64KiB/16KiB anonymous fallback failed. The requesting GC subroutine is not
identified by the available native frames. This is native exhaustion, rather
than evidence of Java heap exhaustion or a proven fixed title memory limit.

Patch0093 replaces the raw allocator's three-word/max-alignment prefix with two
aligned words. Requested size remains explicit. The second word encodes libc,
an aligned slab pointer tagged in its low bit, or page-rounded mapping length.
Allocation, resize, failure preservation, matched release and NMT preinit bridges
continue through the same backend. Other platforms retain their original paths.

`tools/test_java25_native_heap.py` exercises actual allocation bodies with forced
failures, alignment, all classes, concurrency and a narrow NMT contract model
under ASan/UBSan. `tools/test_java25_native_prefix.py` compares the actual prepatch
and patched allocators for261080 simultaneously live allocations approximating
the crash distribution. It saves2162688mapped bytes in the host alignment model
and4194304bytes in the16-byte alignment model, with complete cleanup. These are
repeatable host models, not measured console savings or full HotSpot NMT tests.

The PS5 image reader deliberately copies the module image into anonymous memory;
file-backed mapping remains disabled because of earlier console failures.
`tools/java25_boot_image.py` now defaults to `--compression zip-6` rather than
retaining every resource uncompressed. No modules are removed. For the current
consumer module set this reduces the resident image from about63MiB to27MiB.
Compression trades resource-decode CPU time for a smaller resident allocation.

Patch0094 resolves ZIP_InflateFully directly from the resident libzip on PS5;
the embedded library handle cannot be passed to desktop dlsym. Other platforms
retain their normal lookup. The final package must retain that ZIP symbol.

`tools/test_jimage_host.py` compiles the actual PS5 reader/decompressor branches
and compares decoded Object/String/TLS/desktop classes and JFR metadata with the
host jimage extraction, exercises repeated opens, verifies zero file mappings,
and rejects anonymous mapping failure. The image builder separately checks
target-generated security/JFR resources. `tools/test_java25_jfr_image.py` resolves
the linked metadata and creates238JFR types on a host JVM. Target HotSpot and
java.base-libs rebuild successfully. Console decode, startup, respawn, memory
headroom, latency and sustained stability remain unvalidated.
