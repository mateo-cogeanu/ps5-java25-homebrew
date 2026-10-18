# Guarded C1 execution candidate

The reusable `java25/tests/ps5probe/JitWarmup25.java` gate requires mixed mode,
C1 level 1 and one compiler thread. It checks an integer kernel against eight
independently computed 64-bit results, waits at most 30 seconds for that exact
kernel's level-1 compilation record, then checks another 32,768 calls. A missing
compiler, interpreter mode, pre-existing kernel record, missing compilation
record or incorrect result fails explicitly. It does not silently fall back.
The consumer must enable a fresh unified `jit+compilation=debug` log and invoke
the gate once before heavy workload launch. A small kernel pass does not establish
correct compilation of every method, signal recovery or long-running stability.

The log-sharing allowlist now exposes `/jit.log` and `/previous-jit.log`. New-run
initialization archives then removes the old current log; simply relaunching the
app preserves reports. The command-line collector includes the current JIT log.
No target addresses are embedded in the inbound service.

Host validation: `python3 tools/test_java25_jit_warmup.py` executes actual C1
compilation with an 8 MiB code cache and checks results; interpreter, stale-log
and absent-log controls reject. `python3 tools/test_probe_log_share.py` checks
actual HTTP delivery and session archival under ASan/UBSan. These host results
are not PS5 JIT validation. Target C1 execution, native budget, compiled Java
exceptions, gameplay and two-hour stability remain pending. Frozen milestones
remain unchanged.
