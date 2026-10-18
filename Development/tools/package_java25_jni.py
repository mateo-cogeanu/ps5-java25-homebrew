#!/usr/bin/env python3
"""Embed the real HotSpot objects in a native app for staged JNI setup tests."""
import os
import hashlib
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
parser.add_argument("--network", action="store_true", help="Package the separate Java TCP/UDP/NIO networking title")
parser.add_argument("--lan", action="store_true", help="Package LAN/DNS probes with a configured external echo endpoint")
parser.add_argument("--lan-host", help="IPv4 address of the local echo helper; packaged only in generated assets")
parser.add_argument("--lan-port", type=int, default=38025)
parser.add_argument("--inbound", action="store_true", help="Package separate inbound LAN TCP/UDP server tests")
parser.add_argument("--advanced-network", action="store_true", help="Package HTTPS, IPv6 and concurrent network load tests")
parser.add_argument("--lan-endurance", action="store_true", help="Package IPv6 LAN and prolonged external TCP/UDP tests")
parser.add_argument("--dependencies",action="store_true",help="Package multi-JAR, system class-path and resident JNI dependency tests")
parser.add_argument("--probe-spec",type=Path,help="External consumer probe JSON; source and assets stay in their own project")
args = parser.parse_args()
external=json.loads(args.probe_spec.read_text()) if args.probe_spec else None
if external:
    for key in ("source","param","asset_dir"):
        if not Path(external[key]).exists():parser.error("External probe input missing: "+key)
    compile_classpath=external.get("java_compile_classpath",[])
    if not isinstance(compile_classpath,list) or not all(isinstance(p,str) and Path(p).is_file() for p in compile_classpath):
        parser.error("External java_compile_classpath must list existing JARs")
if args.lan:
    import ipaddress
    try:
        address=ipaddress.IPv4Address(args.lan_host or "")
        if address.is_loopback or address.is_unspecified or address.is_multicast or not address.is_private:
            raise ValueError("Choose a private unicast LAN address")
    except ValueError as error: parser.error(str(error))
    if not 1024 <= args.lan_port <= 65535: parser.error("LAN port must be 1024..65535")
if sum([args.fileio,args.zipjar,args.network,args.lan,args.inbound,args.advanced_network,args.lan_endurance,args.dependencies,bool(external)]) > 1:
    parser.error("Choose one probe: --fileio, --zipjar, --network, --lan, --inbound, --advanced-network, --lan-endurance, --dependencies or --probe-spec")
args.startup = args.startup or args.fileio or args.zipjar or args.network or args.lan or args.inbound or args.advanced_network or args.lan_endurance or args.dependencies or bool(external)
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
# Adapt only the compiler-rt object's allocator references. Keep SDK archives
# untouched, and leave every other libc allocator reference unchanged.
emutls_backend=[]
if args.startup:
    emutls_dir=WORK/"emutls-adapter";emutls_dir.mkdir(exist_ok=True)
    subprocess.run([str(llvm/"llvm-ar"),"x",str(native_libc),"emutls.o"],cwd=emutls_dir,check=True)
    emutls_obj=emutls_dir/"emutls.o"
    if hashlib.sha256(emutls_obj.read_bytes()).hexdigest() != "f12a423ab50bab567caab55986904949f3b15074d253e95b151374054b57d94d":
        raise SystemExit("Unsupported SDK compiler-TLS object/address-array ABI")
    subprocess.run([str(llvm/"llvm-objcopy"),*["--redefine-sym="+name+"=ps5_emutls_"+name for name in ("malloc","realloc","free","pthread_setspecific","pthread_getspecific","pthread_key_create")],str(emutls_obj)],check=True)
    # Scoped pthread adapters have shorter exported names.
    subprocess.run([str(llvm/"llvm-objcopy"),*["--redefine-sym=ps5_emutls_pthread_"+name+"=ps5_emutls_"+name for name in ("setspecific","getspecific","key_create")],str(emutls_obj)],check=True)
    emutls_symbols=subprocess.check_output([str(llvm/"llvm-nm"),"--undefined-only",str(emutls_obj)],text=True)
    for name in ("malloc","realloc","free","setspecific","getspecific","key_create"):
        if not re.search(r"\bU\s+ps5_emutls_"+name+r"$",emutls_symbols,re.M):
            raise SystemExit("Missing scoped compiler-TLS adapter: "+name)
    for name in ("malloc","realloc","free","pthread_setspecific","pthread_getspecific","pthread_key_create"):
        if re.search(r"\bU\s+"+name+r"$",emutls_symbols,re.M):
            raise SystemExit("Unadapted compiler-TLS dependency: "+name)
    subprocess.run([str(llvm/"llvm-ar"),"r",str(native_libc),str(emutls_obj)],check=True)
    backend=emutls_dir/"backend.o"
    subprocess.run([str(llvm/"clang++"),"-target","x86_64-sie-ps5","-fvisibility-nodllstorageclass=default","-isysroot",str(SDK),"-isystem",str(SDK/"target/include/c++/v1"),"-isystem",str(SDK/"target/include"),"-std=c++20","-O2","-Wall","-Wextra","-Werror","-fno-exceptions","-fno-rtti","-fno-stack-protector","-femulated-tls","-c",str(ROOT/"java25/probe/emutls_alloc.cpp"),"-o",str(backend)],check=True)
    emutls_backend=[backend]
