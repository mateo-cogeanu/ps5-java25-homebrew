# Descriptor fallback for nofollow metadata

A consumer reaches world-directory validation and fails a real Java NIO attribute read with EPERM. Inspection of the pinned consumer bytecode confirms NOFOLLOW_LINKS. The existing stat fallback only supports following links, so it cannot implement this operation safely.

Patch 0057 adds a PS5-only fallback after lstat returns EPERM. It opens the leaf with O_RDONLY|O_NONBLOCK|O_NOFOLLOW and obtains genuine fstat attributes, then closes the descriptor while preserving the metadata result. Real open errors propagate, including ENOENT so absent directories retain normal creation semantics. Other lstat failures do not trigger it. Working native lstat behavior remains unchanged.

The fallback does not follow a final symlink or fabricate link metadata. A symlink whose metadata cannot be obtained through native lstat remains an error (typically ELOOP from O_NOFOLLOW). Intermediate components follow normal lstat path resolution. No Java link validator is disabled. This improves ordinary file/directory metadata availability; full sandbox symlink metadata support remains unestablished.

The actual JNI function passes ASan/UBSan against real host files, directories, FIFO, absent paths, final and dangling symlinks, intermediate symlinks and native lstat link metadata, with injected EPERM/descriptor/open errors. Close cannot replace the original metadata errno. The existing following-stat regression also passes. Target and console checks are separate; host results do not establish PS5 success.

The shared report-note writer now uses raw open/write/close instead of allocating a new FILE. It retries interrupted IO, handles partial writes and preserves actual errors across close. A native failure report can therefore avoid that extra libc allocation; failed writes still return false. The host report-writer injection and full HTTP/archive/collector regressions pass. This does not establish why an earlier exception endpoint remained at its placeholder despite the startup log containing a Java failure.
