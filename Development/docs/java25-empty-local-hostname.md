# Empty local hostname fallback (0112)

A PS5 title can receive a successful native gethostname call with an empty output. Previously both Java IPv4 and IPv6 implementations returned that empty string to InetAddress.getLocalHost, which then attempted DNS for an empty hostname and failed. Logging libraries can report this as an initialization error.

Patch0112 applies the existing upstream localhost fallback to empty successful results on PS5 only. Native errors already use localhost. Valid nonempty names and existing truncation/null termination remain unchanged, as do nonPS5 implementations. InetAddress.getLocalHost already handles localhost through its real loopbackAddress implementation without external DNS. This does not replace external hostname lookups, fabricate interface addresses, change bind behavior, or repair missing external DNS configuration.

Host validation compiles the actual IPv4 and IPv6 JNI function bodies with controlled gethostname, registers them in a real host JVM, and tests empty success, errors, valid names and unterminated maximum buffers. It checks PS5/nonPS5 controls and the actual Java loopback shortcut under IPv4 and IPv6 preferences with XcheckJNI/UBSan. Target java.base native build and exact patch reverse check pass. Actual PS5 local-host detection and application startup remain pending. Frozen snapshots are preserved.
