#!/usr/bin/env python3
"""Record target build evidence; this does not test console loadability."""
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import subprocess

ROOT = Path(__file__).resolve().parents[1]
pin = json.loads((ROOT / "java25/upstream.json").read_text())
build = ROOT / pin["cache"] / "build/ps5-bootstrap"
library = build / "support/modules_libs/java.base/server/libjvm.so"
llvm_config = os.environ.get("LLVM_CONFIG", "/opt/homebrew/opt/llvm/bin/llvm-config")
llvm = Path(subprocess.check_output([llvm_config, "--bindir"], text=True).strip())
dynamic = subprocess.run([str(llvm / "llvm-readelf"), "-d", str(library)], capture_output=True, text=True, check=True)
symbols = subprocess.check_output([str(llvm / "llvm-nm"), "--dynamic", "--defined-only", str(library)], text=True)
required = ["JNI_CreateJavaVM", "JNI_GetCreatedJavaVMs", "JNI_GetDefaultJavaVMInitArgs"]
for name in required:
    if not re.search(r"\b" + name + r"(?:@@|$)", symbols, re.MULTILINE):
        raise SystemExit(f"Missing invocation API export: {name}")
object_class = build / "jdk/modules/java.base/java/lang/Object.class"
magic, minor, major = struct.unpack(">IHH", object_class.read_bytes()[:8])
if magic != 0xCAFEBABE or major != 69:
    raise SystemExit("java.base is not Java 25 class format")
artifacts = []
for path in sorted((build / "support/modules_libs/java.base").rglob("*.so")):
    data = path.read_bytes()
    if data[:4] != b"\x7fELF" or struct.unpack_from("<H", data, 18)[0] != 62:
        raise SystemExit(f"Not an x86-64 ELF: {path}")
    artifacts.append({"path": str(path.relative_to(ROOT)), "bytes": len(data),
                      "sha256": hashlib.sha256(data).hexdigest()})
report = {
    "upstream_commit": pin["commit"],
    "target": pin["target"],
    "patches": [{"name": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                for p in sorted((ROOT / "java25/patches").glob("*.patch"))],
    "jni_invocation_exports": required,
    "java_base_object_class_major": major,
    "java_base_class_count": sum(1 for _ in object_class.parents[2].rglob("*.class")),
    "jvm_dependencies": re.findall(r"Shared library: \[([^\]]+)\]", dynamic.stdout),
    "elf_inspection_warnings": dynamic.stderr.strip().splitlines(),
    "artifacts": artifacts,
    "console_jvm_execution": "NOT TESTED",
    "native_application_loadability": "NOT ESTABLISHED; SDK payload ELF requires adaptation",
}
output = ROOT / "build/java25/artifact-audit.json"
output.write_text(json.dumps(report, indent=2) + "\n")
print(f"Audited {len(artifacts)} target libraries, JNI exports and Java 25 classes: {output}")
