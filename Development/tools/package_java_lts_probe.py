#!/usr/bin/env python3
"""Package the isolated Java17/21 startup test title; never publish a release."""
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
from java_compiler_tls import stage_compiler_tls


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-home', required=True, type=Path)
    p.add_argument('--lld', required=True, type=Path)
    p.add_argument('--boot-jdk', required=True, type=Path)
    p.add_argument('--work-dir', type=Path, default=None)
    p.add_argument('--image-dir', type=Path, default=None)
    p.add_argument('--major', type=int, choices=(17, 21), default=17)
    p.add_argument('--probe-dir', type=Path, help='Explicit consumer startup source directory')
    p.add_argument('--extra-assets', type=Path, help='Explicit extra JAR directory, local test only')
    p.add_argument('--management', action='store_true')
    p.add_argument('--library', action='append', default=[])
    p.add_argument('--link-object', action='append', type=Path, default=[])
    p.add_argument('--import-stub', action='append', type=Path, default=[])
    p.add_argument('--staged-constructors', action='append', default=[], metavar='NAME=SECTION')
    p.add_argument('--thread-atexit-provider')
    p.add_argument('--compiler-tls', action='store_true',
                   help='Use the scoped SDK compiler-TLS adapter for a Java 17 consumer')
    a = p.parse_args()
    if (a.import_stub or a.staged_constructors or a.thread_atexit_provider) and not a.probe_dir:
        p.error('Custom native link inputs require an explicit consumer probe')
    if a.compiler_tls and (a.major != 17 or not a.probe_dir):
        p.error('--compiler-tls requires an explicit Java 17 consumer probe')
    identifier = r'[A-Za-z_][A-Za-z0-9_]*'
    if a.thread_atexit_provider and not re.fullmatch(identifier, a.thread_atexit_provider):
        p.error('Invalid thread destructor provider symbol')
    major = a.major
    probe = a.probe_dir.resolve() if a.probe_dir else ROOT / ('java25/lts/probe' if major == 17 else 'java25/lts/probe21')
    a.work_dir = a.work_dir or ROOT / ('build/java-lts/startup' + str(major))
    a.image_dir = a.image_dir or ROOT / ('build/java-lts/' + str(major) + '/boot-image')
    llvm, boot, work = a.llvm_home.resolve(), a.boot_jdk.resolve(), a.work_dir.resolve()
    verify_boot(boot, major)
    sdk = ROOT / '.tools/native-sdk/ps5-payload-sdk'
    native = ROOT / '.tools/native-app/tooling/native'
    source = ROOT / ('.tools/java' + str(major) + '/openjdk')
    build = source / 'build/ps5-bootstrap'
    param = probe / 'param.json'
    metadata = json.loads(param.read_text())
    if not re.fullmatch(r'PPSA[0-9]{5}', metadata['titleId']) or not re.fullmatch(r'[0-9]{2}\.[0-9]{3}\.[0-9]{3}', metadata['contentVersion']):
        raise ValueError('Invalid explicit probe identity/version')
    if not re.fullmatch(r'[A-Z]{2}[0-9]{4}-' + metadata['titleId'] + r'_00-[A-Z0-9]{16}', metadata['contentId']):
        raise ValueError('Invalid explicit content identity')
    if not a.probe_dir and (metadata['titleId'], metadata['contentVersion']) != ({17: ('PPSA99876', '01.000.002'), 21: ('PPSA99877', '01.000.001')}[major]):
        raise ValueError('Review standalone probe identity/version')
    package = ROOT / ('dist/' + metadata['titleId'] + '.zip')
    if package.exists():
        raise FileExistsError('Existing test package preserved; increment the probe version first')
    for obj in a.link_object:
        if not obj.is_file():
            raise FileNotFoundError(obj)
    work.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ, LLVM_CONFIG=str(tool(llvm, 'llvm-config')))
    subprocess.run([sys.executable, str(ROOT / 'tools/java_lts.py'), '--major', str(major),
                    '--llvm-home', str(llvm), '--audit'], cwd=ROOT, env=env, check=True)
    image = a.image_dir.resolve()
    image_audit = json.loads((image.parent / 'image-audit.json').read_text())
    if image_audit['major'] != major or sha(image / 'lib/modules') != image_audit['classImageSha256']:
        raise ValueError('Unverified Java' + str(major) + ' class image')
    resident = work / 'resident'
    subprocess.run([sys.executable, str(ROOT / 'tools/java_lts_resident.py'), '--llvm-home', str(llvm),
                    '--major', str(major), '--lld', str(a.lld.absolute()), '--output-dir', str(resident),
                    *(['--management'] if a.management else []),
                    *[value for entry in a.library for value in ('--library', entry)]], cwd=ROOT, env=env, check=True)
    assets = work / 'assets'
    if assets.exists():
        raise FileExistsError('Existing asset snapshot preserved; choose a new --work-dir')
    runtime = assets / ('java' + str(major))
    shutil.copytree(image, runtime)
    if a.extra_assets:
        shutil.copytree(a.extra_assets.resolve(), runtime / 'extra')
    (runtime / 'classes').mkdir()
    subprocess.run([str(boot / 'bin/javac'), '--release', str(major), '-d', str(runtime / 'classes'),
                    str(probe / 'HelloLts.java')], check=True)
    native_libs = build / 'support/modules_libs/java.base'
    for path in [*native_libs.glob('*.so'), native_libs / 'server/libjvm.so']:
        target = runtime / 'lib' / path.relative_to(native_libs)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    shutil.copytree(source / 'src/java.base/share/legal', runtime / 'legal/java.base')
    # A local probe may be redistributed only with its source/license record.
    source_record = runtime / 'port-source'
    shutil.copytree(ROOT / 'java25/lts', source_record / 'lts')
    if a.probe_dir:
        shutil.copytree(probe, source_record / 'consumer-probe')
    shutil.copyfile(ROOT / 'tools/java_lts.py', source_record / 'java_lts.py')
    shutil.copyfile(ROOT / 'tools/java_lts_resident.py', source_record / 'java_lts_resident.py')
    (runtime / 'runtime-provenance.json').write_text(json.dumps({
        'major': major, 'upstream': json.loads((ROOT / 'java25/lts/upstream.json').read_text())['runtimes'][str(major)],
        'scope': 'Explicit consumer bootstrap test; no game rendering/C2/shader acceptance' if a.probe_dir else 'Unvalidated isolated native startup test; not ProsperoCraft, Minecraft, C2 or shader acceptance',
        'console': 'NOT RUN'}, indent=2) + '\n')
    # Keep the shared pinned SDK archive intact. Native applications use real
    # imported platform memory functions, not payload-side raw mmap callbacks.
    libc = work / 'native-libc.a'
    shutil.copy2(sdk / 'target/lib/libc.a', libc)
    subprocess.run([str(tool(llvm, 'llvm-ar')), 'd', str(libc), 'mman.o'], check=True)
    compiler_tls = []
    if a.compiler_tls:
        backend = stage_compiler_tls(ROOT, work, llvm / 'bin', sdk, libc, source / 'src/hotspot/share',
                                     java17=True)
        compiler_tls = [str(backend), '--wrap=pthread_create', '--wrap=pthread_join']
        for relative in ('tools/java_compiler_tls.py', 'java25/probe/emutls_alloc.cpp',
                         'java25/probe/emutls_keys.hpp'):
            target = source_record / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ROOT / relative, target)
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
    stages = {}
    for spec in a.staged_constructors:
        name, sep, section = spec.partition('=')
        if not sep or not re.fullmatch(identifier, name) or not re.fullmatch(
                r'\.data\.rel\.ro\.[A-Za-z0-9_.]+', section):
            p.error('Expected NAME=.data.rel.ro.SECTION')
        if name in stages or any(section == prior or section.startswith(prior + '.')
                                 or prior.startswith(section + '.') for prior in stages.values()):
            p.error('Duplicate or overlapping consumer constructor stage')
        stages[name] = section
        bounds = (f'        PROVIDE_HIDDEN(__{name}_init_start = .);\n'
                  f'        KEEP(*(SORT_BY_NAME({section}.*)))\n'
                  f'        PROVIDE_HIDDEN(__{name}_init_end = .);\n')
        script = script.replace(anchor, bounds + anchor)
    layout = work / 'probe.ld'
    layout.write_text(script)
    links = json.loads((resident / 'link-inputs.json').read_text())
    args = ['--defsym=__cxa_thread_atexit_impl=' + (a.thread_atexit_provider or '0'),
            '--defsym=collector_func_load=0', '--defsym=kernel_mprotect=0']
    args += ['-L' + str(sdk / 'target/lib'), *links, *[str(p.resolve()) for p in a.link_object],
             *compiler_tls, str(libc)]
    args += [str(sdk / 'target/lib' / name) for name in ('libpthread.a', 'libc++.a', 'libc++abi.a', 'libunwind.a')]
    response = work / 'link.rsp'
    response.write_text('\n'.join(json.dumps(s) for s in args) + '\n')
    headers = build / 'support/modules_include/java.base'
    command = [sys.executable, str(ROOT / 'tools/package_native.py'), '--source', str(probe / 'startup.cpp'),
               '--param', str(param), '--extra-link-response', str(response), '--linker-script', str(layout),
               '--asset-dir', str(assets), '--include-dir', str(headers), '--include-dir', str(headers / 'freebsd'),
               '--include-dir', str(ROOT / ('java25/lts/probe' if major == 17 else 'java25/lts/probe21'))]
    for stub in a.import_stub:
        command += ['--import-stub', str(stub.resolve(strict=True))]
    for license_name in ('LICENSE', 'ADDITIONAL_LICENSE_INFO', 'ASSEMBLY_EXCEPTION'):
        command += ['--license-file', str(source / license_name)]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
    # Preserve this probe's symbols before another native package can replace the
    # shared packaging scratch output. No Java25 application artifacts are rebuilt.
    symbols = work / ('java' + str(major) + '-startup-' + metadata['contentVersion'].split('.')[-1] + '-symbols.elf')
    shutil.copy2(ROOT / 'build/native/llvm-pie.elf', symbols)
    if a.staged_constructors:
        symbols_text = subprocess.check_output([str(tool(llvm, 'llvm-nm')), str(symbols)], text=True)
        for name in stages:
            bounds = {label: re.search(r'^([0-9a-fA-F]+) \w __' + name + '_init_' + label + '$',
                                      symbols_text, re.M) for label in ('start', 'end')}
            if not all(bounds.values()) or int(bounds['start'][1], 16) >= int(bounds['end'][1], 16):
                raise ValueError('Consumer constructor stage was empty or missing')
    verify_package(work, llvm, package, image, metadata, major=major, probe=probe,
                   extra_objects=a.link_object, compiler_tls=a.compiler_tls)


