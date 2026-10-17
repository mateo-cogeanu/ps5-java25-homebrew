#!/usr/bin/env python3
"""Check actual bounded signal stack sampler without allocation or TLS."""
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parents[1];w=r/'build/java25/signal-stack-test';w.mkdir(parents=True,exist_ok=True);inc=r/'.tools/java25/openjdk/src/hotspot/share'
p=w/'test.cpp';p.write_text(r'''
#include <cassert>
#include <sys/mman.h>
#include <unistd.h>
#include "runtime/ps5SignalStack.hpp"
int main(){
 size_t page=sysconf(_SC_PAGESIZE);auto*m=(unsigned char*)mmap(nullptr,page*3,PROT_NONE,MAP_PRIVATE|MAP_ANONYMOUS,-1,0);assert(m!=MAP_FAILED);assert(mprotect(m+page,page,PROT_READ|PROT_WRITE)==0);
 auto*p=(uintptr_t*)(m+page);uintptr_t low=(uintptr_t)p,high=low+page;for(unsigned i=0;i<32;i++)p[i]=0x1000+i;
 p[8]=(uintptr_t)(p+12);p[9]=0x12345678;p[12]=(uintptr_t)(p+16);p[13]=0x23456789;p[16]=(uintptr_t)(p+16);p[17]=0x3456789a;
 unsigned raw=0,frames=0;
 ps5_signal_stack_snapshot(low,(uintptr_t)(p+8),low,high,[&](bool f,uintptr_t at,uintptr_t a,uintptr_t b){if(f){++frames;assert(at>=low&&b>=0x12345678);}else{++raw;assert(at>=low&&at<low+256);}});
 assert(raw==16&&frames==3);
 unsigned count=0;auto emit=[&](bool,uintptr_t,uintptr_t,uintptr_t){++count;};
 ps5_signal_stack_snapshot(low-16,high,low,high,emit);assert(count==0);
 ps5_signal_stack_snapshot(low+1,low+3,low,high,emit);assert(count==0);
 ps5_signal_stack_snapshot(high-2*sizeof(uintptr_t),0,low,high,emit);assert(count==1);
 ps5_signal_stack_snapshot(UINTPTR_MAX-7,UINTPTR_MAX-7,low,high,emit);assert(count==1);
 ps5_signal_stack_snapshot(low,low,high,low,emit);assert(count==1);
 uintptr_t a,b;assert(!ps5_signal_stack_pair(high-1,low,high,&a,&b));assert(munmap(m,page*3)==0);
}
''');subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+str(inc),str(p),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
p=w/'target.cpp';p.write_text('#include "runtime/ps5SignalStack.hpp"\nextern "C" void emit(bool,uintptr_t,uintptr_t,uintptr_t);\nextern "C" void sample(uintptr_t sp,uintptr_t fp,uintptr_t low,uintptr_t high){ps5_signal_stack_snapshot(sp,fp,low,high,emit);}\n')
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config');subprocess.run([str(r/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++17','-O2','-S','-emit-llvm','-I'+str(inc),str(p),'-o',str(w/'target.ll')],env=env,check=True);ir=(w/'target.ll').read_text()
for symbol in ('@malloc','__emutls','__cxa_guard','@mmap'):assert symbol not in ir
print('PASS: actual sampler ASan/UBSan guarded mappings, bounds/alignment/overflow/reversed ranges, monotonic/cyclic frame chains and bounded counts; target IR has no allocator/TLS/guard calls')
