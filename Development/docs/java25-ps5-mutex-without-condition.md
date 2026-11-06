# PS5 condition variables for HotSpot monitors

ProsperoCraft 01.000.230 stopped in `PlatformMonitor` condition initialization
with ENOMEM after all 8,192 initialized relative condition variables were leased.
The failure occurred on a C1 compiler thread with C2 and Parallel GC enabled.
That identifies the exhausted pool. The report does not identify all lease
owners or establish why the native fallback allocation returned ENOMEM.

Patch 0139 lets PS5 HotSpot's lock-only `Mutex` construct its platform lock
without initializing a condition variable. `Monitor` and direct platform
monitors still initialize and release their native condition variable, with
the same clock, wait, notify and ownership behavior. The reserve sizes and
non-PS5 paths are unchanged.

The host pthread regression exercises the actual platform constructors and
destructors under ASan and UBSan. It creates and destroys a lock-only instance
with every relative condition leased and verifies that a real platform monitor
acquires and releases a condition. Existing exhaustion, reuse and wait/signal
checks run for each reserve policy. Console Fabric startup, world entry, save
and Vanilla regression are pending.