def verify_package(work, llvm, package, image, metadata, *, major=None, probe=None,
                   extra_objects=(), compiler_tls=False):
    major = major or { 'PPSA99876': 17, 'PPSA99877': 21 }[metadata['titleId']]
    probe = probe or ROOT / ('java25/lts/probe' if major == 17 else 'java25/lts/probe21')
    symbols = work / ('java' + str(major) + '-startup-' + metadata['contentVersion'].split('.')[-1] + '-symbols.elf')
    resident = work / 'resident'
    image_audit = json.loads((image.parent / 'image-audit.json').read_text())
    text = subprocess.check_output([str(tool(llvm, 'llvm-nm')), str(symbols)], text=True)
    addresses = {parts[-1]: int(parts[0], 16) for line in text.splitlines()
                 if len(parts := line.split()) >= 3 and re.fullmatch('[0-9a-fA-F]+', parts[0])}
    for name in ('JNI_CreateJavaVM', 'JNI_GetDefaultJavaVMInitArgs', 'JVM_CurrentTimeMillis', '__dlopen', '__dlsym'):
        if name not in addresses:
            raise ValueError('Missing actual Java' + str(major) + ' startup definition: ' + name)
    if compiler_tls:
        required = {'__emutls_get_address', '__wrap_pthread_create', '__wrap_pthread_join'}
        required.update('ps5_emutls_' + name for name in
                        ('malloc', 'realloc', 'free', 'setspecific', 'getspecific', 'key_create'))
        if required - addresses.keys():
            raise ValueError('Missing linked compiler-TLS definitions: ' +
                             ', '.join(sorted(required - addresses.keys())))
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
        included = json.loads(archive.read(metadata['titleId'] + '/sce_sys/param.json'))
        if included != metadata:
            raise ValueError('Test package identity mismatch')
        if archive.read(metadata['titleId'] + '/assets/java' + str(major) + '/lib/modules') != (image / 'lib/modules').read_bytes():
            raise ValueError('Packaged class image differs')
    record = {'titleId': metadata['titleId'], 'version': metadata['contentVersion'],
              'packageSha256': sha(package), 'packageBytes': package.stat().st_size, 'symbolsSha256': sha(symbols),
              'classImageSha256': image_audit['classImageSha256'], 'nativeResident': json.loads((resident / 'audit.json').read_text()),
              'sourceSha256': {(str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else 'explicit-probe/' + str(f.relative_to(probe))): sha(f) for f in probe.rglob('*') if f.is_file()},
              'console': 'NOT RUN', 'release': 'Local test only; no release or Store publication',
              'linkObjectsSha256': {p.name: sha(p) for p in extra_objects},
              'scope': 'Genuine' + str(major) + ' interpreter startup/arithmetic/StrictMath/exceptions/JNI/thread/destruction probe'}
    if compiler_tls:
        record['compilerTlsSha256'] = {name: sha(work / 'emutls-adapter' / name)
                                       for name in ('emutls.o', 'backend.o')}
    (work / 'package-audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('Local Java' + str(major) + ' startup test ready:', package, record['packageSha256'])


if __name__ == '__main__':
    main()
