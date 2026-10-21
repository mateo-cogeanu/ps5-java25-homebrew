# PS5 selector user-event wakeup (0107)

A PS5 capture reaches readiness and advances at20TPS in five unjoined samples
through121seconds. On a later connection attempt, selector wakeup fails in
IOUtil.write1 with IOException/ENOMEM. The exception becomes InternalError and
terminates network event loops. This is an observed pipe-write failure, not a
Java heap exhaustion diagnosis: the failed result reports about100MiB free.
The direct ledger's final sample holds0xff8000bytes of128MiB with zero failures;
that does not establish the cause of kernel pipe allocation failure.

0107adds a PS5-only native user-event backend to KQueueSelectorImpl. Registration
uses EVFILT_USER with EV_ADD|EV_CLEAR once per selector. Wakeup triggers the
registered event through NOTE_TRIGGER, without a pipe write or userspace buffer.
The native method returns the actual platform filter value rather than assuming
that macOS and FreeBSD assign the same number. Poll dispatch recognizes that
filter; existing interrupt locking/coalescing governs trigger and reset. Closing
the kqueue owns event cleanup; no pipe descriptors are created or closed on this
backend. Ordinary channel readiness, registration and cancellation remain intact.

Non-PS5 builds return0 and retain the pipe backend. PS5 registration rejection
EINVAL/ENOTSUP/ENOSYS also retains the pipe backend and records a diagnostic;
this fallback does not repair the observed pipe ENOMEM. Other registration
errors throw IOException and release the constructor's existing resources.
Triggers retry EINTR; genuine errors still propagate. No ENOMEM is ignored and
no timer polling or fabricated successful wakeup is introduced. The underlying
pipe-memory cause and other resource-pressure paths remain unresolved.

Host validation runs the actual patched Java selector and actual new JNI bodies
against macOS kqueue in an isolated JVM with -Xcheck:jni/UBSan. It covers1200
wake-before-select/blocked-select/coalescing rounds, socket readiness and cancel,
100close races with captured thread errors, EINTR retry, explicit unsupported
fallback, registration ENOMEM and trigger EIO. Targetjava.base classes/native
libraries compile. These controls establish host event semantics, not PS5
EVFILT_USER availability, firmware behavior or full runtime memory stability.

Next console validation must confirm the selected-backend marker, then startup,
connection, repeated idle/active wakeups and orderly stop under native pressure.
The original memory failure remains possible if the kernel rejects user events.
