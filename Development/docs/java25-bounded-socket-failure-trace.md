# Optional bounded socket failure diagnostics

Development patch0123 adds opt-in diagnosis for native socket creation, bind and
listen failures whose callers may catch IOException without logging it. It is
active only with both `sun.nio.fs.ps5Sandbox=true` and
`ps5.net.traceBindFailures=true`. It does not change socket behavior or repair a
failure. Default behavior is unchanged.

IOException constructors call a static helper that captures a separate Throwable
stack; no partially initialized subclass methods are invoked. Only stacks with
`sun.nio.ch.Net` socket/bind/listen frames qualify. At most32events per JVM print
a fixed error category and at most12class/method frames with `PS5_HOST_IO`.
Exception text, addresses, user data and credentials are never printed by this
helper. Original exception identity, message, cause and stack remain intact.
Diagnostic failures are swallowed so they cannot replace the original exception.
The shared runtime contains no consumer/game-specific class matching.

Validation: `python3 tools/test_java25_socket_failure_trace.py` patches the real
IOException class into host Java25, generates40actual conflicting ServerSocket
binds, checks the32event limit, both property gates, category and secret omission,
and retained exception messages/stacks. The target `java.base-java` build passes.
Host results do not establish PS5 hosting success. A consumer must reproduce its
failed operation on console and retrieve current-run diagnostics. Frozen runtime
milestones and original game JARs are unchanged.
