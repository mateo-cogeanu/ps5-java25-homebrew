#!/usr/bin/env python3
"""Compare actual old/new raw allocator mapping footprints for a crash-sized profile."""
from pathlib import Path
import subprocess,re,shutil
r=Path(__file__).resolve().parents[1];w=r/'build/java25/prefix-bench';w.mkdir(parents=True,exist_ok=True)
actual=r/'.tools/java25/openjdk/src/hotspot/share/runtime/ps5NativeHeap.hpp';patch=r/'java25/patches/0093-ps5-compact-native-allocation-prefix.patch'
for name in ['baseline/runtime','stubs/runtime','stubs/utilities']:(w/name).mkdir(parents=True,exist_ok=True)
# Remove later mapping-backend changes before reconstructing the historical
# prefix-only control; the current compact allocator remains the other arm.
control=w/'pre-direct';(control/'src/hotspot/share/runtime').mkdir(parents=True,exist_ok=True)
for name in ['ps5NativeHeap.hpp','ps5NativeDirectMemory.hpp']:shutil.copy2(actual.parent/name,control/'src/hotspot/share/runtime'/name)
subprocess.run(['git','apply','--reverse','--include=*ps5NativeDirectMemory.hpp',str(r/'java25/patches/0104-ps5-direct-metaspace-reservation-fallback.patch')],cwd=control,check=True)
subprocess.run(['git','apply','--reverse',str(r/'java25/patches/0103-ps5-bound-vm-libc-allocation-budget.patch')],cwd=control,check=True)
subprocess.run(['git','apply','--reverse',str(r/'java25/patches/0101-ps5-native-direct-memory-fallback.patch')],cwd=control,check=True)
subprocess.run(['patch','-R','-o',str(w/'baseline/runtime/ps5NativeHeap.hpp'),str(control/'src/hotspot/share/runtime/ps5NativeHeap.hpp'),str(patch)],check=True,capture_output=True)
(w/'stubs/utilities/permitForbiddenFunctions.hpp').write_text('#pragma once\nnamespace permit_forbidden_function{inline void*malloc(size_t){return nullptr;}inline void*realloc(void*,size_t){return nullptr;}inline void free(void*){abort();}}\n')
(w/'stubs/runtime/ps5StartupTrace.hpp').write_text('#pragma once\ninline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}\n')
c=w/'bench.cpp';c.write_text(r'''
#include <cstdlib>
#include <cstdint>
#include <cstdio>
#include <cassert>
#include <cstring>
#include <vector>
#include <sys/mman.h>
#include <unistd.h>
extern "C" size_t sceKernelGetDirectMemorySize(){return 0;}
extern "C" int sceKernelAllocateDirectMemory(int64_t,int64_t,size_t,size_t,int,int64_t*){return -1;}
extern "C" int sceKernelMapDirectMemory(void**,size_t,int,int,int64_t,size_t){return -1;}
extern "C" int sceKernelMunmap(void*,size_t){return -1;}
extern "C" int sceKernelReleaseDirectMemory(int64_t,size_t){return -1;}
size_t live=0,peak=0;
void*map(void*p,size_t n,int prot,int flags,int fd,off_t off){p=mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED){live+=n;if(live>peak)peak=live;}return p;}
int unmap(void*p,size_t n){int rc=munmap(p,n);if(!rc)live-=n;return rc;}
long model_page(int){return 16384;}
#ifdef MODEL_ALIGNMENT
struct alignas(16) ModelMaxAlign { char bytes[16]; };
#define max_align_t ModelMaxAlign
#endif
#define mmap map
#define munmap unmap
#define sysconf model_page
#include "runtime/ps5NativeHeap.hpp"
int main(){
 std::vector<void*> blocks;const size_t counts[]={123000,50000,63000,18000,4300,1700,280,800};
 for(int k=0;k<8;k++)for(size_t i=0;i<counts[k];i++){size_t n=32UL<<k;void*p=ps5_native_heap::allocate(n);assert(p);memset(p,k+1,n);blocks.push_back(p);}
 printf("mapped_peak=%zu header=%zu blocks=%zu\n",peak,sizeof(ps5_native_heap::Header),blocks.size());
 for(void*p:blocks)ps5_native_heap::release(p);ps5_native_heap::trim_idle();assert(live==0);
}
''')
for alignment in [8,16]:
 peaks={}
 for label,include in [('baseline',w/'baseline'),('compact',r/'.tools/java25/openjdk/src/hotspot/share')]:
  exe=w/(label+'-'+str(alignment)+'-bench');subprocess.run(['clang++','-std=c++17','-O1','-g','-D__PROSPERO__=1',*(['-DMODEL_ALIGNMENT=1'] if alignment==16 else []),'-fsanitize=address,undefined','-I'+str(w/'stubs'),'-I'+str(include),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(c),'-o',str(exe)],check=True)
  result=subprocess.run([str(exe)],check=True,text=True,capture_output=True);print(alignment,label,result.stdout.strip());peaks[label]=int(re.search(r'mapped_peak=(\d+)',result.stdout)[1])
 saved=peaks['baseline']-peaks['compact'];assert saved>=(1500000 if alignment==8 else 4000000),peaks
 print('PASS: actual allocator saves',saved,'mapped bytes with identical261080live blocks, alignment model',alignment,'; ASan/UBSan and complete cleanup; not a console peak guarantee')
