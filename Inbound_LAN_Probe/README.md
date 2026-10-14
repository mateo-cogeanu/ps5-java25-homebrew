# Inbound_LAN_Probe — passing Java LAN listeners

Frozen **PPSA99870 01.000.000**, confirmed ALL PASS on 2026-10-14,
PS5 firmware 13.60. All five rows passed: runtime initialization, Java 25
VM creation, inbound TCP, inbound UDP and VM destruction.

TCP accepts a LAN connection and verifies framed UTF-8 data, a reply and
a client confirmation. UDP receives UTF-8 data and verifies a reply plus
a confirmation from the same sender. The app binds all IPv4 interfaces
on TCP 38026 and UDP 38027, without preset device IPs or client filters.

[Download the passing package, checksum and validation](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Inbound_LAN_Probe-v01.000.000).

## Run

1. Extract the complete PPSA99870 title folder into your ShadowLoader scan location.
2. Double-click `tools/start_inbound_client.command` on the Mac, enter the current
   PS5 address and leave Terminal open. Alternatively run:

   ```sh
   python3 tools/java25_inbound_client.py --ps5-host YOUR_PS5_IP
   ```

3. Launch the console app and run rows 1–5 in order. The helper should report
   TCP PASS and UDP PASS. Each console listener waits up to 25 seconds.

## Reproduce

With the pinned toolchain prepared:

```sh
python3 tools/package_java25_jni.py --inbound
python3 tools/test_java25_inbound.py
```

See validation.json for the exact passing package checksum. This snapshot
stays frozen; future changes go into ../Development. TLS, IPv6, sustained
load and concurrent inbound connections remain unvalidated.
