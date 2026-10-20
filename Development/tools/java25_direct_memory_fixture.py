"""Build the actual VM direct-memory ABI over a fault-controlled host kernel model."""
from pathlib import Path
import subprocess

def build(root,work,jdk,flags=()):
    src=root/'.tools/java25/openjdk'
    fixture=work/'direct-fixture'
    (fixture/'runtime').mkdir(parents=True,exist_ok=True)
    (fixture/'runtime/ps5StartupTrace.hpp').write_text('''#pragma once
inline void ps5_vm_trace_values(const char*,unsigned long long,const char*,unsigned long long,const char*,unsigned long long){}
''')
    actual=(src/'src/hotspot/share/runtime/os.cpp').read_text()
    bridge=actual[actual.index('#ifdef __PROSPERO__\n// Native-library pressure'):]
    code=r'''
#include <jni.h>
#include <stddef.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <pthread.h>
#include <sys/mman.h>
#include "runtime/ps5NativeDirectMemory.hpp"
#include "ps5NativeMemory.h"
static pthread_mutex_t mutex=PTHREAD_MUTEX_INITIALIZER;
struct Physical{void* p;size_t bytes;bool mapped;};
static Physical physical[4096]{};
static int budget=0,live=0,maps=0;
extern "C" void ps5_test_direct_mode(int value){pthread_mutex_lock(&mutex);budget=value;pthread_mutex_unlock(&mutex);}
extern "C" int ps5_test_direct_live(){pthread_mutex_lock(&mutex);int n=live;pthread_mutex_unlock(&mutex);return n;}
extern "C" int ps5_test_direct_maps(){pthread_mutex_lock(&mutex);int n=maps;pthread_mutex_unlock(&mutex);return n;}
extern "C" size_t sceKernelGetDirectMemorySize(){return 1024ULL*1024*1024;}
extern "C" int sceKernelAllocateDirectMemory(int64_t start,int64_t end,size_t bytes,size_t alignment,int type,int64_t* offset){
 assert(start==0&&end==1024LL*1024*1024&&alignment==16384&&bytes%16384==0&&type==12);
 pthread_mutex_lock(&mutex);
 if(budget==0){pthread_mutex_unlock(&mutex);return -17;}
 for(int i=0;i<4096;++i)if(!physical[i].p){void* p=nullptr;if(posix_memalign(&p,16384,bytes)){pthread_mutex_unlock(&mutex);return -18;}physical[i]={p,bytes,false};*offset=i;++live;if(budget>0)--budget;pthread_mutex_unlock(&mutex);return 0;}
 pthread_mutex_unlock(&mutex);return -19;
}
extern "C" int sceKernelMapDirectMemory(void** address,size_t bytes,int prot,int flags,int64_t offset,size_t alignment){
 assert(prot==(PROT_READ|PROT_WRITE)&&flags==0&&alignment==16384&&offset>=0&&offset<4096);
 pthread_mutex_lock(&mutex);assert(physical[offset].p&&physical[offset].bytes==bytes&&!physical[offset].mapped);
 *address=physical[offset].p;physical[offset].mapped=true;++maps;pthread_mutex_unlock(&mutex);return 0;
}
extern "C" int sceKernelMunmap(void* address,size_t bytes){
 pthread_mutex_lock(&mutex);for(auto& p:physical)if(p.p==address){assert(p.mapped&&p.bytes==bytes);p.mapped=false;pthread_mutex_unlock(&mutex);return 0;}abort();
}
extern "C" int sceKernelReleaseDirectMemory(int64_t offset,size_t bytes){
 pthread_mutex_lock(&mutex);assert(offset>=0&&offset<4096&&physical[offset].p&&physical[offset].bytes==bytes&&!physical[offset].mapped);
 free(physical[offset].p);physical[offset]={};--live;pthread_mutex_unlock(&mutex);return 0;
}
'''
    path=fixture/'bridge.cpp';path.write_text(code+bridge)
    obj=fixture/'bridge.o'
    subprocess.run(['clang++','-std=c++17','-O1','-g','-D__PROSPERO__',*flags,
                    '-I'+str(fixture),'-I'+str(src/'src/hotspot/share'),
                    '-I'+str(src/'src/java.base/share/native/libjava'),
                    '-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),
                    '-c',str(path),'-o',str(obj)],check=True)
    return str(obj)
