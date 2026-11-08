#!/usr/bin/env python3
"""Package the isolated Java17 startup test title; never publish a release."""
import argparse
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

from java_lts import ROOT, sha, tool, verify_boot


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-home', required=True, type=Path)
    p.add_argument('--lld', required=True, type=Path)
    p.add_argument('--boot-jdk', required=True, type=Path)
    p.add_argument('--work-dir', type=Path, default=ROOT / 'build/java-lts/startup17')
    p.add_argument('--image-dir', type=Path, default=ROOT / 'build/java-lts/17/boot-image')
    a = p.parse_args()
    llvm, boot, work = a.llvm_home.resolve(), a.boot_jdk.resolve(), a.work_dir.resolve()
    verify_boot(boot, 17)
    sdk = ROOT / '.tools/native-sdk/ps5-payload-sdk'
    native = ROOT / '.tools/native-app/tooling/native'
    source = ROOT / '.tools/java17/openjdk'
    build = source / 'build/ps5-bootstrap'
    param = ROOT / 'java25/lts/probe/param.json'
    metadata = json.loads(param.read_text())
    if metadata['titleId'] != 'PPSA99876' or metadata['contentVersion'] != '01.000.002':
        raise ValueError('Review standalone probe identity/version')
    package = ROOT / 'dist/PPSA99876.zip'
    if package.exists():
        raise FileExistsError('Existing test package preserved; increment the probe version first')
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LLVM_CONFIG=str(tool(llvm, 'llvm-config')))
    subprocess.run([sys.executable, str(ROOT / 'tools/java_lts.py'), '--major', '17',
                    '--llvm-home', str(llvm), '--audit'], cwd=ROOT, env=env, check=True)
    image = a.image_dir.resolve()
    image_audit = json.loads((image.parent / 'image-audit.json').read_text())
    if image_audit['major'] != 17 or sha(image / 'lib/modules') != image_audit['classImageSha256']:
        raise ValueError('Unverified Java17 class image')
    resident = work / 'resident'
    subprocess.run([sys.executable, str(ROOT / 'tools/java_lts_resident.py'), '--llvm-home', str(llvm),
                    '--lld', str(a.lld.absolute()), '--output-dir', str(resident)], cwd=ROOT, env=env, check=True)
    assets = work / 'assets'
    if assets.exists():
        raise FileExistsError('Existing asset snapshot preserved; choose a new --work-dir')
    runtime = assets / 'java17'
    shutil.copytree(image, runtime)
    (runtime / 'classes').mkdir()
    subprocess.run([str(boot / 'bin/javac'), '--release', '17', '-d', str(runtime / 'classes'),
                    str(ROOT / 'java25/lts/probe/HelloLts.java')], check=True)
    native_libs = build / 'support/modules_libs/java.base'
    for path in [*native_libs.glob('*.so'), native_libs / 'server/libjvm.so']:
        target = runtime / 'lib' / path.relative_to(native_libs)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copytree(source / 'src/java.base/share/legal', runtime / 'legal/java.base')
    # A local probe may be redistributed only with its source/license record.
    source_record = runtime / 'port-source'
    shutil.copytree(ROOT / 'java25/lts', source_record / 'lts')
    shutil.copyfile(ROOT / 'tools/java_lts.py', source_record / 'java_lts.py')
    shutil.copyfile(ROOT / 'tools/java_lts_resident.py', source_record / 'java_lts_resident.py')
    (runtime / 'runtime-provenance.json').write_text(json.dumps({
        'major': 17, 'upstream': json.loads((ROOT / 'java25/lts/upstream.json').read_text())['runtimes']['17'],
        'scope': 'Unvalidated isolated native startup test; not ProsperoCraft, Minecraft, C2 or shader acceptance',
        'console': 'NOT RUN'}, indent=2) + '\n')
    # Keep the shared pinned SDK archive intact. Native applications use real
    # imported platform memory functions, not payload-side raw mmap callbacks.
    libc = work / 'native-libc.a'
    shutil.copy2(sdk / 'target/lib/libc.a', libc)
    subprocess.run([str(tool(llvm, 'llvm-ar')), 'd', str(libc), 'mman.o'], check=True)
    script = (native / 'ps5-pie.ld').read_text()
    for section, label in (('.eh_frame_hdr', '__eh_frame_hdr'), ('.eh_frame', '__eh_frame')):
        anchor = 'KEEP(*(' + section + '))'
        if script.count(anchor) != 1:
            raise ValueError('Re-audit exception unwind layout')
        script = script.replace(anchor, 'PROVIDE_HIDDEN(' + label + '_start = .); ' + anchor +
                                ' PROVIDE_HIDDEN(' + label + '_end = .);')
    anchor = '        *(.text .text.*)'
    if script.count(anchor) != 1:
        raise ValueError('Re-audit native linker text layout')
    script = script.replace(anchor, '''        PROVIDE_HIDDEN(__lts_jvm_text_start = .);
        *(.text.lts_jvm*)
        PROVIDE_HIDDEN(__lts_jvm_text_end = .);
''' + anchor)
    anchor = '        *(.data.rel.ro .data.rel.ro.*)'
    if script.count(anchor) != 1:
        raise ValueError('Re-audit native constructor staging layout')
    script = script.replace(anchor, '''        PROVIDE_HIDDEN(__jvm_init_array_start = .);
        KEEP(*(SORT_BY_INIT_PRIORITY(.data.rel.ro.jvm_init_array.*)))
        KEEP(*(.data.rel.ro.jvm_init_array))
        PROVIDE_HIDDEN(__jvm_init_array_end = .);
''' + anchor)
    layout = work / 'probe.ld'
    layout.write_text(script)
    links = json.loads((resident / 'link-inputs.json').read_text())
    args = ['--defsym=' + name + '=0' for name in ('__cxa_thread_atexit_impl', 'collector_func_load', 'kernel_mprotect')]
    args += ['-L' + str(sdk / 'target/lib'), *links, str(libc)]
    args += [str(sdk / 'target/lib' / name) for name in ('libpthread.a', 'libc++.a', 'libc++abi.a', 'libunwind.a')]
    response = work / 'link.rsp'
    response.write_text('\n'.join(json.dumps(s) for s in args) + '\n')
    headers = build / 'support/modules_include/java.base'
    command = [sys.executable, str(ROOT / 'tools/package_native.py'), '--source', 'java25/lts/probe/startup.cpp',
               '--param', str(param), '--extra-link-response', str(response), '--linker-script', str(layout),
               '--asset-dir', str(assets), '--include-dir', str(headers), '--include-dir', str(headers / 'freebsd')]
    for name in ('LICENSE', 'ADDITIONAL_LICENSE_INFO', 'ASSEMBLY_EXCEPTION'):
        command += ['--license-file', str(source / name)]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    # Preserve this probe's symbols before another native package can replace the
    # shared packaging scratch output. No Java25 application artifacts are rebuilt.
    symbols = work / 'java17-startup-002-symbols.elf'
    shutil.copy2(ROOT / 'build/native/llvm-pie.elf', symbols)
    verify_package(work, llvm, package, image, metadata)


