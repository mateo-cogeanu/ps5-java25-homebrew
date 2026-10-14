/* SPDX-License-Identifier: GPL-3.0-or-later */
#include <fcntl.h>
#include <unistd.h>
#include <cstring>
#include <cstdlib>
#include <cassert>
#include <fstream>
#include <string>
static int test_trace_open(const char*,int flags,int mode) {
 return ::open("build/java25/native-call-test.log",flags,mode);
}
#define __PROSPERO__ 1
#define open test_trace_open
#include "../java25/probe/native_trace.hpp"
#undef open
extern "C" {
void* __real_memcpy(void* a,const void* b,size_t n){return std::memcpy(a,b,n);}
void* __real_memmove(void* a,const void* b,size_t n){return std::memmove(a,b,n);}
int __real_memcmp(const void* a,const void* b,size_t n){return std::memcmp(a,b,n);}
int __real_strcmp(const char* a,const char* b){return std::strcmp(a,b);}
size_t __real_strlen(const char* a){return std::strlen(a);}
void* __real_malloc(size_t n){return std::malloc(n);}
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
 ps5_vm_trace("DONE: Metadata zeroing");
 std::string before=ps5_vm_last_stage();ps5_vm_signal_trace_active()=true;
 assert(__wrap_strlen("guarded")==7);assert(before==ps5_vm_last_stage());
 assert(record.caller==ps5_vm_native_call_record().caller&&record.source==ps5_vm_native_call_record().source);
 ps5_vm_signal_trace_active()=false;
 ps5_vm_trace_io_active()=true;
 assert(__wrap_strlen("logging")==7);
 assert(record.caller==ps5_vm_native_call_record().caller);
 ps5_vm_trace_io_active()=false;ps5_native_trace::disable();
 std::ifstream file("build/java25/native-call-test.log");std::string text((std::istreambuf_iterator<char>(file)),{});
 for(const char* name:{"memcpy","memmove","memcmp","strcmp","strlen","memset","strncmp","strncpy","strchr","memchr","strcpy","malloc","strdup"}) {
  assert(text.find(std::string("CALL: ")+name+" caller=")!=std::string::npos);
 }
 assert(text.find(" src=0x")!=std::string::npos&&text.find(" dst=0x")!=std::string::npos);
 std::puts("PASS: thirteen original call semantics, retained caller/pointers/completion state, preserved VM stage and signal guard");
}
