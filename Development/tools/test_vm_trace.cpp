/* SPDX-License-Identifier: GPL-2.0-only
 * Test the actual diagnostic helper with interrupted/partial host writes.
 * This tests trace reliability, not PS5 JVM startup.
 */
#include <fcntl.h>
#include <unistd.h>
#include <string.h>
#include <errno.h>
#include <cassert>
#include <cstdio>
#include <fstream>
#include <string>
static bool interrupt_once=true;
static bool deny_open=false;
static unsigned open_calls=0;
static int trace_open(const char *,int flags,int mode) {
 ++open_calls;
 if(deny_open) {errno=EACCES;return -1;}
 return ::open("build/java25/trace-helper-test.log",flags,mode);
}
static ssize_t trace_write(int fd,const void *bytes,size_t length) {
 if(interrupt_once) {interrupt_once=false;errno=EINTR;return -1;}
 return ::write(fd,bytes,length>3?3:length);
}
#define __PROSPERO__ 1
#define open trace_open
#define write trace_write
#include "runtime/ps5StartupTrace.hpp"
#undef open
#undef write

int main() {
 ::unlink("build/java25/trace-helper-test.log");
 errno=EBUSY;
 ps5_vm_trace("ENTER: output stream initialization");
 assert(errno==EBUSY);
 ps5_vm_trace("DONE: output stream initialization");
 assert(errno==EBUSY);
 deny_open=true;
 ps5_vm_trace("This line must not be written");
 assert(errno==EBUSY);
 std::ifstream file("build/java25/trace-helper-test.log");
 std::string content((std::istreambuf_iterator<char>(file)),{});
 assert(content=="ENTER: output stream initialization\nDONE: output stream initialization\n");
 deny_open=false;
 ps5_vm_trace_memory("TEST MEMORY",nullptr,16384,3,0);
 assert(errno==EBUSY);
 std::ifstream updated("build/java25/trace-helper-test.log");
 std::string with_memory((std::istreambuf_iterator<char>(updated)),{});
 assert(with_memory.find("bytes=16384 mode=3 errno=0")!=std::string::npos);
 ps5_vm_trace_hex("SIGNAL: pc=",0x1234abcdefULL);
 assert(errno==EBUSY);
 std::ifstream hex_file("build/java25/trace-helper-test.log");
 std::string with_hex((std::istreambuf_iterator<char>(hex_file)),{});
 assert(with_hex.find("SIGNAL: pc=0x0000001234abcdef\n")!=std::string::npos);
 assert(std::string(ps5_vm_last_stage()).find("TEST MEMORY") == 0);
 ps5_vm_trace(ps5_vm_last_stage());
 assert(errno==EBUSY);
 ps5_vm_trace_values("SIGNAL: RDI=",1," RSI=",2," RDX=",3);
 assert(errno==EBUSY);
 std::ifstream context_file("build/java25/trace-helper-test.log");
 std::string context((std::istreambuf_iterator<char>(context_file)),{});
 assert(context.find("SIGNAL: RDI=0x0000000000000001 RSI=0x0000000000000002 RDX=0x0000000000000003\n")!=std::string::npos);
 assert(std::string(ps5_vm_last_stage()).find("TEST MEMORY") == 0);
 std::string long_label(200,'x');
 ps5_vm_trace_values(long_label.c_str(),1,long_label.c_str(),2,long_label.c_str(),3);
 assert(errno==EBUSY);
 ps5_vm_set_metadata_interval(64);
 unsigned before_sample=open_calls;
 for(int i=0;i<400;++i){ps5_vm_trace("ENTER: Metadata arena allocation");assert(errno==EBUSY);}
 assert(open_calls-before_sample==6);
 assert(std::string(ps5_vm_last_stage())=="ENTER: Metadata arena allocation");
 ps5_vm_signal_trace_active()=true;ps5_vm_trace(ps5_vm_last_stage());ps5_vm_signal_trace_active()=false;
 assert(open_calls-before_sample==7);
 ps5_vm_trace("FAIL: Metadata arena allocation");
 ps5_vm_trace("THREAD: lifecycle retained");
 assert(open_calls-before_sample==9);
 ps5_vm_set_metadata_interval(0);ps5_vm_trace("DONE: Metadata zeroing");assert(open_calls-before_sample==10);
 ps5_vm_set_metadata_interval(64);unsigned before_phases=open_calls;
 for(int i=0;i<400;i++){ps5_vm_trace("DONE: Metachunk commit boundary");assert(errno==EBUSY);}
 assert(open_calls-before_phases==6);
 assert(std::string(ps5_vm_last_stage())=="DONE: Metachunk commit boundary");
 ps5_vm_signal_trace_active()=true;ps5_vm_trace(ps5_vm_last_stage());ps5_vm_signal_trace_active()=false;
 assert(open_calls-before_phases==7);
 ps5_vm_trace("FAIL: Metachunk commit boundary");assert(open_calls-before_phases==8);
 ps5_vm_set_metadata_interval(0);
 unsigned char raw[274]={};for(unsigned i=0;i<sizeof(raw);++i)raw[i]=(unsigned char)i;
 unsigned before_raw=open_calls;
 ps5_vm_trace_raw_context(raw+1,15);assert(open_calls==before_raw);
 ps5_vm_trace_raw_context(raw+1,16);assert(open_calls==before_raw+1);
 ps5_vm_trace_raw_context(raw+1,273);assert(open_calls==before_raw+17);
 ps5_vm_trace_raw_context(nullptr,256);assert(open_calls==before_raw+17);
 assert(errno==EBUSY);
 std::ifstream raw_file("build/java25/trace-helper-test.log");
 std::string raw_content((std::istreambuf_iterator<char>(raw_file)),{});
 assert(raw_content.find("word0=0x0807060504030201 word1=0x100f0e0d0c0b0a09")!=std::string::npos);
 std::puts("Startup trace helper PASS: EINTR, partial writes, append, denied open, memory fields, fault hex formatting, errno preservation, bounded successful-phase sampling with current last-stage context, unsampled failure/thread lines");
}
