# Bounded report-server stack

The expanded512-row file-handle endpoint added a64KiB automatic array to the
shared HTTP handler. Exact consumer204 and205 target objects reserve0x11348
(70,472) bytes at handler entry, including requests for the index. This is a
stack regression introduced with the expanded report; it is unrelated to URL
selection or downloaded game code. Original host tests called the handler from
the larger main-thread stack and missed it.

The handler now keeps the64KiB full-snapshot buffer in fixed BSS, with an atomic
single-owner lease and503 for overlapping full snapshots. It releases ownership
after a failed send as well as success. Other endpoints remain independently
servable. Parsed request storage is reused for4KiB streaming and the small snapshot.
No heap/TLS allocation, native stack increase, URL allowlist, listening interface,
file ownership or report-size expansion is introduced.

`python3 tools/test_probe_log_stack.py` executes index,512-row snapshot, busy/refusal
and recovery,1MiB streaming, allowlist and descriptor endpoints on actual64KiB
pthread stacks at O0/O2. The existing HTTP/collector, file-activity and descriptor
writer tests remain applicable. Optional `--baseline-header-dir` replays an explicit
historical header at O0 as a negative control. macOS ARM64's optimized historical
handler uses a different layout; the exact original x86_64 O2 header also faults
on64KiB stacks, while the repaired header passes. Host faults do not by themselves
establish a PS5 faulting address or the actual server-thread stack size.

Consumer205 was reported to exit when its HTTP reports are accessed; FTP remains
available after reopening. No physical repair acceptance is inferred. ProsperoCraft
owns the rebuilt app and the separate original1.21.11 native-callback allocation
failure. Preserve original204/205 packages and reports; no release/Store action.

The rebuilt target handler frame is **5,704bytes** (0x1648), down from70,472bytes
(0x11348). Target compile/link/conversion pass; the report remains limited by the
same request/response bounds. See [scoped validation](validation/java25-log-share-stack-2026-11-04.json).
