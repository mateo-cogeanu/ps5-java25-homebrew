# Network_Probe — first passing Java networking milestone

Frozen **PPSA99868 01.000.003**, confirmed ALL PASS by the user on
2026-10-13, PS5 firmware 13.60.

The four rows initialize the native runtime, create the real Java 25 VM,
run Network25 and destroy the VM. The Java fixture checks security
configuration, numeric IPv4 loopback, a framed TCP UTF-8 echo using a Java
worker, two-way UDP datagrams/source ports, and nonblocking NIO channels
with real selector readiness. Tests use ephemeral ports and timeouts.

[Download the passing app ZIP, checksum and console validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Network_Probe-v01.000.003).
Extract and install the entire PPSA99868 folder through your existing
homebrew scan workflow. Close the app fully before replacing its files.

## Reproduce

With the pinned toolchain/dependencies prepared, run from this directory:

```sh
python3 tools/java25_source.py --bootstrap --build-hotspot --build-base
python3 tools/package_java25_jni.py --network
python3 tools/test_java25_network.py
python3 tools/test_java25_network_trace.py
python3 tools/test_java25_socket_blocking.py
python3 tools/test_java25_security_path.py
```

The source pin, 31 OpenJDK patches, fixture and packaging scripts are
retained here. See validation.json for exact results and the ZIP SHA-256.
Only the diagnostic checkpoint callback is registered from the probe;
network functionality uses real Java and target net/nio implementations.

This folder stays frozen. Later source changes go into ../Development.
LAN/remote connectivity, DNS, IPv6, TLS, virtual-thread polling and
sustained/concurrent load are not established by these loopback tests.
Source files retain their upstream licenses and notices.
