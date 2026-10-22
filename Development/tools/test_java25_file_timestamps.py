#!/usr/bin/env python3
"""Exercise actual timestamp JNI bodies against real files and injected errors."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1]
w=r/'build/java25/timestamp-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
s=(r/'.tools/java25/openjdk/src/java.base/unix/native/libnio/fs/UnixNativeDispatcher.c').read_text()
a=s.index('#ifdef __PROSPERO__\n// The title SDK exposes timeval APIs');b=s.index('\nJNIEXPORT jlong JNICALL',a)
c=r'''
#define __PROSPERO__ 1
#include <jni.h>
#include <stdint.h>
#include <errno.h>
#include <fcntl.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <unistd.h>
#include <stdlib.h>
#include <stdio.h>
#include <assert.h>
static int calls, inject, error;
static struct timeval observed[2];
static void throwUnixException(JNIEnv* env,int e){(void)env;error=e;}
static int selected_futimes(int fd,const struct timeval* tv){calls++;observed[0]=tv[0];observed[1]=tv[1];if(inject){errno=inject;inject=0;return -1;}return futimes(fd,tv);}
static int selected_utimes(const char* path,const struct timeval* tv){calls++;observed[0]=tv[0];observed[1]=tv[1];if(inject){errno=inject;inject=0;return -1;}return utimes(path,tv);}
#define futimes selected_futimes
#define utimes selected_utimes
#define PS5_REALPATH_NOTE(a,b) ((void)0)
#define jlong_to_ptr(n) ((void*)(intptr_t)(n))
#define RESTARTABLE(cmd,result) do{result=(cmd);}while(result==-1&&errno==EINTR)
'''+s[a:b]+r'''
int main(void){
 struct timeval tv;
 const jlong values[]={0,1,999,1000,1000000001,-1,-999,-1000,-1000000001,INT64_MIN,INT64_MAX};
 for(unsigned i=0;i<sizeof(values)/sizeof(values[0]);i++){
  ps5_timeval(values[i],&tv);
  assert(tv.tv_usec>=0&&tv.tv_usec<1000000);
  __int128 result=(__int128)tv.tv_sec*1000000000+tv.tv_usec*1000;
  assert(result<=values[i]&&(__int128)values[i]-result<1000);
 }
 char path[]="/tmp/ps5-times-XXXXXX";int fd=mkstemp(path);assert(fd>=0);
 jlong access=1700000000123456789LL,mod=1700000000987654321LL;
 inject=EINTR;int before=calls;
 Java_sun_nio_fs_UnixNativeDispatcher_futimens0(NULL,NULL,fd,access,mod);
 assert(!error&&calls==before+2);struct stat st;assert(!fstat(fd,&st));
 assert(st.st_atimespec.tv_sec==1700000000&&st.st_atimespec.tv_nsec==123456000);
 assert(st.st_mtimespec.tv_nsec==987654000);
 assert(!unlink(path)); // Descriptor operation must still reach the open inode.
 Java_sun_nio_fs_UnixNativeDispatcher_futimens0(NULL,NULL,fd,mod,access);
 assert(!error&&!fstat(fd,&st)&&st.st_mtimespec.tv_nsec==123456000);close(fd);
 Java_sun_nio_fs_UnixNativeDispatcher_futimens0(NULL,NULL,-1,access,mod);assert(error==EBADF);error=0;
 inject=EACCES;Java_sun_nio_fs_UnixNativeDispatcher_futimens0(NULL,NULL,-1,access,mod);assert(error==EACCES);error=0;
 char second[]="/tmp/ps5-times-XXXXXX";fd=mkstemp(second);assert(fd>=0);close(fd);
 inject=EINTR;before=calls;
 Java_sun_nio_fs_UnixNativeDispatcher_utimensat0(NULL,NULL,AT_FDCWD,(jlong)(intptr_t)second,access,mod,0);
 assert(!error&&calls==before+2&&!stat(second,&st)&&st.st_mtimespec.tv_nsec==987654000);
 before=calls;
 Java_sun_nio_fs_UnixNativeDispatcher_utimensat0(NULL,NULL,AT_FDCWD,0,access,mod,AT_SYMLINK_NOFOLLOW);
 assert(error==ENOTSUP&&calls==before);error=0;
 Java_sun_nio_fs_UnixNativeDispatcher_utimensat0(NULL,NULL,123,0,access,mod,0);
 assert(error==ENOTSUP&&calls==before);error=0;
 assert(!unlink(second));
 Java_sun_nio_fs_UnixNativeDispatcher_utimensat0(NULL,NULL,AT_FDCWD,(jlong)(intptr_t)second,access,mod,0);
 assert(error==ENOENT);
 puts("PASS actual timestamp JNI: real fd/path writes, unlinked inode identity, microsecond precision, negative/extreme conversion, EINTR retries, EBADF/EACCES/ENOENT, unsupported flags/dirfd before path access; ASan/UBSan. Console APIs pending.");
}
'''
(w/'test.c').write_text(c)
subprocess.run(['clang','-O1','-g','-fsanitize=address,undefined','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(w/'test.c'),'-o',str(w/'test')],check=True)
subprocess.run([str(w/'test')],check=True)
