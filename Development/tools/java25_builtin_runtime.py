#!/usr/bin/env python3
"""Generate a lookup table from actual compiled core-library symbols.

This is an embedded-library adapter, not a loader for arbitrary ELF modules.
"""
from pathlib import Path
import json
import subprocess
import re
import argparse
import hashlib
from java25_resident_libraries import read_libraries, read_aliases

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '.tools/java25/openjdk/build/ps5-bootstrap'
WORK = ROOT / 'build/java25'
SDK = ROOT / '.tools/native-sdk/ps5-payload-sdk'
LLVM = Path(subprocess.check_output(['/opt/homebrew/opt/llvm/bin/llvm-config','--bindir'],text=True).strip())
LLD = Path(subprocess.check_output(['brew','--prefix','lld'],text=True).strip())/'bin/ld.lld'
LIBRARIES = ['java','zip','jimage','net','nio','verify']

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--management",action="store_true",help="Embed the target java.management native library")
    parser.add_argument("--jni-fixture",action="store_true",help="Include real dependency-probe JNI test library")
    parser.add_argument("--external-libraries",type=Path,help="Consumer-owned named ELF object groups to embed; no arbitrary ELF loading")
    parser.add_argument("--imageio",action="store_true",help="Embed genuine headless ImageIO raster/Disposer and LCMS subset")
    parser.add_argument("--library-alias",action="append",default=[],help="Explicit resident alias=library; same symbols and ownership, no new loader")
    args=parser.parse_args()
    if args.imageio:
        from java25_imageio import build
        build()
    external=read_libraries(args.external_libraries,LIBRARIES+["jvm","management","ps5probe","awt","lcms"]) if args.external_libraries else []
    declarations=[]; tables=[]; mapped=[]; links=[]; alias_index=0; builtin_loaders=[]
    libraries=[('jvm',WORK/'embedded-jvm.o')]
    resident=LIBRARIES+(['management'] if args.management else [])+(['awt','lcms'] if args.imageio else [])
    for name in resident:
        module='java.management' if name=='management' else 'java.base'
        objects=[WORK/'imageio-target'/('lib'+name+'.o')] if name in ('awt','lcms') else sorted((BUILD/'support/native'/module/('lib'+name)).glob('*.o'))
        if not objects: raise SystemExit('Missing built native objects: '+name)
        rsp=WORK/(name+'-objects.rsp')
        rsp.write_text('\n'.join(json.dumps(str(p)) for p in objects)+'\n')
        merged=WORK/('embedded-'+name+'.o')
        subprocess.run([str(LLD),'-r','@'+str(rsp),'-o',str(merged)],check=True)
        symbols=subprocess.check_output([str(LLVM/'llvm-nm'),'--defined-only','--extern-only',str(merged)],text=True)
        # Separate each library's load/unload entry point while preserving
        # its original spelling in that library's symbol table.
        renames=[]
        for entry in ['JNI_OnLoad','JNI_OnUnload']:
            if re.search(r'\b'+entry+r'$',symbols,re.M):
                renames+=['--redefine-sym',entry+'=ps5_'+name+'_'+entry]
        if name=='java':
            # libjava and libjvm each define these formatting helpers in
            # their separate desktop modules; keep libjava's definitions local.
            for entry in ['jio_snprintf','jio_fprintf']:
                renames+=['--redefine-sym',entry+'=ps5_java_'+entry]
        if renames: subprocess.run([str(LLVM/'llvm-objcopy'),*renames,str(merged)],check=True)
        sections=subprocess.check_output([str(LLVM/'llvm-readelf'),'-SW',str(merged)],text=True)
        constructor_sections=sorted(set(re.findall(r'\]\s+(\.(?:init_array|ctors)\S*)\s',sections)))
        if constructor_sections:
            options=[]
            for section in constructor_sections:
                options+=['--rename-section',section+'=.data.rel.ro.jvm_init_array.'+name+section]
            subprocess.run([str(LLVM/'llvm-objcopy'),*options,str(merged)],check=True)
        libraries.append((name,merged));links.append(str(merged))
    if args.jni_fixture:
        headers=BUILD/'support/modules_include/java.base'
        fixture=WORK/'dependency-jni.o'
        subprocess.run([str(LLVM/'clang++'),'-target','x86_64-sie-ps5','-std=c++20','-O2','-fPIC',
            '-DPS5_EMBEDDED_FIXTURE','-fvisibility-nodllstorageclass=default','-isysroot',str(SDK),
            '-I'+str(headers),'-I'+str(headers/'freebsd'),'-c',str(ROOT/'java25/probe/dependency_jni.cpp'),'-o',str(fixture)],check=True)
        libraries.append(('ps5probe',fixture));links.append(str(fixture))
    external_names=set();external_audit=[]
    for name,objects in external:
        merged=WORK/('embedded-'+name+'.o')
        rsp=WORK/(name+'-objects.rsp');rsp.write_text('\n'.join(json.dumps(str(p))for p in objects)+'\n')
        subprocess.run([str(LLD),'-r','@'+str(rsp),'-o',str(merged)],check=True)
        sections=subprocess.check_output([str(LLVM/'llvm-readelf'),'-SW',str(merged)],text=True)
        if re.search(r'\]\s+\.(?:init_array|ctors)(?:\s|\.)',sections):
            raise SystemExit('External resident library constructors require an explicit lifecycle port: '+name)
        symbols=subprocess.check_output([str(LLVM/'llvm-nm'),'--defined-only','--extern-only',str(merged)],text=True)
        renames=[]
        for entry in ['JNI_OnLoad','JNI_OnUnload']:
            if re.search(r'\b'+entry+r'$',symbols,re.M):
                renames+=['--redefine-sym',entry+'=ps5_'+name+'_'+entry]
        if renames:subprocess.run([str(LLVM/'llvm-objcopy'),*renames,str(merged)],check=True)
        libraries.append((name,merged));links.append(str(merged));external_names.add(name)
        external_audit.append({'name':name,'objects_sha256':[hashlib.sha256(p.read_bytes()).hexdigest()for p in objects],'constructors':'none; nontrivial constructors rejected'})
    aliases=read_aliases(args.library_alias,{name for name,_ in libraries})
    for name, merged in libraries:
        symbols=subprocess.check_output([str(LLVM/'llvm-nm'),'--defined-only','--extern-only',str(merged)],text=True)
        entries=[]
        for line in symbols.splitlines():
            fields=line.split()
            if len(fields)!=3 or fields[1] not in ('T','W'): continue
            symbol=fields[2]
            if symbol.startswith('_Z') or '.' in symbol: continue
            if name=='jvm' and not symbol.startswith(('JNI_','JVM_','Java_','jio_')): continue
            if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*',symbol): continue
            display=symbol
            if symbol.startswith('ps5_'+name+'_JNI_On'): display=symbol[len('ps5_'+name+'_'):]
            if symbol.startswith('ps5_java_jio_'): display=symbol[len('ps5_java_'):]
            alias='embedded_symbol_'+str(alias_index);alias_index+=1
            declarations.append('extern "C" void '+alias+'() __asm__("'+symbol+'");')
            entries.append('{"'+display+'", reinterpret_cast<void *>(&'+alias+')}')
        if name in resident or name=='ps5probe' or name in external_names:
            # Advertise known resident libraries through OpenJDK's standard
            # JNI_OnLoad_<name> discovery. This avoids File.exists/canonical
            # path checks before their filesystem natives are registered.
            original = next((entry for entry in entries if entry.startswith('{"JNI_OnLoad",')), None)
            call = '0x00010008'
            if original:
                alias = re.search(r'&([A-Za-z_0-9]+)', original).group(1)
                call = 'reinterpret_cast<int (*)(void *, void *)>(&'+alias+')(vm, reserved)'
            loader = 'ps5_builtin_load_'+name
            builtin_loaders.append('extern "C" int '+loader+'(void *vm, void *reserved) { '
                'int version='+call+'; return version < 0 ? version : '
                '(version < 0x00010008 ? 0x00010008 : version); }')
            entries.append('{"JNI_OnLoad_'+name+'", reinterpret_cast<void *>(&'+loader+')}')
            for alias,target in aliases.items():
                if target==name:entries.append('{"JNI_OnLoad_'+alias+'", reinterpret_cast<void *>(&'+loader+')}')
        tables.append('static const Symbol symbols_'+name+'[]={\n'+',\n'.join(entries)+'\n};')
        mapped.append('{"lib'+name+'.so", symbols_'+name+', sizeof(symbols_'+name+')/sizeof(Symbol)}')
        for alias,target in aliases.items():
            if target==name:mapped.append('{"lib'+alias+'.so", symbols_'+name+', sizeof(symbols_'+name+')/sizeof(Symbol)}')
    output='''/* Generated from real target native symbols; do not edit. */
#include <cstddef>
#include <cstring>
#include <dlfcn.h>
#include <arpa/inet.h>
'''+ '\n'.join(declarations)+'\n'+'\n'.join(builtin_loaders)+'''
struct Symbol { const char *name; void *address; };
struct Library { const char *name; const Symbol *symbols; size_t count; };
'''+ '\n'.join(tables)+'\nstatic const Library libraries[]={\n'+',\n'.join(mapped)+'''\n};
static thread_local const char *last_error=nullptr;
static void *find_symbol(const Library &lib,const char *name) {
 for(size_t i=0;i<lib.count;++i) if(std::strcmp(name,lib.symbols[i].name)==0) return lib.symbols[i].address;
 return nullptr;
}
extern "C" void *__dlopen(const char *path,int) {
 if(!path) return const_cast<Library *>(&libraries[0]);
 auto *slash=std::strrchr(path,'/');const char *name=slash?slash+1:path;
 for(auto &lib:libraries) if(std::strcmp(name,lib.name)==0) return const_cast<Library *>(&lib);
 last_error="Library is not part of the embedded PS5 core runtime";return nullptr;
}
extern "C" void *__dlsym(void *handle,const char *name) {
 if(!name) {last_error="Missing symbol name";return nullptr;}
 if(handle==RTLD_DEFAULT || handle==RTLD_SELF || handle==&libraries[0]) {
  // OpenJDK probes this platform API by name after creating an IPv6 socket.
  if(std::strcmp(name,"inet_pton")==0) return reinterpret_cast<void *>(&inet_pton);
  for(auto &lib:libraries) if(void *p=find_symbol(lib,name)) return p;
 } else {
  for(auto &lib:libraries) if(handle==&lib) if(void *p=find_symbol(lib,name)) return p;
 }
 last_error="Symbol is not exported by the embedded core library";return nullptr;
}
extern "C" int __dlclose(void *handle) {
 for(auto &lib:libraries) if(handle==&lib) return 0; // embedded code remains resident
 last_error="Unknown embedded library handle";return -1;
}
extern "C" char *__dlerror() {auto *error=last_error;last_error=nullptr;return const_cast<char *>(error);}
extern "C" int __dladdr(const void *address,Dl_info *info) {
 if(!address||!info) return 0;
 // This application is one resident native image. HotSpot needs a stable
 // packaged location to derive java.home for its embedded core libraries.
 *info={};info->dli_fname="/app0/assets/java25/lib/server/libjvm.so";return 1;
}
'''
    target=WORK/'builtin-libraries.cpp';target.write_text(output)
    obj=WORK/'builtin-libraries.o'
    subprocess.run([str(LLVM/'clang++'),'-target','x86_64-sie-ps5','-std=c++20','-O2',
        '-fvisibility-nodllstorageclass=default','-isysroot',str(SDK),'-isystem',str(SDK/'target/include/c++/v1'),
        '-isystem',str(SDK/'target/include'),'-femulated-tls','-fno-stack-protector','-fno-plt','-fno-exceptions','-fno-rtti',
        '-c',str(target),'-o',str(obj)],check=True)
    links.append(str(obj))
    (WORK/'builtin-link-inputs.json').write_text(json.dumps(links,indent=2)+'\n')
    (WORK/'builtin-resident-audit.json').write_text(json.dumps({'external_resident_libraries':external_audit,'library_aliases':aliases,'scope':'Build-time resident objects only; no arbitrary ELF loader'},indent=2)+'\n')
    print('Generated embedded lookup table:',alias_index,'real function addresses')

if __name__=='__main__':main()
