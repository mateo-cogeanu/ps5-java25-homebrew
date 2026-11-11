"""Stage the scoped PS5 SDK compiler-TLS adapter in a private archive copy."""
import hashlib
import subprocess


def stage_compiler_tls(root, work, llvm, sdk, archive, hotspot_share, *, java17=False):
    directory = work / 'emutls-adapter'
    directory.mkdir(exist_ok=True)
    obj = directory / 'emutls.o'
    ar = llvm / 'llvm-ar'
    subprocess.run([ar, 'x', archive, obj.name], cwd=directory, check=True)
    if hashlib.sha256(obj.read_bytes()).hexdigest() != 'f12a423ab50bab567caab55986904949f3b15074d253e95b151374054b57d94d':
        raise ValueError('Unsupported SDK compiler-TLS object/address-array ABI')

    rebound = {name: 'ps5_emutls_' + name for name in ('malloc', 'realloc', 'free')}
    rebound.update({f'pthread_{name}': f'ps5_emutls_{name}'
                    for name in ('setspecific', 'getspecific', 'key_create')})
    subprocess.run([llvm / 'llvm-objcopy', *[f'--redefine-sym={old}={new}'
                                             for old, new in rebound.items()], obj], check=True)
    output = subprocess.check_output([llvm / 'llvm-nm', '--undefined-only', obj], text=True)
    undefined = {line.split()[-1] for line in output.splitlines() if line.strip()}
    if set(rebound) & undefined or not set(rebound.values()) <= undefined:
        raise ValueError('Incomplete scoped SDK compiler-TLS rebinding')
    subprocess.run([ar, 'r', archive, obj], check=True)

    backend = directory / 'backend.o'
    subprocess.run([
        llvm / 'clang++', '-target', 'x86_64-sie-ps5',
        '-fvisibility-nodllstorageclass=default', '-isysroot', sdk,
        '-isystem', sdk / 'target/include/c++/v1', '-isystem', sdk / 'target/include',
        '-std=c++20', '-O2', '-Wall', '-Wextra', '-Werror', '-fno-exceptions',
        '-fno-rtti', '-fno-stack-protector', '-femulated-tls', '-I', hotspot_share,
        *(['-DPS5_EMUTLS_JAVA17=1'] if java17 else []),
        '-c', root / 'java25/probe/emutls_alloc.cpp', '-o', backend,
    ], check=True)
    imports = subprocess.check_output([llvm / 'llvm-nm', '--undefined-only', backend], text=True)
    if '__emutls_get_address' in imports:
        raise ValueError('Compiler-TLS backend recursively depends on compiler TLS')
    return backend
