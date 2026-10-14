/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "../java25/probe/vm_diagnostics.hpp"
#include <cassert>
#include <string>
static void print(const char *format,...) {
 va_list arguments;va_start(arguments,format);ps5_vm_diagnostics::capture(format,arguments);va_end(arguments);
}
int main(){
 using namespace ps5_vm_diagnostics;
 print("VM init: %s %d\n","failure",7);assert(std::string(output)=="VM init: failure 7\n");
 reset();std::string large(capacity*2,'x');append(large.data(),large.size());
 print("\nROOT CAUSE: unavailable native method\n");assert(used==capacity-1);assert(std::string(output).ends_with("ROOT CAUSE: unavailable native method\n"));
 reset();assert(used==0&&output[0]=='\0');std::puts("PASS: pre-JNI formatted diagnostics, bounded tail retention and reset");
}
