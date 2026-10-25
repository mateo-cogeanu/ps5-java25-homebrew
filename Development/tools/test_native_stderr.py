#!/usr/bin/env python3
"""Verify actual native stderr capture with real descriptors and native stdio."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=r'''
#include "native_stderr.hpp"
#include <cassert>
#include <cstring>
#include <cstdlib>
int main(int argc,char**argv){assert(argc==3);if(std::strcmp(argv[2],"closed")==0)close(2);errno=EDOM;int result=ps5::native_stderr::begin(argv[1]);
 if(std::strcmp(argv[2],"failure")==0){assert(result==ENOENT);assert(write(2,"original stderr\n",16)==16);return 0;}
 assert(result==0&&errno==EDOM);std::fprintf(stderr,"native stdio error\n");assert(write(2,"raw descriptor error\n",21)==21);std::puts("stdout unchanged");std::fflush(stdout);_exit(0);}
'''
with tempfile.TemporaryDirectory(prefix='native-stderr-test-')as folder:
 w=Path(folder);(w/'test.cpp').write_text(source);binary=w/'test';subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(w/'test.cpp'),'-o',str(binary)],check=True)
 report=w/'native.log'
 for mode in ['success','success','closed']:
  r=subprocess.run([str(binary),str(report),mode],capture_output=True,text=True);assert r.returncode==0 and r.stdout=='stdout unchanged\n' and not r.stderr,(r.returncode,r.stdout,r.stderr)
 assert report.read_text()==('native stdio error\nraw descriptor error\n'*3)
 r=subprocess.run([str(binary),str(w/'missing/native.log'),'failure'],capture_output=True,text=True);assert r.returncode==0 and r.stderr=='original stderr\n' and not r.stdout
 print('PASS actual native stderr capture:stdio/raw fd2 survive _exit,append/open returning fd2,stdout/errno preserved,failed-open leaves original stderr;host ASan/UBSan,PS5 pending')
