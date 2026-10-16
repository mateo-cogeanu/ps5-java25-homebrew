# Low-volume crash tracing and fatal-report retrieval

Build 020 successfully reserved a 16 MiB aligned metaspace region through the
new exact-size hint path. The user reports a whole-app crash and relaunch.
The saved VM trace ends in ordinary successful metadata allocation, with no
SIGNAL record or abort report. The server console is empty and the exception
file remains a placeholder. Absence of the previous thread warning does not
establish successful seed initialization, and no server readiness is claimed.
The termination cause is not identified by this capture.

Patch 0047 adds allocation-free thread lifecycle markers: create request,
attributes acquired, before/after pthread_create, native entry/current-thread
setup, handshake, before Java run and run return. Thread/object identifiers
correlate creator and child events. A returned thread object is never
subsequently dereferenced by the new diagnostic line.

Metadata sampling is opt-in through ps5_vm_set_metadata_interval. The default
continues full logging for other probes. Before VM creation the consumer now
sets interval 1024. Routine ENTER/DONE Metadata lines update the per-thread last
stage on every event but persist one in 1024. FAIL lines and explicit thread,
reservation and signal markers remain unsampled. Native call tracing uses quiet
mode throughout the consumer VM/preflight/server phases, retaining per-thread
call arguments/completion without a disk write for every string/memory call.
This removes a substantial diagnostic I/O load; it is not a proven crash fix.

The reusable HTTP allowlist and collector add /hs-error.log for
/download0/hs_err_java25.log plus a previous-report link. The consumer's
-XX:ErrorFile now uses that fixed name. Starting a new session archives an
existing real fatal report before removing it; archive failure preserves the
source and marks the session incomplete. No placeholder fatal report is created.
Relaunch alone preserves reports. If the OS terminates the process without
HotSpot generating a report, the endpoint correctly remains unavailable.

Host checks cover actual trace sampling counts, last-stage retention, errno,
unfiltered failure/thread lines, partial/EINTR writes and open failure; native
call/signal context and static target storage remain checked. The native HTTP
handler/collector and real fatal-report archive/download path pass sanitizer
checks. Target compilation and package checks are separate from console tests.
Build 021 must still establish a useful failure location or real ready/save/stop.
