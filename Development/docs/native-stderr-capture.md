# Opt-in native stderr capture

`java25/probe/native_stderr.hpp` supplies `ps5::native_stderr::begin(path)` for a
consumer that needs actual native-library messages,including stderr writes that
Java System.setErr does not intercept. Call once before native services start.
It opens the caller-supplied path for append,duplicates its descriptor onto2,
and makes the existing stderr stream unbuffered. stdout and Java streams are
unchanged. No remote address or client filter is embedded. This is a title-lifetime
redirect;it does not automatically restore descriptor2.

Success returns0 and preserves errno. Open/dup errors are returned truthfully;
failed open/dup preserves descriptor2. A setvbuf error returnsEIO after descriptor2
has been redirected;the caller should report setup failure rather than claim
complete capture. When open returns descriptor2 itself,it remains open. Open and
dup retry EINTR. The helper does not promise crash recovery,complete logs after
system termination,or capture of all kernel/GPU diagnostics.

For the standard report routes,after begin_session use write_note to create
`/download0/probe-native-stderr.log` with build/run identity,then pass that path
to the helper and check its return. The consumer controls when capture starts.
The read-only server offers `/native-stderr.log` and `/previous-native-stderr.log`
using fixed paths. A new explicitly started session archives the old file and
removes it only after successful copy;merely relaunching the app leaves it intact.
The collector includes both files;older/non-participating probes can return404.
Native library output can be verbose;keep raw reports local as other logs are.

Validation:

```sh
python3 tools/test_native_stderr.py
python3 tools/test_probe_log_share.py
python3 tools/test_probe_report_writer.py
```

The helper test uses actual native stdio and raw descriptor2 writes in host
children,exiting with _exit to bypass stdio cleanup. It checks append,stdout and
errno preservation,and failed-open behavior under ASan/UBSan. Report-server tests
check both endpoints in the ZIP collector and native-report session archiving,
plus existing allowlist/large binary/disconnect behavior. Actual PS5 descriptor
routing and resulting driver diagnostics remain pending. This tooling change
requires only consumer app recompilation;it changes no JVM image or frozen pass.
