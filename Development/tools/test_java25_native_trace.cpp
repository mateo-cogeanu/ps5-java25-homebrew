/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <cstdlib>
#include <cassert>
#include <fstream>
#include <string>
#include <thread>
#include <signal.h>
#include <sys/stat.h>
static int test_trace_open(const char*,int flags,int mode) {
 return ::open("build/java25/native-call-test.log",flags,mode);
}
#define __PROSPERO__ 1
#define open test_trace_open
#include "../java25/probe/native_trace.hpp"
#undef open
static bool interrupt_malloc=false;
static volatile sig_atomic_t saw_active_call=0;
static void observe_signal(int) {
 auto &record=ps5_vm_native_call_record();
 saw_active_call=record.caller!=0 && !record.completed && record.bytes==987 && record.operation!=nullptr;
}
extern "C" {
void* __real_memcpy(void* a,const void* b,size_t n){return std::memcpy(a,b,n);}
void* __real_memmove(void* a,const void* b,size_t n){return std::memmove(a,b,n);}
int __real_memcmp(const void* a,const void* b,size_t n){return std::memcmp(a,b,n);}
int __real_strcmp(const char* a,const char* b){return std::strcmp(a,b);}
size_t __real_strlen(const char* a){return std::strlen(a);}
void* __real_malloc(size_t n){if(interrupt_malloc){raise(SIGUSR1);errno=ENOMEM;return nullptr;}return std::malloc(n);}
void* __real_calloc(size_t a,size_t b){return std::calloc(a,b);}
void* __real_realloc(void* p,size_t n){return std::realloc(p,n);}
void __real_free(void* p){std::free(p);}
void* __real_memset(void* a,int v,size_t n){return std::memset(a,v,n);}
int __real_strncmp(const char* a,const char* b,size_t n){return std::strncmp(a,b,n);}
char* __real_strncpy(char* a,const char* b,size_t n){return std::strncpy(a,b,n);}
char* __real_strcpy(char* a,const char* b){return std::strcpy(a,b);}
char* __real_strdup(const char* a){return ::strdup(a);}
char* __real_strchr(const char* a,int v){return const_cast<char*>(std::strchr(a,v));}
void* __real_memchr(const void* a,int v,size_t n){return const_cast<void*>(std::memchr(a,v,n));}
}
int main() {
 ::unlink("build/java25/native-call-test.log");
 char output[16]{};ps5_native_trace::enable();
 assert(__wrap_memcpy(output,"hello",6)==output);assert(std::strcmp(output,"hello")==0);
 assert(__wrap_memmove(output+1,output,5)==output+1);assert(std::memcmp(output,"hhello",6)==0);
 assert(__wrap_memcmp("a","b",1)<0);assert(__wrap_strcmp("b","a")>0);assert(__wrap_strlen("hello")==5);
 assert(__wrap_memset(output,0,16)==output);
 assert(__wrap_strncpy(output,"abc",8)==output);assert(std::strcmp(output,"abc")==0);
 assert(__wrap_strncmp("ax","ay",1)==0);assert(__wrap_strchr(output,'b')==output+1);
 assert(__wrap_strcpy(output,"abc")==output);
 assert(std::strcmp(output,"abc")==0);
 assert(__wrap_memchr(output,'c',3)==output+2);
 char* duplicate=__wrap_strdup("native-string");assert(duplicate&&std::strcmp(duplicate,"native-string")==0);
 assert(ps5_vm_native_call_record().destination==(unsigned long long)duplicate);
 std::free(duplicate);
 void* allocation=__wrap_malloc(64);assert(allocation);
 assert(ps5_vm_native_call_record().completed&&ps5_vm_native_call_record().bytes==64);
 assert(ps5_vm_native_call_record().destination==(unsigned long long)allocation);
 std::free(allocation);
 assert(__wrap_memchr(output,'c',3)==output+2);
 auto record=ps5_vm_native_call_record();
 assert(record.completed&&record.bytes==3&&record.source==(unsigned long long)output&&record.caller);
 assert(std::strcmp(record.operation,"CALL: memchr caller=")==0);
 void* zeros=__wrap_calloc(8,8);assert(zeros);
 for(int i=0;i<64;++i)assert(static_cast<unsigned char*>(zeros)[i]==0);
 assert(ps5_vm_native_call_record().bytes==64);
 void* resized=__wrap_realloc(zeros,128);assert(resized);
 assert(ps5_vm_native_call_record().destination==(unsigned long long)resized);
 __wrap_free(resized);assert(ps5_vm_native_call_record().completed);
 __wrap_free(nullptr);
 ps5_native_trace::quiet();
 struct stat before_quiet{};assert(::stat("build/java25/native-call-test.log",&before_quiet)==0);
 assert(__wrap_memcpy(output,"quiet",6)==output);
 auto quiet_record=ps5_vm_native_call_record();
 assert(quiet_record.completed&&quiet_record.bytes==6&&quiet_record.caller);
 ps5_vm_trace("TEST: main-thread stage");
 std::thread worker([&]{
  assert(ps5_vm_native_call_record().caller==0);
  assert(!ps5_vm_trace_io_active()&&!ps5_vm_signal_trace_active());
  ps5_vm_trace_io_active()=true;ps5_vm_signal_trace_active()=true;
  assert(__wrap_strlen("guarded")==7&&ps5_vm_native_call_record().caller==0);
  ps5_vm_trace_io_active()=false;ps5_vm_signal_trace_active()=false;
  assert(__wrap_memcmp("x","y",1)<0);
  assert(ps5_vm_native_call_record().bytes==1);
  ps5_vm_trace("TEST: worker-thread stage");
 });worker.join();
 assert(ps5_vm_native_call_record().caller==quiet_record.caller);
 assert(std::string(ps5_vm_last_stage())=="TEST: main-thread stage");
 assert(!ps5_vm_trace_io_active()&&!ps5_vm_signal_trace_active());
 // Compare file size only around quiet native calls: explicit stages still log.
 struct stat stage_size{};assert(::stat("build/java25/native-call-test.log",&stage_size)==0);
 signal(SIGUSR1,observe_signal);interrupt_malloc=true;
 assert(__wrap_malloc(987)==nullptr&&errno==ENOMEM&&saw_active_call);
 interrupt_malloc=false;
 assert(ps5_vm_native_call_record().completed&&ps5_vm_native_call_record().destination==0);
 struct stat after_quiet{};assert(::stat("build/java25/native-call-test.log",&after_quiet)==0);
 assert(stage_size.st_size==after_quiet.st_size);
 assert(after_quiet.st_size>before_quiet.st_size); // explicit stages were retained
 ps5_vm_trace("DONE: Metadata zeroing");
 assert(__wrap_memchr(output,'q',1)==output);record=ps5_vm_native_call_record();
 std::string before=ps5_vm_last_stage();ps5_vm_signal_trace_active()=true;
 assert(__wrap_strlen("guarded")==7);assert(before==ps5_vm_last_stage());
 assert(record.caller==ps5_vm_native_call_record().caller&&record.source==ps5_vm_native_call_record().source);
 ps5_vm_signal_trace_active()=false;
 ps5_vm_trace_io_active()=true;
 assert(__wrap_strlen("logging")==7);
 assert(record.caller==ps5_vm_native_call_record().caller);
 ps5_vm_trace_io_active()=false;ps5_native_trace::disable();
 std::ifstream file("build/java25/native-call-test.log");std::string text((std::istreambuf_iterator<char>(file)),{});
 for(const char* name:{"memcpy","memmove","memcmp","strcmp","strlen","memset","strncmp","strncpy","strchr","memchr","strcpy","malloc","calloc","realloc","free","strdup"}) {
  assert(text.find(std::string("CALL: ")+name+" caller=")!=std::string::npos);
 }
 assert(text.find(" src=0x")!=std::string::npos&&text.find(" dst=0x")!=std::string::npos);
 // Fill the actual bounded table with synthetic identities; no allocations,
 // no eviction of the live main thread and explicit exhaustion handling.
 auto *main_context=ps5_vm_thread_context();size_t claimed=0;
 for(uintptr_t key=0x100001;key<0x100001+1025;++key)
  if(ps5_vm_context_for_key(key))++claimed;
 assert(claimed>0&&claimed<1024);
 assert(ps5_vm_context_for_key(0xabcdef)==nullptr);
 assert(ps5_vm_thread_context()==main_context);
 Ps5TraceFlag unavailable{nullptr};assert(unavailable);unavailable=false;assert(unavailable);
 std::puts("PASS: sixteen original call semantics; quiet call/signal evidence without per-call IO; per-thread records/stages/guards; bounded non-allocating storage and exhaustion");
}
