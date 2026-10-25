# Optional GC and safepoint report transport

The shared read-only probe server now exposes `/gc.log` and `/gc-rotated.log`
for `/download0/java25-gc.log` and its `.0` rotation. Matching `/previous-gc.log`
and `/previous-gc-rotated.log` routes expose the preceding run. Session startup
archives both files before removing current copies;app/menu relaunch alone does
not initialize a run. The collector includes all four optional reports and
records missing ones as unavailable. No device address is embedded in the app.

This adds transport only. Existing probes do not enable logging automatically.
A consumer can opt into HotSpot unified file logging with a finite rotation;
log contents are observations,not a console pass or a memory diagnosis. Raw
reports stay local. Probe session/build identity must accompany retrieval.

Validation: `python3 tools/test_probe_log_share.py` passed actual HTTP/collector
streaming and current/previous GC archival tests under ASan/UBSan. Target compile
and exact consumer logging settings are validated by that consumer's build.
Target filesystem/rotation/last-phase visibility still require console testing.
No JVM implementation,heap policy or passing snapshot changed.
