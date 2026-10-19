#!/usr/bin/env python3
"""Exercise actual PS5 seed JNI and Java routing; mocked OS boundary, not console RNG evidence."""
from pathlib import Path
import subprocess,shutil,os
r=Path(__file__).resolve().parents[1];w=r/'build/java25/entropy-test';w.mkdir(parents=True,exist_ok=True)
j=Path('/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home');src=r/'.tools/java25/openjdk/src/java.base'
(w/'src/sun/security/provider').mkdir(parents=True,exist_ok=True)
shutil.copy2(src/'unix/classes/sun/security/provider/NativeSeedGenerator.java',w/'src/sun/security/provider')
subprocess.run([str(j/'bin/javac'),'--patch-module','java.base='+str(w/'src'),'-d',str(w/'patch'),str(w/'src/sun/security/provider/NativeSeedGenerator.java')],check=True)
(w/'fixture.c').write_text(r'''
#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <assert.h>
#include <string.h>
#include <unistd.h>
static int calls,fail_after=-1;
int sysctlbyname(const char *name,void *output,size_t *length,void *input,size_t input_size){
 assert(!strcmp(name,"kern.rng_pseudo")&&!input&&!input_size&&*length==64);
 if(getenv("PS5_SEED_KERNEL_FAIL"))return -1;
 if(fail_after>=0&&calls>=fail_after)return -1;
 arc4random_buf(output,*length);
 if(getenv("PS5_SEED_SHORT_RESPONSE"))*length=1;
 if(getenv("PS5_SEED_OVERSIZED_RESPONSE"))*length=65;
 __atomic_add_fetch(&calls,1,__ATOMIC_RELAXED);return 0;
}
extern void Java_sun_security_provider_NativeSeedGenerator_getPS5SeedBytes(JNIEnv*,jclass,jbyteArray);
JNIEXPORT void JNICALL Java_EntropyCheck_mode(JNIEnv*e,jclass c,jint n){fail_after=n;calls=0;}
JNIEXPORT jint JNICALL Java_EntropyCheck_calls(JNIEnv*e,jclass c){return calls;}
JNIEXPORT jint JNICALL JNI_OnLoad(JavaVM*vm,void*x){JNIEnv*e;if((*vm)->GetEnv(vm,(void**)&e,JNI_VERSION_1_8))return JNI_ERR;jclass c=(*e)->FindClass(e,"sun/security/provider/NativeSeedGenerator");JNINativeMethod m={"getPS5SeedBytes","([B)V",(void*)Java_sun_security_provider_NativeSeedGenerator_getPS5SeedBytes};if((*e)->RegisterNatives(e,c,&m,1))return JNI_ERR;return JNI_VERSION_1_8;}
''')
subprocess.run(['clang','-shared','-fPIC','-g','-fsanitize=undefined','-D__PROSPERO__','-I'+str(j/'include'),'-I'+str(j/'include/darwin'),str(src/'unix/native/libjava/PS5SeedGenerator.c'),str(w/'fixture.c'),'-o',str(w/'entropy.dylib')],check=True)
(w/'EntropyCheck.java').write_text(r'''
import java.security.*;import java.lang.reflect.*;
public class EntropyCheck {
 static native void mode(int failure);static native int calls();
 public static void main(String[]args)throws Exception{
  if(args.length>1 && args[1].equals("desktop")) {
   var rng=SecureRandom.getInstance("DRBG");rng.nextBytes(new byte[64]);
   System.out.println("PASS: other Unix platforms retain URL seed source");return;
  }
  System.setProperty("os.name","PS5");System.load(args[0]);
  Class<?> c=Class.forName("sun.security.provider.NativeSeedGenerator");var cons=c.getDeclaredConstructor(String.class);cons.setAccessible(true);
  Object generator=cons.newInstance("file:/definitely-missing-ps5-entropy-device");var fill=c.getDeclaredMethod("getSeedBytes",byte[].class);fill.setAccessible(true);
  if(args.length>1 && args[1].equals("resolve-failure")) {
   try{fill.invoke(generator,(Object)new byte[32]);throw new AssertionError("resolver failure accepted");}catch(InvocationTargetException e){if(!(e.getCause() instanceof ProviderException))throw e;}
   System.out.println("PASS: kernel failure/invalid-length response propagates as ProviderException");return;
  }
  var error=new java.util.concurrent.atomic.AtomicReference<Throwable>();Thread[]threads=new Thread[8];
  for(int i=0;i<threads.length;i++){threads[i]=new Thread(()->{try{fill.invoke(generator,(Object)new byte[129]);}catch(Throwable t){error.set(t);}});threads[i].start();}
  for(Thread t:threads)t.join();if(error.get()!=null)throw new AssertionError(error.get());
  for(int n:new int[]{0,1,32,64,65,129,4097}){mode(-1);byte[]b=new byte[n];fill.invoke(generator,(Object)b);if(calls()!=(n+63)/64)throw new AssertionError("batch count");}
  for(int failure:new int[]{0,1}){mode(failure);try{fill.invoke(generator,(Object)new byte[129]);throw new AssertionError("failure swallowed");}catch(InvocationTargetException e){if(!(e.getCause() instanceof ProviderException))throw e;}}
  mode(-1);var rng=SecureRandom.getInstance("DRBG");byte[]a=new byte[64];rng.nextBytes(a);rng.generateSeed(129);if(calls()<3)throw new AssertionError("actual DRBG did not use OS source");
  if(Thread.getAllStackTraces().keySet().stream().anyMatch(t->t.getName().contains("SeedGenerator")))throw new AssertionError("threaded fallback used");
  System.out.println("PASS: actual PS5 seed Java/JNI routing, 64-byte bounds/empty/multibatch, OS failures propagate, real DRBG seeding and no threaded fallback; OS boundary mocked with host RNG");
 }
}
''')
subprocess.run([str(j/'bin/javac'),'-d',str(w),str(w/'EntropyCheck.java')],check=True)
subprocess.run([str(j/'bin/java'),'--enable-native-access=ALL-UNNAMED','-Xcheck:jni','--patch-module','java.base='+str(w/'patch'),'--add-opens','java.base/sun.security.provider=ALL-UNNAMED','-cp',str(w),'EntropyCheck',str(w/'entropy.dylib')],check=True,timeout=30,env={**os.environ,"UBSAN_OPTIONS":"handle_segv=0:handle_sigbus=0:handle_sigfpe=0"})

subprocess.run([str(j/"bin/java"),"--patch-module","java.base="+str(w/"patch"),"-cp",str(w),"EntropyCheck",str(w/"entropy.dylib"),"desktop"],check=True,timeout=30,env={**os.environ,"UBSAN_OPTIONS":"handle_segv=0:handle_sigbus=0:handle_sigfpe=0"})

for failure in ["PS5_SEED_KERNEL_FAIL","PS5_SEED_SHORT_RESPONSE","PS5_SEED_OVERSIZED_RESPONSE"]:
 subprocess.run([str(j/"bin/java"),"--enable-native-access=ALL-UNNAMED","-Xcheck:jni","--patch-module","java.base="+str(w/"patch"),"--add-opens","java.base/sun.security.provider=ALL-UNNAMED","-cp",str(w),"EntropyCheck",str(w/"entropy.dylib"),"resolve-failure"],check=True,timeout=30,env={**os.environ,failure:"1","UBSAN_OPTIONS":"handle_segv=0:handle_sigbus=0:handle_sigfpe=0"})
