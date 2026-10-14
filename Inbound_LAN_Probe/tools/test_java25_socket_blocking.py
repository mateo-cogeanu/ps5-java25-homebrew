#!/usr/bin/env python3
"""Exercise actual target blocking-mode function with controlled syscall results."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
s=(ROOT/'.tools/java25/openjdk/src/java.base/unix/native/libnio/ch/IOUtil.c').read_text()
start=s.index('static int\nconfigureBlocking(');end=s.index('\nJNIEXPORT',start)
actual=s[start:end]
prefix=r'''
#define __PROSPERO__ 1
#include <cassert>
#include <cerrno>
#include <cstdarg>
#include <cstdio>
#include <fcntl.h>
#include <sys/socket.h>
using jboolean=bool;
static int flags=0,get_error=0,set_error=0,option_error=0,option_calls=0,option_state=-1;
static bool socket_descriptor=true;
int fake_fcntl(int,int command,...) {
 if(command==F_GETFL){errno=get_error;return get_error?-1:flags;}
 assert(command==F_SETFL);va_list args;va_start(args,command);int value=va_arg(args,int);va_end(args);
 errno=set_error;if(set_error)return -1;flags=value;return 0;
}
int fake_getsockopt(int,int level,int option,void *value,socklen_t *length) {
 assert(level==SOL_SOCKET&&option==SO_TYPE&&*length==sizeof(int));
 if(!socket_descriptor){errno=ENOTSOCK;return -1;}
 *static_cast<int*>(value)=SOCK_STREAM;return 0;
}
int fake_setsockopt(int,int level,int option,const void *value,socklen_t length) {
 assert(level==SOL_SOCKET&&option==0x1200&&length==sizeof(int));++option_calls;
 if(option_error){errno=option_error;return -1;}
 option_state=*static_cast<const int*>(value);return 0;
}
#define fcntl fake_fcntl
#define getsockopt fake_getsockopt
#define setsockopt fake_setsockopt
'''
checks=r'''
int main(){
 assert(configureBlocking(45,false)==0&&(flags&O_NONBLOCK)&&option_calls==0);
 assert(configureBlocking(45,true)==0&&!(flags&O_NONBLOCK)&&option_calls==0);
 get_error=EPERM;
 assert(configureBlocking(45,false)==0&&option_calls==1&&option_state==1);
 assert(configureBlocking(45,true)==0&&option_calls==2&&option_state==0);
 get_error=0;set_error=EINVAL;
 assert(configureBlocking(45,false)==0&&option_calls==3&&option_state==1);
 get_error=EACCES;socket_descriptor=false;
 assert(configureBlocking(45,false)==-1&&errno==EACCES&&option_calls==3);
 get_error=EIO;socket_descriptor=true;
 assert(configureBlocking(45,false)==-1&&errno==EIO&&option_calls==3);
 get_error=EPERM;option_error=ENOPROTOOPT;
 assert(configureBlocking(45,false)==-1&&errno==ENOPROTOOPT&&option_calls==4);
 std::puts("PASS: real blocking/nonblocking operations, fcntl fallback, socket identity and native failures");
}
'''
path=ROOT/'build/java25/test-socket-blocking.cpp';path.write_text(prefix+actual+checks)
exe=ROOT/'build/java25/test-socket-blocking'
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-fsanitize=address',str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
