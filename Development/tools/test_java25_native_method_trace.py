#!/usr/bin/env python3
"""Check actual length-delimited native-method trace formatter under sanitizers."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/native-method-trace-test';(w/'runtime').mkdir(parents=True,exist_ok=True)
(w/'runtime/ps5StartupTrace.hpp').write_text('''#pragma once
#include <cstring>
#include <pthread.h>
void test_line(const char*);
void test_values(unsigned long long,unsigned long long);
inline void ps5_vm_trace(const char* s){test_line(s);}
inline void ps5_vm_trace_values(const char*,unsigned long long a,const char*,unsigned long long b,const char*,unsigned long long){test_values(a,b);}
''')
p=w/'test.cpp';p.write_text(r'''
#include <cassert>
#include <cstring>
#include <string>
#include <thread>
#include <vector>
static thread_local std::string captured;
static thread_local unsigned long long target,self;
void test_line(const char* s){captured=s;assert(captured.size()<384);}
void test_values(unsigned long long a,unsigned long long b){target=a;self=b;}
#define __PROSPERO__ 1
#include "runtime/ps5NativeMethodTrace.hpp"
int main(){
 const unsigned char holder[]={'a','/','B'},name[]={'f'},sig[]={'(',')','V'};
 ps5_trace_native_method("begin",holder,3,name,1,sig,3,0x123456);
 assert(captured=="begin a/B.f()V"&&target==0x123456&&self==(uintptr_t)pthread_self());
 unsigned char hostile[2048];memset(hostile,0x80,sizeof(hostile));
 ps5_trace_native_method("a very long diagnostic phase that exceeds the bounded stage length",hostile,sizeof(hostile),hostile,sizeof(hostile),hostile,sizeof(hostile),0);
 assert(captured.size()<384&&captured.find('~')!=std::string::npos&&captured.find('?')!=std::string::npos&&target==0);
 ps5_trace_native_method(nullptr,nullptr,0,nullptr,0,nullptr,0,7);assert(captured==" ."&&target==7);
 std::vector<std::thread> threads;for(int i=0;i<8;i++)threads.emplace_back([i]{for(int n=0;n<1000;n++){const unsigned char a[]={'X'},b[]={'m'},c[]={'(',')','I'};ps5_trace_native_method("lookup",a,1,b,1,c,3,i+1);assert(captured=="lookup X.m()I"&&target==(unsigned)i+1&&self==(uintptr_t)pthread_self());}});
 for(auto& t:threads)t.join();
}
''')
exe=w/'test';subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-pthread','-I'+str(w),'-I'+str(r/'.tools/java25/openjdk/src/hotspot/share'),str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS: actual native-preparation formatter, unterminated Symbol slices, truncation/nonprintable/empty inputs,target/thread identity and concurrent formatting; ASan/UBSan. Trace IO is stubbed; target integration requires console.')
