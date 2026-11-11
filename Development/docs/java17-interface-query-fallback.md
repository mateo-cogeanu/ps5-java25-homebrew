# Java 17 interface query fallback on PS5

The build 032 console reports reproduce the `OutOfMemoryError` in native
`NetworkInterface.getAll` with about 42 MB of Java heap in use. The trace
records an explicit libjava OOM request without identifying the allocation.
Java 25 previously encountered resident `getifaddrs` failure and a secondary
native allocation in the error formatter. See
[Java 25 interface query history](java25-interface-query-fallback.md).

Patch 0016 ports the Java 25 route parser to Java 17. PS5 IPv4, IPv6 and link
address queries use fresh kernel route data when the resident query returns
ENOMEM, EACCES or fails without setting errno. The fallback owns its mappings
and checks the route record layout and bounds. The native error formatter now
uses stack storage for suffixes up to 256 bytes including the terminator, so
a short diagnostic can survive libc allocation pressure.

The target build, route parser and last-error JNI checks passed on the host.
The original 032 failure point within enumeration remains unconfirmed.
Consumer 033 requires a PS5 row 3 and title-screen test.
