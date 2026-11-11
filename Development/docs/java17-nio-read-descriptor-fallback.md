# Java 17 NIO read checks on PS5

The build 041 preflight reported that OpenJDK's JCE could not confirm
its cryptographic policy directory. The matching class line identifies
the check that requires both `Files.isDirectory` and `Files.isReadable`.
The signed archive contains the original policy files. The retained
report does not say which filesystem check failed or provide its errno.

Patch 0022 brings the Java 25 descriptor fallback to Java 17's PS5
NIO following-stat and read-access checks. After a pathname call
returns EPERM, a non-creating, nonblocking read open must succeed.
The fallback takes metadata from the opened descriptor, accepts only
regular files and directories, and checks close. It preserves normal
pathname results and never infers write, execute, or no-follow results.
The JCE policy directory and parsing checks remain in effect.

The PS5 Java 17 target build and ordered Java 17 and 21 patch checks
passed. A host sanitizer fixture used the actual fallback with real
directories, files, links, a FIFO, and injected EPERM, EINTR and close
errors. Successful and non-eligible pathname calls bypassed fallback.
The exact PS5 JCE failure mode and continuation are pending in build 042.
