#!/usr/bin/env python3
"""Compile the actual allocation-free report writer with partial/error IO injection."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/report-writer-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'java25/probe/log_share.hpp').read_text();a=s.index('inline bool write_note(');b=s.index('inline bool archive_report',a);actual=s[a:b].replace('::open','mock_open').replace('::write','mock_write').replace('::close','mock_close')
p=w/'test.cpp';p.write_text(r'''
#include <cassert>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <unistd.h>
static char output[100];static size_t used;static int calls,closed,open_error,write_error,close_error;static bool interrupted,zero;
int mock_open(const char*,int f,int m){assert(f==(O_CREAT|O_WRONLY|O_TRUNC)&&m==0600);if(open_error){errno=open_error;return -1;}return 91;}
ssize_t mock_write(int fd,const char*p,size_t n){assert(fd==91);++calls;if(interrupted){interrupted=false;errno=EINTR;return -1;}if(write_error){errno=write_error;return -1;}if(zero)return 0;if(n>3)n=3;memcpy(output+used,p,n);used+=n;return n;}
int mock_close(int fd){assert(fd==91);++closed;errno=close_error?close_error:EBADF;return close_error?-1:0;}
'''+actual+r'''
int main(){
 errno=EDOM;interrupted=true;assert(write_note("x","abcdefg")&&used==7&&!memcmp(output,"abcdefg",7)&&calls==4&&closed==1&&errno==EDOM);
 write_error=ENOSPC;assert(!write_note("x","x")&&errno==ENOSPC&&closed==2);write_error=0;
 zero=true;assert(!write_note("x","x")&&errno==EIO&&closed==3);zero=false;
 close_error=EIO;assert(!write_note("x","")&&errno==EIO&&closed==4);close_error=0;
 open_error=EACCES;assert(!write_note("x","x")&&errno==EACCES&&closed==4);
 puts("PASS: actual descriptor report writer; partial writes/EINTR, no FILE allocation, zero-write/ENOSPC/open/close errors, cleanup and errno preservation");
}
''');subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined',str(p),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
