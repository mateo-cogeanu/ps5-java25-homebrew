#!/usr/bin/env python3
"""Actual metadata reservation/ledger helpers with aligned storage and fault controls."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/direct-metaspace-test';(w/'runtime').mkdir(parents=True,exist_ok=True)
(w/'runtime/ps5StartupTrace.hpp').write_text('#pragma once\ninline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}\n')
s=(r/'.tools/java25/openjdk/src/hotspot/share/memory/memoryReserver.cpp').read_text();reserve=s[s.index('ReservedSpace MemoryReserver::reserve_memory('):s.index('\nReservedSpace MemoryReserver::reserve_memory_special(')]
s=(r/'.tools/java25/openjdk/src/hotspot/os/bsd/os_bsd.cpp').read_text();release=s[s.index('bool os::pd_release_memory('):s.index('\nstatic bool bsd_mprotect(')]
source=r'''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdlib>
#include <cstring>
#include <signal.h>
#include <sys/mman.h>
#include <sys/wait.h>
#include <unistd.h>
static bool fail_allocate=false,fail_map=false,fail_release=false,fail_protect=false;
static size_t calls=0,live=0,records=0,last_alignment=0;
static void* storage=nullptr;static size_t storage_bytes=0;
extern "C" size_t sceKernelGetDirectMemorySize(){return 1024ULL*1024*1024;}
extern "C" int sceKernelAllocateDirectMemory(int64_t,int64_t,size_t bytes,size_t alignment,int,int64_t* offset){
 ++calls;last_alignment=alignment;if(fail_allocate)return -1;assert(!storage);assert(!posix_memalign(&storage,alignment,bytes));memset(storage,0x71,bytes);storage_bytes=bytes;*offset=0;++live;return 0;
}
extern "C" int sceKernelMapDirectMemory(void** address,size_t bytes,int prot,int flags,int64_t,size_t alignment){assert(bytes==storage_bytes&&prot==(PROT_READ|PROT_WRITE)&&flags==0&&alignment==last_alignment);if(fail_map)return -2;*address=storage;return 0;}
extern "C" int sceKernelMunmap(void* p,size_t bytes){assert(p==storage&&bytes==storage_bytes);return ::mprotect(p,bytes,PROT_READ|PROT_WRITE);}
extern "C" int sceKernelReleaseDirectMemory(int64_t,size_t bytes){assert(bytes==storage_bytes);if(fail_release)return -3;free(storage);storage=nullptr;--live;return 0;}
static int checked_protect(void* p,size_t bytes,int prot){if(fail_protect){errno=EACCES;return -1;}return ::mprotect(p,bytes,prot);}
#define __PROSPERO__ 1
#define mprotect checked_protect
#include "runtime/ps5NativeDirectMemory.hpp"
enum MemTag{mtMetaspace,mtClass,mtJavaHeap,mtCode};
static constexpr int CALLER_PC=0;
struct ReservedSpace{char* p=nullptr;size_t bytes=0;ReservedSpace()=default;ReservedSpace(char* a,size_t b,size_t alignment,size_t,bool exec,bool special):p(a),bytes(b){assert((uintptr_t)a%alignment==0&&!exec&&!special);}bool is_reserved(){return p!=nullptr;}};
struct MemTracker{static void record_virtual_memory_reserve(void* p,size_t bytes,int,MemTag tag){assert(p==storage&&bytes==storage_bytes&&tag==mtMetaspace);++records;}};
struct MemoryReserver{static ReservedSpace reserve_memory(char*,size_t,size_t,size_t,bool,MemTag);};
static int ordinary_errno=ENOMEM;static char* ordinary=nullptr;
static char* reserve_memory_inner(char*,size_t,size_t,bool,MemTag){errno=ordinary_errno;return ordinary;}
struct os{static bool pd_release_memory(char*,size_t);};
static bool anon_munmap(char*,size_t){errno=EFAULT;return false;}
'''
suffix=r'''
#undef mprotect
namespace direct=ps5_native_direct;
static void inaccessible(void* address){
 pid_t child=fork();assert(child>=0);if(!child){signal(SIGSEGV,SIG_DFL);signal(SIGBUS,SIG_DFL);volatile unsigned char value=*(volatile unsigned char*)address;(void)value;_exit(0);}
 int status;assert(waitpid(child,&status,0)==child);assert(WIFSIGNALED(status)&&(WTERMSIG(status)==SIGSEGV||WTERMSIG(status)==SIGBUS));
}
int main(){
 constexpr size_t size=4*1024*1024,alignment=size,page=16384;size_t before=calls;
 for(MemTag tag:{mtClass,mtJavaHeap,mtCode})assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,tag).is_reserved());
 assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,true,mtMetaspace).is_reserved());
 assert(!MemoryReserver::reserve_memory((char*)0x4000000,size,alignment,page,false,mtMetaspace).is_reserved());
 ordinary_errno=EACCES;assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace).is_reserved());assert(calls==before);ordinary_errno=ENOMEM;
 ordinary=(char*)0x4000000;assert(MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace).p==ordinary&&calls==before);ordinary=nullptr;
 fail_allocate=true;assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace).is_reserved());fail_allocate=false;assert(!live&&!direct::state().held&&!records);
 fail_map=true;assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace).is_reserved());fail_map=false;assert(!live&&!direct::state().held&&!records);
 fail_protect=true;assert(!MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace).is_reserved());fail_protect=false;assert(!live&&!direct::state().held&&!records);
 auto rs=MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace);assert(rs.is_reserved()&&records==1&&last_alignment==alignment&&direct::state().held==size);inaccessible(rs.p);
 assert(direct::metadata_range(rs.p,page)&&direct::metadata_range(rs.p+size-page,page));assert(!direct::metadata_range(rs.p+size-page,2*page));
 assert(!direct::metadata_range((void*)(UINTPTR_MAX-100),200));assert(!mprotect(rs.p,size,PROT_READ|PROT_WRITE));for(size_t i=0;i<size;++i)assert(rs.p[i]==0);memset(rs.p,0x6a,size);
 assert(direct::uncommit_metadata(rs.p+page,page));inaccessible(rs.p+page);assert(!mprotect(rs.p+page,page,PROT_READ|PROT_WRITE));
 for(size_t i=0;i<page;++i)assert(rs.p[page+i]==0);assert(rs.p[0]==0x6a&&rs.p[2*page]==0x6a);assert(direct::state().held==size);
 fail_protect=true;assert(!direct::uncommit_metadata(rs.p,page));fail_protect=false;assert(rs.p[0]==0x6a);
 assert(!os::pd_release_memory(rs.p,page)&&direct::state().held==size&&live==1);assert(os::pd_release_memory(rs.p,size));assert(!live&&!direct::state().held);
 // Release failure retains ownership/budget. Test-only final cleanup.
 rs=MemoryReserver::reserve_memory(nullptr,size,alignment,page,false,mtMetaspace);fail_release=true;assert(!os::pd_release_memory(rs.p,size)&&live==1&&direct::state().held==size);fail_release=false;
 direct::lock();for(unsigned i=0;i<direct::entry_count;++i)if(direct::state().entries[i].occupied){assert(!sceKernelReleaseDirectMemory(0,size));direct::abandon(i);}direct::unlock();assert(!live&&!direct::state().held);
 assert(direct::map(page,3*page,true)==MAP_FAILED&&!live);
 puts("PASS: actual metadata reservation path/ledger/release,4MiB alignment,NMT reserve event,PROT_NONE,zeroed subrange recommit,adjacent data,purpose/fixed/exec/error gates,rollback/cleanup retention; ASan/UBSan");
}
'''
(w/'test.cpp').write_text('#include <initializer_list>\n#include <cstdio>\n'+source+reserve+release+suffix)
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(w),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(w/'test.cpp'),'-o',str(w/'check')],check=True)
subprocess.run([str(w/'check')],check=True,timeout=60)
