#!/usr/bin/env python3
"""Build the reusable native presenter; high refresh remains caller opt-in."""
import argparse, hashlib, json, subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 for n in ('sdk','cxx','font-header','output'):p.add_argument('--'+n,type=Path,required=True)
 a=p.parse_args();sdk=a.sdk.resolve();out=a.output.resolve();fonts=a.font_header.resolve();out.parent.mkdir(parents=True,exist_ok=True)
 if fonts.name!='fonts.hpp' or not fonts.is_file():raise ValueError('Explicit generated fonts.hpp required')
 source=ROOT/'native/renderer/demo_renderer.cpp'
 subprocess.run([str(a.cxx.resolve()),'-target','x86_64-sie-ps5','-fvisibility-nodllstorageclass=default','-isysroot',str(sdk),'-isystem',str(sdk/'target/include/c++/v1'),'-isystem',str(sdk/'target/include'),'-I'+str(fonts.parent),'-I'+str(ROOT/'native/renderer'),'-I'+str(ROOT/'src'),'-I'+str(ROOT/'native'),'-std=c++20','-O2','-Wall','-Wextra','-Werror','-march=x86-64','-mno-avx','-mno-avx2','-mno-fma','-fno-stack-protector','-fno-plt','-femulated-tls','-fno-exceptions','-fno-rtti','-ffunction-sections','-fdata-sections','-c',str(source),'-o',str(out)],check=True)
 files=[source,ROOT/'native/renderer/demo_renderer.hpp',ROOT/'native/renderer/presentation_refresh.hpp',ROOT/'native/renderer/tiled_frame_blit.hpp']
 out.with_suffix('.json').write_text(json.dumps({'output_sha256':sha(out),'source_sha256':{str(f.relative_to(ROOT)):sha(f) for f in files},'font_header_sha256':sha(fonts),'scope':'Unchanged default60; explicit ps5DemoPresentationTargetHz hook requests verified120/native fast RGBA tiling and publication; no measured PS5 FPS pass'},indent=2)+'\n');print('PASS native presenter target object',sha(out))
if __name__=='__main__':main()
