# Tiered compilation warmup

The existing JitWarmup25.check entry point validates C1 level 1 with one compiler thread.
The opt-in checkTiered entry point requires mixed mode, tier 4 and two compiler threads.
It requires a current log entry for the ordinary compiled kernel and verifies its results.
Host JDK 25 demonstrated a level 4 entry using Parallel GC. Target compiler behavior and
performance remain console checks. This helper does not select a collector or change the
runtime's default compiler policy.
