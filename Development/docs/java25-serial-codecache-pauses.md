# SerialGC pauses triggered by code-cache growth

The079console capture reaches normal-world readiness and an authenticated
join after Java/native image-reader alignment. The human reports shorter,
more frequent freezes. The available trace ends at roughly49seconds JVM
uptime, so it primarily covers startup and first join, not prolonged gameplay.

Five CodeCacheGCThreshold full collections occur at16.385,22.931,24.802,26.239
and33.534seconds, taking181.935,177.555,190.927,209.647and269.367ms. Total
1029.431ms. Trigger-time code-cache occupancy is37.117to57.227percent.
The521allocation-failure young collections total1269.837ms, maximum8.245ms;
three metadata-threshold full collections total134.402ms, maximum98.226ms.
Not every game/network stall can be assigned from this short capture.

## Existing runtime control

CodeCache::gc_on_allocation in code/codeCache.cpp requests a collection when
compiled-code growth since unloading exceeds SweeperThreshold(default15percent
of reserved capacity, scaled by free capacity after that level). Under SerialGC
this requests a stop-the-world full collection even well below a full cache.
The separate StartAggressiveSweepingAt(default10percentfree) branch is checked
first. This behavior explains an avoidable source of repeated warmup pauses;
it is not evidence that all pauses share this cause.

The consumer080candidate sets SweeperThreshold=50.0 with its existing16MiB
cache. It keeps StartAggressiveSweepingAt=10 and UseCodeCacheFlushing=true,
SerialGC/heap/compilation limits and actual collection/allocation semantics.
No runtime source patch or compiler/GC safety removal is introduced. The tradeoff
is less eager code unloading and potentially greater cache occupancy before
collection. Heap pressure, metadata growth, later near-full cache cleanup,
synchronous file reads/saves and other stalls remain possible.

Host controls check supported flag parsing and retained aggressive cleanup.
Sequential C1 flat-world81-chunk20second consumer runs exercise readiness,
NBTsaveprobe, tick/save monitoring and clean stop, with cause-specific GC
comparison recorded in the consumer repository. Host timing does not establish
PS5 smoothness. The config targets measured repeated pauses; freeze-free
operation and full-duration memory stability are not proven. Frozen snapshots
remain unchanged; raw logs and identities stay local.
