#!/usr/bin/env python3
"""Test actual netif diagnostic writer and getAll body with injected JNI failures.

JNI calls and native enumeration are narrow host stubs, not PS5 evidence.
"""
from pathlib import Path
import subprocess
root = Path(__file__).resolve().parents[1]
source = (root / '.tools/java25/openjdk/src/java.base/unix/native/libnet/NetworkInterface.c').read_text()
writer = source[source.index('static void ps5_netif_note'):source.index('#define NETIF_NOTE')]
start = source.index('JNIEXPORT jobjectArray JNICALL Java_java_net_NetworkInterface_getAll')
body = source[start:source.index('\n/*', start)]
work = root / 'build/java25/netif-trace-test'
work.mkdir(parents=True, exist_ok=True)
test = work / 'test.c'
test.write_text(r'''
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>
static char output[16384]; static size_t used;
static int fail_open, write_mode, interrupted, closes;
static int test_open(const char *p,int flags,...) {(void)flags;assert(!strcmp(p,"/download0/java25-vm-trace.log"));errno=EACCES;return fail_open?-1:42;}
static ssize_t test_write(int fd,const void *p,size_t n){assert(fd==42);if(write_mode==1&&!interrupted++){errno=EINTR;return -1;}if(write_mode==2){errno=EIO;return -1;}if(write_mode==3)return 0;if(n>7)n=7;assert(used+n<sizeof output);memcpy(output+used,p,n);used+=n;output[used]=0;errno=EAGAIN;return n;}
static int test_close(int fd){assert(fd==42);closes++;errno=EBADF;return 0;}
#define open test_open
#define write test_write
#define close test_close
''' + writer + r'''
#undef open
#undef write
#undef close
typedef void *jobject, *jclass, *jobjectArray; typedef int jint;
typedef struct FakeJNI FakeJNI; typedef const FakeJNI *JNIEnv;
struct FakeJNI {int (*ExceptionCheck)(JNIEnv*); jobjectArray (*NewObjectArray)(JNIEnv*,int,jclass,jobject);void (*SetObjectArrayElement)(JNIEnv*,jobjectArray,int,jobject);void (*DeleteLocalRef)(JNIEnv*,jobject);};
typedef struct netif {struct netif *next;} netif;
static netif second={0}, first={&second};
static int pending,mode,freed,created,stored,deleted;
static netif *enumInterfaces(JNIEnv *env){(void)env;if(mode==1){pending=1;return NULL;}return &first;}
static void freeif(netif *p){assert(p==&first);freed++;}
static jobject createNetworkInterface(JNIEnv *env,netif *p){(void)env;(void)p;created++;if(mode==3&&created==2){pending=1;return NULL;}return &second;}
static int check(JNIEnv *e){(void)e;return pending;}
static jobjectArray array(JNIEnv *e,int n,jclass c,jobject v){(void)e;(void)c;(void)v;assert(n==2);if(mode==2){pending=1;return NULL;}return &first;}
static void store(JNIEnv *e,jobjectArray a,int n,jobject v){(void)e;assert(a==&first&&n==stored&&v==&second);stored++;}
static void delete_ref(JNIEnv *e,jobject o){(void)e;assert(o==&second);deleted++;}
#define JNIEXPORT
#define JNICALL
#define NETIF_NOTE(phase,value) ps5_netif_note(phase,(long)(value),(*env)->ExceptionCheck(env))
''' + body + r'''
int main(void){
 errno=EDOM;write_mode=1;ps5_netif_note("allocation failed",123,1);assert(errno==EDOM&&closes==1);assert(strstr(output,"allocation failed value=123 pending=1"));
 for(int i=2;i<=3;i++){write_mode=i;errno=ERANGE;ps5_netif_note("write failure",0,0);assert(errno==ERANGE);}
 fail_open=1;errno=EDOM;ps5_netif_note("open failure",0,0);assert(errno==EDOM);fail_open=0;write_mode=0;
 char huge[300];memset(huge,'x',299);huge[299]=0;size_t before=used;ps5_netif_note(huge,0,0);assert(used==before);
 FakeJNI table={check,array,store,delete_ref};JNIEnv env=&table;
 for(mode=0;mode<4;mode++){
  pending=freed=created=stored=deleted=0;used=0;output[0]=0;
  jobjectArray result=Java_java_net_NetworkInterface_getAll(&env,NULL);
  assert(pending==(mode!=0));assert(freed==(mode!=1));assert(stored==deleted);
  if(mode==0){assert(result==&first&&created==2&&stored==2);assert(strstr(output,"getAll complete value=2 pending=0"));}
  else{assert(!result);if(mode==1)assert(strstr(output,"enumerated value=0 pending=1"));if(mode==2)assert(strstr(output,"array failed value=2 pending=1"));if(mode==3)assert(strstr(output,"create failed value=1 pending=1"));}
 }
 puts("PASS: actual bounded writer short writes/EINTR/errors/errno; actual getAll with JNI/enumeration stubs success/failure propagation, indices and native cleanup; ASan/UBSan");
}
''')
subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=address,undefined',str(test),'-o',str(work/'test')],check=True)
subprocess.run([str(work/'test')],check=True)
