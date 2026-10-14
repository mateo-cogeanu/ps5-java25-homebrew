/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstdarg>
#include <cstdio>
#include <cstring>
#include <cstddef>
namespace ps5_vm_diagnostics {
// Bounded native storage, usable before JNI_CreateJavaVM returns.
inline constexpr std::size_t capacity=4096;
inline char output[capacity]{};
inline std::size_t used=0;
inline void reset() noexcept {used=0;output[0]='\0';}
inline void append(const char *text,std::size_t size) noexcept {
 if(size>=capacity){text+=size-(capacity-1);size=capacity-1;used=0;}
 if(used+size>=capacity){std::size_t discard=used+size-(capacity-1);std::memmove(output,output+discard,used-discard);used-=discard;}
 std::memcpy(output+used,text,size);used+=size;output[used]='\0';
}
inline void capture(const char *format,va_list arguments) noexcept {
 char chunk[capacity];va_list copy;va_copy(copy,arguments);
 int count=std::vsnprintf(chunk,sizeof(chunk),format,copy);va_end(copy);
 if(count>0)append(chunk,static_cast<std::size_t>(count)<sizeof(chunk)?static_cast<std::size_t>(count):sizeof(chunk)-1);
}
}
