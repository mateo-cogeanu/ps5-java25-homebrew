#!/usr/bin/env python3
"""Actual JNI lstat with refused path metadata and genuine nofollow descriptor IO."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/lstat-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text();a=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_lstat0');b=s.index('JNIEXPORT void JNICALL\nJava_sun_nio_fs_UnixNativeDispatcher_fstat0',a);actual=s[a:b].replace('jclass this','jclass klass')
prefix=r'''
#include <cassert>
#include <cerrno>
#include <cstdint>
#include <cstdio>
#include <string>
#include <filesystem>
#include <fcntl.h>
#include <sys/stat.h>
#include <unistd.h>
#define __PROSPERO__ 1
#define JNIEXPORT
#define JNICALL
using jint=int;using jlong=long long;using jclass=void*;using jobject=void*;struct JNIEnv{};
void*jlong_to_ptr(jlong n){return reinterpret_cast<void*>(n);}
int path_error=EPERM,descriptor_error=0,open_error=0,opens=0,closes=0,thrown=0;struct stat observed{};
void copy_stat_attributes(JNIEnv*,struct stat*b,jobject){observed=*b;}
void throwUnixException(JNIEnv*,int e){thrown=e;}
int refused_lstat(const char*p,struct stat*b){if(path_error){errno=path_error;return -1;}return ::lstat(p,b);}
int real_open(const char*p,int flags){assert(flags==(O_RDONLY|O_NONBLOCK|O_NOFOLLOW));++opens;if(open_error){errno=open_error;return -1;}return ::open(p,flags);}
int real_fstat(int fd,struct stat*b){if(descriptor_error){errno=descriptor_error;return -1;}return ::fstat(fd,b);}
int real_close(int fd){++closes;int rc=::close(fd);errno=EBADF;return rc;}
#define lstat(p,b) refused_lstat(p,b)
#define open(p,f) real_open(p,f)
#define fstat(d,b) real_fstat(d,b)
#define close(d) real_close(d)
#define RESTARTABLE(op,result) do{result=(op);}while(result==-1&&errno==EINTR)
'''
checks=r'''
#undef lstat
#undef open
#undef fstat
#undef close
int main(){
 char tmp[]="/tmp/ps5-lstat-test-XXXXXX";assert(mkdtemp(tmp));std::string root=tmp,file=root+"/file",dir=root+"/dir",link=root+"/link",broken=root+"/broken",parent=root+"/parent",fifo=root+"/fifo";
 assert(::mkdir(dir.c_str(),0700)==0);int fd=::open(file.c_str(),O_CREAT|O_WRONLY,0600);assert(fd>=0&&write(fd,"hello",5)==5&&::close(fd)==0);
 assert(symlink(file.c_str(),link.c_str())==0&&symlink("missing",broken.c_str())==0&&symlink(dir.c_str(),parent.c_str())==0&&mkfifo(fifo.c_str(),0600)==0);
 auto probe=[&](std::string path){thrown=0;observed={};Java_sun_nio_fs_UnixNativeDispatcher_lstat0(nullptr,nullptr,(jlong)(intptr_t)path.c_str(),nullptr);return thrown;};
 assert(probe(file)==0&&S_ISREG(observed.st_mode)&&observed.st_size==5&&closes==1);
 assert(probe(dir)==0&&S_ISDIR(observed.st_mode));
 assert(probe(root+"/missing")==ENOENT); // Real absence reaches DirectoryValidator's normal create path.
 assert(probe(link)==ELOOP&&probe(broken)==ELOOP); // Never return target attributes as link attributes.
 assert(probe(parent)==ELOOP);assert(probe(parent+"/.")==0&&S_ISDIR(observed.st_mode)); // lstat follows intermediate components only.
 assert(probe(fifo)==0&&S_ISFIFO(observed.st_mode)); // O_NONBLOCK prevents a diagnostic read-open from waiting.
 descriptor_error=EIO;int before=closes;assert(probe(file)==EIO&&closes==before+1);descriptor_error=0;
 open_error=EACCES;before=closes;assert(probe(file)==EACCES&&closes==before);open_error=0;
 path_error=EACCES;before=opens;assert(probe(file)==EACCES&&opens==before); // Only EPERM triggers fallback.
 path_error=0;before=opens;assert(probe(link)==0&&S_ISLNK(observed.st_mode)&&opens==before); // Working lstat still describes real links normally.
 std::filesystem::remove_all(root);
 puts("PASS: actual JNI lstat; real files/directories/FIFO, missing ENOENT, leaf and dangling symlink rejection, intermediate links, native lstat link metadata, EPERM-only fallback and descriptor cleanup/error preservation");
}
'''
p=w/'test.cpp';p.write_text(prefix+actual+checks);subprocess.run(['/usr/bin/clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined',str(p),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
