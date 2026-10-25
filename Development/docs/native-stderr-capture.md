# Opt-in native stderr capture

`java25/probe/native_stderr.hpp` supplies `ps5::native_stderr::begin(path)` for a
consumer that needs actual native-library messages,including stderr writes that
Java System.setErr does not intercept. Call once before native services start.
It opens the caller-supplied path for append,creates a FILE with fdopen,and
configures it as unbuffered before publishing it as stderr. It never calls dup2:
an actual PS5 title refused that call with EPERM during client048 diagnostic
setup. An inspected upstream SDK uses the same stream-replacement workaround:
[platform/src/klog.c at7a82030](https://github.com/mihawk-99/PS5_PayloadSDK/blob/7a82030dcff6457936d75be97f52aa509b770e1f/platform/src/klog.c).
That source is reference evidence,not a dependency upgrade.

Success returns0 and preserves errno. Open/fdopen/setvbuf errors are returned
truthfully;any unpublished stream/descriptor is closed and the previous stderr
pointer is retained. It does not close descriptor2 or its previous FILE. This is
a title-lifetime stream redirect with no automatic restoration;call once before
concurrent native use. stdout is unchanged. Raw write(2,...) output is **not**
captured. Native fprintf(stderr,...) and equivalent FILE users are captured,
which includes the driver diagnostics motivating this helper. A library that
cached the original FILE before replacement may still write to that original
stream. Consumers should record setup failure and continue when capture is
optional;diagnostic setup must not prevent useful application startup.
The helper does not guarantee logs after system termination or crash recovery.

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
children,exiting with _exit to bypass stdio cleanup. It checks stdio capture/append,raw descriptor2/stdout unchanged,
errno preservation,and failed-open behavior under ASan/UBSan. Report-server tests
check both endpoints in the ZIP collector and native-report session archiving,
plus existing allowlist/large binary/disconnect behavior. Actual PS5 descriptor
routing and resulting driver diagnostics remain pending. This tooling change
requires only consumer app recompilation;it changes no JVM image or frozen pass.
