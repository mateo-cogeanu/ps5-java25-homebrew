#!/usr/bin/env python3
"""Exercise exact Net.available with deniedioctl,real TCP/HTTP reads and errors."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1];JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
s=(ROOT/'.tools/java25/openjdk/src/java.base/unix/native/libnio/ch/Net.c').read_text();actual=s[s.index('JNIEXPORT jint JNICALL\nJava_sun_nio_ch_Net_available'):s.index('JNIEXPORT jint JNICALL\nJava_sun_nio_ch_Net_poll')]
preamble=r'''
#include <jni.h>
#include <sys/socket.h>
#include <sys/ioctl.h>
#include <errno.h>
#include <string.h>
#define IOS_THROWN -2
#define RESTARTABLE(cmd,result) do {result=(cmd);} while(result==-1&&errno==EINTR)
static int injected_error=EPERM,calls=0;
static int fdval(JNIEnv*env,jobject fd){jclass c=env->GetObjectClass(fd);return env->GetIntField(fd,env->GetFieldID(c,"fd","I"));}
static void handleSocketError(JNIEnv*env,int e){env->ThrowNew(env->FindClass("java/net/SocketException"),strerror(e));}
static int denied_ioctl(int fd,unsigned long req,int*count){++calls;if(injected_error){errno=injected_error;return -1;}return ioctl(fd,req,count);}
#define ioctl denied_ioctl
'''
bridge=r'''
#undef ioctl
extern "C" JNIEXPORT void JNICALL Java_AvailableControl_error(JNIEnv*,jclass,jint e){injected_error=e;}
extern "C" JNIEXPORT jint JNICALL Java_AvailableControl_unsupported(JNIEnv*,jclass){return EOPNOTSUPP;}
extern "C" JNIEXPORT jint JNICALL Java_AvailableControl_calls(JNIEnv*,jclass){return calls;}
extern "C" JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*){JNIEnv*env=nullptr;if(vm->GetEnv((void**)&env,JNI_VERSION_1_8)!=JNI_OK)return JNI_ERR;JNINativeMethod m{(char*)"available",(char*)"(Ljava/io/FileDescriptor;)I",(void*)&Java_sun_nio_ch_Net_available};jclass c=env->FindClass("sun/nio/ch/Net");return env->RegisterNatives(c,&m,1)==0?JNI_VERSION_1_8:JNI_ERR;}
'''
java=r'''
import java.io.*;import java.net.*;import java.lang.reflect.*;import java.nio.charset.*;import java.util.*;
public class AvailableControl {
 static native void error(int n);static native int calls();static native int unsupported();
 static void check(boolean x){if(!x)throw new AssertionError();}
 public static void main(String[]args)throws Exception{
  // Initialize normalNet first,then replace only this JNI entry in a test JVM.
  try(var s=new ServerSocket(0)){}System.load(args[0]);boolean ps5=Boolean.parseBoolean(args[1]);
  try(var listener=new ServerSocket(0);var client=new Socket("127.0.0.1",listener.getLocalPort());var peer=listener.accept()){
   peer.getOutputStream().write(new byte[]{1,2,3});peer.getOutputStream().flush();
   error(1);if(ps5){for(int e:new int[]{1,13,25,unsupported()}){error(e);check(client.getInputStream().available()==0);}check(client.getInputStream().read()==1);error(0);check(client.getInputStream().available()==2);check(Arrays.equals(client.getInputStream().readNBytes(2),new byte[]{2,3}));}
   else{try{client.getInputStream().available();throw new AssertionError("desktop fallback");}catch(SocketException expected){}}
  }
  Method available=Class.forName("sun.nio.ch.Net").getDeclaredMethod("available",FileDescriptor.class);available.setAccessible(true);
  for(int err:new int[]{1,9,54}){error(err);try{available.invoke(null,new FileDescriptor());throw new AssertionError("bad descriptor hidden");}catch(InvocationTargetException expected){check(expected.getCause() instanceof SocketException);}}
  try(var udp=java.nio.channels.DatagramChannel.open()){
   var fd=udp.getClass().getDeclaredField("fd");fd.setAccessible(true);error(1);try{available.invoke(null,fd.get(udp));throw new AssertionError("datagram denial hidden");}catch(InvocationTargetException expected){check(expected.getCause() instanceof SocketException);}
  }
  if(ps5){
   error(1);byte[] body=new byte[131071];for(int i=0;i<body.length;i++)body[i]=(byte)i;
   try(var listener=new ServerSocket(0)){
    Thread worker=new Thread(()->{try(var peer=listener.accept()){var in=new BufferedReader(new InputStreamReader(peer.getInputStream(),StandardCharsets.US_ASCII));while(!in.readLine().isEmpty()){}var out=peer.getOutputStream();out.write(("HTTP/1.1 200 OK\r\nContent-Length: "+body.length+"\r\nConnection: close\r\n\r\n").getBytes(StandardCharsets.US_ASCII));for(int i=0;i<body.length;i+=4093){out.write(body,i,Math.min(4093,body.length-i));out.flush();Thread.sleep(1);}}catch(Exception e){throw new RuntimeException(e);}});worker.start();
    var con=new URL("http://127.0.0.1:"+listener.getLocalPort()+"/texture").openConnection();con.setReadTimeout(5000);try(var in=con.getInputStream()){check(Arrays.equals(in.readAllBytes(),body));}worker.join(5000);check(!worker.isAlive());
   }
  }
  check(calls()>0);System.out.println("PASS exactNet.available PS5="+ps5+":deniedioctl conservativeestimate,realTCP/HTTPbytes,successfulcounts,desktoperrorandinvaliddescriptor/errorcontrols;hostonly");
 }
}
'''
with tempfile.TemporaryDirectory(prefix='stream-available-')as folder:
 w=Path(folder);(w/'AvailableControl.java').write_text(java);subprocess.run([str(JDK/'bin/javac'),'--release','25','-d',str(w),str(w/'AvailableControl.java')],check=True)
 for ps5 in [False,True]:
  cpp=w/('check'+str(ps5)+'.cpp');lib=cpp.with_suffix('.dylib');cpp.write_text(preamble+actual+bridge)
  subprocess.run(['clang++','-std=c++17','-dynamiclib','-fsanitize=undefined',*(['-D__PROSPERO__=1']if ps5 else []),'-I'+str(JDK/'include'),'-I'+str(JDK/'include/darwin'),str(cpp),'-o',str(lib)],check=True)
  subprocess.run([str(JDK/'bin/java'),'-Xcheck:jni','--enable-native-access=ALL-UNNAMED','--add-opens','java.base/sun.nio.ch=ALL-UNNAMED','-cp',str(w),'AvailableControl',str(lib),str(ps5).lower()],check=True,timeout=30)
