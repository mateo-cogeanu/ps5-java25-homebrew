<p align="center">
  <img src="docs/readme-banner.svg" alt="Java 25 on PS5 — native homebrew, one console test at a time" width="1200">
</p>

<p align="center">
  <a href="#milestones">Milestones</a> ·
  <a href="#try-a-passing-build">Downloads &amp; setup</a> ·
  <a href="#where-were-going">Roadmap</a> ·
  <a href="Development/">Development</a>
</p>

# Java 25 on PS5

An experimental **native OpenJDK 25 port for PlayStation 5 homebrew**, built and tested in small, reproducible steps.

This repository contains the **Java runtime port, platform adaptations and acceptance probes**. Java 25 bytecode execution, file I/O and JAR class loading have passed their tests on a real console.

> **Current progress:** nine passing milestones on PS5 firmware **13.60**, using interpreter mode. Multi-JAR dependencies, system class-path loading, resident JNI calls, HTTPS and IPv4/IPv6 networking are console-tested.

**Related project:** [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft) uses this runtime and tracks Minecraft-specific work and console milestones separately.

Development is testing a [shared native direct-memory fallback](Development/docs/java25-zip-image-direct-memory.md) for raw allocations, ZIP compression and image buffers. Raw mapping/release is observed on PS5; the ZIP/image extension passes host checks and target builds, with console validation pending.

Development also provides opt-in [native compression/database builds and descriptor diagnostics](Development/docs/java25-native-storage.md). Host checks and consumer target packaging pass; actual console integration remains pending. Core defaults and frozen milestones are unchanged. The [descriptor-first PS5 path update](Development/docs/java25-descriptor-first-paths.md) also removes repeated unsupported canonicalization calls and improves handle diagnostics; console save validation remains pending.

Development0126 adds an opt-in [bounded ZIP/JAR handle pool](Development/docs/java25-bounded-zip-handles.md) for immutable archives. Low-descriptor host tests and target builds pass. Basic console use/reopen is reported through the consumer114 integration; deletion and endurance remain pending.

## Milestones

Each milestone is a **frozen source snapshot** of a build that received **ALL PASS on the PS5**. Its release includes the matching app ZIP, SHA-256 checksum and console validation record.

| Milestone | Console result | Version | What passed | Download |
| :--- | :---: | :---: | :--- | :---: |
| [JVM_Startup](JVM_Startup/) | **ALL PASS** | `01.000.023` | Real VM startup, Java 25 arithmetic, Java thread start/join and VM shutdown | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/JVM_Startup-v01.000.023) |
| [IO_Probe](IO_Probe/) | **ALL PASS** | `01.000.004` | Relative paths, private-file creation, UTF-8 write/read, file size and deletion | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/IO_Probe-v01.000.004) |
| [ZIP_JAR_Probe](ZIP_JAR_Probe/) | **ALL PASS** | `01.000.000` | Stored/deflated ZIP entries, JAR manifest, JAR class loading and UTF-8 resources | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/ZIP_JAR_Probe-v01.000.000) |
| [Network_Probe](Network_Probe/) | **ALL PASS** | `01.000.003` | TCP/UDP IPv4 loopback, Java worker echo, nonblocking NIO channels and selector readiness | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Network_Probe-v01.000.003) |
| [LAN_DNS_Probe](LAN_DNS_Probe/) | **ALL PASS** | `01.000.000` | Outbound LAN TCP/UDP echo to a Mac, forward DNS lookup and VM lifecycle | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/LAN_DNS_Probe-v01.000.000) |
| [Inbound_LAN_Probe](Inbound_LAN_Probe/) | **ALL PASS** | `01.000.000` | Inbound LAN TCP accept and UDP receive/reply with verified UTF-8 exchanges | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Inbound_LAN_Probe-v01.000.000) |
| [Advanced_Network_Probe](Advanced_Network_Probe/) | **ALL PASS** | `01.000.002` | Verified HTTPS, IPv6 loopback, four concurrent TCP workers and repeated UDP round trips | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Advanced_Network_Probe-v01.000.002) |
| [LAN_Endurance_Probe](LAN_Endurance_Probe/) | **ALL PASS** | `01.000.000` | IPv6 link-local LAN TCP/UDP; four concurrent TCP clients and repeated UDP for at least 60 seconds each | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/LAN_Endurance_Probe-v01.000.000) |
| [Dependency_Probe](Dependency_Probe/) | **ALL PASS** | `01.000.001` | Manifest-linked JARs, services/resources, system class path and real resident JNI library calls | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Dependency_Probe-v01.000.001) |
| [Development](Development/) | **In progress** | — | Current source and upcoming probes; updated as changes are completed | [Browse source](Development/) |

Passing folders stay unchanged. New work goes into `Development`; a new milestone is frozen only after its console tests pass. A successful host build alone does not qualify a milestone.

## Try a passing build

1. Choose a milestone release above and download its **app ZIP**. The latest passing probe is **Dependency_Probe**; it needs no network or Mac helper.
2. Extract it and copy the **entire title folder** into the homebrew scan location used by your existing ShadowLoader setup.
3. Let the loader register the app, then launch it from the home screen.
4. Run the test rows **in order** (six for Dependencies, LAN Endurance and Advanced Network, five for inbound LAN and LAN/DNS, four for earlier probes). Use the **D-pad** to select and **X** to run a test. Close the app through the PS menu.

