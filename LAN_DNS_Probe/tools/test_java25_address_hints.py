#!/usr/bin/env python3
"""Exercise the actual PS5 anon_mmap function against an occupied host mapping.
The shim models a kernel ignoring MAP_EXCL. No PS5 execution is claimed.
"""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
source=(root/'.tools/java25/openjdk/src/hotspot/os/bsd/os_bsd.cpp').read_text()
start=source.index('static char* anon_mmap(')
end=source.index('\nstatic int anon_munmap(',start)
function=source[start:end].replace('::mmap(', '::test_mmap(')
prefix=r'''
#include <sys/mman.h>
#include <unistd.h>
#include <cerrno>
#include <cstring>
#include <cassert>
#include <cstdio>
#define __PROSPERO__ 1
#ifndef __FreeBSD__
#define __FreeBSD__ 1
#endif
#ifndef MAP_EXCL
#define MAP_EXCL 0x4000
#endif
#define MACOS_ONLY(x)
#define RANGEFMT "%p %zu"
#define RANGEFMTARGS(p,n) p,n
static int observed_flags=0;
static void* test_mmap(void* p,size_t size,int prot,int flags,int fd,off_t off) {
 observed_flags=flags;
 return ::mmap(p,size,prot,flags&~MAP_EXCL,fd,off);
}
static void ps5_vm_trace_memory(const char*,const void*,size_t,int,int){}
class ErrnoPreserver {int value=errno;public:int saved_errno(){return value;}};
namespace os {static const char* strerror(int error){return ::strerror(error);}}
static void discard_log(const char*,...){}
#define log_trace(...) discard_log
'''
suffix=r'''
int main() {
 size_t page=static_cast<size_t>(sysconf(_SC_PAGESIZE));
 auto* occupied=static_cast<unsigned char*>(mmap(nullptr,page,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0));
 assert(occupied!=MAP_FAILED);memset(occupied,0x5a,page);
 char* reserved=anon_mmap(reinterpret_cast<char*>(occupied),page,false);
 assert(!(observed_flags&MAP_FIXED));
 assert(reserved!=reinterpret_cast<char*>(occupied));
 for(size_t i=0;i<page;++i)assert(occupied[i]==0x5a);
 if(reserved)assert(munmap(reserved,page)==0);
 assert(munmap(occupied,page)==0);
 puts("PASS: real PS5 reservation function preserves occupied memory when MAP_EXCL is ignored");
}
'''
work=root/'build/java25'
cpp=work/'test-address-hints.cpp';cpp.write_text(prefix+function+suffix)
exe=work/'test-address-hints'
subprocess.run(['/usr/bin/clang++','-std=c++14','-O2','-Wall','-Wextra','-Werror','-Wno-unused-parameter',str(cpp),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
