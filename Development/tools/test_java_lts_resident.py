#!/usr/bin/env python3
"""Run generated resident registry code with real host exports and refusal controls."""
import argparse
from pathlib import Path
import os
import subprocess
import tempfile

from java_lts import tool
from java_lts_resident import registry


def main():
    if not __debug__:
        raise RuntimeError('Run registry checks without Python optimization')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-home', required=True, type=Path)
    a = p.parse_args()
    generated = registry({'jvm': ['JVM_Fixture', 'not_jvm_export'],
                          'java': ['Java_Fixture', 'lts_java_JNI_OnLoad'],
                          'net': ['Java_NetFixture', 'lts_net_JNI_OnLoad']},
                         asm_prefix='_' if os.uname().sysname == 'Darwin' else '')
    with tempfile.TemporaryDirectory(prefix='java17-registry-') as folder:
        root = Path(folder)
        (root / 'registry.cpp').write_text(generated)
        test = root / 'test.cpp'
        test.write_text(r'''
#include <cassert>
#include <cstring>
#include <cstdint>
#include <thread>
#include <vector>
#include <cstdio>
#include <dlfcn.h>
extern "C" {
void*__dlopen(const char*,int);void*__dlsym(void*,const char*);int __dlclose(void*);char*__dlerror();int __dladdr(const void*,Dl_info*);
int JVM_Fixture(){return 17;}int Java_Fixture(){return 21;}int Java_NetFixture(){return 31;}
int lts_java_JNI_OnLoad(void*,void*){return 0x00010008;}
int lts_net_JNI_OnLoad(void*,void*){return -1;}
char __lts_jvm_text_start[16]{};char __lts_jvm_text_end[16]{};
}
int main(){
 void*process=__dlopen(nullptr,0);void*java=__dlopen("/app0/assets/java17/lib/libjava.so",0);void*net=__dlopen("libnet.so",0);
 assert(process&&java&&net&&process!=java&&java!=net);
 using Fn=int(*)();using Load=int(*)(void*,void*);
 assert(reinterpret_cast<Fn>(__dlsym(process,"JVM_Fixture"))()==17);
 assert(reinterpret_cast<Fn>(__dlsym(java,"Java_Fixture"))()==21);
 assert(!__dlsym(java,"JVM_Fixture")&&__dlerror()&&!__dlerror());
 assert(!__dlsym(reinterpret_cast<void*>(0x1234),"Java_Fixture")&&__dlerror());
 assert(!__dlsym(java,nullptr)&&__dlerror());
 assert(!__dlsym(process,"not_jvm_export")&&__dlerror());
 assert(!__dlopen("/tmp/foreign.so",0)&&__dlerror());
 assert(reinterpret_cast<Load>(__dlsym(process,"JNI_OnLoad_java"))(nullptr,nullptr)==0x00010008);
 assert(reinterpret_cast<Load>(__dlsym(process,"JNI_OnLoad_net"))(nullptr,nullptr)==-1);
 assert(__dlclose(reinterpret_cast<void*>(0x1234))==-1&&__dlerror());
 assert(__dlclose(java)==0&&reinterpret_cast<Fn>(__dlsym(java,"Java_Fixture"))()==21);
 Dl_info info{};assert(!__dladdr(nullptr,&info)&&!__dladdr(reinterpret_cast<void*>(&JVM_Fixture),nullptr));
 assert(!__dladdr(reinterpret_cast<void*>(&JVM_Fixture),&info));
 assert(reinterpret_cast<uintptr_t>(__lts_jvm_text_start)<reinterpret_cast<uintptr_t>(__lts_jvm_text_end));
 assert(__dladdr(__lts_jvm_text_start,&info)==1&&info.dli_fbase==__lts_jvm_text_start);
 assert(!strcmp(info.dli_fname,"/app0/assets/java17/lib/server/libjvm.so"));
 assert(!__dladdr(__lts_jvm_text_end,&info));
 assert(!__dlopen("retained-main-thread-error.so",0));
 std::vector<std::thread>threads;
 for(int i=0;i<16;++i)threads.emplace_back([&]{for(int n=0;n<1000;++n){
  assert(reinterpret_cast<Fn>(__dlsym(java,"Java_Fixture"))()==21);
  assert(!__dlsym(java,"missing")&&__dlerror()&&!__dlerror());
 }});
 for(auto&t:threads)t.join();assert(__dlerror()&&!__dlerror());
 puts("PASS generated Java17 resident registry: actual exports, process/scoped handles, no foreign module, unknown/null refusal, real JNI_OnLoad success/error, resident close semantics, bounded dladdr refusal,16threads/16000lookups and independent error state");
}
''')
        executable = root / 'test'
        subprocess.run([str(tool(a.llvm_home.resolve(), 'clang++')), '-std=c++17', '-O1', '-g',
                        '-fsanitize=address,undefined', '-fno-sanitize=function', str(root / 'registry.cpp'),
                        str(test), '-pthread', *([] if os.uname().sysname == 'Darwin' else ['-ldl']),
                        '-o', str(executable)], check=True)
        result = subprocess.run([str(executable)], capture_output=True, text=True, timeout=20,
                                env={**os.environ, 'UBSAN_OPTIONS': 'halt_on_error=1'})
        output = result.stdout + result.stderr
        if result.returncode or 'PASS generated Java17 resident registry' not in output:
            raise RuntimeError(output[-6000:])
        print(output)


if __name__ == '__main__':
    main()
