#!/usr/bin/env python3
"""Test actual PS5 Thread current-pointer methods with the real pthread TLS backend."""
from pathlib import Path
import os,re,subprocess
ROOT=Path(__file__).resolve().parents[1]
WORK=ROOT/'build/java25/current-thread-tls-test';WORK.mkdir(parents=True,exist_ok=True)
SRC=ROOT/'.tools/java25/openjdk/src/hotspot'
hpp=(SRC/'share/runtime/thread.hpp').read_text()
cpp=(SRC/'share/runtime/thread.cpp').read_text()
backend=(SRC/'os/posix/threadLocalStorage_posix.cpp').read_text()
def method(text, signature):
 start=text.index(signature);opening=text.index('{',start);depth=1;end=opening+1
 while depth:
  depth += (text[end]=='{')-(text[end]=='}');end+=1
 return text[start:end]+'\n'
decl='''class Thread;
class ThreadLocalStorage {public: static Thread* thread();static void set_thread(Thread*);static void init();static bool is_initialized();};
class Thread {public: void initialize_thread_current();void clear_thread_current();static Thread* current();static Thread* current_or_null();static Thread* current_or_null_safe();};
'''
actual=''.join(method(hpp,'inline Thread* Thread::'+name+'()') for name in ('current_or_null_safe','current_or_null','current'))
actual+=''.join(method(cpp,'void Thread::'+name+'()') for name in ('initialize_thread_current','clear_thread_current'))
backend=backend[backend.index('static pthread_key_t _thread_key;'):]
# Only assertion/trace infrastructure is replaced. Lifecycle/getter methods and
# actual POSIX key, lookup, setter and destructor implementation are extracted.
source='''#define __PROSPERO__ 1
#include <pthread.h>
#include <assert.h>
#include <stdlib.h>
#undef assert
#define assert(condition, ...) do { if (!(condition)) abort(); } while(0)
#define assert_status(condition, ...) assert(condition)
static void ps5_vm_trace(const char*) {}
'''+decl+backend+actual
main=r'''
#include <signal.h>
#include <atomic>
static std::atomic<int> seen{0};
static void signal_handler(int){assert(Thread::current_or_null()!=nullptr);++seen;}
static void* child(void*){
 assert(Thread::current_or_null()==nullptr);
 for(int i=0;i<100;++i){Thread own;own.initialize_thread_current();
  assert(Thread::current()==&own);assert(Thread::current_or_null_safe()==&own);
  for(int j=0;j<100;++j)assert(Thread::current_or_null()==&own);
  raise(SIGUSR1);own.clear_thread_current();assert(Thread::current_or_null()==nullptr);
 }
 return nullptr;
}
int main(){
 assert(Thread::current_or_null()==nullptr);ThreadLocalStorage::init();
 assert(Thread::current_or_null()==nullptr);signal(SIGUSR1,signal_handler);
 Thread main_thread;main_thread.initialize_thread_current();
 pthread_t threads[16];for(auto& t:threads)assert(pthread_create(&t,nullptr,child,nullptr)==0);
 for(auto t:threads)assert(pthread_join(t,nullptr)==0);
 assert(Thread::current()==&main_thread);main_thread.clear_thread_current();
 assert(Thread::current_or_null()==nullptr);assert(seen==1600);
 // Preserve the backend's existing JNI destructor restoration contract.
 restore_thread_pointer(&main_thread);assert(Thread::current()==&main_thread);
 main_thread.clear_thread_current();
}
'''
(WORK/'test.cpp').write_text(source+main)
subprocess.run(['clang++','-std=c++17','-femulated-tls','-fsanitize=address,undefined','-pthread',str(WORK/'test.cpp'),'-o',str(WORK/'check')],check=True)
subprocess.run([str(WORK/'check')],check=True)
(WORK/'target.cpp').write_text(source+'extern "C" Thread* current_probe(){return Thread::current_or_null();}\n')
env=os.environ.copy();env.setdefault('LLVM_CONFIG','/opt/homebrew/opt/llvm/bin/llvm-config')
subprocess.run([str(ROOT/'.tools/native-sdk/ps5-payload-sdk/bin/prospero-clang++'),'-std=c++17','-O2','-S','-emit-llvm',str(WORK/'target.cpp'),'-o',str(WORK/'target.ll')],env=env,check=True)
ir=(WORK/'target.ll').read_text()
for token in ('__emutls','_thr_current','@malloc','@calloc','@realloc','__cxa_guard'):
 assert token not in ir,token
for token in ('@pthread_getspecific','@pthread_setspecific','@pthread_key_create'):
 assert token in ir,token
print('PASS: actual Thread lifecycle/getters and POSIX backend, 1600 attach/clear cycles, concurrent isolation, signal lookups, pre-init null, destructor restoration; target IR has native pthread TLS without compiler-TLS emulation or direct allocator calls')
