#!/usr/bin/env python3
"""Exercise generated resident-library lookup with mocked native addresses.

The loader implementation and tables are the actual packaging output. Only
function bodies are replaced; this is a host contract test, not a PS5 I/O test.
"""
from pathlib import Path
import re
import subprocess

root = Path(__file__).resolve().parents[1]
work = root / 'build/java25'
source = (work / 'builtin-libraries.cpp').read_text()
source = '#define RTLD_SELF ((void *)-3)\nstatic int loads=0, load_version=0x00010002;\n' + source

def mock(match):
    alias, symbol = match.groups()
    if symbol.endswith('_JNI_OnLoad'):
        return f'extern "C" int {alias}(void *,void *) {{ ++loads; return load_version; }}'
    return f'extern "C" void {alias}() {{}}'

source = re.sub(r'extern "C" void (embedded_symbol_\d+)\(\) __asm__\("([^"]+)"\);', mock, source)
source += r'''
#include <cassert>
int main() {
 void *process=__dlopen(nullptr,0);
 assert(process);
 auto parse=reinterpret_cast<int (*)(int,const char *,void *)>(__dlsym(RTLD_DEFAULT,"inet_pton"));
 unsigned char address[16]{};
 assert(parse && parse(AF_INET6,"::1",address)==1 && address[15]==1);
 assert(parse(AF_INET6,"invalid",address)==0);
 assert(!__dlsym(__dlopen("libjava.so",0),"inet_pton"));
 for(const char *name : {"java","zip","jimage","net","nio"}) {
  char symbol[64];std::snprintf(symbol,sizeof(symbol),"JNI_OnLoad_%s",name);
  auto load=reinterpret_cast<int (*)(void *,void *)>(__dlsym(process,symbol));
  assert(load && load(nullptr,nullptr)>=0x00010008);
 }
 assert(loads==3); // original library hooks still execute
 auto nio_load=reinterpret_cast<int (*)(void *,void *)>(__dlsym(process,"JNI_OnLoad_nio"));
 load_version=-1;
 assert(nio_load(nullptr,nullptr)==-1); // failed hook must not become success
 void *nio=__dlopen("/app0/assets/java25/lib/libnio.so",0);
 assert(nio);
 assert(__dlsym(nio,"Java_sun_nio_fs_UnixNativeDispatcher_init"));
 assert(__dlsym(process,"Java_sun_nio_fs_UnixNativeDispatcher_init"));
 void *java=__dlopen("libjava.so",0);
 assert(!__dlsym(java,"Java_sun_nio_fs_UnixNativeDispatcher_init"));
 assert(!__dlsym(process,"JNI_OnLoad_unknown"));
 assert(!__dlopen("libunknown.so",0));
 assert(__dlclose(nio)==0);
 if(void *probe_load=__dlsym(process,"JNI_OnLoad_ps5probe")) {
  load_version=0x00010008;
  assert(reinterpret_cast<int (*)(void *,void *)>(probe_load)(nullptr,nullptr)==0x00010008);
  void *probe=__dlopen("libps5probe.so",0);assert(probe);
  assert(__dlsym(probe,"Java_ps5deps_NativeMath_sum"));
  assert(!__dlsym(java,"Java_ps5deps_NativeMath_sum"));
 }

 std::puts("PASS: built-in discovery, original hooks, JNI versions, native symbols and library scope");
}
'''
source = '#include <cstdio>\n#include <initializer_list>\n' + source
path = work / 'test-builtin-lookup.cpp'
path.write_text(source)
exe = work / 'test-builtin-lookup'
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1',str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
