#!/usr/bin/env python3
"""Exercise target JFR metadata loading from the linked image on a host JVM.

Uses extracted target classes/resources; host native JFR is still host behavior,
not PS5 execution or server readiness evidence.
"""
from pathlib import Path
import hashlib
import json
import os
import subprocess
import tempfile

root = Path(__file__).resolve().parents[1]
jdk = Path(os.environ.get("JAVA25_BOOT_JDK", "/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home"))
image = root / "build/java25/boot-image/lib/modules"
audit = json.loads((root / "build/java25/boot-image-audit.json").read_text())
resource = "jdk.jfr/jdk/jfr/internal/types/metadata.bin"
with tempfile.TemporaryDirectory(prefix="ps5-jfr-image-test-") as temporary:
    work = Path(temporary)
    subprocess.run([str(jdk / "bin/jimage"), "extract", "--include", "glob:/jdk.jfr/**", "--dir", str(work), str(image)], check=True)
    assert hashlib.sha256((work / resource).read_bytes()).hexdigest() == audit["verified_generated_resource_sha256"][resource]
    java = work / "JfrImageCheck.java"
    java.write_text("""
import java.nio.file.*;
import java.util.*;
import jdk.jfr.internal.MetadataLoader;
public class JfrImageCheck {
    public static void main(String[] args) throws Exception {
        try (var input = MetadataLoader.class.getResourceAsStream("/jdk/jfr/internal/types/metadata.bin")) {
            if (input == null || !Arrays.equals(input.readAllBytes(), Files.readAllBytes(Path.of(args[0]))))
                throw new AssertionError("JFR did not resolve the target image metadata");
        }
        var types = MetadataLoader.createTypes();
        if (types.size() < 100) throw new AssertionError("Incomplete JFR types: " + types.size());
        System.out.println("PASS: target linked-image JFR metadata resolves and creates " + types.size() + " types on host JVM");
    }
}
""")
    subprocess.run([str(jdk / "bin/javac"), "--add-exports", "jdk.jfr/jdk.jfr.internal=ALL-UNNAMED", str(java)], check=True)
    subprocess.run([str(jdk / "bin/java"), "-Xshare:off", "--patch-module", "jdk.jfr=" + str(work / "jdk.jfr"), "--add-exports", "jdk.jfr/jdk.jfr.internal=ALL-UNNAMED", "--add-opens", "jdk.jfr/jdk.jfr.internal.types=ALL-UNNAMED", "-cp", str(work), "JfrImageCheck", str(work / resource)], check=True)
