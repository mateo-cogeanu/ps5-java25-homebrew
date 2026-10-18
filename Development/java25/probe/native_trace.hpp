/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#ifdef __PROSPERO__
#include "../../.tools/java25/openjdk/src/hotspot/share/runtime/ps5StartupTrace.hpp"
#include <atomic>
#include <pthread.h>
namespace ps5_native_trace {
inline std::atomic<bool> enabled{false};
inline std::atomic<pthread_t> owner{};

inline std::atomic<bool> verbose{true};
inline void enable() {owner=pthread_self();verbose.store(true);enabled.store(true);}
// Retain per-thread call context without writing every call to disk.
inline void quiet() {verbose.store(false);}
inline void disable() {enabled.store(false);}
inline bool begin(const char* operation,const void* caller,const void* from,void* to,size_t count) {
 if(!enabled.load())return false;
 const bool chatty=verbose.load();
 if(chatty&&!pthread_equal(owner,pthread_self()))return false;
 // One context lookup per entry/exit, instead of repeating pthread_self and
 // the static slot search for each guard, record and busy-flag access.
 auto* context=ps5_vm_thread_context();
 if(!context||context->busy||context->signal_active||context->io_active)return false;
 context->busy=true;
 context->record={operation,(unsigned long long)caller,(unsigned long long)from,(unsigned long long)to,(unsigned long long)count,false};
 if(chatty) {
  ps5_vm_trace_memory(operation,from,count,0,0);
  ps5_vm_trace_values(operation,(unsigned long long)caller," src=",(unsigned long long)from," dst=",(unsigned long long)to);
 }
 context->busy=false;return true;
}
inline void end(bool traced) {
 if(!traced)return;
 auto* context=ps5_vm_thread_context();
 if(!context)return;
 context->busy=true;context->record.completed=true;
 if(verbose.load())ps5_vm_trace("DONE: Traced native memory/string call");
 context->busy=false;
}
}
// Native runtime termination can bypass the JNI abort/vfprintf callbacks.
// Capture its direct caller and previous call context, then preserve semantics.
namespace ps5_native_trace {
inline void termination(const char* kind,const void* caller,int status) {
 if(ps5_vm_trace_io_active()) return; // Do not recurse if logging itself terminates.
 Ps5TraceIOScope io_scope;
 const Ps5NativeCallRecord previous=ps5_vm_native_call_record();
 ps5_vm_trace(ps5_vm_last_stage());
 ps5_vm_trace_values(kind,(uintptr_t)caller," self=",(uintptr_t)pthread_self()," status=",(unsigned int)status);
 ps5_vm_trace_values("NATIVE TERMINATION: anchor=",(uintptr_t)&termination," previous caller=",previous.caller," completed=",previous.completed ? 1 : 0);
 ps5_vm_trace_values(previous.operation ? previous.operation : "CALL: unavailable caller=",previous.caller," src=",previous.source," dst=",previous.destination);
 ps5_vm_trace_hex("NATIVE TERMINATION: previous bytes=",previous.bytes);
}
}
extern "C" {
__attribute__((noreturn)) void __real_abort();
__attribute__((noreturn)) void __real_exit(int);
__attribute__((noreturn)) void __real__exit(int);
void* __real_memcpy(void*,const void*,size_t);
void* __real_memmove(void*,const void*,size_t);
int __real_memcmp(const void*,const void*,size_t);
int __real_strcmp(const char*,const char*);
size_t __real_strlen(const char*);
void* __real_malloc(size_t);
void* __real_calloc(size_t,size_t);
void* __real_realloc(void*,size_t);
void __real_free(void*);
void* __real_memset(void*,int,size_t);
int __real_strncmp(const char*,const char*,size_t);
char* __real_strncpy(char*,const char*,size_t);
char* __real_strcpy(char*,const char*);
char* __real_strdup(const char*);
char* __real_strchr(const char*,int);
void* __real_memchr(const void*,int,size_t);
__attribute__((noinline,noreturn)) void __wrap_abort() {
 ps5_native_trace::termination("NATIVE TERMINATION: abort caller=",__builtin_return_address(0),0);
 __real_abort();
}
__attribute__((noinline,noreturn)) void __wrap_exit(int status) {
 ps5_native_trace::termination("NATIVE TERMINATION: exit caller=",__builtin_return_address(0),status);
 __real_exit(status);
}
__attribute__((noinline,noreturn)) void __wrap__exit(int status) {
 ps5_native_trace::termination("NATIVE TERMINATION: _exit caller=",__builtin_return_address(0),status);
 __real__exit(status);
}
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

__attribute__((noinline)) void* __wrap_calloc(size_t count,size_t size) {
 size_t bytes=(size && count>static_cast<size_t>(-1)/size)?static_cast<size_t>(-1):count*size;
 bool traced=ps5_native_trace::begin("CALL: calloc caller=",__builtin_return_address(0),nullptr,nullptr,bytes);
 void* result=__real_calloc(count,size);
 if(traced)ps5_vm_native_call_record().destination=(unsigned long long)result;
 ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) void* __wrap_realloc(void* previous,size_t count) {
 bool traced=ps5_native_trace::begin("CALL: realloc caller=",__builtin_return_address(0),previous,nullptr,count);
 void* result=__real_realloc(previous,count);
 if(traced)ps5_vm_native_call_record().destination=(unsigned long long)result;
 ps5_native_trace::end(traced);return result;
}
__attribute__((noinline)) void __wrap_free(void* memory) {
 bool traced=ps5_native_trace::begin("CALL: free caller=",__builtin_return_address(0),memory,nullptr,0);
 __real_free(memory);ps5_native_trace::end(traced);
}

__attribute__((noinline)) char* __wrap_strdup(const char* text) {
 bool traced=ps5_native_trace::begin("CALL: strdup caller=",__builtin_return_address(0),text,nullptr,0);
 char* result=__real_strdup(text);
 if(traced) ps5_vm_native_call_record().destination=(unsigned long long)result;
 ps5_native_trace::end(traced);return result;
}

}
#else
namespace ps5_native_trace {inline void enable(){} inline void quiet(){} inline void disable(){}}
#endif
