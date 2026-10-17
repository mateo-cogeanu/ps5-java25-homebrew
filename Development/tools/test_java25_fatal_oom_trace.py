#!/usr/bin/env python3
"""Exercise actual fatal-OOM entry body with reporter/trace contract stubs."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/fatal-oom-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/hotspot/share/utilities/debug.cpp').read_text();body=s[s.index('void report_vm_out_of_memory('):s.index('\nvoid report_should_not_call(')]
p=w/'test.cpp';p.write_text('''#include <cstdarg>
#include <cstddef>
#include <cassert>
#include <cstring>
#define __PROSPERO__ 1
enum VMErrorType { native_oom=3 };
static int stage;static size_t bytes;static unsigned long long line_number;
void ps5_vm_trace_values(const char*,unsigned long long size,const char*,unsigned long long line,const char*,unsigned long long type){assert(stage++==0);bytes=size;line_number=line;assert(type==3);}
void ps5_vm_trace(const char* text){assert((stage==1&&strcmp(text,"allocation.inline.hpp")==0)||(stage==2&&strcmp(text,"AllocateHeap")==0));++stage;}
void print_error_for_unit_test(const char*,const char*,va_list){assert(stage++==3);}
struct Thread {static Thread* current_or_null(){return nullptr;}};
struct VMError {static void report_and_die(Thread*,const char*,int,size_t,VMErrorType,const char*,va_list){assert(stage++==4);}};
void guarantee(bool condition,const char*){assert(!condition&&stage++==5);}
'''+body+'''
int main(){report_vm_out_of_memory("allocation.inline.hpp",87,8256,native_oom,"AllocateHeap");assert(stage==6&&bytes==8256&&line_number==87);}
''')
exe=w/'test';subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined',str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS: actual fatal OOM entry traces size/source/type/detail before reporter; ASan/UBSan. Trace/reporter contracts are stubs, not target IO.')
