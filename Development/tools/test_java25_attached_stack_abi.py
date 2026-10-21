#!/usr/bin/env python3
"""Actual VM attached-stack ABI, shared ledger tagging and guard uncommit controls."""
from pathlib import Path
import subprocess
from java25_direct_memory_fixture import build
r=Path(__file__).resolve().parents[1];w=r/'build/java25/attached-stack-abi';w.mkdir(exist_ok=True);jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
obj=build(r,w,jdk,flags=['-fsanitize=address,undefined'])
(w/'test.cpp').write_text(r'''
#include <jni.h>
#include <cassert>
#include <cstring>
#include <sys/mman.h>
#include "runtime/ps5NativeDirectMemory.hpp"
extern "C" void ps5_test_direct_mode(int);
extern "C" int ps5_test_direct_live();
extern "C" void* JVM_PS5MapNativeThreadStack(size_t);
extern "C" int JVM_PS5UnmapNativeMemory(void*,size_t);
int main(){
 constexpr size_t n=8*1024*1024,page=16384;
 assert(JVM_PS5MapNativeThreadStack(0)==MAP_FAILED);assert(JVM_PS5MapNativeThreadStack(n+page)==MAP_FAILED);assert(JVM_PS5MapNativeThreadStack(n-1)==MAP_FAILED);
 assert(JVM_PS5MapNativeThreadStack(n)==MAP_FAILED&&!ps5_test_direct_live());ps5_test_direct_mode(-1);
 void*p=JVM_PS5MapNativeThreadStack(n);assert(p!=MAP_FAILED&&ps5_test_direct_live()==1);
 assert(ps5_native_direct::stack_range(p,n)&&!ps5_native_direct::metadata_range(p,page));
 memset(p,0x42,n);assert(ps5_native_direct::uncommit_metadata(p,page));assert(!mprotect(p,page,PROT_READ|PROT_WRITE));
 for(size_t i=0;i<page;i++)assert(((char*)p)[i]==0);assert(((char*)p)[page]==0x42);
 assert(JVM_PS5UnmapNativeMemory(p,page)!=0&&ps5_test_direct_live()==1);
 assert(!JVM_PS5UnmapNativeMemory(p,n)&&!ps5_test_direct_live()&&!ps5_native_direct::state().held);
 puts("PASS actual attached-worker stack VM ABI/sharedledger stack-purpose tag,8MiBcap/pagegates,budgetfailure,guard-subrangezero/uncommit,recommit,adjacentdata and exactrelease;ASan/UBSan");
}
''')
exe=w/'check';subprocess.run(['/usr/bin/clang++','-std=c++17','-D__PROSPERO__','-fsanitize=address,undefined','-I'+str(w/'direct-fixture'),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(w/'test.cpp'),obj,'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
