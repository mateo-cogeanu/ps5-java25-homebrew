# Direct native termination diagnostics

The diagnostic link wrapper list includes `abort`, `exit`, and `_exit`. These calls can bypass JNI's VM abort/vfprintf callbacks, leaving no `VM ABORT` or HotSpot fatal report. Each wrapper persists its direct return address, thread identity, status, an in-image anchor for load-base calculation, and the prior in-memory native call/stage record. It then delegates to the original noreturn function with unchanged status. Termination during trace IO delegates without trying to log recursively. No crash recovery, signal handling, allocation backend or server semantics change.

This covers references rewritten by the diagnostic executable's linker. It cannot promise interception of kernel kills or calls wholly inside separately loaded modules. A normal exit marker does not establish a crash. Missing markers do not identify the cause.

Build 024 console evidence confirms pthread key updates return ENOMEM and the static fallback lets the affected threads pass handshake and enter Java; one then clears/returns. The later crash leaves neither SIGNAL/VM ABORT nor a current fatal report. The cause of that later termination is unrecorded. These hooks are additional diagnostics, not a claimed fix for that crash.

Host ASan/UBSan checks execute real wrapper logging with mocked noreturn delegates; verify all three destinations, original exit statuses, errno, disabled tracing and trace-IO recursion bypass. Existing memory/string semantics, signal context, per-thread isolation and bounded context checks also pass. Package validation checks linked wrapper symbols and actual rewritten abort call sites. PS5 termination evidence and real server ready/save/stop remain pending.
