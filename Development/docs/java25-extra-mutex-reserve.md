# Optional extra HotSpot mutex reserve

Patch 0138 adds the bootstrap-only JVM_PS5SetExtraMutexReserveEnabled option.
It requests 12,288 native mutexes. The default and existing extended
option keep their 4,096 and 8,192 mutex requests. Condition capacities
and lease ownership rules remain as before. Late requests return EBUSY.
The native prime count remains authoritative. A failed initialization
still returns its real error.

ProsperoCraft 229 reached 8,192 initialized and leased mutexes during
a Fabric startup. The next mutex initialization returned ENOMEM on
the C1 compiler thread in the tiered VM. The source of all leases and
the console's available native capacity remain open. The extra reserve
is intended to give this workload more headroom.

The actual synchronization pool passed host sanitizer tests at all
three capacities, including reuse, wait and signal, and injected native
allocation refusal. Target HotSpot built and the embedded object exports
the opt-in setter. The object is assembled with staged constructors by
tools/java25_embedded_hotspot.py. Console priming and workload validation
are pending.
