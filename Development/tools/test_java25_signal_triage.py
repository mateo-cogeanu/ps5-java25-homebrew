#!/usr/bin/env python3
"""Run the actual stack-guard triage block with platform calls instrumented."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'.tools/java25/openjdk/src/hotspot/os_cpu/bsd_x86/os_bsd_x86.cpp').read_text()
a=s.index('    // Handle ALL stack overflow variations here');b=s.index('    if ((sig == SIGSEGV || sig == SIGBUS) && VM_Version::is_cpuinfo_segv_addr(pc))',a)
block=s[a:b]
w=ROOT/'build/java25/signal-triage-test';w.mkdir(parents=True,exist_ok=True)
source=r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstdio>
#define __FreeBSD__ 1
#define SIGSEGV 11
#define SIGBUS 10
#define P_PID 1
#define PROC_STACKGAP_STATUS 18
#define PROC_STACKGAP_DISABLE 2
using address=unsigned char*;
unsigned char stack[65536];
int calls=0,queries=0,guards=0,control_ret=-1,control_status=0,handled=0;
int getpid(){return 1;}
int procctl(int,int,int command,int*status){++calls;assert(command==18);*status=control_status;return control_ret;}
int sysctlbyname(const char*,int*value,size_t*,void*,size_t){++queries;*value=guards;return 0;}
void ps5_vm_trace(const char*){}
struct JavaThread{bool is_in_full_stack(address a){return a>=stack+16384&&a<stack+32768;}};
namespace os{size_t vm_page_size(){return 16384;} namespace Posix{bool handle_stack_overflow(JavaThread*,address,address,void*,address*stub){++handled;*stub=stack;return true;}}}
struct Info{address si_addr;};
bool triage(int sig,Info*info,JavaThread*thread){address pc=stack,stub=nullptr;void*uc=nullptr;
'''+block+r'''
return false;}
int main(){
 JavaThread thread;Info info{stack};
 assert(!triage(SIGSEGV,&info,&thread));assert(handled==0);
#ifdef __PROSPERO__
 assert(calls==0&&queries==0);
#else
 assert(calls==1&&queries==1);
#endif
 info.si_addr=stack+20000;assert(triage(SIGSEGV,&info,&thread));assert(handled==1);
 assert(triage(SIGBUS,&info,&thread));assert(handled==2);
 assert(!triage(4,&info,&thread));assert(handled==2);
#ifndef __PROSPERO__
 calls=queries=0;control_ret=0;control_status=2;info.si_addr=stack;assert(!triage(SIGSEGV,&info,&thread));assert(calls==1&&queries==0);
 control_ret=-1;guards=1;info.si_addr=stack+40000;assert(triage(SIGSEGV,&info,&thread));assert(handled==3);
#else
 guards=1;info.si_addr=stack+40000;assert(!triage(SIGSEGV,&info,&thread));assert(handled==2&&calls==0&&queries==0);
#endif
 puts("PASS: actual triage; JVM stack guards retained; desktop adjustment retained; PS5 makes no desktop kernel queries");
}
'''
(w/'test.cpp').write_text(source)
for platform,flags in [('ps5',['-D__PROSPERO__=1']),('freebsd',[])]:
 subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined',*flags,str(w/'test.cpp'),'-o',str(w/platform)],check=True)
 subprocess.run([str(w/platform)],check=True)
