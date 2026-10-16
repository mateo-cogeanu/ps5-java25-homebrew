#!/usr/bin/env python3
"""Exercise the scoped compiler-TLS allocator with real maps and injected failures."""
from pathlib import Path
import os,subprocess
ROOT=Path(__file__).resolve().parents[1];W=ROOT/'build/java25/emutls-test';W.mkdir(parents=True,exist_ok=True)
source=r'''
#include <cassert>
#include <atomic>
#include <thread>
#include <vector>
#include <cstdlib>
#include <cstring>
#include <cerrno>
#include <sys/mman.h>
#include <unistd.h>
static std::atomic<bool> deny_heap{false},deny_map{false};
static std::atomic<int> heaps{0},maps{0};
namespace injected {
void* malloc(size_t n){if(deny_heap){errno=ENOMEM;return nullptr;}void*p=::malloc(n);if(p)++heaps;return p;}
void free(void*p){if(p)--heaps;::free(p);}
}
void* test_mmap(void*p,size_t n,int prot,int flags,int fd,off_t off){if(deny_map){errno=ENOMEM;return MAP_FAILED;}p=::mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED)++maps;return p;}
int test_munmap(void*p,size_t n){int r=::munmap(p,n);if(!r)--maps;return r;}
// Header uses std::malloc/free; rebind only these identifiers after system headers.
namespace std {inline void* injected_malloc(size_t n){return injected::malloc(n);}inline void injected_free(void*p){injected::free(p);}}
#define malloc injected_malloc
#define free injected_free
#define mmap test_mmap
#define munmap test_munmap
#include "java25/probe/emutls_alloc.hpp"
#undef malloc
#undef free
#undef mmap
#undef munmap
namespace a=ps5::emutls_alloc;
int main(){
 errno=EDOM;void*p=a::allocate(128);assert(p&&errno==EDOM&&heaps==1);assert((uintptr_t)p%alignof(max_align_t)==0);memset(p,0x51,128);
 deny_heap=true;void*q=a::resize(p,4096);assert(q&&heaps==0&&maps==1&&errno==EDOM);for(int i=0;i<128;++i)assert(((char*)q)[i]==0x51);
 deny_map=true;assert(!a::resize(q,8192)&&errno==ENOMEM);for(int i=0;i<128;++i)assert(((char*)q)[i]==0x51);assert(!a::allocate(SIZE_MAX));deny_map=false;
 errno=ERANGE;assert(a::resize(q,16)==q&&errno==ERANGE);a::release(q);assert(maps==0&&errno==ERANGE);
 p=a::resize(nullptr,0);assert(p);assert(!a::resize(p,0));a::release(nullptr);assert(!maps&&!heaps);
 // Compiler-rt requests the array first (128 bytes), then individually aligned
 // variable blocks, later grows the array and frees every matching allocation.
 std::vector<std::thread> threads;
 for(int i=0;i<16;++i)threads.emplace_back([]{for(int t=0;t<100;++t){void*array=a::allocate(128);assert(array);memset(array,0x42,128);void*value=a::allocate(128+31);assert(value);array=a::resize(array,512);assert(array);for(int j=0;j<128;++j)assert(((char*)array)[j]==0x42);a::release(value);a::release(array);}});
 for(auto&t:threads)t.join();assert(!maps&&!heaps);
 puts("PASS: forced 128-byte compiler-TLS allocation, map fallback, alignment, array growth/failure preservation, overflow/errno, 1600 concurrent lifetimes and complete cleanup");
}
'''
p=W/'test.cpp';p.write_text(source)
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-g','-fsanitize=address,undefined','-pthread','-I',str(ROOT),str(p),'-o',str(W/'test')],check=True)
subprocess.run([str(W/'test')],check=True)
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
subprocess.run([str(ROOT/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++20','-O2','-S','-emit-llvm',str(ROOT/'java25/probe/emutls_alloc.cpp'),'-o',str(W/'backend.ll')],env=env,check=True)
ir=(W/'backend.ll').read_text()
assert '__emutls' not in ir and '__cxa_guard' not in ir
assert '@mmap' in ir and '@munmap' in ir
print('PASS: target adapter uses real OS maps; no compiler TLS or lazy initialization guard')
