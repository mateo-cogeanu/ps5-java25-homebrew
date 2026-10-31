# Returned pthread error controls the owned-stack retry

Patch0133 corrects the PS5 Java/compiler thread stack fallback gate. After the
existing bounded native retries return EAGAIN, it tries the existing bounded
owned-stack path regardless of errno. pthread_create reports errors by its return
value; an unchanged/stale errno must not disable recovery. Other returned errors,
VM/watcher/GC threads and successful native creation retain their behavior.
See [pthread_create return contract](https://man.openbsd.org/pthread_create.3).

No resource limit is lifted: the retry still calls actual pthread_create, uses
requested stack size,64 slots/32MiB, the shared native-direct ledger, joined
retirement and conservative failed-cleanup ownership. Process quota/metadata
failure may still refuse. Added trace lines distinguish unavailable/invalid
requests and slot/budget exhaustion; existing map/create/reap traces remain.

Consumer171 terrain logs show EAGAIN for Sodium Async Cull Thread and Vitrail
compile worker4, followed by OutOfMemoryError and emergency world shutdown.
The earlier voice-thread abort does not recur in the readable report; audio
unavailability remains. The live VM trace/status files were denied by the console
FTP service, so whether0133's gate caused this exact refusal is unproven. Do not
claim the observed terrain freeze fixed until physical172 validation.

Actual extracted gate matrix passes with errno0/ENOMEM/EACCES, returned errors,
thread kinds, original requested sizes and entry arguments. Real1024KiB owned
stack host tests pass220 lifecycles, TLS destructor/join-before-free, refusal,
cleanup failures and budget controls under ASan/UBSan. Target HotSpot rebuild
passes. PS5 world entry with shaders on/off, save/reload, voice and endurance are
pending. Raw reports remain local; no release or Store approval implied.

Follow-up: Safari HTTP retrieval succeeded. The complete171 native trace reaches
32MiB of live owned stacks with eight further native refusals before emergency
shutdown. The old errno gate did run in that trace (errno ENOMEM); it is not the
observed cause. See [opt-in budget134](java25-thread-stack-budget.md).
