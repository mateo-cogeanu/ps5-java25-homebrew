#!/usr/bin/env python3
"""Embed the real HotSpot objects in a native app for staged JNI setup tests."""
import os
import re
import json
from pathlib import Path
import subprocess
import argparse
import shutil

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--startup", action="store_true", help="Package the experimental VM startup attempt")
parser.add_argument("--fileio", action="store_true", help="Package the separate Java file I/O title")
parser.add_argument("--zipjar", action="store_true", help="Package the separate ZIP/JAR and class-loading title")
args = parser.parse_args()
if args.fileio and args.zipjar:
    parser.error("Choose one probe: --fileio or --zipjar")
args.startup = args.startup or args.fileio or args.zipjar
WORK = ROOT / "build/java25"
SDK = ROOT / ".tools/native-sdk/ps5-payload-sdk"
JVM = ROOT / ".tools/java25/openjdk/build/ps5-bootstrap/hotspot/variant-server/libjvm/objs"
NATIVE = ROOT / ".tools/native-app/tooling/native"
env = dict(os.environ)
env.setdefault("LLVM_CONFIG", "/opt/homebrew/opt/llvm/bin/llvm-config")
llvm = Path(subprocess.check_output([env["LLVM_CONFIG"], "--bindir"], text=True).strip())
WORK.mkdir(parents=True, exist_ok=True)
objects = sorted(JVM.glob("*.o"))
pin = json.loads((ROOT / "java25/upstream.json").read_text())
source = ROOT / pin["cache"]
actual = subprocess.check_output(["git", "-C", str(source), "rev-parse", "HEAD"], text=True).strip()
if actual != pin["commit"]:
    raise SystemExit("Embedded JVM source is not the pinned revision")
if not objects:
    raise SystemExit("Build HotSpot with tools/java25_source.py --build-hotspot first")
headers = JVM.parents[3] / "support/modules_include/java.base"
for name, source in (("jni.h", headers / "jni.h"), ("jni_md.h", headers / "freebsd/jni_md.h")):
    (ROOT / "build/native").mkdir(parents=True, exist_ok=True)
    (ROOT / "build/native" / name).write_bytes(source.read_bytes())

def response(path, values):
    path.write_text("\n".join('"' + str(value).replace('\\', '\\\\').replace('"', '\\"') + '"'
                              for value in values) + "\n")

# Keep HotSpot constructors out of application startup. They run once only
# after the UI shows RUN, so a constructor crash has an identifiable stage.
source_response = WORK / "jvm-objects.rsp"
response(source_response, objects)
merged = WORK / "embedded-jvm.o"
lld = llvm / "ld.lld"
if not lld.exists():
    lld = Path(subprocess.check_output(["brew", "--prefix", "lld"], text=True).strip()) / "bin/ld.lld"
subprocess.run([str(lld), "-r", "@" + str(source_response), "-o", str(merged)], check=True)
sections = subprocess.check_output([str(llvm / "llvm-readelf"), "-SW", str(merged)], text=True)
names = sorted(set(re.findall(r"\]\s+(\.(?:init_array|ctors)\S*)\s", sections)))
renames = []
for name in names:
    renames += ["--rename-section", name + "=.data.rel.ro.jvm_init_array" + name]
if not names:
    raise SystemExit("No HotSpot constructors found in merged object")
