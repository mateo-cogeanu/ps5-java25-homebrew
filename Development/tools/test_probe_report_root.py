#!/usr/bin/env python3
"""Check bootstrap-only report routing, default preservation and actual HTTP allowlist."""
from pathlib import Path
import os,subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "log_share.hpp"
#include <cassert>
#include <string>
int main(int argc,char**argv){
 assert(argc==2);using namespace ps5::log_share;
 assert(std::strcmp(report_root(),"/download0")==0);
 for(const auto& f:files)assert(std::strncmp(f.path,"/download0/",11)==0);
 for(const char* bad:{"", "relative", "/a/../b", "/a/.", "/a/..", "/root/"}){assert(!configure_root(bad)&&errno==EINVAL);assert(!configured_root[0]);}
 std::string excessive(600,'x');excessive[0]='/';assert(!configure_root(excessive.c_str()));
 assert(configure_root(argv[1]));assert(std::strcmp(report_root(),argv[1])==0);
 for(size_t i=0;i<file_count;i++){assert(std::strcmp(configured_files[i].url,files[i].url)==0);assert(std::string(configured_files[i].path)==std::string(argv[1])+std::string(files[i].path+10));}
 assert(begin_session("fixture","run"));std::string build=std::string(argv[1])+"/probe-build.txt";assert(write_note(build.c_str(),"relocated-report"));
 int fds[2];assert(socketpair(AF_UNIX,SOCK_STREAM,0,fds)==0);const char req[]="GET /build.txt HTTP/1.1\r\nHost: fixture\r\n\r\n";assert(write(fds[0],req,sizeof(req)-1)==sizeof(req)-1);serve(fds[1]);shutdown(fds[1],SHUT_WR);char buffer[1024]{};int used=0,n;while((n=read(fds[0],buffer+used,sizeof(buffer)-1-used))>0)used+=n;assert(std::strstr(buffer,"200 OK")&&std::strstr(buffer,"relocated-report"));close(fds[0]);close(fds[1]);
 start(0);assert(state==1);assert(!configure_root("/other")&&errno==EBUSY);stop();assert(!configure_root("/other")&&errno==EBUSY);
 puts("PASS default/report allowlist unchanged; explicit bounded bootstrap root, actual HTTP relocated bytes, archive default and frozen-after-start refusal");
}
'''
with tempfile.TemporaryDirectory(prefix='report-root-')as td:
 root=Path(td);(root/'main.cpp').write_text(SOURCE);out=root/'check';reports=root/'reports';reports.mkdir()
 subprocess.run([os.environ.get('CXX','clang++'),'-std=c++20','-pthread','-fsanitize=address,undefined','-fno-omit-frame-pointer','-I'+str(ROOT/'java25/probe'),str(root/'main.cpp'),'-o',str(out)],check=True)
 subprocess.run([str(out),str(reports)],check=True,env={**os.environ,'UBSAN_OPTIONS':'halt_on_error=1'})
