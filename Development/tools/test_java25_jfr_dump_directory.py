#!/usr/bin/env python3
"""Exercise actual JFR default/get/set path bodies without a target cwd query."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];w=r/'build/java25/jfr-dump-test';w.mkdir(parents=True,exist_ok=True)
s=(r/'.tools/java25/openjdk/src/hotspot/share/jfr/recorder/repository/jfrEmergencyDump.cpp').read_text()
def body(start,end):return s[s.index(start):s.index(end,s.index(start))]
helper=body('static char* get_default_dump_directory(', '// returns with an appended file separator')
getdir=body('static size_t get_dump_directory()', '\nstatic ',)
setdir=body('void JfrEmergencyDump::set_dump_path(', '\nvoid JfrEmergencyDump::on_vm_error_report(')
p=w/'test.cpp';p.write_text(r'''
#include <cassert>
#include <cstddef>
#include <cstring>
#include <cstdio>
#include <string>
#define JVM_MAXPATHLEN 1025
#define jio_snprintf snprintf
static int queries;
namespace os {
char* get_current_directory(char* p,size_t n){++queries;const char* v="/host-cwd";if(n<=strlen(v))return nullptr;strcpy(p,v);return p;}
const char* file_separator(){return "/";}
}
struct JfrEmergencyDump {static void set_dump_path(const char*);static const char* get_dump_path();};
static char _dump_path[JVM_MAXPATHLEN]={},_path_buffer[JVM_MAXPATHLEN]={};
'''+helper+'\n'+getdir+'\n'+setdir+r'''
int main(){
 char b[32];memset(b,'q',sizeof(b));
#ifdef __PROSPERO__
 assert(!get_default_dump_directory(b,0)&&b[0]=='q');
 assert(!get_default_dump_directory(b,9)&&b[0]=='q');
 assert(!get_default_dump_directory(nullptr,32));
 assert(get_default_dump_directory(b,11)==b&&strcmp(b,"/download0")==0&&b[11]=='q');
 const char* expected="/download0";
#else
 const char* expected="/host-cwd";
#endif
 JfrEmergencyDump::set_dump_path(nullptr);assert(strcmp(_dump_path,expected)==0);
 JfrEmergencyDump::set_dump_path("");assert(strcmp(_dump_path,expected)==0);
 _dump_path[0]=0;assert(get_dump_directory()==strlen(expected)+1);assert(std::string(_path_buffer)==std::string(expected)+"/");
 JfrEmergencyDump::set_dump_path("/explicit/path");assert(strcmp(_dump_path,"/explicit/path")==0);
 assert(get_dump_directory()==15&&strcmp(_path_buffer,"/explicit/path/")==0);
 std::string too_long(JVM_MAXPATHLEN,'x');JfrEmergencyDump::set_dump_path(too_long.c_str());assert(strcmp(_dump_path,"/explicit/path")==0);
 std::string maximum(JVM_MAXPATHLEN-1,'x');JfrEmergencyDump::set_dump_path(maximum.c_str());assert(strlen(_dump_path)==JVM_MAXPATHLEN-1);
#ifdef __PROSPERO__
 assert(queries==0);
#else
 assert(queries==3);
#endif
}
''')
for ps5 in [False,True]:
 exe=w/('ps5' if ps5 else 'host');subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined',*(['-D__PROSPERO__'] if ps5 else []),str(p),'-o',str(exe)],check=True);subprocess.run([str(exe)],check=True)
print('PASS: actual JFR path helper/get/set bodies, PS5 null/empty defaults without cwd query, explicit/max/oversize preservation, bounds; desktop cwd branch retained; ASan/UBSan. File-open/write not modeled.')
