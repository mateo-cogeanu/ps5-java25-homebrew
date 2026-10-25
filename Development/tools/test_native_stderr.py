#!/usr/bin/env python3
"""Verify actual native stderr capture with real descriptors and native stdio."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=r'''
#include "native_stderr.hpp"
#include <cassert>
#include <cstring>
#include <cstdlib>
int main(int argc,char**argv){assert(argc==3);errno=EDOM;int result=ps5::native_stderr::begin(argv[1]);
 if(std::strcmp(argv[2],"failure")==0){assert(result==ENOENT);assert(write(2,"original stderr\n",16)==16);return 0;}
 assert(result==0&&errno==EDOM);std::fprintf(stderr,"native stdio error\n");assert(write(2,"raw descriptor error\n",21)==21);std::puts("stdout unchanged");std::fflush(stdout);_exit(0);}
'''
with tempfile.TemporaryDirectory(prefix='native-stderr-test-')as folder:
 w=Path(folder);(w/'test.cpp').write_text(source);binary=w/'test';subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(w/'test.cpp'),'-o',str(binary)],check=True)
 report=w/'native.log'
 for mode in ['success','success']:
  r=subprocess.run([str(binary),str(report),mode],capture_output=True,text=True);assert r.returncode==0 and r.stdout=='stdout unchanged\n' and r.stderr=='raw descriptor error\n',(r.returncode,r.stdout,r.stderr)
 assert report.read_text()==('native stdio error\n'*2)
 r=subprocess.run([str(binary),str(w/'missing/native.log'),'failure'],capture_output=True,text=True);assert r.returncode==0 and r.stderr=='original stderr\n' and not r.stdout
 failure_source=r'''
#include <cstdio>
#include <cerrno>
#include <cassert>
#include <fcntl.h>
#include <unistd.h>
static int failed_fd;
static FILE* failed_fdopen(int fd,const char*){failed_fd=fd;errno=ENOMEM;return nullptr;}
#define fdopen failed_fdopen
#include "native_stderr.hpp"
#undef fdopen
int main(int argc,char**argv){assert(argc==2);FILE*old=stderr;assert(ps5::native_stderr::begin(argv[1])==ENOMEM);assert(stderr==old);assert(fcntl(failed_fd,F_GETFD)==-1&&errno==EBADF);std::fprintf(stderr,"old stream retained\n");}
'''
 (w/'failure.cpp').write_text(failure_source);failure_binary=w/'failure'
 subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(w/'failure.cpp'),'-o',str(failure_binary)],check=True)
 failed=subprocess.run([str(failure_binary),str(w/'failed-open-stream.log')],capture_output=True,text=True);assert failed.returncode==0 and failed.stderr=='old stream retained\n'
 print('PASS actual native stderr stream capture:stdio survives _exit/append,raw fd2/stdout unchanged,errno preserved,failed-open/fdopen retains old stream and closes unpublished fd;host ASan/UBSan,PS5 pending')
