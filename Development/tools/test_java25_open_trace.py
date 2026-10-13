#!/usr/bin/env python3
"""Test the probe's actual open wrapper with mocked platform calls."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
source=(root/'java25/probe/fileio.cpp').read_text()
wrapper=source[source.index('static char native_open_error'):source.index('namespace {\nusing ps5')]
prefix=r'''
#define __PROSPERO__ 1
#include <atomic>
#include <cassert>
#include <cstdarg>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <pthread.h>
static bool io=false;
static int traces=0, platform_flags=0, platform_mode=0, platform_result=-1;
namespace ps5_native_trace {
 std::atomic<bool> enabled{true};pthread_t owner=pthread_self();
}
bool &ps5_vm_trace_io_active(){return io;}
struct Ps5TraceIOScope {
 bool saved=io;Ps5TraceIOScope(){io=true;}~Ps5TraceIOScope(){io=saved;}
};
void ps5_vm_trace(const char *){++traces;errno=EIO;}
extern "C" int __real_open(const char *,int flags,...) {
 platform_flags=flags;platform_mode=0;
 if(flags&O_CREAT){va_list args;va_start(args,flags);platform_mode=va_arg(args,int);va_end(args);}
 errno=EPERM;return platform_result;
}
'''
checks=r'''
int main(){
 assert(__wrap_open("/download0/probe",O_CREAT|O_EXCL|O_WRONLY,0600)==-1);
 assert(platform_flags==(O_CREAT|O_EXCL|O_WRONLY)&&platform_mode==0600);
 assert(errno==EPERM&&traces==1&&!io);
 assert(std::strstr(native_open_error,"mode=0600"));
 assert(std::strstr(native_open_error,"errno=1"));
 io=true;
 __wrap_open("/download0/trace",O_CREAT|O_WRONLY,0600);
 assert(traces==1);io=false;
 __wrap_open("/app0/asset",O_RDONLY);
 assert(traces==1&&platform_mode==0);
 platform_result=7;
 assert(__wrap_open("/download0/probe",O_WRONLY)==7&&traces==1);
 ps5_native_trace::enabled=false;platform_result=-1;
 __wrap_open("/download0/probe",O_WRONLY);
 assert(traces==1);
 std::puts("PASS: original open flags/mode/result, errno preservation, trace recursion guard and scope");
}
'''
work=root/'build/java25'
path=work/'test-open-trace.cpp';path.write_text(prefix+wrapper+checks)
exe=work/'test-open-trace'
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-fsanitize=address',str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
