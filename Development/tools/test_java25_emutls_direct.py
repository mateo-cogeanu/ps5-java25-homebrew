#!/usr/bin/env python3
"""Actual emutls allocator with failed libc/anonymous routes and opt-in direct backend."""
from pathlib import Path
import ast,subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/emutls-direct-test';w.mkdir(exist_ok=True)
tree=ast.parse((r/'tools/test_java25_emutls_allocator.py').read_text());s=next(ast.literal_eval(n.value)for n in tree.body if isinstance(n,ast.Assign)and any(isinstance(t,ast.Name)and t.id=='source'for t in n.targets))
s=s.replace('#include <vector>','#include <vector>\n#include <mutex>\n#define PS5_EMUTLS_DIRECT_TEST')
s=s.replace('namespace a=ps5::emutls_alloc;',r'''
static std::mutex direct_lock;
static void* owned[256];static size_t lengths[256];static std::atomic<int> direct_live{0},direct_calls{0};static std::atomic<bool> refuse_direct{false};
extern "C" void* ps5_emutls_direct_map(size_t n){++direct_calls;if(refuse_direct){errno=ENOMEM;return MAP_FAILED;}std::lock_guard<std::mutex> lock(direct_lock);for(int i=0;i<256;i++)if(!owned[i]){void*p=::mmap(nullptr,n,PROT_READ|PROT_WRITE,MAP_PRIVATE|MAP_ANON,-1,0);if(p!=MAP_FAILED){owned[i]=p;lengths[i]=n;++direct_live;}return p;}errno=ENOMEM;return MAP_FAILED;}
extern "C" bool ps5_emutls_direct_unmap(void*p,size_t n,int*result){std::lock_guard<std::mutex> lock(direct_lock);for(int i=0;i<256;i++)if(owned[i]==p){assert(lengths[i]==n);*result=::munmap(p,n);assert(!*result);owned[i]=nullptr;--direct_live;return true;}return false;}
namespace a=ps5::emutls_alloc;
''')
s=s.replace(' puts("PASS:',r'''
 deny_map=true;assert(!a::allocate(16)&&direct_calls==0);a::enable_direct(true);errno=EDOM;
 void*d=a::allocate(16);assert(d&&direct_live==1&&errno==EDOM);memset(d,0x71,16);
 d=a::resize(d,4096);assert(d&&direct_live==1);for(int i=0;i<16;i++)assert(((unsigned char*)d)[i]==0x71);
 refuse_direct=true;assert(!a::resize(d,8192)&&errno==ENOMEM&&direct_live==1);for(int i=0;i<16;i++)assert(((unsigned char*)d)[i]==0x71);refuse_direct=false;a::release(d);assert(!direct_live&&!maps&&!heaps);
 threads.clear();for(int i=0;i<8;i++)threads.emplace_back([]{for(int j=0;j<100;j++){void*p=a::allocate(16);assert(p);memset(p,0x52,16);p=a::resize(p,512);assert(p);for(int k=0;k<16;k++)assert(((unsigned char*)p)[k]==0x52);a::release(p);}});for(auto&t:threads)t.join();assert(!direct_live&&!maps&&!heaps);a::enable_direct(false);assert(!a::allocate(16));
 puts("PASS: opt-in direct emutls16byte payload/48byte total, failed-growth ownership,800concurrent lifetimes and paired cleanup;''')
p=w/'test.cpp';p.write_text(s);exe=w/'test';subprocess.run(['clang++','-std=c++20','-fsanitize=address,undefined','-pthread','-I'+str(r),str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
