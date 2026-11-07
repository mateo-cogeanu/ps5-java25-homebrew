#!/usr/bin/env python3
"""Actual target symbol scoping, generated tables and NativeLibraries JNI load body.

Requires an already built runtime. Host OS loading is an injected boundary;
this test does not execute the PS5 VM. All namespace options are default-off.
"""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import struct
import tempfile

from java25_resident_libraries import read_symbol_prefixes, symbol_prefix_map, read_scoped_handle_groups

ROOT = Path(__file__).resolve().parents[1]


def rejects(action):
    try:
        action()
    except ValueError:
        return
    raise AssertionError('Invalid namespace accepted')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--java-home', type=Path, required=True)
    parser.add_argument('--llvm-home', type=Path, required=True)
    parser.add_argument('--cc', default='clang')
    parser.add_argument('--cxx', default='clang++')
    args = parser.parse_args()
    jdk, llvm = args.java_home.resolve(), args.llvm_home.resolve() / 'bin'
    assert read_symbol_prefixes([], {'consumer'}) == {}
    assert read_scoped_handle_groups([], {'consumer'}) == set()
    assert read_scoped_handle_groups(['consumer'], {'consumer'}) == {'consumer'}
    for values in (['missing'], ['java'], ['consumer', 'consumer'], ['ConsumerAlias'], ['../consumer']):
        rejects(lambda: read_scoped_handle_groups(values, {'consumer'}))
    assert read_symbol_prefixes(['consumer=isolated_'], {'consumer'}) == {'consumer': 'isolated_'}
    for values in (['missing=ok_'], ['java=ok_'], ['consumer=x'], ['consumer=../x_'],
                   ['consumer=JNI_OnLoad'], ['consumer=bad;code_'], ['consumer=1x_'],
                   ['consumer=a_', 'consumer=b_'], ['consumer=a_', 'other=a_']):
        rejects(lambda: read_symbol_prefixes(values, {'consumer', 'other'}))
    assert symbol_prefix_map('000 T call\n000 B state\n000 V weak_data\n         U shared\n', 'p_') == {
        'call': 'p_call', 'state': 'p_state', 'weak_data': 'p_weak_data'}
    rejects(lambda: symbol_prefix_map('000 T bad-name', 'p_'))
    with tempfile.TemporaryDirectory(prefix='ps5-resident-namespace-') as folder:
        work = Path(folder)
        objects = []
        for name, value in (('plain_fixture', 17), ('scoped_fixture', 23)):
            source = work / (name + '.c')
            source.write_text('int state=' + str(value) + ';\n__thread int tlsstate;\n'
                'int Java_Scoped_value(void){return state+tlsstate;}\n'
                'int alternate(void){return state+1;}\n'
                'int JNI_OnLoad(void *vm,void *reserved){return 0x00010008;}\n')
            obj = source.with_suffix('.o')
            subprocess.run([str(llvm / 'clang'), '-target', 'x86_64-sie-ps5', '-fPIC', '-femulated-tls',
                            '-c', str(source), '-o', str(obj)], check=True)
            objects.append({'name': name, 'objects': [str(obj)]})
        manifest = work / 'libraries.json'
        manifest.write_text(json.dumps(objects))
        subprocess.run(['python3', str(ROOT / 'tools/java25_builtin_runtime.py'),
                        '--external-libraries', str(manifest), '--library-symbol-prefix',
                        'scoped_fixture=isolated_', '--library-alias', 'ScopedAlias=scoped_fixture'], check=True)
        build = ROOT / 'build/java25'
        plain, scoped = (build / ('embedded-' + n + '.o') for n in ('plain_fixture', 'scoped_fixture'))
        # Real target relocatable objects with originally colliding code AND data
        # now link together; internal references must follow their renamed data.
        subprocess.run([str(llvm / 'ld.lld') if (llvm / 'ld.lld').exists() else 'ld.lld',
                        '-r', str(plain), str(scoped), '-o', str(work / 'both.o')], check=True)
        names = subprocess.check_output([str(llvm / 'llvm-nm'), '--defined-only', str(scoped)], text=True)
        assert 'isolated_Java_Scoped_value' in names and 'isolated_state' in names
        assert 'isolated___emutls_v.tlsstate' in names
        assert not re.search(r'\b(?:T|B|D) (?:Java_Scoped_value|state)$', names, re.M)
        undefined = subprocess.check_output([str(llvm / 'llvm-nm'), '-u', str(scoped)], text=True)
        assert not re.search(r'\bstate$', undefined, re.M)
        def allocated(path):
            data = Path(path).read_bytes()
            offset = struct.unpack_from('<Q', data, 40)[0]
            size, count, strings = struct.unpack_from('<HHH', data, 58)
            sections = [struct.unpack_from('<IIQQQQIIQQ', data, offset + i * size) for i in range(count)]
            table = sections[strings]
            names = data[table[4]:table[4] + table[5]]
            return {names[s[0]:].split(b'\0', 1)[0]: (s[5], data[s[4]:s[4] + s[5]] if s[1] != 8 else b'')
                    for s in sections if s[2] & 2}
        # Compare actual objcopy input/output, excluding symbol/relocation tables
        # which necessarily change. lld's preceding merge may alter unwind layout.
        renamed = work / 'renamed.o'
        subprocess.run([str(llvm / 'llvm-objcopy'), '--redefine-syms=' + str(build / 'scoped_fixture-symbol-prefix.txt'),
                        objects[1]['objects'][0], str(renamed)], check=True)
        assert allocated(objects[1]['objects'][0]) == allocated(renamed)
        generated = (build / 'builtin-libraries.cpp').read_text()
        assert 'JVM_PS5ScopedBuiltinHandle' in generated
        def mock(match):
            alias, symbol = match.groups()
            if symbol.endswith('_JNI_OnLoad'):
                return 'extern "C" int ' + alias + '(void*,void*){++loads;return load_version;}'
            if symbol == 'Java_Scoped_value':
                return 'extern "C" int ' + alias + '(){return 17;}'
            if symbol == 'isolated_Java_Scoped_value':
                return 'extern "C" int ' + alias + '(){return 23;}'
            return 'extern "C" void ' + alias + '(){}'
        generated = re.sub(r'extern "C" void (embedded_symbol_\d+)\(\) __asm__\("([^"]+)"\);', mock, generated)
        generated = '#define RTLD_SELF ((void*)-3)\n#include <cassert>\nstatic int loads=0,load_version=0x10008;\n' + generated
        generated += r'''
int main(){
 void *plain=__dlopen("libplain_fixture.so",0),*scoped=__dlopen("libscoped_fixture.so",0);
 assert(plain&&scoped&&plain!=scoped);
 assert(!JVM_PS5ScopedBuiltinHandle(nullptr));
 assert(!JVM_PS5ScopedBuiltinHandle("plain_fixture"));
 assert(!JVM_PS5ScopedBuiltinHandle("missing"));
 assert(JVM_PS5ScopedBuiltinHandle("scoped_fixture")==scoped);
 assert(JVM_PS5ScopedBuiltinHandle("ScopedAlias")==__dlopen("libScopedAlias.so",0));
 assert(reinterpret_cast<int(*)()>(__dlsym(plain,"Java_Scoped_value"))()==17);
 assert(reinterpret_cast<int(*)()>(__dlsym(scoped,"Java_Scoped_value"))()==23);
 assert(reinterpret_cast<int(*)()>(__dlsym(__dlopen(nullptr,0),"Java_Scoped_value"))()==17);
 assert(!__dlsym(scoped,"isolated_Java_Scoped_value"));
 assert(!__dlopen("libunknown.so",0));
 auto load=reinterpret_cast<int(*)(void*,void*)>(__dlsym(__dlopen(nullptr,0),"JNI_OnLoad_scoped_fixture"));
 assert(load&&load(nullptr,nullptr)==0x10008&&loads==1);
 load_version=-1;assert(load(nullptr,nullptr)==-1&&loads==2);
 assert(__dlclose(scoped)==0);
}
'''
        source = work / 'table.cpp'
        source.write_text(generated)
        subprocess.run([args.cxx, '-std=c++20', '-fsanitize=address,undefined',
                        str(source), '-o', str(work / 'table')], check=True)
        subprocess.run([str(work / 'table')], check=True)
        # A second selected library must not turn JNI lookup into process lookup
        # merely because its actual definitions do not require a namespace.
        subprocess.run(['python3', str(ROOT / 'tools/java25_builtin_runtime.py'),
                        '--external-libraries', str(manifest), '--library-symbol-prefix',
                        'scoped_fixture=isolated_', '--library-alias', 'ScopedAlias=scoped_fixture',
                        '--library-scoped-handle', 'plain_fixture',
                        '--library-alias', 'PlainAlias=plain_fixture'], check=True)
        checked = (build / 'builtin-libraries.cpp').read_text()
        checked = re.sub(r'extern "C" void (embedded_symbol_\d+)\(\) __asm__\("([^"]+)"\);', mock, checked)
        checks = generated[generated.index('int main(){'):].replace(
            'assert(!JVM_PS5ScopedBuiltinHandle("plain_fixture"));',
            'assert(JVM_PS5ScopedBuiltinHandle("plain_fixture")==plain);\n'
            'assert(JVM_PS5ScopedBuiltinHandle("PlainAlias")==__dlopen("libPlainAlias.so",0));\n'
            'assert(!__dlsym(plain,"JNI_OnLoad_scoped_fixture"));')
        source.write_text('#define RTLD_SELF ((void*)-3)\n#include <cassert>\n'
                          'static int loads=0,load_version=0x10008;\n' + checked + checks)
        subprocess.run([args.cxx, '-std=c++20', '-fsanitize=address,undefined',
                        str(source), '-o', str(work / 'table')], check=True)
        subprocess.run([str(work / 'table')], check=True)
        assert json.loads((build / 'builtin-resident-audit.json').read_text())['library_scoped_handles'] == ['plain_fixture']
        subprocess.run(['python3', str(ROOT / 'tools/java25_builtin_runtime.py'),
                        '--external-libraries', str(manifest),
                        '--library-scoped-handle', 'plain_fixture'], check=True)
        checked = (build / 'builtin-libraries.cpp').read_text()
        checked = re.sub(r'extern "C" void (embedded_symbol_\d+)\(\) __asm__\("([^"]+)"\);', mock, checked)
        source.write_text('#define RTLD_SELF ((void*)-3)\n#include <cassert>\n'
                          'static int loads=0,load_version=0x10008;\n' + checked + r'''
int main(){
 void *plain=__dlopen("libplain_fixture.so",0);
 assert(JVM_PS5ScopedBuiltinHandle("plain_fixture")==plain);
 assert(!JVM_PS5ScopedBuiltinHandle("scoped_fixture"));
 assert(!__dlsym(plain,"JNI_OnLoad_scoped_fixture"));
 assert(__dlsym(__dlopen(nullptr,0),"JNI_OnLoad_scoped_fixture"));
}
''')
        subprocess.run([args.cxx, '-std=c++20', '-fsanitize=address,undefined',
                        str(source), '-o', str(work / 'table')], check=True)
        subprocess.run([str(work / 'table')], check=True)
        check_load_body(args, work)
    print('PASS namespaces: real target code/data renames, collision-free link, unchanged section bytes, '
          'actual generated host tables/hooks/aliases/refusals; actual JNI load body scoped/default/error cases')


