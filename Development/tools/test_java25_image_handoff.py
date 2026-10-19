#!/usr/bin/env python3
"""Actual Java image reader + actual index-only native reader/JNI on host JDK25."""
from pathlib import Path
import subprocess,os
r=Path(__file__).resolve().parents[1];src=r/'.tools/java25/openjdk';w=r/'build/java25/image-handoff';w.mkdir(parents=True,exist_ok=True)
j=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
share=src/'src/java.base/share/native/libjimage';zipbase=src/'src/java.base/share/native/libzip'
# Actual native ZIP entry and allocation adapter; no substitute inflater.
z=(zipbase/'zip_util.c').read_text();a=z.index('JNIEXPORT jboolean\nZIP_InflateFully');b=z.index('\nstatic voidpf tracking_zlib_alloc',a)
(w/'zip.c').write_text('#include <jni.h>\n#include <zlib.h>\n#include "ps5ZipAlloc.h"\n'+z[a:b])
includes=[share,src/'src/java.base/share/native/libjava',src/'src/java.base/unix/native/libjava',src/'src/hotspot/share/include',src/'src/hotspot/os/posix/include',src/'build/ps5-bootstrap/support/modules_include/java.base',src/'build/ps5-bootstrap/support/headers/java.base',r/'build/native',zipbase,j/'include',j/'include/darwin']
base=['-O1','-g','-fsanitize=undefined','-D__PROSPERO__','-DNDEBUG']+['-I'+str(p) for p in includes]
subprocess.run(['/usr/bin/clang',*base,'-c',str(w/'zip.c'),'-o',str(w/'zip.o')],check=True)
(w/'prepare.cpp').write_text('''#include "jni.h"
#include "jimage.hpp"
extern "C" JNIEXPORT void JNICALL Java_jdk_internal_jimage_NativeImageBuffer_prepare(JNIEnv* env,jclass,jstring name) {
 const char* path=env->GetStringUTFChars(name,nullptr);if(!path)return;
 jint error=0;auto image=JIMAGE_Open(path,&error);env->ReleaseStringUTFChars(name,path);
 if(!image)env->ThrowNew(env->FindClass("java/io/IOException"),"Actual index-only JIMAGE open failed");
}
''')
objects=[]
for name in ['endian.cpp','imageDecompressor.cpp','imageFile.cpp','jimage.cpp','NativeImageBuffer.cpp']:
 obj=w/(name+'.o');extra=[]
 if name=='NativeImageBuffer.cpp':extra=['-DJava_jdk_internal_jimage_NativeImageBuffer_getNativeMap=Java_jdk_internal_jimage_NativeImageBuffer_getMap']
 subprocess.run(['/usr/bin/clang++','-std=c++14',*base,*extra,'-c',str(share/name),'-o',str(obj)],check=True);objects.append(str(obj))
for path in [src/'src/java.base/unix/native/libjimage/osSupport_unix.cpp',w/'prepare.cpp']:
 obj=w/(path.stem+'.o');subprocess.run(['/usr/bin/clang++','-std=c++14',*base,'-c',str(path),'-o',str(obj)],check=True);objects.append(str(obj))
lib=w/'libimagehandoff.dylib'
subprocess.run(['/usr/bin/clang++','-dynamiclib','-fsanitize=undefined',*objects,str(w/'zip.o'),'-L'+str(j/'lib/server'),'-Wl,-rpath,'+str(j/'lib/server'),'-ljvm','-lz','-o',str(lib)],check=True)
actual=src/'src/java.base/share/classes/jdk/internal/jimage/BasicImageReader.java'
native='''package jdk.internal.jimage;
import java.nio.ByteBuffer;
class NativeImageBuffer {
 static {System.load(System.getProperty("ps5.test.imageLibrary"));}
 static native void prepare(String path);
 static native ByteBuffer getMap(String path);
 static ByteBuffer getNativeMap(String path){prepare(path);return getMap(path);}
}
'''
for mode,reader,shim in [('fixed',actual.read_text(),True),('old',actual.read_text().replace('MAP_ALL = !IS_PS5 &&','MAP_ALL ='),True),('desktop',actual.read_text(),False)]:
 sources=w/mode/'src/jdk/internal/jimage';sources.mkdir(parents=True,exist_ok=True);(sources/'BasicImageReader.java').write_text(reader)
 files=[sources/'BasicImageReader.java']
 if shim:(sources/'NativeImageBuffer.java').write_text(native);files.append(sources/'NativeImageBuffer.java')
 subprocess.run([str(j/'bin/javac'),'--patch-module','java.base='+str(w/mode/'src'),'-d',str(w/mode/'classes'),*map(str,files)],check=True)
