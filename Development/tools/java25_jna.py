#!/usr/bin/env python3
"""Build opt-in genuine JNA dispatch JNI for a resident PS5 library group.

The target object leaves ffi symbols unresolved for an explicit compatible
resident libffi implementation. No default runtime library is changed.
"""
from pathlib import Path
import argparse,hashlib,json,re,subprocess,shutil,tarfile,io
ROOT=Path(__file__).resolve().parents[1]
REPOSITORY='https://github.com/java-native-access/jna.git'
COMMIT='1a91122853f6ab6f1fb2a4a284a6cf2ed8af0a4d'
JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
LLVM=Path('/opt/homebrew/opt/llvm/bin')
def build(ffi_include,host=False,source=None,offline=False):
 cache=Path(source).resolve()if source else ROOT/'.tools/jna-5.19.1'
 if not cache.exists():
  if offline:raise FileNotFoundError(cache)
  subprocess.run(['git','clone','--no-checkout',REPOSITORY,str(cache)],check=True)
 if subprocess.run(['git','-C',str(cache),'cat-file','-e',COMMIT],capture_output=True).returncode:
  if offline:raise FileNotFoundError('Pinned JNA source commit unavailable')
  subprocess.run(['git','-C',str(cache),'fetch','--depth','1',REPOSITORY,COMMIT],check=True)
 out=ROOT/'build/java25'/('jna-host'if host else'jna-target');out.mkdir(parents=True,exist_ok=True)
 src=out/'source';shutil.rmtree(src,ignore_errors=True);src.mkdir()
 archive=subprocess.check_output(['git','-C',str(cache),'archive',COMMIT])
 with tarfile.open(fileobj=io.BytesIO(archive))as tar:tar.extractall(src,filter='data')
 properties=dict(re.findall(r'<property name="([^"]+)" value="([^"]+)"', (src/'common.xml').read_text()))
 version='.'.join(properties['jni.'+part]for part in ['major','minor','revision']);checksum=properties['jni.md5']
 jna_version='.'.join(properties['jna.'+part]for part in ['major','minor','revision'])
 template=src/'src/com/sun/jna/Version.java';template.write_text(template.read_text().replace('VERSION = "TEMPLATE"','VERSION = "'+jna_version+'"').replace('VERSION_NATIVE = "TEMPLATE"','VERSION_NATIVE = "'+version+'"'))
 headers=out/'headers';classes=out/'classes';headers.mkdir(exist_ok=True);classes.mkdir(exist_ok=True)
 subprocess.run([str(JDK/'bin/javac'),'--release','8','-Xlint:-options','-h',str(headers),'-d',str(classes),'-sourcepath',str(src/'src'),str(src/'src/com/sun/jna/Native.java'),str(src/'src/com/sun/jna/Function.java')],check=True)
 sdk=ROOT/'.tools/native-sdk/ps5-payload-sdk';jni=JDK/'include'if host else ROOT/'.tools/java25/openjdk/build/ps5-bootstrap/support/modules_include/java.base'
 flags=['-O2','-fPIC','-fno-strict-aliasing','-DNO_JAWT','-DJNA_JNI_VERSION="'+version+'"','-DCHECKSUM="'+checksum+'"','-I'+str(headers),'-I'+str(ffi_include),'-I'+str(jni),'-I'+str(jni/('darwin'if host else'freebsd'))]
 if not host:flags+=['-target','x86_64-sie-ps5','-isysroot',str(sdk),'-fvisibility-nodllstorageclass=default','-fno-stack-protector','-mno-avx','-mno-avx2','-mno-fma']
 objects=[]
 for unit in ['dispatch','callback']:
  obj=out/(unit+'.o');subprocess.run([str(LLVM/'clang'),*flags,'-c',str(src/'native'/(unit+'.c')),'-o',str(obj)],check=True);objects.append(obj)
 if host:
  output=out/'libjnidispatch.dylib';subprocess.run([str(LLVM/'clang'),'-dynamiclib',*map(str,objects),'/opt/homebrew/opt/libffi/lib/libffi.dylib','-o',str(output)],check=True)
 else:
  output=out/'jnidispatch.o';subprocess.run(['/opt/homebrew/opt/lld/bin/ld.lld','-r',*map(str,objects),'-o',str(output)],check=True)
  sections=subprocess.check_output([str(LLVM/'llvm-readelf'),'-SW',str(output)],text=True);assert not re.search(r'\]\s+\.(?:init_array|ctors)(?:\s|\.)',sections)
 sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
 symbols=subprocess.check_output([str(LLVM/'llvm-nm'),'--defined-only','--extern-only',str(output)],text=True)
 exports=sorted(l.split()[-1].lstrip('_')if host else l.split()[-1]for l in symbols.splitlines()if l.split()and 'Java_com_sun_jna_'in l)
 audit={'repository':REPOSITORY,'commit':COMMIT,'jna_version':'5.19.1','native_version':version,'native_api_checksum':checksum,'host':host,'output_sha256':sha(output),'jni_exports':exports,'native_sources_sha256':{name:sha(src/'native'/name)for name in ['dispatch.c','callback.c','dispatch.h','protect.h']},'ffi_header_sha256':sha(Path(ffi_include)/'ffi.h'),'jni_header_sha256':{p.name:sha(p)for p in headers.glob('*.h')},'options':{'jawt':False,'signal_protection':False,'nio_buffers':True},'scope':'Original JNA native dispatch/callback sources and generated JNI headers. No game/Java class replacement. Target uses caller-supplied existing libffi; arbitrary external ELF loading is not added.','console':'Target bootstrap/memory/calls/callbacks remain pending; host tests do not establish PS5 behavior.'}
 (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('PASS genuine JNA dispatch JNI',len(exports),'exports',sha(output));return output
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--ffi-include',type=Path,required=True);p.add_argument('--host',action='store_true');p.add_argument('--source',type=Path);p.add_argument('--offline',action='store_true');a=p.parse_args();build(a.ffi_include,a.host,a.source,a.offline)
