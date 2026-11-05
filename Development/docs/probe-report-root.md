# Optional bootstrap report directory

The shared native log service offers explicit constructor-free
`ps5::log_share::configure_root(absolute_directory)` before `start()`. It relocates
only the existing fixed URL/file allowlist into bounded resident buffers and sets
the default archive/session directory. It does not create or mount storage, change
filesystem permissions, map arbitrary URLs to paths, or relocate caller-supplied
tables. The caller verifies access and configures its report writers consistently.

Default users retain the original `/download0` table and session directory.
Invalid relative/traversing/trailing/oversized roots are refused without changing
the selection. `start()` freezes configuration even after stop or a listener
failure; subsequent attempts return EBUSY. Bootstrap is single-threaded and
publication precedes worker creation. No new native/Java allocation, constructor,
VM policy, sandbox privilege or legacy milestone change is introduced.

`python3 tools/test_probe_report_root.py` checks default preservation, invalid
root refusal, actual relocated HTTP bytes, default session/archive placement and
late reconfiguration rejection under ASan/UBSan. Existing full HTTP/collector and
actual64KiB pthread O0/O2 stack/snapshot/stream tests pass. Consumer216 owns its
shared-directory access/fallback, reports/tmp/game path integration and physical
migration validation. Host routing is not PS5 permissions or storage acceptance.
