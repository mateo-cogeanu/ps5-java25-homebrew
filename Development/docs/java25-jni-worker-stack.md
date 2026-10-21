# JNI worker stack preparation and fallback

A consumer capture completes VM creation and actual C1 preflight. Its play row
fails before the worker callback emits any stage or Java/server exception. The
old start/join caller discarded the worker phase and native error code, so this
capture does not prove whether attribute initialization, pthread_create or
attachment failed. Do not describe a specific syscall errno as observed here.

The reusable JNI worker now offers prepare(), called before VM allocation
pressure to initialize separate ordinary and direct-stack pthread attributes.
The ordinary path remains first with its8MiB requested stack. Only on PS5, after
pthread_create returns EAGAIN with errnoENOMEM, a page-multiple stack of at most
8MiB can use the existing JVM_PS5MapNativeThreadStack C ABI/shared direct ledger.
Storage is zeroed and set with explicit stack attributes/guardsize0. No executable
mapping or kernel default guard is fabricated. Runtime0110 exposes a stack-
purpose mapper so VM guard-page removal uses existing stack subrange handling
instead of replacing direct storage with anonymous MAP_FIXED. The same exact
unmap ABI handles cleanup. The callback follows real
AttachCurrentThread, uses its own JNIEnv and DetachCurrentThread.

This worker has one explicit stack mapping per Job; it does not use the VM's
internal thread-stack reaper. Native join must complete through TLS destructors
before the matching VM unmap is called. Failed join leaves the live ownership
and started flag; failed unmap retains storage and blocks reuse. Allocation,
attribute, create, attach and detach errors remain failures. Cached attributes
last for the Job's process lifetime (the consumer uses a singleton); no attribute
reuse occurs while its worker is live. A start failure rolls back the stack or
retains it if cleanup fails. No new memory pool, larger shared budget or smaller
worker stack is introduced.

The stage string identifies ordinary attribute/stack/create, direct allocation/
attribute/create, Attach/DetachCurrentThread, join and cleanup. Consumers should
save that stage and numeric code. A start failure is now actionable even when
Java has not run and therefore cannot produce an exception report. This change
is both a pressure-path repair candidate and missing-diagnostics repair; the old
capture cannot distinguish the original start failure's precise cause.

Host tests run the actual header against a real JVM/pthreads and controlled
native API failures: ordinary attach/callback/distinctJNIEnv/detach, forced late
attribute ENOMEM after early preparation, ordinary native create ENOMEM followed
by real8MiB custom-stack pthread success, non-ENOMEM exclusion, map/create/join/
release faults, gated TLS-destructor proof of join-before-free and retained
ownership. The direct-stack test supplies controlled real mappings behind the
VM memory ABI; it does not retest the already separately covered shared ledger
or PS5 kernel behavior. Actual0110VMABI/shared-ledger ASan/UBSan checks also cover stack-purpose tagging,
8MiBcap/page gates,guard-subrange zero/uncommit/recommit/adjacent data and exact
release. TargetHotSpot compiles; linking/package checks establish the actual VM
ABI binding. FullPS5 pressure/stack guards/TLS/attachment/lifecycle remain pending.
