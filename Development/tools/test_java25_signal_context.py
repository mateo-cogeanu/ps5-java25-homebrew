#!/usr/bin/env python3
"""Actual context accessor against console register bytes and pinned SDK offsets."""
from pathlib import Path
import re,subprocess,os
r=Path(__file__).resolve().parents[1];w=r/'build/java25/signal-context-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/native-sdk/ps5-payload-sdk/target/include/x86/ucontext.h').read_text();a=s.index('typedef struct __mcontext {',s.index('#ifdef __amd64__'));b=s.index('} mcontext_t;',a)+len('} mcontext_t;');struct=s[a:b]
struct=struct.replace('__register_t','uint64_t').replace('__uint32_t','uint32_t').replace('__uint16_t','uint16_t').replace('__aligned(16)','__attribute__((aligned(16)))')
p=w/'test.cpp';p.write_text('#include <cstdint>\n#include <cstring>\n#include <cassert>\n#include <cstdio>\n'+struct+r'''
struct ucontext_t {unsigned char mask[16];mcontext_t uc_mcontext;};
#define __PROSPERO__ 1
#include "runtime/ps5SignalContext.hpp"
int main(){
 alignas(16) unsigned char raw[sizeof(Ps5SignalContext)]{};
 auto put=[&](size_t offset,uint64_t value){memcpy(raw+offset,&value,8);};
 // Captured 033 context: independent literal offsets, not header-derived writes.
 put(0x88,0x7ed672968);put(0xa8,0x2071dd643);put(0xb0,0x7ed672978);put(0xc0,0x001b00130000000c);put(0xc8,0xc);put(0xd8,4);put(0xe0,0x206085421);put(0xe8,0x43);put(0xf0,0x10202);put(0xf8,0x7ed672910);
 auto*uc=reinterpret_cast<ucontext_t*>(raw);const ucontext_t*constant=uc;
 assert(uc->uc_mcontext.mc_rip==0x7ed672978); // Old accessor incorrectly reads stack data as RIP.
 auto*view=ps5_signal_context(uc);assert(ps5_signal_context(constant)->uc_mcontext.mc_rip==0x206085421);
 assert(view->uc_mcontext.mc_rsp==0x7ed672910&&view->uc_mcontext.mc_rbp==0x7ed672968&&view->uc_mcontext.mc_r13==0x2071dd643);
 assert(view->uc_mcontext.mc_trapno==12&&view->uc_mcontext.mc_addr==12&&view->uc_mcontext.mc_err==4&&view->uc_mcontext.mc_rflags==0x10202);
 unsigned char before[sizeof(raw)];memcpy(before,raw,sizeof(raw));view->uc_mcontext.mc_rip=0x12345678;
 for(size_t i=0;i<sizeof(raw);++i)if(i<0xe0||i>=0xe8)assert(raw[i]==before[i]);
 uint64_t rip;memcpy(&rip,raw+0xe0,8);assert(rip==0x12345678);
 puts("PASS: actual accessor and SDK machine fields; console PC/SP/FP/BCP/trap/flags fixture; old misread reproduced; continuation write changes only true RIP bytes");
}
''');inc=str(r/'.tools/java25/openjdk/src/hotspot/share');subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined','-I'+inc,str(p),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
p=w/'target.cpp';p.write_text('#include <ucontext.h>\n#include "runtime/ps5SignalContext.hpp"\nextern "C" unsigned long getpc(const ucontext_t*u){return ps5_signal_context(u)->uc_mcontext.mc_rip;}\nextern "C" void setpc(ucontext_t*u,unsigned long p){ps5_signal_context(u)->uc_mcontext.mc_rip=p;}\n')
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config');subprocess.run([str(r/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++17','-O2','-S','-emit-llvm','-I'+inc,str(p),'-o',str(w/'target.ll')],env=env,check=True);ir=(w/'target.ll').read_text();assert 'i64 224' in ir and '__emutls' not in ir and '__cxa_guard' not in ir
s=(r/'.tools/java25/openjdk/src/hotspot/os_cpu/bsd_x86/os_bsd_x86.cpp').read_text();assert not re.search(r'\buc->',s)
print('PASS: target SDK layout assertions, RIP read/write offset224 and all BSD x86 context member accesses routed through adapter')
