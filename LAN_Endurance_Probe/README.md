# LAN_Endurance_Probe — IPv6 LAN and sustained external traffic

Frozen **PPSA99872 01.000.000**, confirmed ALL PASS on 2026-10-14,
PS5 firmware 13.60. All six rows passed on the actual console.

[Download the passing app ZIP, checksum and validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/LAN_Endurance_Probe-v01.000.000).

## Run

1. Extract and install the entire PPSA99872 title folder using ShadowLoader.
2. Double-click tools/start_lan_endurance.command on the Mac. Enter the
   current PS5 IPv4 address and its IPv6 link-local address from Settings.
   Use valid IPv6 notation, including a double colon where shown. The
   helper selects the Mac LAN interface scope for link-local addresses.
3. Keep Terminal open and run all six console rows in order:
   initialize runtime, create VM, IPv6 LAN, TCP load, UDP load, destroy VM.

TCP and UDP load each take about one minute. The console app has no preset
device addresses. The IPv6 row verifies actual external IPv6 TCP/UDP peers,
UTF-8 exchanges and helper confirmations. The TCP row requires four
concurrent external clients, at least 60 seconds/128 verified 4096-byte frames
per worker. UDP requires at least 60 seconds/128 verified 512-byte round trips
and final confirmation. Actual counters appear in Terminal.

The passing run used a manually supplied link-local IPv6 address. Automatic
ARP/NDP discovery was inconclusive; it is optional and does not define the
console result. tools/check_lan_ipv6.command diagnoses discovery separately.
Helper logs stay local under build/java25.

## Reproduce

With the pinned dependencies/toolchain prepared:

```sh
python3 tools/package_java25_jni.py --lan-endurance
python3 tools/test_java25_lan_endurance.py
python3 tools/java25_lan_endurance_client.py --ps5-ipv4 YOUR_PS5_IPV4 --ps5-ipv6 YOUR_PS5_IPV6
```

See validation.json for the exact tested package SHA-256. This snapshot
stays frozen; future changes belong in ../Development. Routed/global IPv6,
hours-long endurance, simultaneous mixed TCP/UDP load, broader TLS and
JIT stability remain unverified.
