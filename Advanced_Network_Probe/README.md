# Advanced_Network_Probe — HTTPS, IPv6 and concurrent traffic

Frozen **PPSA99871 01.000.002**, confirmed ALL PASS on 2026-10-14,
PS5 firmware 13.60. All six rows passed on the actual console.

[Download the matching app ZIP, checksum and validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Advanced_Network_Probe-v01.000.002).

## Run

Extract the entire PPSA99871 title folder into your ShadowLoader scan location.
Close the app fully before replacing files. Run these rows in order:

1. Initialize embedded runtime.
2. Create the Java 25 interpreter VM.
3. HTTPS to https://example.com/ with bundled CA trust and standard hostname verification.
4. IPv6 ::1 TCP/UDP loopback.
5. Four concurrent TCP clients: 128 verified 4096-byte frames each, then 256 verified 512-byte UDP round trips.
6. Destroy the VM.

HTTPS needs Internet and a correct system clock. No Mac helper or preset
device IPs are used. IPv6/load use loopback and do not establish IPv6 LAN
reachability or extended LAN endurance.

## Reproduce

With the pinned dependencies and toolchain prepared:

```sh
python3 tools/package_java25_jni.py --advanced-network
python3 tools/test_java25_crypto_policy.py
python3 tools/test_java25_advanced_network.py --crypto-patch build/java25/crypto-policy-test/patch
```

The snapshot retains 32 OpenJDK patches. The bundled policy adaptation
reads and parses standard limited/unlimited policy files directly under
the PS5 sandbox; it preserves their restrictions and rejects required-file
failures. Host tests verify untrusted certificate and hostname rejection.
Those negative TLS cases still need console testing.

See validation.json for the exact ZIP SHA-256 and console scope. This snapshot
stays frozen; future work belongs in ../Development. Broader TLS configurations,
IPv6 LAN, prolonged network load and JIT stability remain unverified.