subprocess.run([str(llvm / "llvm-objcopy"), *renames, str(merged)], check=True)
layout = WORK / "jni-probe.ld"
script = (NATIVE / "ps5-pie.ld").read_text()
script = script.replace("KEEP(*(.eh_frame_hdr))", "PROVIDE_HIDDEN(__eh_frame_hdr_start = .); KEEP(*(.eh_frame_hdr)) PROVIDE_HIDDEN(__eh_frame_hdr_end = .);")
script = script.replace("KEEP(*(.eh_frame))", "PROVIDE_HIDDEN(__eh_frame_start = .); KEEP(*(.eh_frame)) PROVIDE_HIDDEN(__eh_frame_end = .);")
needle = "        *(.data.rel.ro .data.rel.ro.*)"
assert needle in script
script = script.replace(needle, """
        PROVIDE_HIDDEN(__jvm_init_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.data.rel.ro.jvm_init_array.*)))
        KEEP(*(.data.rel.ro.jvm_init_array))
        PROVIDE_HIDDEN(__jvm_init_array_end = .);
""" + needle, 1)
layout.write_text(script)
link_response = WORK / "jni-link.rsp"
# SDK mman.o implements payload-side raw mmap syscalls and a kernel_mprotect
# callback. Native applications use the public platform imports already tested
# by our OS probes. Keep the SDK cache intact and filter only this archive copy.
native_libc = WORK / "native-libc.a"
shutil.copy2(SDK / "target/lib/libc.a", native_libc)
subprocess.run([str(llvm / "llvm-ar"), "d", str(native_libc), "mman.o"], check=True)
# Optional SDK callbacks normally stay unresolved weak symbols in payloads.
# The native converter requires every remaining import to have a provider.
# For this setup-only probe, explicitly retain their ELF absent/NULL meaning;
# this does not implement dynamic loading or change any strong import.
absent_callbacks = ["__cxa_thread_atexit_impl", "__dladdr", "__dlclose", "__dlerror",
                    "__dlopen", "__dlsym", "collector_func_load", "kernel_mprotect"]
extra_objects=[]
extra_args=[]
app_source="java25/probe/jni.cpp"
app_param="java25/probe/jni-param.json"
if args.startup:
    subprocess.run(["python3",str(ROOT/"tools/java25_boot_image.py")],check=True)
    subprocess.run(["python3",str(ROOT/"tools/java25_builtin_runtime.py")],check=True)
    extra_objects=json.loads((WORK/"builtin-link-inputs.json").read_text())
    absent_callbacks=[name for name in absent_callbacks if not name.startswith("__dl")]
    assets=WORK/("zipjar-assets/java25" if args.zipjar else "startup-assets/java25")
    shutil.copytree(WORK/"boot-image",assets,dirs_exist_ok=True)
    shutil.copy2(WORK/"boot-image-audit.json",assets/"boot-image-audit.json")
    legal=ROOT/".tools/java25/openjdk/src/java.base/share/legal"
    if legal.exists():
        shutil.copytree(legal,assets/"legal/java.base",dirs_exist_ok=True)
    native_libs=ROOT/".tools/java25/openjdk/build/ps5-bootstrap/support/modules_libs/java.base"
    (assets/"lib/server").mkdir(parents=True,exist_ok=True)
    shutil.copy2(native_libs/"server/libjvm.so",assets/"lib/server/libjvm.so")
    for name in ("java","zip","jimage","net","nio"):
        shutil.copy2(native_libs/("lib"+name+".so"),assets/"lib"/("lib"+name+".so"))
    (assets/"release").write_text('JAVA_VERSION="25.0.4"\nMODULES="java.base"\nOS_NAME="FreeBSD"\nOS_ARCH="amd64"\nIMPLEMENTOR="Experimental PS5 port"\n')
    (assets/"classes").mkdir(exist_ok=True)
    subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/Hello25.java")],check=True)
    if args.fileio:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/FileIO25.java")],check=True)
    if args.zipjar:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/ZipJar25.java")],check=True)
        subprocess.run(["python3",str(ROOT/"tools/java25_jar_fixture.py"),"--output",str(assets/"jars/probe.jar")],check=True)
        if (assets/"classes/ps5probe/JarHello25.class").exists():
            raise SystemExit("JAR payload must not be available as a loose class")
    sounds=assets.parent/"sounds"
    sounds.mkdir(exist_ok=True)
    for name in ("menu_music", "sel"):
        subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(ROOT/"sounds"/(name+".wav")),
                        "-ar", "48000", "-ac", "2", "-f", "s16le", str(sounds/(name+".pcm"))], check=True)
    extra_args=["--asset-dir",str(assets.parent)]
    app_source="java25/probe/startup.cpp"
    app_param="java25/probe/startup-param.json"
    if args.fileio:
        app_source="java25/probe/fileio.cpp"
        app_param="java25/probe/fileio-param.json"
    if args.zipjar:
        app_source="java25/probe/zipjar.cpp"
        app_param="java25/probe/zipjar-param.json"
