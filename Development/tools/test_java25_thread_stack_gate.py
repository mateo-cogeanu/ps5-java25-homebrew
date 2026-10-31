#!/usr/bin/env python3
"""Compile the actual os::create_thread fallback block against controlled owner calls."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/thread-stack-gate';w.mkdir(exist_ok=True)
s=(r/'.tools/java25/openjdk/src/hotspot/os/bsd/os_bsd.cpp').read_text();a=s.index('#ifdef __PROSPERO__\n    // CompilerThread');b=s.index('#endif',a)+len('#endif');actual=s[a:b]
source=r'''
#include <cassert>
#include <cerrno>
#include <cstddef>
#define __PROSPERO__ 1
enum Type{vm_thread,java_thread,compiler_thread,watcher_thread,gc_thread};
static int calls;static size_t last_size;static void* last_argument;
namespace ps5_thread_stacks {int create(int*tid,size_t size,void*(*entry)(void*),void*arg){++calls;last_size=size;last_argument=arg;*tid=42;return 0;}}
static void* thread_native_entry(void*){return nullptr;}
static int attempt(int ret,int error,Type thr_type,size_t stack_size){errno=error;int tid=0;void*thread=(void*)0x1234;
'''+actual+r'''
return ret;}
int main(){
 for(Type type:{vm_thread,java_thread,compiler_thread,watcher_thread,gc_thread})for(int ret:{0,EAGAIN,EINVAL})for(int error:{0,ENOMEM,EACCES}){
  int before=calls;size_t size=type==compiler_thread?1024*1024:512*1024;
  int result=attempt(ret,error,type,size);bool eligible=ret==EAGAIN&&(type==java_thread||type==compiler_thread);
  assert(calls==before+(eligible?1:0));assert(result==(eligible?0:ret));if(eligible)assert(last_size==size&&last_argument==(void*)0x1234);
 }
}
'''
(w/'gate.cpp').write_text('#include <initializer_list>\n'+source)
subprocess.run(['/usr/bin/clang++','-std=c++17','-fsanitize=address,undefined',str(w/'gate.cpp'),'-o',str(w/'gate')],check=True)
subprocess.run([str(w/'gate')],check=True)
print('PASS actual fallback gate matrix: Java/compiler after returned EAGAIN regardless of unchanged/stale errno, requested stack sizes/entry arguments unchanged; VM/watcher/GC/ordinary success/other errors excluded')
