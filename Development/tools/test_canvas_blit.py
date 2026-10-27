#!/usr/bin/env python3
"""Check actual tiled-frame blit, padded rows and atomic short-input refusal."""
from pathlib import Path
import subprocess, tempfile

root=Path(__file__).resolve().parents[1]
renderer=(root/'native/renderer/demo_renderer.cpp').read_text()
def function(signature):
    start=renderer.index(signature)
    brace=renderer.index('{',start);depth=1;end=brace+1
    while depth:
        if renderer[end]=='{':depth+=1
        elif renderer[end]=='}':depth-=1
        end+=1
    return renderer[start:end]
source='''#include <cassert>
#include <vector>
#include <span>
#include <string_view>
#define private public
#include "demo_renderer.hpp"
#undef private
namespace ps5::demo {
constexpr unsigned frame_width=1920,frame_height=1080;
'''+function('std::size_t tiled_byte_offset(')+function('void put_pixel_unchecked(')+function('bool Canvas::blit_rgba(')+'''
}
int main(){
 using namespace ps5::demo;
 std::vector<std::uint32_t> tiled(1920*1152,0xdeadbeef),input(1936*1080);
 for(unsigned y=0;y<1080;y++)for(unsigned x=0;x<1936;x++)input[y*1936+x]=0xff000000u|((y*1920+x)&0xffffff);
 Canvas canvas(tiled.data());
 assert(canvas.blit_rgba(input,1936));
 for(unsigned y=0;y<1080;y++)for(unsigned x=0;x<1920;x++)assert(tiled[tiled_byte_offset(x,y)/4]==input[y*1936+x]);
 auto before=tiled;assert(!canvas.blit_rgba({}));assert(!canvas.blit_rgba(input,1919));assert(!canvas.blit_rgba({input.data(),1920*1079}));assert(!canvas.blit_rgba(input,0xffffffffu));assert(tiled==before);
 assert(canvas.blit_rgba({input.data(),1920*1080}));
 for(unsigned y=0;y<1080;y++)for(unsigned x=0;x<1920;x++)assert(tiled[tiled_byte_offset(x,y)/4]==input[y*1920+x]);
}
'''
with tempfile.TemporaryDirectory() as d:
    work=Path(d);(work/'test.cpp').write_text(source)
    subprocess.run(['clang++','-std=c++20','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(root/'native/renderer'),str(work/'test.cpp'),'-o',str(work/'test')],check=True)
    subprocess.run([str(work/'test')],check=True)
print('PASS actual RGBA blit: all1080p tiled pixels, padded rows, short/invalid input unchanged; ASan/UBSan')