# Keep SDK resolver result ownership coherent when its small libc allocations
# fail. Rebind only the pinned netdb object, including its matching free/strdup.
if args.startup:
    netdb_dir=WORK/"netdb-adapter";netdb_dir.mkdir(exist_ok=True)
    subprocess.run([str(llvm/"llvm-ar"),"x",str(native_libc),"netdb.o"],cwd=netdb_dir,check=True)
    netdb_obj=netdb_dir/"netdb.o"
    if hashlib.sha256(netdb_obj.read_bytes()).hexdigest()!="ccf0c18495f3e1329570d4f0dac5157a00c5ab9625f2102b197e2575944197f4":
        raise SystemExit("Unsupported SDK netdb object")
    rebound={"malloc":"ps5_dns_malloc","free":"ps5_dns_free","strdup":"ps5_dns_strdup","getaddrinfo":"ps5_sdk_getaddrinfo","sceNetPoolCreate":"ps5_dns_pool_create","sceNetPoolDestroy":"ps5_dns_pool_destroy","sceNetResolverCreate":"ps5_dns_resolver_create","sceNetResolverDestroy":"ps5_dns_resolver_destroy","sceNetResolverStartNtoa":"ps5_dns_ntoa"}
    subprocess.run([str(llvm/"llvm-objcopy"),*["--redefine-sym="+a+"="+b for a,b in rebound.items()],str(netdb_obj)],check=True)
    text=subprocess.check_output([str(llvm/"llvm-nm"),str(netdb_obj)],text=True)
    for a,b in rebound.items():
        if not re.search(r"\b"+b+r"$",text,re.M) or re.search(r"\b"+a+r"$",text,re.M):
            raise SystemExit("Incomplete scoped DNS adaptation: "+a)
    subprocess.run([str(llvm/"llvm-ar"),"r",str(native_libc),str(netdb_obj)],check=True)
    backend=netdb_dir/"backend.o"
    subprocess.run([str(llvm/"clang++"),"-target","x86_64-sie-ps5","-fvisibility-nodllstorageclass=default","-isysroot",str(SDK),"-isystem",str(SDK/"target/include/c++/v1"),"-isystem",str(SDK/"target/include"),"-std=c++20","-O2","-Wall","-Wextra","-Werror","-fno-exceptions","-fno-rtti","-fno-stack-protector","-femulated-tls","-c",str(ROOT/"java25/probe/netdb_alloc.cpp"),"-o",str(backend)],check=True)
    emutls_backend.append(backend)
