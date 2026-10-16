#!/usr/bin/env python3
"""Check release-build synchronization failures using actual helper/constructor."""
from pathlib import Path
import subprocess
R=Path(__file__).resolve().parents[1];W=R/'build/java25/pthread-check-test';(W/'runtime').mkdir(parents=True,exist_ok=True)
(W/'runtime/ps5StartupTrace.hpp').write_text('''#pragma once
inline void ps5_vm_trace(const char*){++notes;}
inline void ps5_vm_trace_values(const char* op,unsigned long long status,const char*,unsigned long long,const char*,unsigned long long){last_op=op;last_status=status;}
''')
s=(R/'.tools/java25/openjdk/src/hotspot/os/posix/os_posix.cpp').read_text();a=s.index('PlatformEvent::PlatformEvent()');b=s.index('\nvoid PlatformEvent::park()',a);ctor=s[a:b]
assert 'PlatformMutex::PlatformMutex() {\n  int status = ps5_sync::mutex_init(&_mutex, _mutexAttr);\n  PS5_PTHREAD_CHECK(status == 0, status, "monitor mutex_init");' in s
p=W/'test.cpp';p.write_text(r'''
#undef NDEBUG
#include <cassert>
#include <cstdio>
#include <cerrno>
#include <cstring>
#include <cstdint>
#include <pthread.h>
int notes=0,last_status=0,cond_calls=0,mutex_calls=0;const char* last_op=nullptr;int fail_cond=0,fail_mutex=0;
#define __PROSPERO__ 1
#define guarantee(p,...) do{if(!(p))throw last_status;}while(0)
#include "runtime/ps5PthreadChecks.hpp"
struct PlatformEvent {pthread_cond_t _cond[1];pthread_mutex_t _mutex[1];int _event,_nParked;PlatformEvent();};
static pthread_condattr_t _condAttr[1];static pthread_mutexattr_t _mutexAttr[1];
int test_cond_init(pthread_cond_t*,const pthread_condattr_t*){++cond_calls;return fail_cond;}
int test_mutex_init(pthread_mutex_t*,const pthread_mutexattr_t*){++mutex_calls;return fail_mutex;}
#define pthread_cond_init test_cond_init
#define pthread_mutex_init test_mutex_init
#include "runtime/ps5Synchronization.hpp"
'''+ctor+r'''
int main(){
 PlatformEvent ok;assert(ok._event==0&&ok._nParked==0&&notes==0);
 fail_cond=ENOMEM;int before=mutex_calls;try{PlatformEvent bad;assert(false);}catch(int s){assert(s==ENOMEM&&strcmp(last_op,"cond_init")==0);}assert(mutex_calls==before);
 fail_cond=0;fail_mutex=ENOMEM;try{PlatformEvent bad;assert(false);}catch(int s){assert(s==ENOMEM&&strcmp(last_op,"event mutex_init")==0);}
 assert(notes==2);int status=ETIMEDOUT;PS5_PTHREAD_CHECK(status==0||status==ETIMEDOUT,status,"timeout");status=EBUSY;PS5_PTHREAD_CHECK(status==0||status==EBUSY,status,"trylock");assert(notes==2);
 puts("PASS: actual release-check helper and PlatformEvent constructor report ENOMEM before invalid use; successful init and allowed timeout/busy results retained");
}
''')
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-g','-DNDEBUG','-fsanitize=address,undefined','-I',str(W),'-I',str(R/'.tools/java25/openjdk/src/hotspot/share'),str(p),'-o',str(W/'test')],check=True)
subprocess.run([str(W/'test')],check=True)
