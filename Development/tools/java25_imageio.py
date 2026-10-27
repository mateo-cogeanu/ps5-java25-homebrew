#!/usr/bin/env python3
"""Build genuine OpenJDK raster/Disposer and bundled LCMS natives, without a desktop toolkit.

Opt-in resident ImageIO support. No drawing/window/font/printing/JPEG claim.
"""
from pathlib import Path
import argparse,subprocess,json,hashlib,concurrent.futures
ROOT=Path(__file__).resolve().parents[1];SOURCE=ROOT/'.tools/java25/openjdk';LLVM=Path('/opt/homebrew/opt/llvm/bin');LLD=Path('/opt/homebrew/opt/lld/bin/ld.lld');JDK=Path('/Library/Java/JavaVirtualMachines/openjdk-25.jdk/Contents/Home')
def build(host=False):
 out=ROOT/('build/java25/imageio-host' if host else 'build/java25/imageio-target');out.mkdir(parents=True,exist_ok=True)
 desktop=SOURCE/'src/java.desktop/share/native';base=SOURCE/'src/java.base/share/native/libjava';headers=SOURCE/'build/ps5-bootstrap/support/headers/java.desktop';jni=JDK/'include' if host else SOURCE/'build/ps5-bootstrap/support/modules_include/java.base'
 includes=[jni,jni/('darwin' if host else 'freebsd'),headers,base,SOURCE/'src/java.base/unix/native/libjava',desktop/'common/awt/debug',desktop/'libawt/java2d',desktop/'libawt/java2d/loops',desktop/'liblcms',SOURCE/'src/hotspot/share/include',SOURCE/'src/hotspot/os/posix/include']
 flags=['-std=c11','-O2','-fPIC','-fno-strict-aliasing','-DNDEBUG','-D_LITTLE_ENDIAN','-DHEADLESS','-D__MEDIALIB_OLD_NAMES','-D__USE_J2D_NAMES','-DMLIB_NO_LIBSUNMATH']
 if not host:flags+=['-target','x86_64-sie-ps5','-isysroot',str(ROOT/'.tools/native-sdk/ps5-payload-sdk'),'-fvisibility-nodllstorageclass=default','-mno-avx','-mno-avx2','-mno-fma','-fno-stack-protector']
 else:flags+=['-D_ALLBSD_SOURCE']
 groups={'awt':[desktop/'libawt/java2d/Disposer.c',desktop/'libawt/java2d/Trace.c',desktop/'libawt/awt/image/imageInitIDs.c',SOURCE/'src/java.desktop/unix/native/libawt/awt/initIDs.c'],'lcms':sorted((desktop/'liblcms').glob('*.c'))}
 audit={'scope':'Genuine upstream image raster IDs/Disposer and bundled LCMS only;no display/toolkit/fonts/printing/JPEG','upstream':json.loads((ROOT/'java25/upstream.json').read_text()),'host':host,'groups':{}}
 for name,sources in groups.items():
  def compile(p):
   obj=out/(name+'-'+p.stem+'.o');subprocess.run([str(LLVM/'clang'),*flags,*['-I'+str(i)for i in includes],'-c',str(p),'-o',str(obj)],check=True);return obj
  with concurrent.futures.ThreadPoolExecutor(max_workers=4)as pool:objects=list(pool.map(compile,sources))
  if host:
   target=out/('lib'+name+'.dylib');subprocess.run([str(LLVM/'clang'),'-dynamiclib','-Wl,-undefined,dynamic_lookup',*map(str,objects),*([str(out/'libawt.dylib')] if host and name=='lcms' else []),'-o',str(target)],check=True)
  else:
   target=out/('lib'+name+'.o');subprocess.run([str(LLD),'-r',*map(str,objects),*([str(out/'libawt.dylib')] if host and name=='lcms' else []),'-o',str(target)],check=True)
   subprocess.run([str(LLD),'-shared',str(target),'-o',str(out/('lib'+name+'.so'))],check=True)
   sections=subprocess.check_output([str(LLVM/'llvm-readelf'),'-SW',str(target)],text=True);assert '.init_array'not in sections and '.ctors'not in sections
  audit['groups'][name]={'sources_sha256':{str(p.relative_to(SOURCE)):hashlib.sha256(p.read_bytes()).hexdigest()for p in sources},'output_sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'compile_units':len(sources)}
 (out/'audit.json').write_text(json.dumps(audit,indent=2)+'\n');print('PASS genuine ImageIO raster/Disposer + LCMS build:',out);return out
if __name__=='__main__':
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('--host',action='store_true');a=p.parse_args();build(a.host)
