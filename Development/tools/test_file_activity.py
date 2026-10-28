#!/usr/bin/env python3
"""Check opt-in descriptor accounting without owning or closing caller handles."""
from pathlib import Path
import tempfile,subprocess
r=Path(__file__).resolve().parents[1]
s=r'''
#include "file_activity.hpp"
#include <cassert>
#include <thread>
#include <fcntl.h>
#include <unistd.h>
int main(){
 char report[4096];errno=EBUSY;
 ps5::file_activity::open_result(-1,"/missing");assert(errno==EBUSY);
 int fd=open("/dev/null",O_RDONLY);assert(fd>=0);ps5::file_activity::open_result(fd,"/dev/null");
 ps5::file_activity::snapshot(report,sizeof(report));assert(strstr(report,"tracked_live=1")&&strstr(report,"path=/dev/null"));
 assert(fcntl(fd,F_GETFD)>=0);ps5::file_activity::close_result(fd,-1);ps5::file_activity::snapshot(report,sizeof(report));assert(strstr(report,"tracked_live=1"));
 assert(close(fd)==0);ps5::file_activity::close_result(fd,0);
 ps5::file_activity::open_result(9000,"/outside");ps5::file_activity::snapshot(report,sizeof(report));assert(strstr(report,"outside=1")&&strstr(report,"tracked_live=0"));
 auto worker=[](int id){for(int n=0;n<500;n++){ps5::file_activity::open_result(id,"/fixture");ps5::file_activity::close_result(id,0);}};
 std::thread a(worker,30),b(worker,31);a.join();b.join();
 ps5::file_activity::snapshot(report,sizeof(report));assert(strstr(report,"tracked_live=0"));char tiny[2];assert(ps5::file_activity::snapshot(tiny,2)==1&&tiny[1]==0);
 puts("PASS optional file activity:actual handle remains caller-owned,failed close retained,successful close clears,failed/out-of-bound opens counted,concurrent recording,bounded output");
}
'''
with tempfile.TemporaryDirectory()as d:
 p=Path(d);(p/'test.cpp').write_text(s);subprocess.run(['clang++','-std=c++17','-DPS5_TRACK_FILE_ACTIVITY=1','-O1','-fsanitize=address,undefined','-I'+str(r/'java25/probe'),str(p/'test.cpp'),'-o',str(p/'test')],check=True);subprocess.run([str(p/'test')],check=True)
