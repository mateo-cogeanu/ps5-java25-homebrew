#!/usr/bin/env python3
"""Run actual Java17 PS5 JIMAGE OS code with host read/map/protect failure injection."""
import argparse
from pathlib import Path
import os
import subprocess

from java_lts import ROOT, tool, verify_boot


def main():
    if not __debug__:
        raise RuntimeError('Run image checks without Python optimization')
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-home', required=True, type=Path)
    p.add_argument('--boot-jdk', required=True, type=Path)
    a = p.parse_args()
    boot = a.boot_jdk.resolve()
    verify_boot(boot, 17)
    source = ROOT / '.tools/java17/openjdk'
    work = ROOT / 'build/java-lts/startup17-image-host'
    work.mkdir(parents=True, exist_ok=True)
    bindings = work / 'bindings.hpp'
    bindings.write_text(r'''
#include <sys/mman.h>
#include <unistd.h>
extern "C" void*checked_map(void*,size_t,int,int,int,off_t);
extern "C" int checked_unmap(void*,size_t);
extern "C" int checked_protect(void*,size_t,int);
extern "C" ssize_t checked_read(int,void*,size_t,off_t);
#define mmap checked_map
#define munmap checked_unmap
#define mprotect checked_protect
#define pread checked_read
''')
    fixture = work / 'test.cpp'
    fixture.write_text(r'''
#include <jni.h>
#include "osSupport.hpp"
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <limits>
#include <fcntl.h>
#include <sys/mman.h>
#include <unistd.h>
static int failure,live,maps,unmaps,interrupts;
extern "C" void*checked_map(void*a,size_t n,int p,int f,int fd,off_t o){
 ++maps;if(failure==1){errno=ENOMEM;return MAP_FAILED;}
 void*v=mmap(a,n,p,f,fd,o);if(v!=MAP_FAILED)++live;return v;
}
extern "C" int checked_unmap(void*a,size_t n){int rc=munmap(a,n);if(!rc){++unmaps;--live;}return rc;}
extern "C" int checked_protect(void*a,size_t n,int p){if(failure==2){errno=EACCES;return -1;}return mprotect(a,n,p);}
extern "C" ssize_t checked_read(int fd,void*b,size_t n,off_t o){
 if(interrupts){--interrupts;errno=EINTR;return -1;}
 if(failure==3){errno=EIO;return -1;}
 return pread(fd,b,n>7?7:n,o);
}
int main(int argc,char**argv){
 assert(argc==2);int fd=open(argv[1],O_CREAT|O_EXCL|O_RDWR,0600);assert(fd>=0);
 const char data[]="original-image-fixture-at-offset";
 assert(write(fd,data,sizeof(data))==sizeof(data));
 assert(osSupport::size(argv[1])==sizeof(data));
 char buffer[sizeof(data)]{};interrupts=2;
 assert(osSupport::read(fd,buffer,sizeof(data),0)==sizeof(data)&&!memcmp(buffer,data,sizeof(data)));
 assert(osSupport::read(fd,buffer,-1,0)==-1&&errno==EINVAL);
 assert(osSupport::read(fd,buffer,8,std::numeric_limits<jlong>::max()-2)==-1&&errno==EINVAL);
 interrupts=3;void*image=osSupport::map_memory(fd,argv[1],3,19);
 assert(image&&live==1&&!memcmp(image,data+3,19));
 assert(osSupport::unmap_memory(image,19)&&live==0&&maps==unmaps);
 int before=maps;
 assert(!osSupport::map_memory(fd,argv[1],0,0));
 assert(!osSupport::map_memory(fd,argv[1],std::numeric_limits<size_t>::max(),8)&&maps==before);
 for(int mode=1;mode<=3;++mode){failure=mode;assert(!osSupport::map_memory(fd,argv[1],0,19)&&live==0);}
 failure=0;assert(!osSupport::map_memory(fd,argv[1],sizeof(data)-2,19)&&live==0);
 close(fd);unlink(argv[1]);
 puts("PASS actual Java17 JIMAGE OS implementation: original file size/content, non-page-aligned file offset, partial reads/EINTR, zero/overflow refusal, allocation/protection/read/truncation failure cleanup and matched unmapping; ASan/UBSan");
}
''')
    platform = 'darwin' if os.uname().sysname == 'Darwin' else 'linux'
    flags = [str(tool(a.llvm_home.resolve(), 'clang++')), '-std=c++17', '-O1', '-g', '-fsanitize=address,undefined',
             '-I' + str(boot / 'include'), '-I' + str(boot / 'include' / platform),
             '-I' + str(source / 'src/java.base/share/native/libjimage')]
    obj = work / 'actual-os.o'
    subprocess.run([*flags, '-D__PROSPERO__', '-include', str(bindings), '-c',
                    str(source / 'src/java.base/unix/native/libjimage/osSupport_unix.cpp'), '-o', str(obj)], check=True)
    executable = work / 'test'
    subprocess.run([*flags, str(fixture), str(obj), '-o', str(executable)], check=True)
    result = subprocess.run([str(executable), str(work / 'fixture.jimage')], capture_output=True, text=True,
                            timeout=20, env={**os.environ, 'UBSAN_OPTIONS': 'halt_on_error=1'})
    output = result.stdout + result.stderr
    (work / 'result.log').write_text(output)
    if result.returncode or 'PASS actual Java17 JIMAGE' not in output:
        raise RuntimeError(output[-6000:])
    print(output)


if __name__ == '__main__':
    main()