wrapped_calls=["--wrap="+name for name in ("memcpy","memmove","memcmp","strcmp","strlen","memset","strncmp","strncpy","strchr","memchr","strcpy","malloc","strdup")] if args.startup else []
if args.fileio or args.zipjar:
    wrapped_calls.append("--wrap=open")
response(link_response, [*wrapped_calls,*("--defsym=" + name + "=0" for name in absent_callbacks),
                        "-L" + str(SDK / "target/lib"), merged,*extra_objects, native_libc, SDK / "target/lib/libpthread.a",
                        SDK / "target/lib/libc++.a", SDK / "target/lib/libc++abi.a",
                        SDK / "target/lib/libunwind.a"])
subprocess.run(["python3", str(ROOT / "tools/package_native.py"),
                "--source",app_source,"--param",app_param,*extra_args,
                "--extra-link-response", str(link_response), "--linker-script", str(layout),
                "--license-file", ".tools/java25/openjdk/LICENSE",
                "--license-file", ".tools/java25/openjdk/ADDITIONAL_LICENSE_INFO",
                "--license-file", ".tools/java25/openjdk/ASSEMBLY_EXCEPTION",
                "--license-file", "java25/EMBEDDED-RUNTIME-NOTICES.md"],
               cwd=ROOT, env=env, check=True)
pie = ROOT / "build/native/llvm-pie.elf"
symbol_text = subprocess.check_output([str(llvm / "llvm-nm"), str(pie)], text=True)
symbols = {}
for line in symbol_text.splitlines():
    fields = line.split()
    if len(fields) == 3:
        symbols[fields[2]] = int(fields[0], 16)
first, last = symbols["__jvm_init_array_start"], symbols["__jvm_init_array_end"]
if first >= last or (last-first) % 8:
    raise SystemExit("Invalid staged constructor range")
if symbols["__init_array_start"] != symbols["__init_array_end"]:
    raise SystemExit("JVM probe unexpectedly runs constructors before UI")
for name in ("JNI_GetDefaultJavaVMInitArgs", "JNI_GetCreatedJavaVMs"):
    if not symbols.get(name):
        raise SystemExit(f"Missing embedded JVM function: {name}")
if args.startup:
    for name in ("JNI_CreateJavaVM","__dlopen","__dlsym","__dladdr","JIMAGE_Open",
                 "Java_java_lang_System_registerNatives"):
        if not symbols.get(name):
            raise SystemExit(f"Missing actual VM startup definition: {name}")
for name in absent_callbacks:
    if symbols.get(name, -1) != 0:
        raise SystemExit(f"Optional callback unexpectedly active: {name}")
dynamic_symbols = subprocess.check_output([str(llvm / "llvm-nm"), "--dynamic", "--undefined-only", str(pie)], text=True)
for name in ("mmap", "mprotect"):
    if not re.search(r"\bU\s+" + name + r"$", dynamic_symbols, re.MULTILINE):
        raise SystemExit(f"Native app must import platform {name}, not embed the payload shim")
report = {"source_commit": actual, "hotspot_object_count": len(objects),
          "staged_constructor_count": (last-first)//8,
          "automatic_constructor_count": 0,
          "jni_setup_functions": "real embedded HotSpot definitions",
          "absent_optional_sdk_callbacks": absent_callbacks,
          "memory_api_binding": "mmap/mprotect are undefined platform imports; SDK payload mman.o excluded",
          "console_execution": "pending",
          "vm_creation_and_java_bytecode": "new ZIP/JAR title console execution pending" if args.zipjar else ("new file I/O title console execution pending" if args.fileio else ("package-specific console execution pending" if args.startup else "not attempted by this package"))}
(WORK / ("zipjar-package-audit.json" if args.zipjar else ("fileio-package-audit.json" if args.fileio else ("startup-package-audit.json" if args.startup else "jni-package-audit.json")))).write_text(json.dumps(report, indent=2)+"\n")
print(f"Verified embedded HotSpot: {len(objects)} objects, {(last-first)//8} staged constructors")
