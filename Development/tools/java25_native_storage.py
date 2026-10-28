#!/usr/bin/env python3
"""Opt-in genuine Zstd JNI and SQLite JDBC native builds, with explicit Java namespaces."""
from pathlib import Path
import argparse,subprocess,hashlib,json,urllib.request,zipfile,concurrent.futures,re,shutil
ROOT=Path(__file__).resolve().parents[1];LLVM=Path('/opt/homebrew/opt/llvm/bin');JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
PINS={'zstd':('https://github.com/luben/zstd-jni','b1ab612ca2777d6937f418933b5899132517dab3','com.github.luben.zstd'),'sqlite':('https://github.com/xerial/sqlite-jdbc','94c0ea142dccd729c9a56833704743d74602e58c','org.sqlite')}
SQLITE_URL='https://www.sqlite.org/2026/sqlite-amalgamation-3530200.zip'
SQLITE_SHA='8a310d0a16c7a90cacd4c884e70faa51c902afed2a89f63aaa0126ab83558a32'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def jni(s):return s.replace('_','_1').replace('.','_')
def build(component,namespace=None,host=False,source=None):
 repo,commit,original=PINS[component];namespace=namespace or original
 if not re.fullmatch(r'[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*',namespace):raise ValueError('Invalid Java namespace')
 cache=ROOT/'.tools/java25/native-storage';cache.mkdir(parents=True,exist_ok=True)
 source=Path(source).resolve()if source else cache/component
 if not source.exists():subprocess.run(['git','clone','--no-checkout',repo,str(source)],check=True)
 if subprocess.run(['git','-C',str(source),'cat-file','-e',commit],capture_output=True).returncode:subprocess.run(['git','-C',str(source),'fetch','--depth','1','origin',commit],check=True)
 out=ROOT/'build/java25/native-storage'/(component+'-'+namespace+('-host'if host else'-target'));out.mkdir(parents=True,exist_ok=True)
 src=out/'source';shutil.rmtree(src,ignore_errors=True);src.mkdir()
 archive=subprocess.check_output(['git','-C',str(source),'archive',commit]);tar=out/'source.tar';tar.write_bytes(archive);subprocess.run(['tar','-xf',str(tar),'-C',str(src)],check=True);tar.unlink()
 flags=['-std=c11','-O2','-fPIC','-fno-strict-aliasing','-fvisibility=hidden','-DNDEBUG']
 headers=JDK/'include'if host else ROOT/'.tools/java25/openjdk/build/ps5-bootstrap/support/modules_include/java.base'
 includes=[headers,headers/('darwin'if host else'freebsd')]
 if not host:flags+=['-target','x86_64-sie-ps5','-isysroot',str(ROOT/'.tools/native-sdk/ps5-payload-sdk'),'-fvisibility-nodllstorageclass=default','-mno-avx','-mno-avx2','-mno-fma','-fno-stack-protector']
 if component=='zstd':
  native=src/'src/main/native';includes+=[native,native/'common',native/'legacy'];flags+=['-DZSTD_MULTITHREAD=1','-DZSTD_LEGACY_SUPPORT=4','-DZSTD_TRACE=0']
  sources=sorted(native.glob('jni*.c'))+sum([sorted((native/d).glob('*.c'))for d in ['common','compress','decompress','dictBuilder','legacy']],[])
  for p in native.glob('jni*.c'):p.write_text(p.read_text().replace('Java_'+jni(original),'Java_'+jni(namespace)).replace(original.replace('.','/'),namespace.replace('.','/')))
 else:
  archive=cache/'sqlite-amalgamation-3530200.zip'
  if not archive.exists():archive.write_bytes(urllib.request.urlopen(SQLITE_URL).read())
  if sha(archive)!=SQLITE_SHA:raise ValueError('SQLite publisher archive checksum mismatch: '+sha(archive))
  with zipfile.ZipFile(archive)as z:
   for name in ['sqlite3.c','sqlite3.h']: (src/name).write_bytes(z.read('sqlite-amalgamation-3530200/'+name))
  wrapper=src/'src/main/java/org/sqlite/core/NativeDB.c';wrapper.write_text(wrapper.read_text().replace('#include "NativeDB.h"','#include <jni.h>').replace('Java_'+jni(original),'Java_'+jni(namespace)).replace(original.replace('.','/'),namespace.replace('.','/')).replace('return sqlite3_enable_load_extension(db, enable ? 1 : 0);','#ifdef SQLITE_OMIT_LOAD_EXTENSION\n    return enable ? SQLITE_ERROR : SQLITE_OK;\n#else\n    return sqlite3_enable_load_extension(db, enable ? 1 : 0);\n#endif'))
  includes+=[src];sources=[src/'sqlite3.c',wrapper];flags+=['-DSQLITE_THREADSAFE=1','-DSQLITE_OMIT_LOAD_EXTENSION=1','-DSQLITE_MAX_MMAP_SIZE=0','-DHAVE_USLEEP=1','-DSQLITE_ENABLE_COLUMN_METADATA=1','-DSQLITE_ENABLE_DESERIALIZE=1']
 objects=[]
 def compile_one(pair):
  i,p=pair;o=out/(str(i)+'.o');subprocess.run([str(LLVM/'clang'),*flags,*['-I'+str(d)for d in includes],'-c',str(p),'-o',str(o)],check=True);return o
 with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:objects=list(pool.map(compile_one,enumerate(sources)))
 if host:
  result=out/('lib'+component+'.dylib');subprocess.run([str(LLVM/'clang'),'-dynamiclib',*map(str,objects),'-o',str(result)],check=True)
 else:
  result=out/(component+'.o');subprocess.run(['/opt/homebrew/opt/lld/bin/ld.lld','-r',*map(str,objects),'-o',str(result)],check=True)
  symbols=subprocess.check_output([str(LLVM/'llvm-nm'),'--defined-only','--extern-only',str(result)],text=True);renames=out/'symbols.map'
  names=[line.split()[-1]for line in symbols.splitlines()if len(line.split())==3 and not line.split()[-1].startswith(('Java_','JNI_'))]
  renames.write_text(''.join(n+' java25_storage_'+component+'_'+n+'\n'for n in names));subprocess.run([str(LLVM/'llvm-objcopy'),'--redefine-syms='+str(renames),str(result)],check=True)
  sections=subprocess.check_output([str(LLVM/'llvm-readelf'),'-SW',str(result)],text=True);assert '.init_array'not in sections and '.ctors'not in sections
 audit={'component':component,'repository':repo,'commit':commit,'java_namespace':namespace,'host':host,'output_sha256':sha(result),'source_sha256':{str(p.relative_to(src)):sha(p)for p in sources},'flags':flags,'sqlite_archive_sha256':SQLITE_SHA if component=='sqlite'else None,'console':'pending;native build is not a console pass'}
 (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');return result
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('component',choices=PINS);p.add_argument('--namespace');p.add_argument('--host',action='store_true');p.add_argument('--source',type=Path);a=p.parse_args();print(build(a.component,a.namespace,a.host,a.source))
