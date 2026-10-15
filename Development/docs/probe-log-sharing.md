# Probe log sharing

Development probes can include `java25/probe/log_share.hpp` and start the native
read-only HTTP service with `ps5::log_share::start()` (port 8765 by default).
It listens on available IPv4 interfaces without a preset device address or client
filter. Start it independently of Java VM creation, and stop it at normal app exit.
The service works while a test blocks the menu. A process crash stops the service;
relaunch the app to retrieve persisted files before running another test.

Open `http://<PS5-IP>:8765/` in a browser on the same LAN. Substitute the console's
current IPv4 address. Keep the app open. The screen shows whether the listener
started or its socket error. The app serves files through its own filesystem
access, so FTP does not need access to its sandbox mount.

For a ZIP containing available logs and a manifest of byte counts and SHA-256
checksums, run from the runtime workspace:

```sh
python3 tools/fetch_probe_logs.py <PS5-IP> --output build/probe-logs.zip
```

The collector reports missing files individually; a missing abort or server log
can be normal before that event/test. A partial transfer is discarded. Existing
ZIPs are never overwritten. Generated logs stay out of Git.

Only these exact routes exist: `/startup.log`, `/vm-trace.log`, `/server.log`,
`/abort.txt` and `/exception.txt`, plus the index page. There is no directory
browser, path input, upload, deletion, remote command or CORS access. Responses
are uncached and streamed with a fixed initial file length; actively growing logs
may contain an incomplete final line. Refresh after the test for later output.
The read-only service has no authentication or encryption: other devices on the
same reachable network can read these diagnostics while the app is open. Use it
on the intended LAN; do not forward this port to the Internet. Logs are never
automatically sent to GitHub or another service.

Host validation: `python3 tools/test_probe_log_share.py` exercises the actual C++
handler with sanitizers, binary/large streaming, allowlist rejection, method and
header limits, disconnected clients, service start/stop and the ZIP collector.
Console download and availability during a JVM failure require actual PS5 testing.
