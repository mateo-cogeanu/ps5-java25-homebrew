# Conservative TCP availability when the PS5 sandbox denies FIONREAD

Patch0124 changes only Net.available in the PS5 build. Saved Minecraft skin
failure reports show BindException: Permission denied from this JNI entry while
HttpURLConnection reads the original publisher texture. The launcher already
passes the authenticated profile; replacing game classes or rewriting texture
URLs is unnecessary for this concrete failure.

When FIONREAD fails with EPERM/EACCES/ENOTTY/EOPNOTSUPP, query SO_TYPE. Only a
confirmed stream socket can return a conservative estimate of zero. No bytes
are consumed, no socket flags change, and normal reads/EOF/errors remain real.
Successful ioctl counts are unchanged. Failed descriptor/type verification,
datagrams and other errno values keep the original exception. Restore the
original errno after the type query. Non-PS5 behavior is unchanged. A zero
available() estimate does not mean EOF and is permitted by the stream contract.

The host regression registers the exact JNI function in isolated real JVMs,
forces the sandbox ioctl errors, and checks unconsumed TCP bytes, real successful
counts, invalid descriptors, nonfallback errors, datagram rejection and desktop
behavior. A fragmented131071-byte HTTP response is read byte-for-byte through
HttpURLConnection/readAllBytes despite denied availability. UBSan/XcheckJNI are
used; this is not PS5 networking evidence.

Incremental cached PS5 java.base-java/java.base-libs rebuild passes. Standard
java25_source.py --build-base stops at pre-existing patch0009 reverse/apply
checking against this evolved source cache; it does not establish a clean source
replay. The new patch reverses cleanly against the cached Net.c, and only Net.o/
libnio are rebuilt by the incremental target. Frozen passing snapshots remain
untouched. Actual PS5 skin/TCP/HTTP/error behavior still requires console tests.
ProsperoCraft101 integrates the rebuilt native runtime and owns the launcher,
controls and game validation; no Minecraft JAR is modified.
