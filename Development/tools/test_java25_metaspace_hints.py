#!/usr/bin/env python3
"""Actual MemoryReserver decision path with real non-replacing host mappings."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];work=ROOT/'build/java25/metaspace-hints-test';work.mkdir(parents=True,exist_ok=True)
s=(ROOT/'.tools/java25/openjdk/src/hotspot/share/memory/memoryReserver.cpp').read_text();code=s[s.index('static char* reserve_memory_inner('):s.index('\nReservedSpace MemoryReserver::reserve_memory(')]
prefix=r'''
#include <sys/mman.h>
#include <unistd.h>
#include <stdint.h>
#include <stddef.h>
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#undef assert
#define assert(condition, ...) do { if (!(condition)) abort(); } while (0)
static void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long) {}
enum MemTag {mtMetaspace,mtOther};
static bool deny_hints=false,deny_initial=false;static int live=0,hints=0,oversized=0;
static size_t alignment=16*1024*1024;
static uintptr_t align_up(uintptr_t p,size_t a){return (p+a-1)&~(a-1);}
static bool is_aligned(const void* p,size_t a){return ((uintptr_t)p&(a-1))==0;}
static void fatal(const char*){abort();}
namespace os {
char* reserve_memory(size_t n,MemTag,bool){if(deny_initial)return nullptr;size_t total=n+alignment;char* raw=(char*)mmap(nullptr,total,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);assert(raw!=MAP_FAILED);char* base=(char*)align_up((uintptr_t)raw,alignment)+sysconf(_SC_PAGESIZE);size_t lead=base-raw,tail=total-lead-n;if(lead)assert(!munmap(raw,lead));if(tail)assert(!munmap(base+n,tail));++live;return base;}
bool release_memory(char* p,size_t n){int result=munmap(p,n);if(!result)--live;return result==0;}
char* attempt_reserve_memory_at(char* hint,size_t n,MemTag,bool){++hints;if(deny_hints)return nullptr;char* p=(char*)mmap(hint,n,PROT_NONE,MAP_PRIVATE|MAP_ANON,-1,0);if(p==MAP_FAILED)return nullptr;if(p!=hint){assert(!munmap(p,n));return nullptr;}++live;return p;}
char* reserve_memory_aligned(size_t,size_t,MemTag,bool){++oversized;return nullptr;}
}
'''
suffix=r'''
int main(){const size_t bytes=16*1024*1024;
 char* p=reserve_memory_inner(nullptr,bytes,alignment,false,mtMetaspace);assert(p&&is_aligned(p,alignment)&&oversized==0&&hints>0&&live==1);assert(os::release_memory(p,bytes));assert(live==0);
 deny_hints=true;int before=oversized;assert(!reserve_memory_inner(nullptr,bytes,alignment,false,mtMetaspace));assert(oversized==before+1&&live==0);deny_hints=false;
 int oldhints=hints;assert(!reserve_memory_inner(nullptr,bytes,alignment,false,mtOther));assert(hints==oldhints&&live==0);
 assert(!reserve_memory_inner(nullptr,bytes,alignment,true,mtMetaspace));assert(hints==oldhints&&live==0);
 deny_initial=true;assert(!reserve_memory_inner(nullptr,bytes,alignment,false,mtMetaspace));assert(hints==oldhints&&live==0);deny_initial=false;
 // A live occupied requested address is never replaced by a hint mapping.
 char* guard=(char*)mmap(nullptr,bytes,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);assert(guard!=MAP_FAILED);memset(guard,0x5a,bytes);assert(!reserve_memory_inner(guard,bytes,1,false,mtMetaspace));for(size_t i=0;i<bytes;++i)assert((unsigned char)guard[i]==0x5a);assert(!munmap(guard,bytes));
}
'''
(work/'test.cpp').write_text(prefix+code+suffix)
subprocess.run(['clang++','-std=c++17','-D__PROSPERO__','-fsanitize=address,undefined',str(work/'test.cpp'),'-o',str(work/'check')],check=True);subprocess.run([str(work/'check')],check=True)
print('PASS: actual reservation control flow, real exact-size non-replacing aligned mappings, occupied-address preservation, hint exhaustion cleanup and unchanged executable/other-tag/initial-failure routes')
