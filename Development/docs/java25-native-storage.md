# Optional native compression and database libraries

`tools/java25_native_storage.py` builds genuine pinned Zstd JNI 1.5.7-12 and SQLite JDBC 3.53.2.1 native code as target resident objects or host test libraries. Nothing is enabled in the default core image. Consumers explicitly register each object and the required library aliases. JNI namespaces are caller-selected Java package names; their exported methods and class lookup names follow the supplied original Java library. No Java classes or game JARs are transformed.

Zstd JNI source is pinned to b1ab612ca2777d6937f418933b5899132517dab3; SQLite JDBC to 94c0ea142dccd729c9a56833704743d74602e58c. SQLite 3.53.2 amalgamation is publisher-hash checked (8a310d0a16c7a90cacd4c884e70faa51c902afed2a89f63aaa0126ab83558a32). Builds write source, flags, hashes and an audit into ignored build outputs. Consumers must preserve upstream licenses. Zstd weak tracing is disabled; SQLite extension loading and mmap are disabled, with threads, column metadata and deserialize enabled. Non-JNI target globals receive component prefixes to avoid symbol collisions. No arbitrary native loader is introduced.

Host checks use the consumer's unchanged upstream Java library with `-Xcheck:jni` and full verification. Compression arrays, streams and contexts, SQLite WAL, prepared statements, BLOBs, commit, rollback and persistent reopen pass. A missing native library must fail rather than fall back to host stock natives. Target objects compile and integrate into consumer112. Actual PS5 native calls, filesystem locking and database lifecycle remain pending. This is not a general promise of compatibility with every JNI library.

Resident aliases now accept bounded versioned basenames such as `zstd-jni_dh-1.5.7-12`; empty segments, path separators and unsafe characters remain rejected. Alias ownership and initialization behavior remain unchanged.

## File descriptor diagnostics

`java25/probe/file_limits.hpp` provides an explicit consumer policy to raise only the current soft `RLIMIT_NOFILE`, within the existing hard cap, plus an allocation-free scan bounded to8192 descriptors. Core defaults are unchanged. Query/set failures are reported and caller errno is preserved. The log HTTP handler exposes `/resource-status.txt` and returns503 with the real errno and descriptor snapshot when an existing report cannot be opened, instead of claiming it does not exist. ENOENT remains404. Process usage includes the descriptor limits.

Host tests cover real soft-limit raising in a child, capped/failed/infinite limits and log retrieval under actual EMFILE pressure. Consumer111 logs show Too many open files during chunk saves. Consumer112 requests8192 before the JVM starts. This is a mitigation with diagnostics; ownership of the accumulating descriptors and sustained PS5 save/reload remain unresolved until console testing. Frozen passing milestones are preserved.