(w/'ImageHandoff.java').write_text('''import java.nio.file.*;
import java.util.*;
import jdk.internal.jimage.BasicImageReader;
public class ImageHandoff {
 public static void main(String[] args)throws Exception {
  // Reproduce the real preflight's JarFile input stream/module initialization.
  try(var jar=new java.util.jar.JarFile(args[1]);var input=new java.io.DataInputStream(jar.getInputStream(jar.getJarEntry("net/minecraft/server/Main.class")))) {
   if(input.readInt()!=0xcafebabe)throw new AssertionError("Jar class magic");input.readUnsignedShort();if(input.readUnsignedShort()!=69)throw new AssertionError("Java25 class");
  }
  try(var reader=BasicImageReader.open(Path.of(args[0]))) {
   String[] names={"java.base/java/lang/Object.class","java.base/jdk/internal/icu/impl/data/icudt76b/nfkc.nrm","java.base/javax/net/ssl/HttpsURLConnection$DefaultHostnameVerifier.class","java.base/sun/security/ssl/DTLSInputRecord.class","jdk.jfr/jdk/jfr/internal/types/metadata.bin"};
   for(String name:names){byte[] actual=reader.getResource("/"+name);if(!Arrays.equals(actual,Files.readAllBytes(Path.of(args[2],name))))throw new AssertionError(name);}
  }
  System.out.println("PASS: actual Java/native/JNI image handoff, JarFile bytecode read and exact Object/Unicode/HTTPS/DTLS/JFR bytes");
 }
}
''')
subprocess.run([str(j/'bin/javac'),'--add-exports','java.base/jdk.internal.jimage=ALL-UNNAMED','-d',str(w),str(w/'ImageHandoff.java')],check=True)
expected=w/'expected';expected.mkdir(exist_ok=True)
subprocess.run([str(j/'bin/jimage'),'extract','--dir',str(expected),str(r/'build/java25/boot-image/lib/modules')],check=True)
jar=r/'.tools/github-publish/ps5-minecraft-java/build/assets/java25/jars/server-26.3.jar'
for mode in ['old','fixed','desktop']:
 command=[str(j/'bin/java'),'--patch-module','java.base='+str(w/mode/'classes'),'--add-exports','java.base/jdk.internal.jimage=ALL-UNNAMED','-Dps5.test.imageLibrary='+str(lib)]
 if mode!='desktop':command+=['-Dos.name=PS5','-Djdk.image.map.all=true']
 result=subprocess.run([*command,'-cp',str(w),'ImageHandoff',str(r/'build/java25/boot-image/lib/modules'),str(jar),str(expected)],text=True,capture_output=True,timeout=45,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1:print_stacktrace=1:handle_sigbus=0:handle_sigsegv=0:handle_sigill=0'})
 (w/(mode+'.log')).write_text(result.stdout+result.stderr)
 if mode=='old':
  assert result.returncode!=0 and ('IndexOutOfBoundsException' in result.stderr or 'ExceptionInInitializerError' in result.stderr),result.stdout+result.stderr
  print('PASS: old Java map-all mode with index-only JNI reproduces JarFile initialization failure')
 else:
  assert result.returncode==0,result.stdout+result.stderr
  print(mode+': '+result.stdout.strip())
