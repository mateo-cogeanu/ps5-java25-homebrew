#!/usr/bin/env python3
"""Real Java17/21 VM runs the exact probe JNI/Java checks on the host; no PS5 claim."""
import argparse
from pathlib import Path
import os
import subprocess

from java_lts import ROOT, verify_boot, tool


def main():
    if not __debug__:
        raise RuntimeError('Run startup checks without Python optimization')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--boot-jdk', required=True, type=Path)
    parser.add_argument('--llvm-home', required=True, type=Path)
    parser.add_argument('--output-dir', type=Path, default=None)
    parser.add_argument('--major', type=int, choices=(17,21), default=17)
    parser.add_argument('--probe-dir', type=Path)
    parser.add_argument('--vm-option', action='append', default=[])
    a = parser.parse_args()
    a.output_dir = a.output_dir or ROOT / ('build/java-lts/startup' + str(a.major) + '-host')
    probe = a.probe_dir.resolve() if a.probe_dir else ROOT / ('java25/lts/probe' if a.major == 17 else 'java25/lts/probe21')
    boot, work = a.boot_jdk.resolve(), a.output_dir.resolve()
    verify_boot(boot, a.major)
    work.mkdir(parents=True, exist_ok=True)
    subprocess.run([str(boot / 'bin/javac'), '--release', str(a.major), '-d', str(work),
                    str(probe / 'HelloLts.java')], check=True)
    source = work / 'host.cpp'
    source.write_text(r'''
#include "jni_checks.hpp"
#include <cassert>
#include <cstdio>
#include <fstream>
#include <iterator>
#include <vector>
int main(int argc,char**argv){
 assert(argc==2);
 JavaVMOption options[]={{const_cast<char*>("-Xint"),nullptr},
                        {const_cast<char*>("-Xcheck:jni"),nullptr},
                        {const_cast<char*>("-Xmx128m"),nullptr}};
 JavaVMInitArgs args{};args.version=JNI_VERSION_1_8;args.nOptions=3;args.options=options;args.ignoreUnrecognized=JNI_FALSE;
 JavaVM*vm=nullptr;JNIEnv*env=nullptr;
 assert(JNI_CreateJavaVM(&vm,reinterpret_cast<void**>(&env),&args)==JNI_OK&&vm&&env);
 assert(ps5_lts_probe::run(env,nullptr,0)==-1701&&!env->ExceptionCheck());
 std::ifstream file(argv[1],std::ios::binary);
 std::vector<unsigned char> bytes((std::istreambuf_iterator<char>(file)),{});assert(bytes.size()>8);
 auto bad=bytes;bad[7]=69;assert(ps5_lts_probe::run(env,bad.data(),bad.size())==-1701&&!env->ExceptionCheck());
 int result=ps5_lts_probe::run(env,bytes.data(),bytes.size());
 if(env->ExceptionCheck())env->ExceptionDescribe();
 assert(result==0&&!env->ExceptionCheck());
 assert(vm->DestroyJavaVM()==JNI_OK);
 puts("PASS actual Java17 probe: VM creation, original probe class, Java arithmetic/UTF16/StrictMath/exceptions, RegisterNatives, JNI on a Java worker, joined thread, genuine VM destruction; wrong class major refused");
}
'''.replace('Java17', 'Java' + str(a.major)))
    import json
    text = source.read_text()
    text = text.replace('args.nOptions=3;', 'args.nOptions=' + str(3 + len(a.vm_option)) + ';')
    text = text.replace('{const_cast<char*>("-Xmx128m"),nullptr}};', '{const_cast<char*>("-Xmx128m"),nullptr}' +
                        ''.join(',{const_cast<char*>(' + json.dumps(o) + '),nullptr}' for o in a.vm_option) + '};')
    source.write_text(text)
    platform = 'darwin' if os.uname().sysname == 'Darwin' else 'linux'
    executable = work / 'probe-host'
    subprocess.run([str(tool(a.llvm_home.resolve(), 'clang++')), '-std=c++17', '-O1', '-g',
                    '-fsanitize=undefined', '-fno-sanitize=function', '-I' + str(boot / 'include'),
                    '-I' + str(boot / 'include' / platform), '-I' + str(probe), '-I' + str(ROOT / ('java25/lts/probe' if a.major == 17 else 'java25/lts/probe21')),
                    str(source), '-L' + str(boot / 'lib/server'), '-Wl,-rpath,' + str(boot / 'lib/server'),
                    '-ljvm', '-o', str(executable)], check=True)
    result = subprocess.run([str(executable), str(work / 'HelloLts.class')], capture_output=True,
                            text=True, timeout=40, env={**os.environ, 'UBSAN_OPTIONS': 'halt_on_error=1'})
    output = result.stdout + result.stderr
    (work / 'result.log').write_text(output)
    if result.returncode or ('PASS actual Java' + str(a.major) + ' probe:') not in output or any(n in output for n in
            ('runtime error:', 'WARNING in native method', 'FATAL ERROR in native method')):
        raise RuntimeError(output[-8000:])
    print(output)


if __name__ == '__main__':
    main()
