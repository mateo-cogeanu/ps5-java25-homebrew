# PS5 directory moves and access preflight

Patch0122 fixes a directory-move failure caused by the PS5 access fallback.
The normal Unix `Files.move` implementation first calls `access(source, W_OK)`
for a directory. A sandboxed PS5 title can refuse access with EPERM; the existing
fallback then opens the path with O_WRONLY. Directories reject that operation
with EISDIR, so the move fails before trying the permitted rename operation.

For `sun.nio.fs.ps5Sandbox=true` only, omit this preliminary access check and
let the real rename enforce directory and parent permissions. Source/target
metadata, target conflict handling, symbolic-link behavior, atomic move,
cross-device handling and actual rename failures retain their existing paths.
No recursive copy or delete fallback is introduced. Other platforms keep the
original preliminary check. This fixes the operation instead of reporting
artificial writable-directory access through the descriptor fallback.

`python3 tools/test_java25_directory_move.py` compiles the actual UnixFileSystem
class with one injected access(W_OK)=EISDIR response. It verifies the desktop
failure remains, while the PS5-gated path moves a populated directory and restores
it without changing its contents. Existing targets, missing sources and symbolic
link renames are also checked using real host native metadata and rename.
The PS5 java.base target builds. Actual PS5 directory move/delete/Undo/restart
validation remains pending. Consumer package evidence belongs to ProsperoCraft.
Frozen runtime milestones are unchanged.
