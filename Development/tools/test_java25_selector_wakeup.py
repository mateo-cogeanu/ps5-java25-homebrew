#!/usr/bin/env python3
"""Run the actual patched selector and native user-event bodies on macOS kqueue."""
from pathlib import Path
import subprocess, os
r=Path(__file__).resolve().parents[1]; src=r/'.tools/java25/openjdk/src/java.base/macosx'
w=r/'build/java25/selector-wakeup-test';w.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
classes=w/'classes';classes.mkdir(exist_ok=True)
subprocess.run([str(jdk/'bin/javac'),'--patch-module','java.base='+str(src/'classes'),'-d',str(classes),*[str(src/'classes/sun/nio/ch'/f) for f in ['KQueue.java','KQueueSelectorImpl.java']]],check=True)
s=(src/'native/libnio/ch/KQueue.c').read_text();s=s[s.index('JNIEXPORT jint JNICALL\nJava_sun_nio_ch_KQueue_registerUserWakeup'):]
c=w/'bridge.c';c.write_text(r'''
#include <jni.h>
#include <sys/types.h>
#include <sys/event.h>
#include <sys/time.h>
#include <errno.h>
#include <stdio.h>
#include <assert.h>
#define __PROSPERO__ 1
#define jio_fprintf fprintf
#define RESTARTABLE(cmd,result) do { result=(cmd); } while(result<0 && errno==EINTR)
static int mode, triggers, registrations, interruptions;
static void JNU_ThrowIOException(JNIEnv*e,const char*s){jclass c=(*e)->FindClass(e,"java/io/IOException");(*e)->ThrowNew(e,c,s);}
static void JNU_ThrowIOExceptionWithLastError(JNIEnv*e,const char*s){JNU_ThrowIOException(e,s);}
static int injected_kevent(int kq,const struct kevent*c,int nc,struct kevent*ev,int n,const struct timespec*t){
 assert(nc==1&&c->filter==EVFILT_USER&&c->ident==0);
 if(c->flags&EV_ADD){registrations++;if(mode==1){errno=ENOTSUP;return -1;}if(mode==2){errno=ENOMEM;return -1;}}
 else {assert(c->fflags==NOTE_TRIGGER);triggers++;if(mode==3){errno=EIO;return -1;}if(mode==4&&!interruptions++){errno=EINTR;return -1;}}
 return kevent(kq,c,nc,ev,n,t);
}
#define kevent(...) injected_kevent(__VA_ARGS__)
''' + s +r'''
JNIEXPORT void JNICALL Java_SelectorWakeupCheck_install(JNIEnv*e,jclass c){
 jclass k=(*e)->FindClass(e,"sun/nio/ch/KQueue");assert(k);
 JNINativeMethod methods[]={{"registerUserWakeup","(I)I",(void*)Java_sun_nio_ch_KQueue_registerUserWakeup},{"triggerUserWakeup","(I)V",(void*)Java_sun_nio_ch_KQueue_triggerUserWakeup}};
 assert((*e)->RegisterNatives(e,k,methods,2)==0);
}
JNIEXPORT void JNICALL Java_SelectorWakeupCheck_mode(JNIEnv*e,jclass c,jint m){mode=m;interruptions=0;}
JNIEXPORT jint JNICALL Java_SelectorWakeupCheck_triggers(JNIEnv*e,jclass c){return triggers;}
''')
lib=w/'libwakeup.dylib'
subprocess.run(['/usr/bin/clang','-shared','-fPIC','-fsanitize=undefined','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(c),'-o',str(lib)],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0'})
j=w/'SelectorWakeupCheck.java';j.write_text(r'''
import java.nio.*;import java.nio.channels.*;import java.net.*;import java.util.concurrent.*;
public class SelectorWakeupCheck {
 static native void install();static native void mode(int m);static native int triggers();
 static void check(boolean b){if(!b)throw new AssertionError();}
 public static void main(String[]a)throws Exception {
  System.load(a[0]);install();
  mode(2);try{Selector.open();throw new AssertionError();}catch(java.io.IOException expected){}
  mode(1);try(Selector s=Selector.open()){s.wakeup();check(s.select(5000)==0);}
  mode(0);
  for(int lifetime=0;lifetime<12;lifetime++)try(Selector s=Selector.open()){
   for(int i=0;i<100;i++){
    // Wake before select, coalesce repeated requests, then wake a blocked select.
    s.wakeup();s.wakeup();long start=System.nanoTime();s.select(5000);check(System.nanoTime()-start<1_000_000_000L);
    var f=CompletableFuture.runAsync(()->{try{Thread.sleep(2);}catch(Exception e){throw new RuntimeException(e);}s.wakeup();});
    start=System.nanoTime();s.select(5000);f.get();check(System.nanoTime()-start<1_000_000_000L);
   }
   try(ServerSocketChannel server=ServerSocketChannel.open()){
    server.bind(new InetSocketAddress(InetAddress.getLoopbackAddress(),0));
    try(SocketChannel client=SocketChannel.open(server.getLocalAddress());SocketChannel peer=server.accept()){
     peer.configureBlocking(false);var key=peer.register(s,SelectionKey.OP_READ);
     client.write(ByteBuffer.wrap(new byte[]{42}));check(s.select(5000)>0);check(key.isReadable());s.selectedKeys().clear();
     ByteBuffer b=ByteBuffer.allocate(1);check(peer.read(b)==1&&b.get(0)==42);key.cancel();s.selectNow();
    }
   }
  }
  mode(4);try(Selector s=Selector.open()){s.wakeup();s.select(1000);}mode(0);
  try(Selector s=Selector.open()){mode(3);try{s.wakeup();throw new AssertionError();}catch(InternalError expected){check(expected.getCause() instanceof java.io.IOException);}finally{mode(0);}}
  for(int i=0;i<100;i++){Selector s=Selector.open();var error=new java.util.concurrent.atomic.AtomicReference<Throwable>();Thread t=Thread.ofPlatform().start(()->{try{s.wakeup();}catch(Throwable e){error.set(e);}});s.close();t.join();check(error.get()==null);s.wakeup();}
  check(triggers()>2400);
  System.out.println("PASS: actual selector/user-event JNI, 1200 wake-before/blocking/coalescing rounds, socket readiness/cancel, 100 close races, EINTR, unsupported fallback and real-error propagation");
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),'-d',str(w),str(j)],check=True)
subprocess.run([str(jdk/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xcheck:jni','--patch-module','java.base='+str(classes),'-cp',str(w),'SelectorWakeupCheck',str(lib)],check=True,env={**os.environ,'UBSAN_OPTIONS':'handle_segv=0:handle_sigbus=0:handle_sigfpe=0'})
