#!/usr/bin/env python3
"""Exercise the actual patched JNI stat function with mocked platform outcomes."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
source=(root/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text()
start=source.index('JNIEXPORT jint JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_stat0')
end=source.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_lstat0',start)
actual=source[start:end].replace("jclass this", "jclass klass") # C parameter name is a C++ keyword
prefix=r'''
#define __PROSPERO__ 1
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <fcntl.h>
#include <sys/stat.h>
#define JNIEXPORT
#define JNICALL
using jint=int;using jlong=long long;using jclass=void*;using jobject=void*;struct JNIEnv {};
void *jlong_to_ptr(jlong x){return reinterpret_cast<void*>(x);}
static int stat_error=0, open_error=0, fstat_error=0, opens=0, closes=0;
static long long observed_size=0;
void copy_stat_attributes(JNIEnv*,struct stat *buf,jobject){observed_size=buf->st_size;}
int mock_stat(const char*,struct stat *buf){errno=stat_error;if(stat_error)return -1;buf->st_size=11;return 0;}
int mock_open(const char*,int flags){++opens;assert(flags==(O_RDONLY|O_NONBLOCK));errno=open_error;return open_error?-1:91;}
int mock_fstat(int fd,struct stat *buf){assert(fd==91);errno=fstat_error;if(fstat_error)return -1;buf->st_size=43;return 0;}
int mock_close(int fd){assert(fd==91);++closes;errno=EBADF;return 0;}
#define stat(path,buf) mock_stat(path,buf)
#define open(path,flags) mock_open(path,flags)
#define fstat(fd,buf) mock_fstat(fd,buf)
#define close(fd) mock_close(fd)
#define RESTARTABLE(op,result) do {result=(op);} while(result==-1 && errno==EINTR)
'''
checks=r'''
int main(){
 auto probe=[](){return Java_sun_nio_fs_UnixNativeDispatcher_stat0(nullptr,nullptr,(jlong)(intptr_t)"/download0/probe",nullptr);};
 assert(probe()==0&&observed_size==11&&opens==0);
 stat_error=EPERM;
 assert(probe()==0&&observed_size==43&&opens==1&&closes==1);
 fstat_error=EIO;
 assert(probe()==EIO&&closes==2); // close must not replace metadata errno
 open_error=EACCES;
 assert(probe()==EPERM&&closes==2);
 stat_error=EACCES;int previous=opens;
 assert(probe()==EACCES&&opens==previous); // no fallback for unrelated failures
 std::puts("PASS: actual JNI stat, descriptor metadata, denied opens, close/error preservation");
}
'''
path=root/'build/java25/test-stat-fallback.cpp';path.write_text(prefix+actual+checks)
exe=root/'build/java25/test-stat-fallback'
subprocess.run(['/usr/bin/clang++','-std=c++20','-O1','-fsanitize=address',str(path),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
