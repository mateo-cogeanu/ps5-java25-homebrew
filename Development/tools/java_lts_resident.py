#!/usr/bin/env python3
"""Prepare isolated genuine Java17/21 core resident objects for the startup probe."""
import argparse
import json
from pathlib import Path
import re
import subprocess

from java_lts import ROOT, sha, tool
from java25_embedded_hotspot import embed_hotspot

GROUPS = ('java', 'zip', 'jimage', 'net', 'nio', 'verify')


def registry(libraries, *, major=17, asm_prefix=''):
    if major not in (17, 21):
        raise ValueError('Unsupported runtime major')
    if asm_prefix not in ('', '_'):
        raise ValueError('Unsupported object-format symbol prefix')
    declarations, tables, loaders, rows = [], [], [], []
    count = 0
    for name, symbols in libraries.items():
        entries = []
        original_load = None
        for symbol in sorted(symbols):
            if not re.fullmatch('[A-Za-z_][A-Za-z0-9_]*', symbol) or symbol.startswith('_Z'):
                continue
            if name == 'jvm' and not symbol.startswith(('JNI_', 'JVM_', 'Java_', 'jio_')):
                continue
            label = symbol
            if symbol.startswith('lts_' + name + '_JNI_On'):
                label = symbol.removeprefix('lts_' + name + '_')
            if symbol.startswith('lts_java_jio_'):
                label = symbol.removeprefix('lts_java_')
            alias = 'lts_symbol_' + str(count)
            count += 1
            declarations.append('extern "C" void ' + alias + '() __asm__("' + asm_prefix + symbol + '");')
            entries.append('{"' + label + '", reinterpret_cast<void *>(&' + alias + ')}')
            if label == 'JNI_OnLoad':
                original_load = alias
        if name in GROUPS:
            # Standard OpenJDK static-library discovery. Run each real JNI_OnLoad
            # when present; statically linked groups without one require only JNI1.8.
            expression = ('reinterpret_cast<int (*)(void*,void*)>(&' + original_load + ')(vm, reserved)'
                          if original_load else '0x00010008')
            loader = 'lts_builtin_load_' + name
            loaders.append('extern "C" int ' + loader + '(void*vm,void*reserved){int v=' + expression +
                           ';return v<0?v:(v<0x00010008?0x00010008:v);}')
            entries.append('{"JNI_OnLoad_' + name + '",reinterpret_cast<void*>(&' + loader + ')}')
        tables.append('static const Symbol symbols_' + name + '[]={' + ',\n'.join(entries) + '};')
        rows.append('{"lib' + name + '.so",symbols_' + name + ',sizeof(symbols_' + name + ')/sizeof(Symbol)}')
    return r'''/* Generated solely from the matched target object's real symbols. */
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <dlfcn.h>
#include <arpa/inet.h>
''' + '\n'.join(declarations) + r'''
struct Symbol{const char*name;void*address;};
struct Library{const char*name;const Symbol*symbols;size_t count;};
''' + '\n'.join(loaders + tables) + '\nstatic const Library libraries[]={' + ',\n'.join(rows) + r'''};
static thread_local const char*last_error=nullptr;
static void*find_symbol(const Library&lib,const char*name){
 for(size_t i=0;i<lib.count;++i)if(std::strcmp(name,lib.symbols[i].name)==0)return lib.symbols[i].address;
 return nullptr;
}
extern "C" void*__dlopen(const char*path,int){
 if(!path)return const_cast<Library*>(&libraries[0]);
 const char*slash=std::strrchr(path,'/');const char*name=slash?slash+1:path;
 for(auto&lib:libraries)if(std::strcmp(name,lib.name)==0)return const_cast<Library*>(&lib);
 last_error="Not a resident Java17 core library";return nullptr;
}
extern "C" void*__dlsym(void*handle,const char*name){
 if(!name){last_error="Missing symbol name";return nullptr;}
 if(handle==RTLD_DEFAULT||handle==RTLD_SELF||handle==&libraries[0]){
  if(std::strcmp(name,"inet_pton")==0)return reinterpret_cast<void*>(&inet_pton);
  for(auto&lib:libraries)if(void*p=find_symbol(lib,name))return p;
 }else{
  for(auto&lib:libraries)if(handle==&lib)if(void*p=find_symbol(lib,name))return p;
 }
 last_error="No such export in the selected resident core group";return nullptr;
}
extern "C" int __dlclose(void*handle){
 for(auto&lib:libraries)if(handle==&lib)return 0;
 last_error="Unknown resident core handle";return -1;
}
extern "C" char*__dlerror(){const char*e=last_error;last_error=nullptr;return const_cast<char*>(e);}
extern "C" char __lts_jvm_text_start[],__lts_jvm_text_end[];
extern "C" int __dladdr(const void*address,Dl_info*info){
 if(!address||!info)return 0;
 uintptr_t value=reinterpret_cast<uintptr_t>(address);
 if(value<reinterpret_cast<uintptr_t>(__lts_jvm_text_start)||value>=reinterpret_cast<uintptr_t>(__lts_jvm_text_end))return 0;
 *info={};info->dli_fname="/app0/assets/java17/lib/server/libjvm.so";
 info->dli_fbase=__lts_jvm_text_start;return 1;
}
'''.replace('Java17', 'Java' + str(major)).replace('/java17/', '/java' + str(major) + '/')


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--llvm-home', required=True, type=Path)
    p.add_argument('--lld', required=True, type=Path)
    p.add_argument('--output-dir', required=True, type=Path)
    p.add_argument('--major', type=int, choices=(17, 21), default=17)
    a = p.parse_args()
    llvm = a.llvm_home.resolve()
    output = a.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=True)
    build = ROOT / ('.tools/java' + str(a.major) + '/openjdk/build/ps5-bootstrap')
    sdk = ROOT / '.tools/native-sdk/ps5-payload-sdk'
    groups = {}
    inputs = {}
    objects = sorted((build / 'hotspot/variant-server/libjvm/objs').glob('*.o'))
    vm = output / 'embedded-jvm.o'
    embed_hotspot(objects, vm, llvm / 'bin', a.lld.absolute())
    inputs['jvm'] = {str(f.relative_to(build)): sha(f) for f in objects}
    # Bound dladdr ownership to this actual VM code range in the final title.
    sections = subprocess.check_output([str(tool(llvm, 'llvm-readelf')), '-SW', str(vm)], text=True)
    names = sorted(set(re.findall(r'\]\s+(\.text(?:\.[^\s]+)?)\s', sections)))
    response = output / 'jvm-text-sections.rsp'
    response.write_text('\n'.join(json.dumps(arg) for name in names
                                  for arg in ('--rename-section', name + '=.text.lts_jvm' + name)) + '\n' + json.dumps(str(vm)) + '\n')
    subprocess.run([str(tool(llvm, 'llvm-objcopy')), '@' + str(response)], check=True)
    groups['jvm'] = vm
    for name in GROUPS:
        objects = sorted((build / 'support/native/java.base' / ('lib' + name)).glob('*.o'))
        if name == 'java':
            objects += sorted((build / 'support/native/java.base/libfdlibm').glob('*.o'))
        if not objects:
            raise ValueError('Missing genuine target core objects: ' + name)
        merged = output / ('embedded-' + name + '.o')
        response = merged.with_suffix('.rsp')
        response.write_text('\n'.join(json.dumps(str(f)) for f in objects) + '\n')
        subprocess.run([str(a.lld.absolute()), '-r', '@' + str(response), '-o', str(merged)], check=True)
        text = subprocess.check_output([str(tool(llvm, 'llvm-nm')), '--defined-only', '--extern-only', str(merged)], text=True)
        renames = {symbol: 'lts_' + name + '_' + symbol for symbol in ('JNI_OnLoad', 'JNI_OnUnload')
                   if re.search(r'\b' + symbol + '$', text, re.M)}
        if name == 'java':
            renames.update({n: 'lts_java_' + n for n in ('jio_snprintf', 'jio_fprintf')
                            if re.search(r'\b' + n + '$', text, re.M)})
        sections = subprocess.check_output([str(tool(llvm, 'llvm-readelf')), '-SW', str(merged)], text=True)
        initializers = sorted(set(re.findall(r'\]\s+(\.(?:init_array|ctors)\S*)\s', sections)))
        args = [arg for before, after in renames.items() for arg in ('--redefine-sym', before + '=' + after)]
        args += [arg for n in initializers for arg in ('--rename-section', n + '=.data.rel.ro.jvm_init_array.' + name + n)]
        if args:
            subprocess.run([str(tool(llvm, 'llvm-objcopy')), *args, str(merged)], check=True)
        inputs[name] = {str(f.relative_to(build)): sha(f) for f in objects}
        groups[name] = merged
    exports = {}
    for name, obj in groups.items():
        text = subprocess.check_output([str(tool(llvm, 'llvm-nm')), '--defined-only', '--extern-only', str(obj)], text=True)
        exports[name] = [line.split()[-1] for line in text.splitlines() if len(line.split()) >= 3]
    source = output / 'builtin-libraries.cpp'
    source.write_text(registry(exports, major=a.major))
    obj = output / 'builtin-libraries.o'
    subprocess.run([str(tool(llvm, 'clang++')), '-target', 'x86_64-sie-ps5', '-std=c++20', '-O2',
                    '-fvisibility-nodllstorageclass=default', '-isysroot', str(sdk),
                    '-isystem', str(sdk / 'target/include/c++/v1'), '-isystem', str(sdk / 'target/include'),
                    '-femulated-tls', '-fno-stack-protector', '-fno-plt', '-fno-exceptions', '-fno-rtti',
                    '-c', str(source), '-o', str(obj)], check=True)
    (output / 'link-inputs.json').write_text(json.dumps([str(p) for p in groups.values()] + [str(obj)], indent=2) + '\n')
    (output / 'audit.json').write_text(json.dumps({'major': a.major, 'groupObjectsSha256': {n: sha(p) for n, p in groups.items()},
        'inputObjectsSha256': inputs, 'registrySourceSha256': sha(source), 'registryObjectSha256': sha(obj),
        'console': 'NOT RUN', 'scope': 'Matched' + str(a.major) + ' core groups only; no arbitrary ELF loading or Java25 registry replacement'}, indent=2) + '\n')
    print('Built matched Java' + str(a.major) + ' resident core objects and generated exact-export lookup')


if __name__ == '__main__':
    main()
