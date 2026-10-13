/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#ifdef __PROSPERO__
#include "../../.tools/java25/openjdk/src/hotspot/share/runtime/ps5StartupTrace.hpp"
#include <atomic>
#include <pthread.h>
namespace ps5_native_trace {
inline std::atomic<bool> enabled{false};
inline pthread_t owner{};
inline bool busy=false;
inline void enable() {owner=pthread_self();enabled.store(true);}
inline void disable() {enabled.store(false);}
inline bool begin(const char* operation,const void* caller,const void* from,void* to,size_t count) {
 if(!enabled.load()||!pthread_equal(owner,pthread_self())||busy||ps5_vm_signal_trace_active()||ps5_vm_trace_io_active()) return false;
 busy=true;
 ps5_vm_native_call_record() = {operation,(unsigned long long)caller,(unsigned long long)from,(unsigned long long)to,(unsigned long long)count,false};
 ps5_vm_trace_memory(operation,from,count,0,0);
 ps5_vm_trace_values(operation,(unsigned long long)caller," src=",(unsigned long long)from," dst=",(unsigned long long)to);
 busy=false;return true;
}
inline void end(bool traced) {
 if(traced) {busy=true;ps5_vm_native_call_record().completed=true;ps5_vm_trace("DONE: Traced native memory/string call");busy=false;}
}
}
extern "C" {
void* __real_memcpy(void*,const void*,size_t);
void* __real_memmove(void*,const void*,size_t);
int __real_memcmp(const void*,const void*,size_t);
int __real_strcmp(const char*,const char*);
size_t __real_strlen(const char*);
void* __real_malloc(size_t);
void* __real_memset(void*,int,size_t);
int __real_strncmp(const char*,const char*,size_t);
char* __real_strncpy(char*,const char*,size_t);
char* __real_strcpy(char*,const char*);
char* __real_strdup(const char*);
char* __real_strchr(const char*,int);
void* __real_memchr(const void*,int,size_t);
__attribute__((noinline)) void* __wrap_memcpy(void* to,const void* from,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: memcpy caller=",__builtin_return_address(0),from,to,count);
 void* result=__real_memcpy(to,from,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) void* __wrap_memmove(void* to,const void* from,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: memmove caller=",__builtin_return_address(0),from,to,count);
 void* result=__real_memmove(to,from,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) int __wrap_memcmp(const void* a,const void* b,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: memcmp caller=",__builtin_return_address(0),a,const_cast<void*>(b),count);
 int result=__real_memcmp(a,b,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) int __wrap_strcmp(const char* a,const char* b) {
 bool traced=ps5_native_trace::begin("CALL: strcmp caller=",__builtin_return_address(0),a,const_cast<char*>(b),0);
 int result=__real_strcmp(a,b);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) size_t __wrap_strlen(const char* text) {
 bool traced=ps5_native_trace::begin("CALL: strlen caller=",__builtin_return_address(0),text,nullptr,0);
 size_t result=__real_strlen(text);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) void* __wrap_memset(void* to,int value,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: memset caller=",__builtin_return_address(0),nullptr,to,count);
 void* result=__real_memset(to,value,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) int __wrap_strncmp(const char* a,const char* b,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: strncmp caller=",__builtin_return_address(0),a,const_cast<char*>(b),count);
 int result=__real_strncmp(a,b,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) char* __wrap_strncpy(char* to,const char* from,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: strncpy caller=",__builtin_return_address(0),from,to,count);
 char* result=__real_strncpy(to,from,count);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) char* __wrap_strchr(const char* text,int value) {
 bool traced=ps5_native_trace::begin("CALL: strchr caller=",__builtin_return_address(0),text,nullptr,0);
 char* result=__real_strchr(text,value);ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) void* __wrap_memchr(const void* text,int value,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: memchr caller=",__builtin_return_address(0),text,nullptr,count);
 void* result=__real_memchr(text,value,count);ps5_native_trace::end(traced);return result;
}

__attribute__((noinline)) char* __wrap_strcpy(char* to,const char* from) {
 bool traced=ps5_native_trace::begin("CALL: strcpy caller=",__builtin_return_address(0),from,to,0);
 char* result=__real_strcpy(to,from);ps5_native_trace::end(traced);return result;
}

__attribute__((noinline)) void* __wrap_malloc(size_t count) {
 bool traced=ps5_native_trace::begin("CALL: malloc caller=",__builtin_return_address(0),nullptr,nullptr,count);
 void* result=__real_malloc(count);
 if(traced) ps5_vm_native_call_record().destination=(unsigned long long)result;
 ps5_native_trace::end(traced);return result;
}

__attribute__((noinline)) char* __wrap_strdup(const char* text) {
 bool traced=ps5_native_trace::begin("CALL: strdup caller=",__builtin_return_address(0),text,nullptr,0);
 char* result=__real_strdup(text);
 if(traced) ps5_vm_native_call_record().destination=(unsigned long long)result;
 ps5_native_trace::end(traced);return result;
}

}
#else
namespace ps5_native_trace {inline void enable(){} inline void disable(){}}
#endif