extra_objects=[]
extra_args=[]
app_source="java25/probe/jni.cpp"
app_param="java25/probe/jni-param.json"
if args.startup:
    subprocess.run(["python3",str(ROOT/"tools/java25_boot_image.py"),*(["--modules",",".join(external.get("modules",["java.base"]))] if external else [])],check=True)
    management=bool(external and "java.management" in external.get("modules",[]))
    if management:
        subprocess.run(["gmake","-C",str(ROOT/".tools/java25/openjdk"),"CONF=ps5-bootstrap","java.management-libs"],env=env,check=True)
    subprocess.run(["python3",str(ROOT/"tools/java25_builtin_runtime.py"),*(["--jni-fixture"] if args.dependencies else []),*(["--management"] if management else [])],check=True)
    extra_objects=json.loads((WORK/"builtin-link-inputs.json").read_text())
    absent_callbacks=[name for name in absent_callbacks if not name.startswith("__dl")]
    if external:shutil.rmtree(WORK/"external-assets",ignore_errors=True)
    assets=WORK/("external-assets/java25" if external else "dependency-assets/java25" if args.dependencies else "lan-endurance-assets/java25" if args.lan_endurance else "advanced-network-assets/java25" if args.advanced_network else "inbound-assets/java25" if args.inbound else ("lan-assets/java25" if args.lan else ("network-assets/java25" if args.network else ("zipjar-assets/java25" if args.zipjar else "startup-assets/java25"))))
    shutil.copytree(WORK/"boot-image",assets,dirs_exist_ok=True)
    shutil.copy2(WORK/"boot-image-audit.json",assets/"boot-image-audit.json")
    legal=ROOT/".tools/java25/openjdk/src/java.base/share/legal"
    if legal.exists():
        shutil.copytree(legal,assets/"legal/java.base",dirs_exist_ok=True)
    native_libs=ROOT/".tools/java25/openjdk/build/ps5-bootstrap/support/modules_libs/java.base"
    (assets/"lib/server").mkdir(parents=True,exist_ok=True)
    shutil.copy2(native_libs/"server/libjvm.so",assets/"lib/server/libjvm.so")
    for name in ("java","zip","jimage","net","nio","verify"):
        shutil.copy2(native_libs/("lib"+name+".so"),assets/"lib"/("lib"+name+".so"))
    if management:
        shutil.copy2(native_libs.parent/"java.management/libmanagement.so",assets/"lib/libmanagement.so")
    module_names=re.search(r'^MODULES="([^"]+)"',(WORK/"boot-image/release").read_text(),re.M).group(1)
    (assets/"release").write_text('JAVA_VERSION="25.0.4"\nMODULES="'+module_names+'"\nOS_NAME="FreeBSD"\nOS_ARCH="amd64"\nIMPLEMENTOR="Experimental PS5 port"\n')
    (assets/"classes").mkdir(exist_ok=True)
    subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/Hello25.java")],check=True)
    if args.fileio:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/FileIO25.java")],check=True)
    if args.zipjar:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/ZipJar25.java")],check=True)
        subprocess.run(["python3",str(ROOT/"tools/java25_jar_fixture.py"),"--output",str(assets/"jars/probe.jar")],check=True)
        if (assets/"classes/ps5probe/JarHello25.class").exists():
            raise SystemExit("JAR payload must not be available as a loose class")
    if args.network:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/Network25.java")],check=True)
    if args.lan:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/Lan25.java"),str(ROOT/"java25/tests/Dns25.java")],check=True)
        (assets/"probe.properties").write_text("lan.host="+args.lan_host+"\nlan.port="+str(args.lan_port)+"\n")
    if external:
        shutil.copytree(Path(external['asset_dir'])/'java25',assets,dirs_exist_ok=True)
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),*(["-classpath",os.pathsep.join(compile_classpath)] if compile_classpath else []),*external['java_sources']],check=True)
    if args.dependencies:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),*[str(ROOT/"java25/tests"/(name+".java")) for name in ("MultiJar25","SystemClasspath25","NativeDeps25")]],check=True)
        subprocess.run(["python3",str(ROOT/"tools/java25_dependency_fixture.py"),"--output",str(assets/"jars")],check=True)
        if (assets/"classes/ps5deps").exists():raise SystemExit("Dependency classes must exist only inside JARs")
        (assets/"probe.properties").unlink(missing_ok=True)
    if args.lan_endurance:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),*[str(ROOT/"java25/tests"/(name+".java")) for name in ("Ipv6Lan25","LanTcpLoad25","LanUdpLoad25")]],check=True)
        (assets/"probe.properties").unlink(missing_ok=True)
    if args.advanced_network:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),*[str(ROOT/"java25/tests"/(name+".java")) for name in ("Https25","Ipv625","NetworkLoad25")]],check=True)
        (assets/"lib/security").mkdir(exist_ok=True)
        shutil.copy2(native_libs/"security/cacerts",assets/"lib/security/cacerts")
        (assets/"probe.properties").unlink(missing_ok=True)
    if args.inbound:
        subprocess.run(["/opt/homebrew/opt/openjdk@25/bin/javac","--release","25","-d",str(assets/"classes"),str(ROOT/"java25/tests/InboundTcp25.java"),str(ROOT/"java25/tests/InboundUdp25.java")],check=True)
        (assets/"probe.properties").unlink(missing_ok=True) # No endpoint/address configuration for listeners.
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
    if args.network:
        app_source="java25/probe/network.cpp"
        app_param="java25/probe/network-param.json"
    if args.lan:
        app_source="java25/probe/lan.cpp"
        app_param="java25/probe/lan-param.json"
    if args.inbound:
        app_source="java25/probe/inbound.cpp"
        app_param="java25/probe/inbound-param.json"
    if args.advanced_network:
        app_source="java25/probe/advanced-network.cpp"
        app_param="java25/probe/advanced-network-param.json"
    if args.lan_endurance:
        app_source="java25/probe/lan-endurance.cpp"
        app_param="java25/probe/lan-endurance-param.json"
    if args.dependencies:
        app_source="java25/probe/dependencies.cpp"
        app_param="java25/probe/dependencies-param.json"
    if external:
        app_source=external["source"];app_param=external["param"]
        extra_args.extend([item for path in external.get("include_dirs",[]) for item in ("--include-dir",path)])
