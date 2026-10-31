#!/usr/bin/env python3
"""Exercise genuine LLVM exception-global storage and audit PS5 compiler TLS calls."""
import os, shutil, subprocess
from pathlib import Path
from java25_cxxabi_tls import ROOT,build
w=ROOT/'build/java25/cxxabi-tls-test';w.mkdir(parents=True,exist_ok=True)
llvm=Path(os.environ.get('LLVM_HOME','/opt/homebrew/opt/llvm'))/'bin'
sdk=ROOT/'.tools/native-sdk/ps5-payload-sdk'
obj=build(w/'target.o',sdk,llvm/'clang++',llvm/'llvm-nm')
source=ROOT/'.tools/cxxabi-18.1.8'
for name in ['cxa_exception_storage.cpp','cxa_exception.h']:shutil.copy2(source/name,w/name)
for name in ['cxxabi.h','__cxxabi_config.h']:shutil.copy2(sdk/'target/include/c++/v1'/name,w/name)
# LLVM18's threading header is unused in HAS_THREAD_LOCAL; current host libc++
# no longer ships its old filename. No thread/TLS implementation is substituted.
(w/'__threading_support').write_text('// Unused include in the selected upstream compiler-TLS branch.\n')
(w/'test.cpp').write_text(r'''
#include "cxa_exception.h"
#include <thread>
#include <atomic>
#include <cassert>
#include <cerrno>
extern "C" int pthread_setspecific(pthread_key_t,const void*) { return ENOMEM; }
std::atomic<int> ready{0};
int main(){
 auto*main=__cxxabiv1::__cxa_get_globals();assert(main&&main==__cxxabiv1::__cxa_get_globals_fast());
 for(int round=0;round<100;++round){
  std::thread workers[8];ready=0;
  for(int i=0;i<8;++i)workers[i]=std::thread([=]{
   auto*g=__cxxabiv1::__cxa_get_globals();assert(g&&g!=main&&g->caughtExceptions==nullptr&&g->uncaughtExceptions==0);
   g->uncaughtExceptions=i+1; ++ready;while(ready<8)std::this_thread::yield();
   assert(__cxxabiv1::__cxa_get_globals_fast()==g&&g->uncaughtExceptions==unsigned(i+1));g->uncaughtExceptions=0;
   try{try{throw 42;}catch(int x){assert(x==42);throw;}}catch(int x){assert(x==42);}
  });for(auto&t:workers)t.join();
 }assert(main->uncaughtExceptions==0);
}
''')
cxx=os.environ.get('CXX','clang++')
subprocess.run([cxx,'-std=c++14','-DHAS_THREAD_LOCAL','-I'+str(w),str(w/'cxa_exception_storage.cpp'),str(w/'test.cpp'),'-pthread','-o',str(w/'test')],check=True)
subprocess.run([str(w/'test')],check=True)
print('PASS genuine LLVM18 compiler-TLS exception globals: 800 worker lifecycles, concurrent isolation, nested throws/rethrow with pthread_setspecific refusing; PS5 object uses emutls only, console pending')
