#!/usr/bin/env python3
"""Run the actual last-error formatter with real host JNI exception/string calls.

Only diagnostic-buffer malloc and last-error text are injected; this is host
behavior, not console flag-query validation.
"""
from pathlib import Path
import os,subprocess
root=Path(__file__).resolve().parents[1]
jdk=Path(os.environ.get('JAVA25_BOOT_JDK','/opt/homebrew/opt/openjdk@25/libexec/openjdk.jdk/Contents/Home'))
s=(root/'.tools/java25/openjdk/src/java.base/share/native/libjava/jni_util.c').read_text()
a=s.index('JNU_ThrowByNameWithMessageAndLastError\n');body=s[a:s.index('\nJNIEXPORT',a)]
w=root/'build/java25/error-message-test';w.mkdir(parents=True,exist_ok=True)
c=w/'test.c';c.write_text(r'''
#include <jni.h>
#include <assert.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
static int refuse,live;
static void *test_malloc(size_t n){if(refuse)return NULL;void*p=malloc(n);assert(p);live++;return p;}
static void test_free(void*p){if(p){live--;free(p);}}
static jstring getLastErrorString(JNIEnv *e){return (*e)->NewStringUTF(e,"Permission denied");}
static void JNU_ThrowByName(JNIEnv *e,const char *name,const char *message){jclass c=(*e)->FindClass(e,name);if(c){(*e)->ThrowNew(e,c,message);(*e)->DeleteLocalRef(e,c);}}
static void JNU_ThrowOutOfMemoryError(JNIEnv *e,const char *m){JNU_ThrowByName(e,"java/lang/OutOfMemoryError",m);}
static jvalue JNU_CallMethodByName(JNIEnv *e,void *unused,jobject o,const char *name,const char *sig,jobject arg){(void)unused;jvalue r={0};jclass c=(*e)->GetObjectClass(e,o);if(!c)return r;jmethodID id=(*e)->GetMethodID(e,c,name,sig);if(id)r.l=(*e)->CallObjectMethod(e,o,id,arg);(*e)->DeleteLocalRef(e,c);return r;}
static jobject JNU_NewObjectByName(JNIEnv *e,const char *name,const char *sig,jobject arg){jclass c=(*e)->FindClass(e,name);if(!c)return NULL;jmethodID id=(*e)->GetMethodID(e,c,"<init>",sig);jobject r=id?(*e)->NewObject(e,c,id,arg):NULL;(*e)->DeleteLocalRef(e,c);return r;}
#define JNU_CHECK_EXCEPTION(e) do{if((*(e))->ExceptionCheck(e))return;}while(0)
#define jio_snprintf snprintf
#define malloc test_malloc
#define free test_free
void
''' + body + r'''
#undef malloc
#undef free
JNIEXPORT void JNICALL Java_JnuMessageCheck_run(JNIEnv *e,jclass cls,jstring value,jboolean deny){
 (void)cls;const char *message=value?(*e)->GetStringUTFChars(e,value,NULL):NULL;
 if(value&&!message)return;refuse=deny;
 JNU_ThrowByNameWithMessageAndLastError(e,"java/net/SocketException",message);
 if(message)(*e)->ReleaseStringUTFChars(e,value,message);
 assert(!live);
}
''')
java=w/'JnuMessageCheck.java';java.write_text('''
import java.net.SocketException;
public class JnuMessageCheck {
    static native void run(String message, boolean deny);
    public static void main(String[] args) {
        System.load(args[0]); boolean ps5=Boolean.parseBoolean(args[1]);
        for (String message : new String[]{null,"","getFlags() failed","x".repeat(252),"x".repeat(253),"x".repeat(300)}) {
            for (boolean deny : new boolean[]{false,true}) {
                boolean oom=deny && message!=null && !message.isEmpty() && (!ps5 || message.length()>252);
                try { run(message,deny); throw new AssertionError("No exception"); }
                catch (OutOfMemoryError error) { if(!oom) throw new AssertionError("Unexpected OOM",error); }
                catch (Throwable error) {
                    if(oom || !(error instanceof SocketException)) throw new AssertionError("Wrong exception",error);
                    String expected="Permission denied"+(message==null||message.isEmpty()?"":" ("+message+")");
                    if(!expected.equals(error.getMessage())) throw new AssertionError("Wrong detail: "+error.getMessage());
                }
            }
        }
        System.out.println("PASS: actual last-error body real JNI/-Xcheck:jni, PS5="+ps5+", native scratch refusal, null/empty/252/253 boundaries, exact SocketException/OOM and cleanup");
    }
}
''')
subprocess.run([str(jdk/'bin/javac'),str(java)],check=True)
for ps5 in [True,False]:
 lib=w/('ps5.dylib' if ps5 else 'desktop.dylib')
 subprocess.run(['clang','-std=c11','-Wall','-Wextra','-Werror','-fsanitize=undefined','-dynamiclib',*(['-D__PROSPERO__=1'] if ps5 else []),'-I'+str(jdk/'include'),'-I'+str(jdk/'include/darwin'),str(c),'-o',str(lib)],check=True)
 subprocess.run([str(jdk/'bin/java'),'-Xcheck:jni','-cp',str(w),'JnuMessageCheck',str(lib),str(ps5).lower()],check=True)