def verify_package(work, llvm, package, image, metadata):
    symbols = work / 'java17-startup-002-symbols.elf'
    resident = work / 'resident'
    image_audit = json.loads((image.parent / 'image-audit.json').read_text())
    text = subprocess.check_output([str(tool(llvm, 'llvm-nm')), str(symbols)], text=True)
    addresses = {parts[-1]: int(parts[0], 16) for line in text.splitlines()
                 if len(parts := line.split()) >= 3 and re.fullmatch('[0-9a-fA-F]+', parts[0])}
    for name in ('JNI_CreateJavaVM', 'JNI_GetDefaultJavaVMInitArgs', 'JVM_CurrentTimeMillis', '__dlopen', '__dlsym'):
        if name not in addresses:
            raise ValueError('Missing actual Java17 startup definition: ' + name)
    if not addresses['__jvm_init_array_start'] < addresses['__jvm_init_array_end']:
        raise ValueError('Missing staged real VM constructors')
    if addresses['__init_array_start'] != addresses['__init_array_end']:
        raise ValueError('Unexpected automatically executed constructors')
    for name in ('JNI_CreateJavaVM', 'JNI_GetDefaultJavaVMInitArgs', 'JVM_CurrentTimeMillis'):
        if not addresses['__lts_jvm_text_start'] <= addresses[name] < addresses['__lts_jvm_text_end']:
            raise ValueError('VM ownership range excludes actual VM function: ' + name)
    with zipfile.ZipFile(package) as archive:
        if archive.testzip() is not None:
            raise ValueError('Test package CRC failure')
        included = json.loads(archive.read('PPSA99876/sce_sys/param.json'))
        if included != metadata:
            raise ValueError('Test package identity mismatch')
        if archive.read('PPSA99876/assets/java17/lib/modules') != (image / 'lib/modules').read_bytes():
            raise ValueError('Packaged class image differs')
    record = {'titleId': metadata['titleId'], 'version': metadata['contentVersion'],
              'packageSha256': sha(package), 'packageBytes': package.stat().st_size, 'symbolsSha256': sha(symbols),
              'classImageSha256': image_audit['classImageSha256'], 'nativeResident': json.loads((resident / 'audit.json').read_text()),
              'sourceSha256': {str(f.relative_to(ROOT)): sha(f) for f in (ROOT / 'java25/lts/probe').rglob('*') if f.is_file()},
              'console': 'NOT RUN', 'release': 'Local test only; no release or Store publication',
              'scope': 'Genuine17 interpreter startup/arithmetic/StrictMath/exceptions/JNI/thread/destruction probe'}
    (work / 'package-audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Local Java17 startup test ready:', package, record['packageSha256'])


if __name__ == '__main__':
    main()
