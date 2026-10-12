# PS5 Java 25 Homebrew

Console-tested Java 25 milestones for native PS5 homebrew.

| Folder | Status | Purpose |
| --- | --- | --- |
| [JVM_Startup](JVM_Startup/) | **All four console tests PASS** | Frozen first Java 25 application-execution milestone, version 01.000.023 |
| [Development](Development/) | Work in progress | Current source, including the unverified Java file-I/O probe |

[Download the first passing native title folder](https://github.com/mateo-cogeanu/ps5-java25-homebrew/releases/tag/JVM_Startup-v01.000.023).

Development is updated as work progresses. A new milestone folder is added only after the user confirms all its tests pass on the PS5. `IO_Probe` will be added after the file-I/O console tests pass.

The current Java bootstrap uses interpreter mode and direct JNI class definition. Minecraft, JIT stability and ordinary directory/JAR discovery still require further work.

Source files retain their individual licenses and upstream notices; see each folder's THIRD_PARTY_NOTICES.md and java25/EMBEDDED-RUNTIME-NOTICES.md.
