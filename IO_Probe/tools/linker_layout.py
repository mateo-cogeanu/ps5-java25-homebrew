"""Keep orphan metadata out of PT_DYNAMIC in the SDK's LLVM linker layout."""
from pathlib import Path
import sys

source = Path(sys.argv[1]).read_text()
marker = "} : ph_rodata : ph_dyn"
if source.count(marker) != 1:
    raise SystemExit("Unexpected SDK linker layout; review before building")
sections = "\n".join(
    f"\t{name} : {{ *({name}) }} : ph_rodata"
    for name in (".dynsym", ".gnu.hash", ".dynstr", ".rela.dyn", ".rela.plt",
                 ".note.gnu.build-id")
)
Path(sys.argv[2]).write_text(source.replace(marker, marker + "\n" + sections))
