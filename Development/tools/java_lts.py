#!/usr/bin/env python3
"""Explicit isolated Java 17/21 PS5 HotSpot/java.base cross-builds.

This builds initial target baselines, not a console-ready runtime or game package.
Java25 source, images and default configuration are never selected or modified.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import shutil
import sys
import subprocess
import tarfile
import tempfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open('rb') as stream:
        while data := stream.read(1024 * 1024):
            digest.update(data)
    return digest.hexdigest()


def pinned_download(pin, path, *, fetch=False):
    if not path.exists():
        if not fetch:
            raise FileNotFoundError('Missing pinned boot JDK; use --fetch-deps or --boot-jdk')
        temporary = path.with_name(path.name + '.part')
        if temporary.exists():
            raise FileExistsError('Existing partial download preserved: ' + str(temporary))
        try:
            with urllib.request.urlopen(pin['url'], timeout=90) as response, temporary.open('xb') as output:
                total = 0
                while data := response.read(1024 * 1024):
                    total += len(data)
                    if total > pin['size']:
                        raise ValueError('Boot JDK download exceeds pinned size')
                    output.write(data)
            if temporary.stat().st_size != pin['size'] or sha(temporary) != pin['sha256']:
                raise ValueError('Boot JDK size/SHA-256 mismatch')
            temporary.rename(path)
        finally:
            temporary.unlink(missing_ok=True)
    if path.stat().st_size != pin['size'] or sha(path) != pin['sha256']:
        raise ValueError('Cached boot JDK size/SHA-256 mismatch')


def verify_boot(home, major):
    for tool in ('java', 'javac', 'jmod', 'jlink'):
        if not (home / 'bin' / tool).is_file():
            raise ValueError('Incomplete matching host JDK: missing ' + tool)
    for tool in ('java', 'javac'):
        result = subprocess.run([str(home / 'bin' / tool), '-version'], capture_output=True, text=True, check=True)
        if not re.search(r'(?:version\s+"|javac\s+)' + str(major) + r'[.\s"]', result.stdout + result.stderr):
            raise ValueError('Host boot/build JDK major must match Java ' + str(major))


def apply_patches(source, patches):
    """Check the complete ordered patch set; no reset, partial skip or overwriting."""
    bodies = b'\n'.join(p.read_bytes() for p in sorted(patches))
    forward = subprocess.run(['git', 'apply', '--unidiff-zero', '--check', '-'], cwd=source, input=bodies, capture_output=True)
    if forward.returncode == 0:
        subprocess.run(['git', 'apply', '--unidiff-zero', '-'], cwd=source, input=bodies, check=True)
        return 'applied'
    reverse = subprocess.run(['git', 'apply', '--unidiff-zero', '--reverse', '--check', '-'], cwd=source, input=bodies, capture_output=True)
    if reverse.returncode == 0:
        return 'already applied'
    raise ValueError('LTS source patch conflict; local changes retained:\n' + forward.stderr.decode()[-3000:])


def tool(llvm, name):
    path = llvm / 'bin' / name
    if not path.is_file() or not os.access(path, os.X_OK):
        raise FileNotFoundError('Required explicit LLVM tool missing: ' + str(path))
    return path


def audit(source, port, output, llvm, major, spec):
    build = source / 'build/ps5-bootstrap'
    flags = (build / 'spec.gmk').read_text()
    features = re.search(r'^JVM_FEATURES_server\s*:?=\s*(.*)$', flags, re.M)
    if not features or not {'compiler1', 'compiler2'}.issubset(set(features[1].split())):
        raise ValueError('Server C1+C2 build required')
    libs = build / 'support/modules_libs/java.base'
    files = [libs / 'server/libjvm.so', *[libs / ('lib' + name + '.so') for name in
             ('java', 'verify', 'zip', 'jimage', 'net', 'nio')]]
    natives = {}
    for path in files:
        result = subprocess.run([str(tool(llvm, 'llvm-readelf')), '-h', str(path)],
                                capture_output=True, text=True, check=True)
        header = result.stdout
        if 'ELF64' not in header or 'X86-64' not in header:
            raise ValueError('Expected x86_64 target ELF: ' + str(path))
        natives[str(path.relative_to(build))] = {'sha256': sha(path), 'bytes': path.stat().st_size,
                                               'readelfWarnings': result.stderr.splitlines()}
    symbols = subprocess.check_output([str(tool(llvm, 'llvm-nm')), '--defined-only',
                                      str(libs / 'server/libjvm.so')], text=True)
    if not re.search(r'\bJNI_CreateJavaVM$', symbols, re.M):
        raise ValueError('Missing genuine JNI_CreateJavaVM')
    classes = build / 'jdk/modules/java.base'
    for name in ('java/lang/Object.class', 'java/lang/Runtime.class', 'java/lang/StrictMath.class'):
        body = (classes / name).read_bytes()
        if body[:4] != b'\xca\xfe\xba\xbe' or int.from_bytes(body[6:8], 'big') != major + 44:
            raise ValueError('Class library major differs from VM: ' + name)
    archive = build / 'support/native/java.base/libfdlibm.a'
    #17's native StrictMath must link the genuine bundled implementation.
    if major == 17:
        names = subprocess.check_output([str(tool(llvm, 'llvm-nm')), '--defined-only', str(archive)], text=True)
        for name in ('jcos', 'jsin', 'jtan', 'jsqrt'):
            if not re.search(r'\b' + name + '$', names, re.M):
                raise ValueError('Missing original fdlibm symbol: ' + name)
    record = {'major': major, 'source': spec, 'patchesSha256': {p.name: sha(p) for p in sorted(port.glob('*.patch'))},
              'jvmFeatures': features[1].split(), 'nativeLibraries': natives,
              'classMajor': major + 44, 'classFiles': sum(1 for p in classes.rglob('*.class')),
              'console': 'NOT RUN', 'scope': 'Cross-build baseline only; native image/resident loader, PS5 startup/memory/thread/signal integration and consumer compatibility remain pending',
              'defaultJava25Changed': False}
    (output / 'audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS Java', major, 'target HotSpot C1+C2, java.base class generation and native ELF audit; console pending')


def build_image(source, output, boot, major, env):
    """Encode only target classes/configuration; never include desktop native code."""
    make = shutil.which('gmake')
    if make is None:
        raise FileNotFoundError('GNU make is required as gmake')
    with (output / 'image-gendata.log').open('w') as log:
        subprocess.run([make, 'CONF=ps5-bootstrap', 'java.base-gendata'], cwd=source,
                       env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    build = source / 'build/ps5-bootstrap'
    classes = build / 'jdk/modules/java.base'
    conf = build / 'support/modules_conf/java.base'
    if not (conf / 'security/java.security').is_file() or b'security.provider.tbd' in (conf / 'security/java.security').read_bytes():
        raise ValueError('Missing processed target security configuration')
    image = output / 'boot-image'
    if image.exists():
        raise FileExistsError('Existing LTS class image preserved; select a new --output-dir')
    version = re.search(r'^JAVA_VERSION="([^"]+)"', (build / 'jdk/release').read_text(), re.M) if (build / 'jdk/release').exists() else None
    version = version[1] if version else str(major)
    with tempfile.TemporaryDirectory(prefix='lts-image-', dir=output) as folder:
        temporary = Path(folder)
        # Host jlink accepts this transport tag. The JMOD contains class/config
        # data only; it has no host/Linux launcher, library or platform spoof.
        jmod = temporary / 'java.base.jmod'
        subprocess.run([str(boot / 'bin/jmod'), 'create', '--class-path', str(classes),
                        '--config', str(conf), '--module-version', version,
                        '--target-platform', 'linux-amd64', str(jmod)], check=True)
        staged = temporary / 'image'
        subprocess.run([str(boot / 'bin/jlink'), '--module-path', str(temporary), '--add-modules', 'java.base',
                        '--compress=2', '--no-header-files', '--no-man-pages', '--output', str(staged)], check=True)
        libs = build / 'support/modules_libs/java.base'
        for name in ('tzdb.dat', 'security/cacerts'):
            target = staged / 'lib' / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(libs / name, target)
        if (staged / 'bin').exists() or list(staged.rglob('*.so')) or list(staged.rglob('*.dylib')):
            raise ValueError('Unexpected native executable/library in class-only image')
        extracted = temporary / 'extracted'
        subprocess.run([str(boot / 'bin/jimage'), 'extract', '--include',
                        'glob:/java.base/java/lang/*.class', '--dir', str(extracted),
                        str(staged / 'lib/modules')], check=True)
        for name in ('Object', 'Runtime', 'StrictMath'):
            relative = 'java/lang/' + name + '.class'
            if sha(extracted / 'java.base' / relative) != sha(classes / relative):
                raise ValueError('Image differs from genuine target class: ' + name)
        staged.rename(image)
    record = {'major': major, 'classImageSha256': sha(image / 'lib/modules'),
              'classImageBytes': (image / 'lib/modules').stat().st_size,
              'targetGeneratedData': {name: sha(image / 'lib' / name) for name in ('tzdb.dat', 'security/cacerts')},
              'jmodTransportTag': 'linux-amd64; classes/config only, no Linux native artifacts',
              'targetClassReadBack': ['Object', 'Runtime', 'StrictMath'], 'modules': ['java.base'],
              'nativeLibrariesIncluded': False, 'console': 'NOT RUN; native packaging/startup integration pending'}
    (output / 'image-audit.json').write_text(json.dumps(record, indent=2) + '\n')
    print('PASS Java', major, 'target class-only core image and exact class read-back; not a runnable application')


def main():
    if sys.version_info < (3, 12):
        raise SystemExit('Java LTS provisioning requires Python 3.12+ for safe tar extraction')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--major', type=int, choices=(17, 21), required=True)
    parser.add_argument('--boot-jdk', type=Path)
    parser.add_argument('--cache-dir', type=Path)
    parser.add_argument('--output-dir', type=Path)
    parser.add_argument('--llvm-home', type=Path)
    parser.add_argument('--fetch-deps', action='store_true')
    parser.add_argument('--configure', action='store_true')
    parser.add_argument('--build', action='store_true')
    parser.add_argument('--audit', action='store_true')
    parser.add_argument('--image', action='store_true', help='Encode target-built java.base classes/config; no native app')
    args = parser.parse_args()
    spec = json.loads((ROOT / 'java25/lts/upstream.json').read_text())['runtimes'][str(args.major)]
    cache = (args.cache_dir or ROOT / ('.tools/java' + str(args.major))).resolve()
    source = cache / 'openjdk'
    output = (args.output_dir or ROOT / ('build/java-lts/' + str(args.major))).resolve()
    cache.mkdir(parents=True, exist_ok=True)
    output.mkdir(parents=True, exist_ok=True)
    if not source.exists():
        if not args.fetch_deps:
            parser.error('Missing pinned source; explicitly use --fetch-deps')
        subprocess.run(['git', 'clone', '--depth', '1', '--branch', spec['tag'], spec['repository'], str(source)], check=True)
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=source, text=True).strip()
    if commit != spec['commit']:
        raise ValueError('LTS source differs from pinned commit; source preserved')
    port = ROOT / ('java25/lts/' + str(args.major) + '/patches')
    # Minimal-context patches preserve upstream tab recipes and are restricted
    # to exact pristine or exact previously patched file bytes at the pinned
    # source commit. Never merge them into unexplained local modifications.
    for name, expected in spec['patchedFilesSha256'].items():
        path = source / name
        original = subprocess.check_output(['git', 'show', 'HEAD:' + name], cwd=source)
        if not path.is_file() or sha(path) not in (hashlib.sha256(original).hexdigest(), expected):
            raise ValueError('Modified LTS source preserved; review file before patching: ' + name)
    print('Java', args.major, 'patches:', apply_patches(source, list(port.glob('*.patch'))), flush=True)
    for name, expected in spec['patchedFilesSha256'].items():
        if sha(source / name) != expected:
            raise ValueError('Patched source differs from reviewed generation: ' + name)
    if not (args.configure or args.build or args.audit or args.image):
        return
    llvm = (args.llvm_home or Path(os.environ.get('LLVM_HOME', ''))).resolve()
    for name in ('llvm-config', 'llvm-ar', 'llvm-nm', 'llvm-strip', 'llvm-objcopy', 'llvm-objdump', 'llvm-readelf'):
        tool(llvm, name)
    env = dict(os.environ)
    env['LLVM_CONFIG'] = str(tool(llvm, 'llvm-config'))
    if args.configure or args.build or args.image:
        if args.boot_jdk:
            boot = args.boot_jdk.resolve()
        else:
            key = platform.system() + '-' + platform.machine()
            pin = spec['bootJdks'].get(key)
            if pin is None:
                parser.error('Supply --boot-jdk for this host; no pinned archive for ' + key)
            pinned_download(pin, cache / pin['file'], fetch=args.fetch_deps)
            bootroot = cache / 'boot'
            if not bootroot.exists():
                temporary = cache / 'boot.extracting'
                if temporary.exists():
                    raise FileExistsError('Existing interrupted boot extraction retained')
                temporary.mkdir()
                with tarfile.open(cache / pin['file']) as archive:
                    archive.extractall(temporary, filter='data')
                temporary.rename(bootroot)
            boot = bootroot / pin['home']
        verify_boot(boot, args.major)
        sdk = ROOT / '.tools/native-sdk/ps5-payload-sdk'
        if not (sdk / 'bin/prospero-clang++').is_file():
            raise FileNotFoundError('Prepare the pinned native SDK first')
        command = ['bash', 'configure', '--openjdk-target=x86_64-unknown-freebsd',
                   '--with-jvm-variants=server', '--with-conf-name=ps5-bootstrap', '--enable-ps5-bootstrap',
                   '--with-boot-jdk=' + str(boot), '--with-build-jdk=' + str(boot),
                   '--disable-warnings-as-errors', '--enable-headless-only', '--with-toolchain-type=clang',
                   '--with-native-debug-symbols=none', '--with-freetype=bundled', '--with-jvm-features=-dtrace',
                   '--with-sysroot=' + str(sdk), '--with-stdc++lib=dynamic',
                   '--with-extra-cxxflags=-fno-stack-protector', '--with-jobs=4',
                   'CC=' + str(ROOT / 'tools/java25_cc.py'), 'CXX=' + str(sdk / 'bin/prospero-clang++')]
        command += [name + '=' + str(tool(llvm, llvmname)) for name, llvmname in
                    (('AR', 'llvm-ar'), ('NM', 'llvm-nm'), ('STRIP', 'llvm-strip'),
                     ('OBJCOPY', 'llvm-objcopy'), ('OBJDUMP', 'llvm-objdump'))]
        with (output / 'configure.log').open('w') as log:
            subprocess.run(command, cwd=source, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        (output / 'configure-command.json').write_text(json.dumps(command, indent=2) + '\n')
    if args.build:
        make = shutil.which('gmake')
        if make is None:
            raise FileNotFoundError('GNU make is required as gmake')
        with (output / 'build.log').open('w') as log:
            subprocess.run([make, 'CONF=ps5-bootstrap', *spec['targets']], cwd=source, env=env,
                           stdout=log, stderr=subprocess.STDOUT, check=True)
    if args.build or args.audit:
        audit(source, port, output, llvm, args.major, spec)
    if args.image:
        build_image(source, output, boot, args.major, env)


if __name__ == '__main__':
    main()
