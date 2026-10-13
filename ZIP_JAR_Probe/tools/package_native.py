#!/usr/bin/env python3
"""Build the ShadowMountPlus title folder using pinned community native tools."""
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import urllib.request
import zipfile
import argparse

ROOT = Path(__file__).resolve().parents[1]
UPSTREAM = ROOT / ".tools/native-app"
REVISION = "e79502f4ce3c278e41c172fe14b6ffe5164b29d3"
SDK = ROOT / ".tools/native-sdk/ps5-payload-sdk"
WORK = ROOT / "build/native"
LLVM_CONFIG = os.environ.get("LLVM_CONFIG", "/opt/homebrew/opt/llvm/bin/llvm-config")


def run(*args, **kwargs):
    subprocess.run([str(a) for a in args], check=True, **kwargs)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default="native/main.cpp")
    parser.add_argument("--param", default="sce_sys/param.json")
    parser.add_argument("--icon", default="sce_sys/icon0.png")
    parser.add_argument("--extra-link-response", help="LLVM linker response file for an experimental embedded runtime")
    parser.add_argument("--linker-script", default=str(UPSTREAM / "tooling/native/ps5-pie.ld"))
    parser.add_argument("--license-file", action="append", default=[], help="Additional upstream notice/license to include")
    parser.add_argument("--asset-dir", help="Directory whose contents are included under app assets/")
    args = parser.parse_args()
    if not UPSTREAM.exists():
        run("git", "clone", "https://github.com/blackbearreloaded/ps5-native-app-boilerplate.git", UPSTREAM)
        run("git", "-C", UPSTREAM, "checkout", "--detach", REVISION)
    revision = subprocess.check_output(["git", "-C", str(UPSTREAM), "rev-parse", "HEAD"], text=True).strip()
    if revision != REVISION:
        raise SystemExit("Native tool dependency revision differs from pinned revision")
    if not SDK.exists():
        archive = ROOT / ".tools/native-sdk.zip"
        urllib.request.urlretrieve("https://github.com/ps5-payload-dev/sdk/releases/download/v0.42/ps5-payload-sdk.zip", archive)
        if digest(archive) != "8cfbc7cd5811e719eb4f0c47eea668d3dc7b40bc8ab11c4a5031d40c23ec02da":
            raise SystemExit("SDK archive checksum mismatch")
        with zipfile.ZipFile(archive) as z:
            z.extractall(SDK.parent)
        for path in (SDK / "bin").iterdir():
            path.chmod(0o755)
    WORK.mkdir(parents=True, exist_ok=True)
    host = WORK / "host"
    host.mkdir(exist_ok=True)
    native = UPSTREAM / "tooling/native"
    cxx = "/usr/bin/clang++" if os.uname().sysname == "Darwin" else "clang++"
    tool = host / "ps5-native-tool"
    builder = host / "libc-builder"
    common = [cxx, "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror"]
    if not tool.exists():
        run(*common, *[native / (s + ".cpp") for s in ("native_app_builder", "self_container", "elf_object", "sce_module_writer")], "-lz", "-o", tool)
    if not builder.exists():
        run(*common, native / "libc_builder.cpp", "-o", builder)
    runtime_raw = WORK / "libc.raw.elf"
    runtime = WORK / "libc.prx"
    run(builder, native / "runtime/api-surface.txt", native / "runtime/imports.txt", runtime_raw)
    run(tool, "self", "--sign", "--in", runtime_raw, "--out", runtime)
    if digest(runtime) != "e6ff45d16adf687855cc3b33b0c8a4132b6504360b221e0a34c7e99fb3ba0036":
        raise SystemExit("Clean-room runtime digest differs from upstream reference")
    llvm = Path(subprocess.check_output([LLVM_CONFIG, "--bindir"], text=True).strip())
    env = dict(os.environ, LLVM_CONFIG=LLVM_CONFIG)
    run("python3", ROOT / "tools/bake_fonts.py")
    run("python3", ROOT / "tools/generate_icon.py")
    objects = []
    for name, source in (("main", ROOT / args.source), ("renderer", ROOT / "native/renderer/demo_renderer.cpp"), ("crt", native / "app_crt.cpp"), ("cpp_runtime", native / "app_cpp_runtime.cpp")):
        obj = WORK / (name + ".o")
        run(llvm / "clang++", "-target", "x86_64-sie-ps5", "-fvisibility-nodllstorageclass=default", "-isysroot", SDK,
            "-isystem", SDK / "target/include/c++/v1", "-isystem", SDK / "target/include", "-I", ROOT / "native/renderer", "-I", WORK, "-I", ROOT / "src",
            "-std=c++20", "-O2", "-Wall", "-Wextra", "-Werror", "-fno-stack-protector", "-fno-plt", "-femulated-tls", "-fno-exceptions", "-fno-rtti",
            "-ffunction-sections", "-fdata-sections", "-c", source, "-o", obj, env=env)
        objects.append(obj)
    pie, elf = WORK / "llvm-pie.elf", WORK / "eboot.elf"
    extras = ["@" + str(ROOT / args.extra_link_response)] if args.extra_link_response else []
    run("bash", SDK / "bin/prospero-lld", "-T", args.linker_script, "--eh-frame-hdr", "--version-script", native / "app-symbols.map", "-e", "_start", "-o", pie, *objects, *extras, "--as-needed", *sorted((SDK / "target/lib").glob("*.so")), env=env)
    run(tool, "link", "--in", pie, "--out", elf, "--stub-dir", SDK / "target/lib", "--module-sdk", "0x02000009", "--companion-sdk", "0x08050001", "--file-name", "eboot.elf")
    metadata = json.loads((ROOT / args.param).read_text())
    title = metadata["titleId"]
    if (not re.fullmatch(r"PPSA\d{5}", title) or
        not re.fullmatch(r"[A-Z]{2}\d{4}-" + title + r"_00-[A-Z0-9]{16}", metadata["contentId"]) or
        not re.fullmatch(r"\d{2}\.\d{3}\.\d{3}", metadata["contentVersion"])):
        raise SystemExit("Invalid title identity or version metadata")
    app = ROOT / "dist" / title
    app.mkdir(parents=True, exist_ok=True)
    (app / "sce_module").mkdir(exist_ok=True)
    (app / "sce_sys").mkdir(exist_ok=True)
    run(tool, "self", "--sign", "--in", elf, "--out", app / "eboot.bin", "--magic", "0x1D3D154F")
    shutil.copy2(runtime, app / "sce_module/libc.prx")
    shutil.copy2(ROOT / args.param, app / "sce_sys/param.json")
    shutil.copy2(ROOT / args.icon, app / "sce_sys/icon0.png")
    if args.asset_dir:
        shutil.copytree(ROOT / args.asset_dir, app / "assets", dirs_exist_ok=True)
    (app / "licenses").mkdir(exist_ok=True)
    shutil.copy2(UPSTREAM / "LICENSE", app / "licenses/GPL-3.0.txt")
    shutil.copy2(ROOT / "THIRD_PARTY_NOTICES.md", app / "licenses/THIRD_PARTY_NOTICES.md")
    shutil.copy2(ROOT / "assets/fonts/OFL.txt", app / "licenses/Inter-OFL.txt")
    for notice in args.license_file:
        source = ROOT / notice
        shutil.copy2(source, app / "licenses" / source.name)
    run(tool, "self", "--inspect", "--file", app / "eboot.bin")
    run(tool, "self", "--inspect", "--file", app / "sce_module/libc.prx")
    with zipfile.ZipFile(ROOT / "dist" / (title + ".zip"), "w", zipfile.ZIP_DEFLATED) as z:
        for path in sorted(app.rglob("*")):
            path.chmod(0o777)
            if path.is_file():
                info = zipfile.ZipInfo(str(path.relative_to(app.parent)))
                info.external_attr = (0o100777 << 16)
                info.compress_type = zipfile.ZIP_DEFLATED
                z.writestr(info, path.read_bytes())
    print(f"Ready: {app}")


if __name__ == "__main__":
    main()
