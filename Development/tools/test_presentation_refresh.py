#!/usr/bin/env python3
"""Actual optional native refresh negotiation under injected VideoOut boundaries."""
from pathlib import Path
import os, subprocess, tempfile
ROOT=Path(__file__).resolve().parents[1]
source=r'''
#include <cassert>
#include "presentation_refresh.hpp"
using namespace ps5::demo::detail;
int main(){
 for(int scenario=0;scenario<8;scenario++){
 int supports=0,configs=0,restores=0,waits=0;std::uint64_t time=0;
 auto r=negotiate_refresh(scenario==0?60:120,[&]{supports++;return scenario==2?0:1;},[&](unsigned mode){configs++;if(mode==1){restores++;return scenario==7?-1:0;}assert(mode==15);return scenario==3?-1:0;},[&]{waits++;time+=scenario==4||scenario==7?16667:scenario==6?1000:8333;return scenario==5?-1:0;},[&]{return time;});
 if(scenario==0)assert(r.selected_hz==60&&!supports&&!configs&&!waits);
 if(scenario==1)assert(r.selected_hz==120&&r.changed&&r.period_us==8333&&waits==7&&!restores);
 if(scenario==2||scenario==3)assert(r.selected_hz==60&&!r.changed&&!waits&&!restores);
 if(scenario>=4)assert(r.selected_hz==60&&!r.changed&&restores==1&&r.safe==(scenario!=7));
 }
}
'''
with tempfile.TemporaryDirectory() as d:
 w=Path(d);(w/'test.cpp').write_text(source);subprocess.run([os.environ.get('CXX','clang++'),'-std=c++20','-O1','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'native/renderer'),str(w/'test.cpp'),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
print('PASS actual default-no-query/verified120/unsupported/config-refusal/slow/failed-wait/impossible-fast/failed-restore native refresh controls; physical output pending')
