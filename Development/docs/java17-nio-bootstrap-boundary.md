# Java17 default filesystem bootstrap boundary

Consumer004's JNI and native Java-entry checkpoints show DefineClass, native
registration, run-method lookup and Java entry succeed. It stops at the first
Path.of call before Java stage-file creation, management, consumer graphics binding
or original application entry. The scoped recorder now captures SIGSEGV and its
bounded context. The PC is not yet assigned to a specific generated/resident code
region; the exact native cause is unproven. Raw traces remain consumer-local.

Upstream UnixFileSystem's default constructor compares its configured directory
to native getcwd unless sun.nio.fs.chdirAllowed is true. In true mode it always
resolves native relative paths against its configured Java default directory and
skips that optimization. This is genuine upstream configuration, with real path/
permission/error handling; no fabricated getcwd success or replacement classes.
The consumer005policy selects that mode; policy belongs in its launcher/harness,
not a runtime default. Whether it bypasses the failing path needs PS5 validation.

The runtime17patch adds fixed native breadcrumbs at UnixNativeDispatcher.init
entry/completion and before/after getcwd. Each preserves errno, writes fixed labels
through bounded open/write/close and never emits caller paths. No NIO return value,
capability, syscall selection or default policy changes. Non-PS5 paths are no-ops.
Complete source replay/refusal and target core/native builds pass. The exact host17
consumer Java/JNI bootstrap with the mode reaches original application's argument
gate; host PS5-specific graphics binding remains explicitly skipped. This does
not validate actual target filesystem or application/world behavior. Frozen17/21
startup and working25consumer remain preserved; no release acceptance follows.