| App | Title folder |
| :--- | :--- |
| JVM startup | `PPSA99865` |
| File I/O | `PPSA99866` |
| ZIP / JAR | `PPSA99867` |
| Networking | `PPSA99868` |
| LAN / DNS | `PPSA99869` |
| Inbound LAN | `PPSA99870` |
| Advanced Network | `PPSA99871` |
| LAN Endurance | `PPSA99872` |
| Dependencies | `PPSA99873` |

The apps use separate title IDs, so you can keep the passing probes installed side by side. Keep all files inside each extracted folder, including its assets, runtime and licenses. Compare the ZIP against the checksum supplied in its release.

If a test fails, report the **app version**, **test row** and **full exception/code**. After a crash, relaunch and photograph the saved checkpoints.

## Where we're going

- [x] Start the native Java 25 VM and execute Java bytecode.
- [x] Test Java file I/O and controlled VM shutdown.
- [x] Read ZIP/JAR archives and load a Java class and resource from a JAR.
- [x] Test Java TCP/UDP loopback and NIO selector readiness.
- [x] Test outbound IPv4 LAN TCP/UDP and forward DNS resolution.
- [x] Accept inbound LAN TCP connections and receive/reply to UDP datagrams.
- [x] Verify HTTPS, IPv6 loopback and bounded concurrent/repeated TCP/UDP traffic.
- [x] Exchange IPv6 link-local LAN traffic and run 60-second external TCP/UDP workloads.
- [ ] Expand TLS coverage, routed IPv6 and longer mixed network workloads.
- [x] Load manifest-linked JAR dependencies, service providers and system class-path applications.
- [x] Resolve and call a real resident JNI test library.
- [ ] Expand application dependency coverage, filesystem behavior and external native-library loading.
- [ ] Validate JIT execution, garbage collection and sustained workloads.
- [ ] Improve JNI and native-library compatibility for Java applications.
- [ ] Test broader Java APIs, error handling and repeated application runs.

**Latest passing networking probe:** [LAN_Endurance_Probe](LAN_Endurance_Probe/), `PPSA99872` version `01.000.000`. Start the [Mac launcher](Development/tools/start_lan_endurance.command), enter the PS5’s current IPv4 and IPv6 addresses, and keep Terminal open. The helper adds the LAN interface scope for a link-local IPv6 address when needed. Run all six console rows in order; each load row takes about a minute. The app contains no preset device addresses.

**Other network scopes:** [Advanced_Network_Probe](Advanced_Network_Probe/) covers verified HTTPS and local IPv6; [Inbound_LAN_Probe](Inbound_LAN_Probe/) covers short inbound IPv4 exchanges; [LAN_DNS_Probe](LAN_DNS_Probe/) covers outbound LAN and DNS. Routed IPv6, hours-long endurance, simultaneous mixed load and broader TLS configurations remain unverified.

**Latest passing dependency probe:** [Dependency_Probe](Dependency_Probe/), `PPSA99873` version `01.000.001`. Run all six rows in order. The controlled application and its dependencies exist only in JARs; the JNI fixture is target-compiled and embedded. Arbitrary external native ELF loading and real application compatibility remain unverified. Longer network endurance is deferred until there is a useful application to exercise.

Native diagnostic capture is available through the opt-in
[native stderr helper](docs/native-stderr-capture.md). Current/previous native
stderr files have fixed read-only download routes and are included by the log
collector. Host checks pass;actual console native FILE stream capture remains pending.

**Reusable consumer tooling:** the runtime builder supports external probe specifications and optional target-built Java modules. Application-specific work remains in its own repository. Existing passing snapshots stay frozen; additional-module console coverage is pending.

External specifications also support [consumer-owned resident JNI object groups](docs/java25-external-resident-libraries.md), with named export tables and standard Java library discovery. Target packaging and host checks pass, and the exact external-consumer JNI loading/function-lookup probe is now reported ALL PASS on PS5. General third-party native-library compatibility remains unvalidated.

## Explore the source

[Development](Development/) contains the current probe apps, Java fixtures, packaging tools and patches against a pinned FreeBSD OpenJDK source revision. The native UI grew out of a controller tester and Interface Lab prototype.

| Start here | Contents |
| :--- | :--- |
| [Port notes](Development/java25/README.md) | Build setup, platform adaptations and testing history |
| [Java fixtures](Development/java25/tests/) | The Java programs behind each acceptance test |
| [PS5 adaptations](Development/java25/patches/) | The tracked OpenJDK patch series |
| [Console results](Development/java25/console-results.json) | Recorded console evidence and version-specific results |
| [Interface Lab notes](Development/docs/interface-lab.md) | The earlier native UI prototype |

Builds currently use a macOS development environment and the community PS5 Payload SDK. Each frozen milestone's README provides its build entry point. Downloaded dependencies and generated binaries are excluded from source control; passing app packages live in Releases.

## Credits & licenses

This project builds on **OpenJDK**, the **FreeBSD OpenJDK port**, the community **PS5 Payload SDK**, and the **ps5-native-app-boilerplate**. The interface uses **Inter** typography.

Sources retain their individual licenses and upstream notices. See [THIRD_PARTY_NOTICES.md](Development/THIRD_PARTY_NOTICES.md) and [embedded runtime notices](Development/java25/EMBEDDED-RUNTIME-NOTICES.md) for attribution and licensing details.

Development runtime 127 adds an opt-in bounded direct-memory fallback for temporary JNI platform-string and class-loading buffers under native allocation pressure. Defaults stay unchanged; [scope and validation](docs/java25-core-direct-scratch.md). Physical PS5 validation remains pending.
