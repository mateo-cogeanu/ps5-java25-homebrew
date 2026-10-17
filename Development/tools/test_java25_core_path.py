#!/usr/bin/env python3
"""Compile and exercise the actual PS5 core-path body without desktop services."""
from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
s=(root/'.tools/java25/openjdk/src/hotspot/os/bsd/os_bsd.cpp').read_text()
body=s[s.index('int os::get_core_path('):s.index('\nbool os::supports_map_sync()')]
work=root/'build/java25/core-path-test';work.mkdir(parents=True,exist_ok=True)
source=work/'test.cpp'
source.write_text('''#include <cstddef>
#include <cassert>
#define __PROSPERO__ 1
namespace os { int get_core_path(char*,size_t); }
'''+body+'''
int main(){char b[8]="marker";assert(os::get_core_path(b,sizeof(b))==0&&b[0]==0);char c='x';assert(os::get_core_path(&c,0)==0&&c=='x');assert(os::get_core_path(nullptr,0)==0);}
''')
exe=work/'test'
subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined',str(source),'-o',str(exe)],check=True)
subprocess.run([str(exe)],check=True)
print('PASS: actual PS5 core-path body returns unavailable without desktop queries, allocation or buffer overrun')
