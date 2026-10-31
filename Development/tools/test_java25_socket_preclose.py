#!/usr/bin/env python3
"""Actual UnixDispatcher JNI: shutdown without early FD reuse; real blocked Java I/O."""
import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, default=os.environ.get('JAVA_HOME'))
    args = parser.parse_args()
    jdk = args.java_home
    if jdk is None:
        javac = shutil.which('javac')
        if not javac:
            parser.error('Set JAVA_HOME or --java-home to JDK25')
        jdk = Path(javac).resolve().parent.parent
    source = (ROOT/'.tools/java25/openjdk/src/java.base/unix/native/libnio/ch/UnixDispatcher.c').read_text()
    actual = source[source.index('JNIEXPORT void JNICALL\nJava_sun_nio_ch_UnixDispatcher_preClose0'):]
    preamble = r'''
#include <jni.h>
#include <sys/socket.h>
#include <unistd.h>
#include <errno.h>
#include <string.h>
static int preCloseFD=99, deny=0, dup_calls=0, shutdown_calls=0;
static int fdval(JNIEnv*e,jobject f){return e->GetIntField(f,e->GetFieldID(e->GetObjectClass(f),"fd","I"));}
static void JNU_ThrowIOExceptionWithLastError(JNIEnv*e,const char*){e->ThrowNew(e->FindClass("java/io/IOException"),strerror(errno));}
static int denied_dup2(int,int){++dup_calls;errno=EPERM;return -1;}
static int checked_shutdown(int fd,int how){++shutdown_calls;if(deny){errno=deny;deny=0;return -1;}return shutdown(fd,how);}
#define dup2 denied_dup2
#define shutdown checked_shutdown
'''
    bridge = r'''
extern "C" JNIEXPORT void JNICALL Java_PreCloseControl_deny(JNIEnv*,jclass,jint e){deny=e;}
extern "C" JNIEXPORT jint JNICALL Java_PreCloseControl_dups(JNIEnv*,jclass){return dup_calls;}
extern "C" JNIEXPORT jint JNICALL Java_PreCloseControl_shutdowns(JNIEnv*,jclass){return shutdown_calls;}
extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*v,void*){
 JNIEnv*e=nullptr;if(v->GetEnv((void**)&e,JNI_VERSION_1_8)!=JNI_OK)return JNI_ERR;
 JNINativeMethod m{(char*)"preClose0",(char*)"(Ljava/io/FileDescriptor;)V",(void*)&Java_sun_nio_ch_UnixDispatcher_preClose0};
 return e->RegisterNatives(e->FindClass("sun/nio/ch/UnixDispatcher"),&m,1)==0?JNI_VERSION_1_8:JNI_ERR;
}
'''
    java = r'''
import java.io.*;import java.net.*;import java.nio.*;import java.nio.channels.*;import java.lang.reflect.*;import java.util.concurrent.*;import java.util.concurrent.atomic.*;
public class PreCloseControl {
 static native void deny(int e);static native int dups();static native int shutdowns();
 static void check(boolean b){if(!b)throw new AssertionError();}
 static Method method;
 static FileDescriptor fd(Object channel)throws Exception {Field f=channel.getClass().getDeclaredField("fd");f.setAccessible(true);return (FileDescriptor)f.get(channel);}
 static void pre(FileDescriptor fd)throws Exception{method.invoke(null,fd);}
 static void error(FileDescriptor fd,int e)throws Exception{deny(e);try{pre(fd);throw new AssertionError("error hidden");}catch(InvocationTargetException x){check(x.getCause() instanceof IOException);}}
 interface IO {void run()throws Exception;}
 static Thread blocked(IO io,AtomicReference<Throwable> failure)throws Exception{
  CountDownLatch ready=new CountDownLatch(1);Thread t=Thread.ofPlatform().start(()->{ready.countDown();try{io.run();failure.set(new AssertionError("closed I/O completed"));}catch(ClosedChannelException|SocketException expected){}catch(Throwable x){failure.set(x);}});
  ready.await();long end=System.nanoTime()+TimeUnit.SECONDS.toNanos(3);while(t.getState()!=Thread.State.RUNNABLE&&System.nanoTime()<end)Thread.yield();Thread.sleep(30);return t;
 }
 static void joined(Thread t,AtomicReference<Throwable> f)throws Exception{t.join(3000);check(!t.isAlive());if(f.get()!=null)throw new AssertionError(f.get());}
 public static void main(String[]args)throws Exception {
  try(var c=DatagramChannel.open()){}System.load(args[0]);boolean ps5=Boolean.parseBoolean(args[1]);
  method=Class.forName("sun.nio.ch.UnixDispatcher").getDeclaredMethod("preClose0",FileDescriptor.class);method.setAccessible(true);
  try(var c=DatagramChannel.open().bind(new InetSocketAddress(InetAddress.getLoopbackAddress(),0))){
   if(!ps5){error(fd(c),0);check(dups()==1&&shutdowns()==0);System.out.println("PASS desktop dup2/error unchanged");return;}
   deny(4);pre(fd(c));check(shutdowns()==2&&dups()==0); // EINTR retried; unconnected UDP ENOTCONN accepted
  }
  try(var c=DatagramChannel.open()){error(fd(c),1);} // genuine shutdown EPERM propagates
  error(new FileDescriptor(),0); // EBADF is not success
  try(var file=new RandomAccessFile(args[2],"rw")){error(file.getFD(),0);check(dups()==1);} // non-socket path unchanged
  for(int n=0;n<40;n++){
   AtomicReference<Throwable> f=new AtomicReference<>();
   try(var c=DatagramChannel.open().bind(new InetSocketAddress(InetAddress.getLoopbackAddress(),0))){
    Thread t=blocked(()->c.receive(ByteBuffer.allocate(8)),f);c.close();joined(t,f);
   }
   try(var server=ServerSocketChannel.open().bind(new InetSocketAddress(InetAddress.getLoopbackAddress(),0));var client=SocketChannel.open(server.getLocalAddress());var peer=server.accept()){
    Thread t=blocked(()->client.read(ByteBuffer.allocate(8)),f);client.close();joined(t,f);
    // Open a fresh descriptor immediately. It must remain usable after old I/O ends.
    try(var replacement=new DatagramSocket(new InetSocketAddress(InetAddress.getLoopbackAddress(),0))){check(!replacement.isClosed());}
   }
   try(var server=ServerSocketChannel.open().bind(new InetSocketAddress(InetAddress.getLoopbackAddress(),0))){
    Thread t=blocked(()->server.accept(),f);server.close();joined(t,f);
   }
  }
  check(dups()==1);System.out.println("PASS actual JNI PS5 blocked UDP/TCP/accept close, repeated descriptor ownership, EINTR/ENOTCONN, errors and non-socket control");
 }
}
'''
    with tempfile.TemporaryDirectory(prefix='preclose-') as td:
        work = Path(td)
        (work/'PreCloseControl.java').write_text(java)
        subprocess.run([str(jdk/'bin/javac'), '-d', td, str(work/'PreCloseControl.java')], check=True)
        for ps5 in (False, True):
            cpp = work/'test.cpp'
            cpp.write_text(preamble+actual+bridge)
            lib = work/('test.dylib' if sys.platform=='darwin' else 'test.so')
            flags = ['-dynamiclib'] if sys.platform=='darwin' else ['-shared','-fPIC']
            subprocess.run([os.environ.get('CXX','clang++'),*flags,'-fsanitize=undefined','-O1','-g',
                            '-I'+str(jdk/'include'),'-I'+str(jdk/'include'/('darwin' if sys.platform=='darwin' else 'linux')),
                            *(['-D__PROSPERO__'] if ps5 else []),str(cpp),'-o',str(lib)],check=True)
            subprocess.run([str(jdk/'bin/java'),'-Xcheck:jni','--enable-native-access=ALL-UNNAMED','--add-opens=java.base/sun.nio.ch=ALL-UNNAMED','-cp',td,
                            'PreCloseControl',str(lib),str(ps5).lower(),str(work/'data')],check=True,timeout=35,
                           env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1:handle_segv=0:handle_sigbus=0:handle_sigfpe=0'})

if __name__=='__main__':
    main()
