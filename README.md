# PS5 Java 25 Homebrew

Console-tested Java 25 milestones for native PS5 homebrew.

| Folder | Status | Purpose |
| --- | --- | --- |
| [JVM_Startup](JVM_Startup/) | **All four console tests PASS** | Frozen first Java 25 application-execution milestone, version 01.000.023 |
| [IO_Probe](IO_Probe/) | **All four console tests PASS** | Frozen first Java file-I/O milestone, version 01.000.004 |
| [ZIP_JAR_Probe](ZIP_JAR_Probe/) | **All four console tests PASS** | Frozen ZIP/JAR reads and Java JAR class-loading milestone, version 01.000.000 |
| [Development](Development/) | Current work | Source changes and upcoming probes |

[Download the first passing JVM title folder](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/JVM_Startup-v01.000.023).

Development is updated as work progresses. A new milestone folder is added only after the user confirms all its tests pass on the PS5. Passing snapshots stay frozen while Development receives later changes.

The current Java bootstrap uses interpreter mode and direct JNI class definition. Minecraft, JIT stability and automatic system application class-path discovery still require further work.

Source files retain their individual licenses and upstream notices; see each folder's THIRD_PARTY_NOTICES.md and java25/EMBEDDED-RUNTIME-NOTICES.md.

[Download the passing File I/O title folder](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/IO_Probe-v01.000.004).

[Download the passing ZIP/JAR title folder](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/ZIP_JAR_Probe-v01.000.000).
