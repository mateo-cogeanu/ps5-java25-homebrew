# LAN_DNS_Probe — passing cross-device LAN and DNS milestone

Frozen **PPSA99869 01.000.000**, confirmed ALL PASS by the user on
2026-10-13, PS5 firmware 13.60. The helper log independently confirms
TCP and UDP requests from the PS5 peer rather than only host self-tests.

The five rows initialize the runtime, create the Java 25 VM, test LAN
TCP/UDP echo, resolve example.com through Java DNS and destroy the VM.
The LAN fixture verifies framed UTF-8 TCP bytes, UDP bytes and source
address/port against an external Mac echo helper.

[Download the passing app ZIP, checksum and validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/LAN_DNS_Probe-v01.000.000).
Extract and install the full PPSA99869 title folder. Close the app fully
before replacing its files.

## Configure the LAN test

The exact passing package retains the tested endpoint. For your own LAN:

1. Start the helper on your Mac's IPv4 LAN address:

   ```sh
   python3 tools/java25_lan_server.py --bind YOUR_MAC_IP --port 38025 --background
   ```

2. Set `lan.host=YOUR_MAC_IP` and `lan.port=38025` in the extracted
   `PPSA99869/assets/java25/probe.properties`.
3. Keep your Mac awake and run the five app rows in order. DNS needs a
   working resolver; it does not contact a website.

Helper logs/PID live under build/java25 and are excluded from Git. Stop
the helper after testing. LAN and DNS results are separate rows.

## Reproduce

With the pinned toolchain/dependencies prepared, run from this folder:

```sh
python3 tools/java25_source.py --bootstrap --build-hotspot --build-base
python3 tools/package_java25_jni.py --lan --lan-host YOUR_MAC_IP --lan-port 38025
python3 tools/test_java25_lan.py
```

Source, fixtures and 31 OpenJDK patches are retained here. See validation.json
for console results and the exact tested ZIP SHA-256. Endpoint edits change
the package/configuration from that archived build; the checksum describes
the untouched release ZIP.

This snapshot stays frozen; future work goes into ../Development. Inbound
LAN server acceptance, TLS, IPv6, DNS edge cases and sustained/concurrent
load remain unverified. Retain upstream source licenses and notices.
