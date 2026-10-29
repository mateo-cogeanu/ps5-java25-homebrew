#!/usr/bin/env python3
"""Actual libjava scratch fallback with bounded direct-memory fixtures under sanitizers."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];native=ROOT/'.tools/java25/openjdk/src/java.base/share/native/libjava'
pre=r'''
#include <assert.h>
#include <stdint.h>
#include <stddef.h>
#include <stdlib.h>
#include <errno.h>
#include <sys/mman.h>
#include <pthread.h>
#include <string.h>
static int enabled,deny_anon=1,deny_allocate,deny_direct_map,deny_unmap,deny_release;
static unsigned allocations,releases,maps,unmaps;
int JNU_PS5DirectScratchEnabled(void){return enabled;}
static void* fixture_mmap(void*a,size_t n,int p,int f,int d,off_t o){if(deny_anon){errno=ENOMEM;return MAP_FAILED;}return mmap(a,n,p,f,d,o);}
static int fixture_munmap(void*a,size_t n){return munmap(a,n);}
size_t sceKernelGetDirectMemorySize(void){return 1ULL<<30;}
int sceKernelAllocateDirectMemory(int64_t a,int64_t b,size_t n,size_t align,int type,int64_t*out){assert(!a&&b==(1ULL<<30)&&align==16384&&type==12);if(deny_allocate)return -1;void*p=NULL;if(posix_memalign(&p,align,n))return -1;*out=(int64_t)(uintptr_t)p;allocations++;return 0;}
int sceKernelMapDirectMemory(void**out,size_t n,int p,int f,int64_t physical,size_t align){assert(p==3&&!f&&align==16384);if(deny_direct_map)return -1;*out=(void*)(uintptr_t)physical;maps++;return 0;}
int sceKernelMunmap(void*a,size_t n){if(deny_unmap)return -1;unmaps++;return 0;}
int sceKernelReleaseDirectMemory(int64_t p,size_t n){if(deny_release)return -1;free((void*)(uintptr_t)p);releases++;return 0;}
#define mmap fixture_mmap
#define munmap fixture_munmap
#define __PROSPERO__ 1
'''
post=r'''
static void reset_orphans(void){for(unsigned i=0;i<64;i++)if(ps5_scratch_entries[i].state){free((void*)(uintptr_t)ps5_scratch_entries[i].physical);ps5_scratch_forget(i);}assert(!ps5_scratch_held);}
int main(void){
 assert(ps5_core_scratch_map(16384)==MAP_FAILED&&!allocations);enabled=1;
 errno=EDOM;void*p=ps5_core_scratch_map(16384);assert(p!=MAP_FAILED&&errno==EDOM&&ps5_scratch_held==16384);memset(p,0xa5,16384);
 errno=EACCES;assert(!ps5_core_scratch_unmap(p,16384)&&errno==EACCES&&!ps5_scratch_held);
 deny_anon=0;unsigned before=allocations;p=ps5_core_scratch_map(16384);assert(p!=MAP_FAILED&&allocations==before&&!ps5_scratch_held);assert(!ps5_core_scratch_unmap(p,16384));deny_anon=1;
 assert(ps5_core_scratch_map(0)==MAP_FAILED&&ps5_core_scratch_map(1)==MAP_FAILED&&ps5_core_scratch_map(SIZE_MAX)==MAP_FAILED);
 void* slots[64];for(unsigned i=0;i<64;i++){slots[i]=ps5_core_scratch_map(16384);assert(slots[i]!=MAP_FAILED);}assert(ps5_core_scratch_map(16384)==MAP_FAILED);for(unsigned i=0;i<64;i++)assert(!ps5_core_scratch_unmap(slots[i],16384));assert(!ps5_scratch_held);
 p=ps5_core_scratch_map(8*1024*1024);assert(p!=MAP_FAILED&&ps5_core_scratch_map(16384)==MAP_FAILED);assert(ps5_core_scratch_unmap(p,16384)==-1&&errno==EINVAL);assert(!ps5_core_scratch_unmap(p,8*1024*1024));
 deny_allocate=1;assert(ps5_core_scratch_map(16384)==MAP_FAILED&&!ps5_scratch_held);deny_allocate=0;
 deny_direct_map=1;assert(ps5_core_scratch_map(16384)==MAP_FAILED&&!ps5_scratch_held);deny_direct_map=0;
 p=ps5_core_scratch_map(16384);deny_unmap=1;before=releases;assert(ps5_core_scratch_unmap(p,16384)==-1&&releases==before&&ps5_scratch_held==16384);deny_unmap=0;reset_orphans();
 p=ps5_core_scratch_map(16384);deny_release=1;assert(ps5_core_scratch_unmap(p,16384)==-1&&ps5_scratch_held==16384);deny_release=0;reset_orphans();
 return 0;
}
'''
with tempfile.TemporaryDirectory()as d:
 p=Path(d);(p/'test.c').write_text(pre+(native/'ps5_core_direct_scratch.h').read_text()+post)
 subprocess.run(['clang','-std=c11','-D_DARWIN_C_SOURCE','-fsanitize=address,undefined','-g',str(p/'test.c'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
print('PASS actual core scratch header: default off, anonymous-first, opt-in direct buffers, exact matching release, size/64slot/8MiB bounds, allocation/map rollback and unmap/release failure ownership retained under ASan/UBSan. PS5 pending.')
