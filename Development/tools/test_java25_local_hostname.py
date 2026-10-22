#!/usr/bin/env python3
"""Actual IPv4/IPv6 hostname JNI bodies, controlled gethostname and real Java fallback."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
work=root/'build/java25/local-hostname-test';work.mkdir(parents=True,exist_ok=True)
jdk=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
bodies=[]
for family in (4,6):
 text=(root/f'.tools/java25/openjdk/src/java.base/unix/native/libnet/Inet{family}AddressImpl.c').read_text()
 a=text.index('JNIEXPORT jstring JNICALL\nJava_java_net_');b=text.index('\n}\n',a)+3
 bodies.append(text[a:b])
c=r'''
#include <jni.h>
#include <netdb.h>
#include <errno.h>
#include <string.h>
static int mode;
static int controlled_gethostname(char* out,size_t n){
 if(mode==2){errno=EIO;return -1;}
 if(mode==3){memset(out,'x',n);return 0;}
 if(mode==1){strncpy(out,"unit-host.example",n);return 0;}
 out[0]=0;return 0;
}
#define gethostname controlled_gethostname
'''+ '\n'.join(bodies)+r'''
#undef gethostname
JNIEXPORT void JNICALL Java_LocalHostname_setMode(JNIEnv* env,jclass cls,jint value){(void)env;(void)cls;mode=value;}
JNIEXPORT jstring JNICALL Java_LocalHostname_local(JNIEnv* env,jclass cls,jint family){(void)cls;return family==4?Java_java_net_Inet4AddressImpl_getLocalHostName(env,0):Java_java_net_Inet6AddressImpl_getLocalHostName(env,0);}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM* vm,void* reserved){
 (void)reserved;JNIEnv* env=0;if((*vm)->GetEnv(vm,(void**)&env,JNI_VERSION_1_8)!=JNI_OK)return JNI_ERR;
 JNINativeMethod m={"getLocalHostName","()Ljava/lang/String;",(void*)Java_java_net_Inet4AddressImpl_getLocalHostName};
 jclass c4=(*env)->FindClass(env,"java/net/Inet4AddressImpl");if(!c4||(*env)->RegisterNatives(env,c4,&m,1)!=0)return JNI_ERR;
 m.fnPtr=(void*)Java_java_net_Inet6AddressImpl_getLocalHostName;
 jclass c6=(*env)->FindClass(env,"java/net/Inet6AddressImpl");if(!c6||(*env)->RegisterNatives(env,c6,&m,1)!=0)return JNI_ERR;
 return JNI_VERSION_1_8;
}
'''
(work/'test.c').write_text(c)
(work/'LocalHostname.java').write_text(r'''
import java.net.InetAddress;
public class LocalHostname {
 static native void setMode(int value);
 static native String local(int family);
 public static void main(String[] args)throws Exception {
  System.load(args[0]);int mode=Integer.parseInt(args[1]);boolean ps5=Boolean.parseBoolean(args[2]);setMode(mode);
  String expected=mode==0?(ps5?"localhost":""):mode==1?"unit-host.example":mode==2?"localhost":"x".repeat(1025);
  for(int family:new int[]{4,6})if(!local(family).equals(expected))throw new AssertionError("family="+family+" mode="+mode+" value="+local(family));
  if((mode==0&&ps5)||mode==2)if(!InetAddress.getLocalHost().isLoopbackAddress())throw new AssertionError("standard localhost fallback did not return loopback");
 }
}
''')
subprocess.run([str(jdk/'bin/javac'),str(work/'LocalHostname.java')],check=True)
for ps5 in (False,True):
 lib=work/('libps5.dylib' if ps5 else 'libcontrol.dylib')
 subprocess.run(['clang','-dynamiclib','-O1','-g','-fsanitize=undefined','-Wall','-Wextra','-Wno-unused-parameter','-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),*(['-D__PROSPERO__']if ps5 else []),str(work/'test.c'),'-o',str(lib)],check=True)
 for mode in range(4):
  for ipv4 in ('true','false'):
   subprocess.run([str(jdk/'bin/java'),'-Xcheck:jni','--enable-native-access=ALL-UNNAMED','-Djava.net.preferIPv4Stack='+ipv4,'-cp',str(work),'LocalHostname',str(lib),str(mode),str(ps5).lower()],check=True,timeout=15)
print('PASS actual IPv4/IPv6 hostname JNI bodies in real JVM: empty success/failure/named/unterminated boundaries; PS5-only empty fallback and nonPS5 control; actual InetAddress.getLocalHost loopback fallback under IPv4/IPv6 preference; XcheckJNI/UBSan. No remote DNS override or PS5 proof.')
