#!/usr/bin/env python3
"""Exercise actual classloader scratch helpers with real storage and forced failures."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/classloader-pool-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/java.base/share/native/libjava/ClassLoader.c').read_text();body=s[s.index('/* Temporary class-file'):s.index('static JNINativeMethod methods[]')]
body='''
int JNU_PS5DirectScratchEnabled(void){return 0;}
size_t sceKernelGetDirectMemorySize(void){return 0;}
int sceKernelAllocateDirectMemory(int64_t a,int64_t b,size_t c,size_t d,int e,int64_t*f){return -1;}
int sceKernelMapDirectMemory(void**a,size_t b,int c,int d,int64_t e,size_t f){return -1;}
int sceKernelMunmap(void*a,size_t b){return -1;}
int sceKernelReleaseDirectMemory(int64_t a,size_t b){return -1;}
''' + (r/'.tools/java25/openjdk/src/java.base/share/native/libjava/ps5_core_direct_scratch.h').read_text()+body
p=w/'test.cpp';p.write_text(r'''
#include <cstddef>
#include <cstdint>
#include <cstdlib>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{true},deny_maps{true};
static std::atomic<int> mapped{0},heaped{0};
static void* test_malloc(size_t n){if(deny_heap){errno=ENOMEM;return nullptr;}void* p=std::malloc(n);if(p)++heaped;return p;}
static void test_free(void* p){if(p)--heaped;std::free(p);}
static void* test_map(void* a,size_t n,int p,int f,int d,off_t o){if(deny_maps){errno=ENOMEM;return MAP_FAILED;}void* v=::mmap(a,n,p,f,d,o);if(v!=MAP_FAILED)++mapped;return v;}
static int test_unmap(void* p,size_t n){int v=::munmap(p,n);if(!v)--mapped;return v;}
#define malloc test_malloc
#define free test_free
#define mmap test_map
#define munmap test_unmap
#define jio_fprintf std::fprintf
#define __PROSPERO__ 1
'''+body+r'''
int main(){
 static_assert(offsetof(ClassLoaderScratchSlot,bytes)==offsetof(ClassLoaderScratchSlot,header)+sizeof(ClassLoaderScratchHeader));
 void* leases[4];
 for(int i=0;i<4;i++){errno=EDOM;leases[i]=classloader_scratch_allocate(20257);assert(leases[i]&&errno==EDOM);assert((uintptr_t)leases[i]%alignof(max_align_t)==0);memset(leases[i],i+1,20257);}
 assert(!classloader_scratch_allocate(1)&&errno==ENOMEM);assert(!classloader_scratch_allocate(32769));assert(!classloader_scratch_allocate(SIZE_MAX));
 deny_maps=false;void* overflow=classloader_scratch_allocate(20000);assert(overflow&&mapped==1);classloader_scratch_release(overflow);assert(mapped==0);deny_maps=true;
 for(int i=0;i<4;i++){for(int n=0;n<20257;n++)assert(((unsigned char*)leases[i])[n]==i+1);classloader_scratch_release(leases[i]);}
 for(size_t n:{0u,1u,4097u,20257u,32768u}){void* p=classloader_scratch_allocate(n);assert(p);memset(p,0x44,n);classloader_scratch_release(p);}
 std::vector<std::thread> threads;
 for(int t=0;t<8;t++)threads.emplace_back([t]{for(int j=0;j<2000;j++){void* p=classloader_scratch_lease(32768);if(!p)continue;memset(p,t+1,32768);for(int i=0;i<32768;i++)assert(((unsigned char*)p)[i]==t+1);classloader_scratch_release(p);}});
 for(auto& t:threads)t.join();for(auto& slot:classloader_scratch_slots)assert(slot.leased==0);
 deny_heap=false;void* p=classloader_scratch_allocate(20257);assert(p&&heaped==1);classloader_scratch_release(p);assert(heaped==0&&mapped==0);
 puts("PASS: actual helpers, four exclusive aligned leases,20257-byte pressure, exhaustion/mmap fallback, bounds/reuse, concurrent ownership and heap cleanup; ASan/UBSan");
}
''')
exe=w/'test';subprocess.run(['clang++','-std=c++17','-O1','-fsanitize=address,undefined','-pthread',str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
