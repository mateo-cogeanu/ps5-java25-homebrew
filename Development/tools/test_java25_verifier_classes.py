#!/usr/bin/env python3
"""Compile the patched real legacy verifier for macOS and verify supplied classes."""
from pathlib import Path
import argparse,subprocess
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--class-path',required=True)
parser.add_argument('classes',nargs='+')
args=parser.parse_args();work=ROOT/'build/java25';source=ROOT/'.tools/java25/openjdk/src'
(work/"VerifyPoolCheck.java").write_text('public class VerifyPoolCheck {\n static native int verify(Class<?> type,int major);\n public static void main(String[] args)throws Exception {System.load(args[0]);for(String name:java.util.Arrays.copyOfRange(args,1,args.length)){Class<?> type=Class.forName(name,false,ClassLoader.getSystemClassLoader());int major;try(var input=new java.io.DataInputStream(type.getResourceAsStream("/"+name.replace(".","/")+".class"))){if(input.readInt()!=0xCAFEBABE)throw new AssertionError("class magic");input.readUnsignedShort();major=input.readUnsignedShort();}if(major>50)throw new IllegalArgumentException("Use the modern JVM verifier for class version "+major+": "+name);int result=verify(type,major);if(result!=1)throw new AssertionError(name+" result "+result);System.out.println("PASS real legacy verifier: "+name);}}\n}\n')
(work/"verifier-host-bridge.c").write_text('#include <jni.h>\n#include <stdio.h>\nextern jboolean VerifyClassForMajorVersion(JNIEnv*,jclass,char*,jint,jint);\nJNIEXPORT jint JNICALL Java_VerifyPoolCheck_verify(JNIEnv *env,jclass self,jclass type,jint major){char error[4096]={0};int result=VerifyClassForMajorVersion(env,type,error,sizeof(error),major);if(result!=1)fprintf(stderr,"%s\\n",error);return result;}\n')
incs=[JDK/'include',JDK/'include/darwin',source/'java.base/share/native/libjava',source/'java.base/unix/native/libjava',source/'hotspot/share/include',source/'hotspot/os/posix/include',source/'java.base/share/native/include']
subprocess.run(['clang','-std=c11','-D__PROSPERO__','-DNDEBUG','-D_LITTLE_ENDIAN','-dynamiclib','-undefined','dynamic_lookup',*['-I'+str(p) for p in incs],str(source/'java.base/share/native/libverify/check_code.c'),str(work/'verifier-host-bridge.c'),'-o',str(work/'libverify-pool-host.dylib')],check=True)
subprocess.run([str(JDK/'bin/javac'),'-d',str(work),str(work/'VerifyPoolCheck.java')],check=True)
subprocess.run([str(JDK/'bin/java'),'--enable-native-access=ALL-UNNAMED','-cp',str(work)+':'+args.class_path,'VerifyPoolCheck',str(work/'libverify-pool-host.dylib'),*args.classes],check=True)
