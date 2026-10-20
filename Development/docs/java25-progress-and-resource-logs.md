# Class-loading progress and native resource samples

Read-only log sharing exposes `/class-load.log` and `/process-usage.log`, with corresponding previous-report routes. Session initialization archives existing diagnostics and removes the originals only after a successful copy. Relaunch leaves them intact. The collector downloads both into the local ZIP.

Consumers can enable HotSpot's built-in class-load logger to `/download0/java25-class-load.log` using uptime/thread decorators and `filecount=0`. The last successfully loaded class is progress evidence, not necessarily the class or operation that failed. No class verification rules change.

`process_usage.hpp` appends one fixed-stack, descriptor-written sample when the consumer requests it. The server probe invokes it on its UI thread when the once-per-second elapsed display advances. It calls the actual OS `getrusage(RUSAGE_SELF)` and records return/errno or raw maximum-RSS, page-fault and CPU-time counters. It does not call JNI from that thread. OS `ru_maxrss` units and the process/container memory limit are not assumed; high-water RSS is not current free memory. An unsupported query is logged as unavailable. UI scheduling means samples are best effort, not a precise one-second timer.

Build 025 leaves no direct native termination or fatal-signal marker. Raw logs remain local. Its current startup section contains 272930 successful verifier fallback mapping messages, over 21MiB of text. Patch 0051 keeps the first 8 successful messages and every 1024th afterward, includes the success-event counter, and always retains existing mmap-failure messages. Atomic static storage avoids compiler TLS/heap initialization. Allocation, validation, release and error propagation are unchanged. Removing known diagnostic IO overhead does not establish the crash cause.

Validation: native HTTP/collector ASan/UBSan checks new report archive/removal, downloads, allowlist and existing behavior; actual host resource sample and write failure preserve errno. Java25 accepts the class logger option and emits class records. Actual verifier allocator under ASan/UBSan performs 1200 forced fallback mappings, emits 9 success records, retains a mapping-failure record, preserves errno and cleans every mapping. Target java.base-libs builds successfully; PS5 telemetry and crash resolution remain pending.

A consumer JNI `vfprintf` hook must honor non-console FILE targets. Redirecting every stream to the startup capture leaves the class-log file empty even though class records appear in startup.log. The Minecraft consumer corrects this routing separately; the runtime logger itself is unchanged.


## Bounded thrown-exception diagnostics (consumer087)

The fixed allowlist now also serves `/exceptions.log` and
`/exceptions-rotated.log`, plus matching previous-run routes. Consumers can use
HotSpot's standard `-Xlog:exceptions=info` with `filesize=8M,filecount=1` to
retain the active file and one rotated file (about16MiB total, with possible
single-record overshoot). Exceptions that applications catch without printing
may then have VM throw-site/handler evidence. This includes expected exceptions;
a thrown exception alone is not a failure diagnosis. This diagnostic setting can
add I/O overhead and is not a performance acceptance configuration.

Session initialization archives both files and clears them only after successful
copy; reopening the app alone preserves them. The collector includes both current
files and records missing files in its manifest. The actual HTTP/collector test
checks exact binary downloads and archival of both files under ASan/UBSan.
No runtime exception handling or application bytecode is changed.
