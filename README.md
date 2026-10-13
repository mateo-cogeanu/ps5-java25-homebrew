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

> **Current progress:** four passing milestones on PS5 firmware **13.60**, using interpreter mode. IPv4 loopback networking is now console-tested.

**Related project:** [ps5-minecraft-java](https://github.com/mateo-cogeanu/ps5-minecraft-java) tracks Minecraft-specific work separately and will use this Java runtime.

## Milestones

Each milestone is a **frozen source snapshot** of a build that received **ALL PASS on the PS5**. Its release includes the matching app ZIP, SHA-256 checksum and console validation record.

| Milestone | Console result | Version | What passed | Download |
| :--- | :---: | :---: | :--- | :---: |
| [JVM_Startup](JVM_Startup/) | **ALL PASS** | `01.000.023` | Real VM startup, Java 25 arithmetic, Java thread start/join and VM shutdown | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/JVM_Startup-v01.000.023) |
| [IO_Probe](IO_Probe/) | **ALL PASS** | `01.000.004` | Relative paths, private-file creation, UTF-8 write/read, file size and deletion | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/IO_Probe-v01.000.004) |
| [ZIP_JAR_Probe](ZIP_JAR_Probe/) | **ALL PASS** | `01.000.000` | Stored/deflated ZIP entries, JAR manifest, JAR class loading and UTF-8 resources | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/ZIP_JAR_Probe-v01.000.000) |
| [Network_Probe](Network_Probe/) | **ALL PASS** | `01.000.003` | TCP/UDP IPv4 loopback, Java worker echo, nonblocking NIO channels and selector readiness | [Release](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Network_Probe-v01.000.003) |
| [Development](Development/) | **In progress** | — | Current source and upcoming probes; updated as changes are completed | [Browse source](Development/) |

Passing folders stay unchanged. New work goes into `Development`; a new milestone is frozen only after its console tests pass. A successful host build alone does not qualify a milestone.

## Try a passing build

1. Choose a milestone release above and download its **app ZIP**. The latest passing probe is **Network_Probe**.
2. Extract it and copy the **entire title folder** into the homebrew scan location used by your existing ShadowLoader setup.
3. Let the loader register the app, then launch it from the home screen.
4. Run the four test rows **in order**. Use the **D-pad** to select and **X** to run a test. Close the app through the PS menu.

| App | Title folder |
| :--- | :--- |
| JVM startup | `PPSA99865` |
| File I/O | `PPSA99866` |
| ZIP / JAR | `PPSA99867` |
| Networking | `PPSA99868` |

The apps use separate title IDs, so you can keep the passing probes installed side by side. Keep all files inside each extracted folder, including its assets, runtime and licenses. Compare the ZIP against the checksum supplied in its release.

If a test fails, report the **app version**, **test row** and **full exception/code**. After a crash, relaunch and photograph the saved checkpoints.

## Where we're going

- [x] Start the native Java 25 VM and execute Java bytecode.
- [x] Test Java file I/O and controlled VM shutdown.
- [x] Read ZIP/JAR archives and load a Java class and resource from a JAR.
- [x] Test Java TCP/UDP loopback and NIO selector readiness.
- [ ] Validate LAN reachability, name resolution and further socket behavior.
- [ ] Expand class-path/dependency loading and filesystem coverage.
- [ ] Validate JIT execution, garbage collection and sustained workloads.
- [ ] Improve JNI and native-library compatibility for Java applications.
- [ ] Test broader Java APIs, error handling and repeated application runs.

**Latest passing networking probe:** [Network_Probe](Network_Probe/), `PPSA99868` version `01.000.003`. Its console result covers IPv4 loopback; LAN connections, DNS and TLS remain separate tests.

**Current development probe:** [LAN / DNS](Development/java25/probe/lan.cpp), `PPSA99869` version `01.000.000`. Separate LAN echo and DNS rows await PS5 validation; LAN needs the [Mac helper](Development/tools/java25_lan_server.py) running at the configured address.

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