wrapped_calls=["--wrap="+name for name in ("memcpy","memmove","memcmp","strcmp","strlen","memset","strncmp","strncpy","strchr","memchr","strcpy","malloc","calloc","realloc","free","strdup","abort","exit","_exit","pthread_create","pthread_join")] if args.startup else []
if args.fileio or args.zipjar or args.network or args.lan or args.inbound or args.advanced_network or args.lan_endurance or args.dependencies or bool(external):
    wrapped_calls.append("--wrap=open")
response(link_response, [*wrapped_calls,*("--defsym=" + name + "=0" for name in absent_callbacks),
                        "-L" + str(SDK / "target/lib"), merged,*extra_objects,*emutls_backend, native_libc, SDK / "target/lib/libpthread.a",
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
          "vm_creation_and_java_bytecode": "Multi-JAR/system-classpath/JNI console execution pending" if args.dependencies else "IPv6 LAN/endurance console execution pending" if args.lan_endurance else "HTTPS/IPv6/load console execution pending" if args.advanced_network else "inbound LAN console execution pending" if args.inbound else "LAN/DNS console execution pending" if args.lan else "new Java networking title console execution pending" if args.network else "new ZIP/JAR title console execution pending" if args.zipjar else ("new file I/O title console execution pending" if args.fileio else ("package-specific console execution pending" if args.startup else "not attempted by this package"))}
audit_name="external-probe-package-audit.json" if external else "dependency-package-audit.json" if args.dependencies else "lan-endurance-package-audit.json" if args.lan_endurance else "advanced-network-package-audit.json" if args.advanced_network else "inbound-package-audit.json" if args.inbound else "lan-package-audit.json" if args.lan else "network-package-audit.json" if args.network else ("zipjar-package-audit.json" if args.zipjar else ("fileio-package-audit.json" if args.fileio else ("startup-package-audit.json" if args.startup else "jni-package-audit.json")))
(WORK / audit_name).write_text(json.dumps(report, indent=2)+"\n")
print(f"Verified embedded HotSpot: {len(objects)} objects, {(last-first)//8} staged constructors")
