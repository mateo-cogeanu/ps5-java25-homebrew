#!/usr/bin/env python3
"""Exercise actual OpenJDK management C sources against a real host JMM table."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1];WORK=ROOT/'build/java25';SRC=ROOT/'.tools/java25/openjdk/src';JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
java=r'''
import java.lang.management.MemoryUsage;
public class ManagementNativeCheck {
 static native MemoryUsage usage(boolean heap);
 static native String[] flags();
 public static void main(String[] args){System.load(args[0]);MemoryUsage heap=usage(true),other=usage(false);if(heap.getMax()!=Runtime.getRuntime().maxMemory()||heap.getUsed()<0||other.getUsed()<0)throw new AssertionError("Memory data mismatch");if(!java.util.Arrays.asList(flags()).contains("-Xint"))throw new AssertionError("Missing real VM flag");System.out.println("PASS: real management JNI_OnLoad/JMM table, heap/non-heap memory and actual VM flags");}
}
'''
bridge=r'''
#include <jni.h>
extern jobject Java_sun_management_MemoryImpl_getMemoryUsage0(JNIEnv*,jobject,jboolean);
extern jobjectArray Java_sun_management_VMManagementImpl_getVmArguments0(JNIEnv*,jobject);
JNIEXPORT jobject JNICALL Java_ManagementNativeCheck_usage(JNIEnv *env,jclass type,jboolean heap){return Java_sun_management_MemoryImpl_getMemoryUsage0(env,NULL,heap);}
JNIEXPORT jobjectArray JNICALL Java_ManagementNativeCheck_flags(JNIEnv *env,jclass type){return Java_sun_management_VMManagementImpl_getVmArguments0(env,NULL);}
'''
(WORK/'ManagementNativeCheck.java').write_text(java);(WORK/'management-host-bridge.c').write_text(bridge)
incs=[JDK/'include',JDK/'include/darwin',SRC/'java.base/share/native/libjava',SRC/'java.base/unix/native/libjava',SRC/'hotspot/share/include',SRC/'hotspot/os/posix/include',SRC/'java.management/share/native/libmanagement',ROOT/'.tools/java25/openjdk/build/ps5-bootstrap/support/headers/java.management']
subprocess.run(['clang','-std=c11','-dynamiclib','-undefined','dynamic_lookup',*['-I'+str(p) for p in incs],*[str(p) for p in sorted((SRC/'java.management/share/native/libmanagement').glob('*.c'))],str(WORK/'management-host-bridge.c'),'-o',str(WORK/'libmanagement-host-check.dylib')],check=True)
subprocess.run([str(JDK/'bin/javac'),'-d',str(WORK),str(WORK/'ManagementNativeCheck.java')],check=True)
subprocess.run([str(JDK/'bin/java'),'-Xint','--enable-native-access=ALL-UNNAMED','-cp',str(WORK),'ManagementNativeCheck',str(WORK/'libmanagement-host-check.dylib')],check=True)
