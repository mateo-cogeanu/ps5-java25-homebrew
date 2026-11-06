# Bounded PS5 HotSpot method profiling locks

ProsperoCraft 01.000.231 reached the loading screen and then stopped after
leasing all 12,288 reserved native mutexes. The next native initialization
returned ENOMEM on a C1 compiler thread during tiered startup. The trace
identifies the exhausted pool and the platform lock constructor. It does not
break down all lease owners.

HotSpot's original MethodData path can allocate one native mutex per profiled
method. On PS5, patch 0140 instead initializes 64 padded mutexes during VM
startup and selects a stable stripe by the address of the nonmoving metadata.
Each stripe retains the existing rank and no-safepoint locking protocol.
Different methods on the same stripe serialize. Method profiling and trap data
remain separate, and the existing release/reacquire path continues to select the
same lock. Other platforms retain per-method locks. The native reserves and
collector/compiler settings are unchanged.

Host checks use the patched stripe functions with real pooled pthread mutexes.
They cover 32,768 simulated MethodData addresses and concurrent updates with
only 64 leases, and rerun the existing condition and mutex fault tests.
Fabric startup, world entry, saves and Vanilla frame pacing need PS5 validation.
