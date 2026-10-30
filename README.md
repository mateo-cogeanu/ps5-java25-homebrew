<p align="center">
  <img src="docs/readme-banner.svg" alt="Java 25 on PS5 — native homebrew, one console test at a time" width="1200">
</p>

# Java 25 on PS5

An experimental native **OpenJDK 25 runtime for PlayStation 5 homebrew**. This is the canonical repository for the Java port, platform adaptations, packaging tools and acceptance tests.

[Active source](Development/) · [Build and source organization](Development/docs/source-organization.md) · [Releases](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases) · [Historical source](https://github.com/mateo-cogeanu/ps5-homebrew-history)

**Related application:** [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft) owns Minecraft-specific launchers, game integration, configuration and validation. Reusable runtime changes stay here.

## Current status

Nine frozen runtime milestones received **ALL PASS on a real PS5, firmware 13.60**, in interpreter mode. Tested scopes include VM startup/shutdown, Java threads and file I/O, ZIP/JAR loading, manifest-linked dependencies, service/resource discovery, system class paths, resident JNI, HTTPS and IPv4/IPv6 networking. These passes apply to the exact recorded milestone builds; they do not establish full Java API, JIT, arbitrary native ELF loading or general application compatibility.

Active development remains in `Development/`. All compatibility patches, optional policies, diagnostic probes and regression tests remain there, including work awaiting console validation:

- Native allocation, direct-memory, thread-stack, metadata and compiler-TLS fallbacks. Defaults and resource-ownership limits are documented per policy.
- [Descriptor-first PS5 paths](Development/docs/java25-descriptor-first-paths.md) and the opt-in [bounded ZIP/JAR handle pool](Development/docs/java25-bounded-zip-handles.md).
- [ImageIO raster/LCMS subset](Development/docs/java25-imageio-raster.md), [genuine JNA dispatch](Development/docs/java25-jna-dispatch.md), [resident native libraries](Development/docs/java25-external-resident-libraries.md) and [native storage libraries](Development/docs/java25-native-storage.md). These do not imply complete desktop AWT, arbitrary loading or universal native-library compatibility.
- Opt-in [JNI core scratch](Development/docs/java25-core-direct-scratch.md), [variable-sized verifier reserve](Development/docs/java25-verifier-variable-reserve.md), [network-node scratch](Development/docs/java25-network-direct-scratch.md), [extended synchronization reserve](Development/docs/java25-extended-sync-reserve.md) and [native library-name scratch](Development/docs/java25-native-library-direct-scratch.md).

See [port notes](Development/java25/README.md), [console results](Development/java25/console-results.json) and the individual validation records for exact evidence and remaining limits. Host tests and successful packaging do not establish PS5 acceptance. Default-off implementations remain available even when a consumer feature is disabled or unfinished.

## Build and maintain

The supported development environment is macOS with Python 3, Git, GNU make, LLVM/LLD 22.1.7 and a Java 25 host JDK. The source preparation tools check pinned upstream revisions and dependency hashes.

```sh
cd Development
python3 tools/package_native.py --source java25/probe/main.cpp --param java25/probe/param.json
python3 tools/java25_source.py --build-hotspot --build-base
python3 tools/java25_audit.py
python3 tools/test_java25_native_library_names.py
```

Use a separate build workspace to preserve tested packages. The [build guide](Development/docs/source-organization.md) explains the public `Development/` layout, dependency preparation, the existing incremental patch-check limitation and consumer integration. Build outputs, SDKs, downloaded artifacts and raw reports stay in ignored local directories.

| Active area | Contents |
| --- | --- |
| [java25/patches](Development/java25/patches/) | Complete OpenJDK platform patch series |
| [java25/probe](Development/java25/probe/) and [tests](Development/java25/tests/) | Native adapters, probes and Java regression fixtures |
| [tools](Development/tools/) | Source preparation, builds, packaging, host tests and publication |
| [docs](Development/docs/) | Compatibility scopes, build notes and validation records |
| [Notices](Development/THIRD_PARTY_NOTICES.md) | Upstream attribution and licensing |

Completed runtime source changes are published through `tools/sync_github.py`. It publishes the active allowlist and does not recreate archived snapshots. Consumer changes are published separately to ProsperoCraft. See [AGENTS.md](AGENTS.md) for maintainer rules.

## Passing downloads and source history

The latest passing runtime acceptance probe is **Dependency_Probe**, title **PPSA99873**, version **01.000.001**: [original release and checksums](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/Dependency_Probe-v01.000.001). Extract the entire app title folder, install it through your existing homebrew workflow, and run its six rows in order using D-pad and X. Close through the PS menu. It needs no network helper.

All nine frozen runtime sources, including **JVM_Startup 01.000.023**, now live in the [runtime archive index](https://github.com/mateo-cogeanu/ps5-homebrew-history/tree/aa7db35ee9aa5cc6515f49b23ebda6d1ecfcf91d/runtime). The [archive README and manifest](https://github.com/mateo-cogeanu/ps5-homebrew-history/tree/aa7db35ee9aa5cc6515f49b23ebda6d1ecfcf91d) record original commits, title IDs, versions, console evidence, file checksums and historical build instructions. ProsperoCraft snapshots have a separate archive section.

Original [release assets](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases) and tags remain in this repository at their existing URLs. Compare downloaded packages with their release checksums. Runtime probes have distinct title IDs and can remain installed side by side. Old source history is preserved; this organization change does not rewrite Git history or reduce historical objects in existing clones.

## Runtime roadmap

- Broader Java API, dependency, JNI and filesystem compatibility.
- Sustained workloads, resource cleanup and longer mixed network testing.
- JIT and garbage-collection validation on the console.
- Further resident native-library and optional module coverage.

Game, graphics and mod-loader plans belong to [ProsperoCraft](https://github.com/mateo-cogeanu/ProsperoCraft).

## Credits and licenses

Built on OpenJDK, the FreeBSD OpenJDK port, the community PS5 Payload SDK and ps5-native-app-boilerplate. The interface uses Inter typography. Sources retain their upstream licenses and per-file notices; see [third-party notices](Development/THIRD_PARTY_NOTICES.md) and [embedded runtime notices](Development/java25/EMBEDDED-RUNTIME-NOTICES.md). Historical notices remain with their archived snapshots. Passing binaries remain release assets, with matching validation and checksums.
