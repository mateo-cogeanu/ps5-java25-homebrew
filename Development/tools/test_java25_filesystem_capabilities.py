#!/usr/bin/env python3
"""Check actual optional-directory capability block and target path helper imports."""
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parents[1];w=r/'build/java25/fs-capability-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('    /* system calls that might not be available at run time */');b=s.index('    /* supports file birthtime */',a);block=s[a:b]
source=r'''
#include <cassert>
#include <cstddef>
#define _ALLBSD_SOURCE 1
#define RTLD_DEFAULT nullptr
#define sun_nio_fs_UnixNativeDispatcher_SUPPORTS_OPENAT 1
using openat_func=void();using fstatat_func=void();using fdopendir_func=void();using unlinkat_func=void();using renameat_func=void();
openat_func*my_openat_func=nullptr;fstatat_func*my_fstatat_func=nullptr;fdopendir_func*my_fdopendir_func=nullptr;unlinkat_func*my_unlinkat_func=nullptr;renameat_func*my_renameat_func=nullptr;
void openat(){}void fstatat(){}void fdopendir(){}
int lookups=0;void*dlsym(void*,const char*){++lookups;return reinterpret_cast<void*>(&openat);}
int main(){int capabilities=0;
'''+block+r'''
#ifdef __PROSPERO__
assert(capabilities==0&&lookups==0&&my_openat_func==nullptr&&my_fdopendir_func==nullptr&&my_fstatat_func==nullptr&&my_unlinkat_func==nullptr&&my_renameat_func==nullptr);
#else
assert(capabilities==1&&lookups==2&&my_openat_func!=nullptr&&my_fdopendir_func!=nullptr);
#endif
}
''';p=w/'capabilities.cpp';p.write_text(source)
for name,defines in [('ps5',['-D__PROSPERO__=1']),('bsd',[])]:
 subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined',*defines,str(p),'-o',str(w/name)],check=True);subprocess.run([str(w/name)],check=True)
inc=r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs';p=w/'target.c';p.write_text('#include "ps5Realpath.h"\nint canonical(const char*p,char*out){return ps5_descriptor_realpath(p,out);}\n')
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
subprocess.run([str(r/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang'),'-O2','-S','-emit-llvm','-I'+str(inc),str(p),'-o',str(w/'target.ll')],env=env,check=True)
ir=(w/'target.ll').read_text();assert '@open(' in ir and '@close(' in ir and '@openat(' not in ir and '__emutls' not in ir
print('PASS: actual PS5 capability block makes no desktop lookups; BSD capabilities retained; actual target path helper uses open/close without raw openat or compiler TLS')