def check_load_body(args, work):
    source = (ROOT / '.tools/java25/openjdk/src/java.base/share/native/libjava/NativeLibraries.c').read_text()
    a = source.index('static void *findJniFunction(')
    find = source[a:source.index('\n/*', a)]
    a = source.index('JNIEXPORT jboolean JNICALL\nJava_jdk_internal_loader_NativeLibraries_load')
    load = source[a:source.index('\n/*', a)].replace('Java_jdk_internal_loader_NativeLibraries_load', 'Java_ScopedBuiltinCheck_load')
    assert 'JVM_PS5ScopedBuiltinHandle(cname)' in load
    bridge = r'''
#include <jni.h>
#include <stdint.h>
#include <stdlib.h>
#include <stdio.h>
#include <string.h>
#include <assert.h>
typedef jint (JNICALL *JNI_OnLoad_t)(JavaVM*,void*);
static jfieldID handleID,jniVersionID;
static void *procHandle=(void*)1;static int mode,unloads,scoped_calls;
static int initIDs(JNIEnv*e){jclass c=(*e)->FindClass(e,"ScopedBuiltinCheck$Library");if(!c)return 0;handleID=(*e)->GetFieldID(e,c,"handle","J");jniVersionID=(*e)->GetFieldID(e,c,"jniVersion","I");(*e)->DeleteLocalRef(e,c);return handleID&&jniVersionID;}
static void JNU_ThrowByName(JNIEnv*e,const char*n,const char*t){jclass c=(*e)->FindClass(e,n);if(c){(*e)->ThrowNew(e,c,t);(*e)->DeleteLocalRef(e,c);}}
static void JNU_ThrowOutOfMemoryError(JNIEnv*e,const char*t){JNU_ThrowByName(e,"java/lang/OutOfMemoryError",t);}
static const char*JNU_GetStringPlatformChars(JNIEnv*e,jstring s,void*x){(void)x;return (*e)->GetStringUTFChars(e,s,0);}
static void JNU_ReleaseStringPlatformChars(JNIEnv*e,jstring s,const char*p){(*e)->ReleaseStringUTFChars(e,s,p);}
static void*native_library_allocate(size_t n){return malloc(n);}
static void native_library_release(void*p){free(p);}
static void*JVM_LoadLibrary(const char*n,jboolean fail){(void)n;(void)fail;return (void*)3;}
static void JVM_UnloadLibrary(void*h){assert(h==(void*)3);++unloads;}
static int JVM_IsSupportedJNIVersion(int v){return v==JNI_VERSION_1_6||v==JNI_VERSION_1_8;}
static jint hook(JavaVM*vm,void*r){(void)r;if(mode==1)return JNI_ERR;if(mode==2)return JNI_VERSION_1_6;if(mode==3){JNIEnv*e=0;assert((*vm)->GetEnv(vm,(void**)&e,JNI_VERSION_1_8)==JNI_OK);JNU_ThrowByName(e,"java/lang/IllegalStateException","original hook failure");}return JNI_VERSION_1_8;}
static void*JVM_FindLibraryEntry(void*h,const char*n){assert(h==(void*)1||h==(void*)2||h==(void*)3);if(!strncmp(n,"JNI_OnLoad",10))return (void*)hook;return 0;}
#ifdef WITH_SCOPED_HOOK
static void*JVM_PS5ScopedBuiltinHandle(const char*n){++scoped_calls;return !strcmp(n,"scoped_fixture")?(void*)2:0;}
#else
static void*(*JVM_PS5ScopedBuiltinHandle)(const char*)=0;
#endif
#define jio_snprintf snprintf
#define ptr_to_jlong(p) ((jlong)(uintptr_t)(p))
''' + find + '\n' + load + r'''
JNIEXPORT void JNICALL Java_ScopedBuiltinCheck_config(JNIEnv*e,jclass c,jint m){(void)e;(void)c;mode=m;unloads=scoped_calls=0;}
JNIEXPORT jint JNICALL Java_ScopedBuiltinCheck_unloads(JNIEnv*e,jclass c){(void)e;(void)c;return unloads;}
'''
    java = work / 'ScopedBuiltinCheck.java'
    java.write_text(r'''
public class ScopedBuiltinCheck {
 static final class Library {long handle;int jniVersion;}
 static native boolean load(Library lib,String name,boolean builtin,boolean throwFailure);
 static native void config(int mode);static native int unloads();
 public static void main(String[]args){System.load(args[0]);boolean scoped=Boolean.parseBoolean(args[1]);
  config(0);Library lib=new Library();if(!load(lib,"plain_fixture",true,true)||lib.handle!=1||lib.jniVersion!=0x10008)throw new AssertionError("default handle");
  lib=new Library();if(!load(lib,"scoped_fixture",true,true)||lib.handle!=(scoped?2:1))throw new AssertionError("scoped handle");
  lib=new Library();if(!load(lib,"unknown",true,true)||lib.handle!=1)throw new AssertionError("unknown retains process boundary");
  lib=new Library();if(!load(lib,"external",false,true)||lib.handle!=3)throw new AssertionError("nonbuiltin unchanged");
  for(int mode:new int[]{1,2,3}){config(mode);lib=new Library();try{load(lib,"scoped_fixture",true,true);throw new AssertionError("failed hook accepted");}catch(UnsatisfiedLinkError|IllegalStateException expected){}if(lib.handle!=0||unloads()!=0)throw new AssertionError("builtin ownership");}
  config(1);lib=new Library();try{load(lib,"external",false,true);throw new AssertionError("external failure accepted");}catch(UnsatisfiedLinkError expected){}if(lib.handle!=0||unloads()!=1)throw new AssertionError("external cleanup");
  System.out.println("PASS actual JNI load body: default/scoped/nonbuiltin handles, version/hook/exception failures, field publication and cleanup");
 }
}
''')
    subprocess.run([str(args.java_home / 'bin/javac'), str(java)], check=True)
    native = work / 'bridge.c'
    native.write_text(bridge)
    import platform
    system = platform.system()
    for ps5, present in ((True, True), (True, False), (False, True)):
        library = work / ('load-' + str(ps5) + '-' + str(present) + ('.dylib' if system == 'Darwin' else '.so'))
        flags = ['-dynamiclib'] if system == 'Darwin' else ['-shared', '-fPIC']
        subprocess.run([args.cc, '-std=c11', '-O1', '-g', '-fsanitize=undefined', *flags,
                        *(['-D__PROSPERO__'] if ps5 else []), *(['-DWITH_SCOPED_HOOK'] if present else []),
                        '-I' + str(args.java_home / 'include'),
                        '-I' + str(args.java_home / 'include' / ('darwin' if system == 'Darwin' else 'linux')),
                        str(native), '-o', str(library)], check=True)
        subprocess.run([str(args.java_home / 'bin/java'), '--enable-native-access=ALL-UNNAMED', '-Xcheck:jni',
                        '-cp', str(work), 'ScopedBuiltinCheck', str(library), str(ps5 and present).lower()], check=True,
                       env={**os.environ, 'UBSAN_OPTIONS': 'halt_on_error=1'})


if __name__ == '__main__':
    main()
