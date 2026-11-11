# Java 17 directory streams on PS5

Build 042 passed the JCE policy directory type and readability checks.
The first provider failure moved to opening the directory stream in
the original policy setup. The Java stack identifies the
`opendir` branch of `UnixFileSystemProvider.newDirectoryStream`.
The native reason that libc refused to open the stream was not recorded.

Patch 0023 adapts the Java 25 directory reader to Java 17. PS5 NIO
opens a real directory descriptor and reads entries through
`sceKernelGetdents` into a page-aligned buffer. It tries the alternate
`sceKernelGetdirentries` ABI only on an eligible initial error, before
returning any entries and after a successful rewind. It checks record
sizes and terminators, preserves native errors, and closes and unmaps
the stream on release. The descriptor form takes ownership only after
success. Java still enumerates and parses the genuine policy files.

The target build and ordered patch replay passed. Host Java 17 loaded
JCE and JSSE through the actual patched JNI functions with a host
adapter supplying directory records. The same fixture exercised
`Files.walk`, Unicode names, symlink following, and failed opens.
Sanitizer checks covered malformed records, interrupted calls,
alternate ABI selection, and descriptor ownership. The PS5 kernel's
actual results and Minecraft startup remain pending.
