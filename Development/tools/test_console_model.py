#!/usr/bin/env python3
"""Native model-query fixtures, never evidence of physical-console detection."""
from pathlib import Path
import subprocess,tempfile,hashlib,base64
ROOT=Path(__file__).resolve().parents[1]
salted=hashlib.sha1(b'sceKernelGetHwModelName'+bytes.fromhex('518d64a635ded8c1e6b039b1c3e55230')).digest()
assert base64.b64encode(salted[:8][::-1]).decode().rstrip('=').replace('/','-')=='JC7I7J1bllQ'
assert '"JC7I7J1bllQ"' in (ROOT/'java25/platform/console_model.hpp').read_text()
SOURCE=r'''
#include "console_model.hpp"
#include <cassert>
#include <cstdio>
using namespace ps5::console;
static const char* answer="CFI-7019";static int rc=0;static bool terminated=true;
static int query(char* p){if(terminated)std::strcpy(p,answer);else std::memset(p,'X',1000);return rc;}
static int wanted=1,mode=0,calls=0,list_mode=0;
static int resolver(int handle,const char* symbol,void** out){
 calls++;assert(std::strcmp(symbol,"sceKernelDlsym"));
 *out=reinterpret_cast<void*>(query);
 if(mode==0||handle!=wanted)return -2; // poisoned failure pointer must be ignored
 if(mode==2&&std::strcmp(symbol,"JC7I7J1bllQ"))return -3;
 if(mode==3){*out=nullptr;return 0;}
 return 0;
}
static int modules(int* handles,std::size_t count,std::size_t* actual){
 assert(count==512);if(list_mode==3){for(int i=0;i<512;i++)handles[i]=100+i;*actual=512;return 0;}handles[0]=1;handles[1]=0x2001;handles[2]=-1;handles[3]=77;handles[4]=77;
 *actual=list_mode==2?513:5;return list_mode==1?-4:0;
}
int main(){
 assert(!resolve_loaded_query(nullptr).query);
 assert(!resolve_loaded_query(resolver).query);
 mode=1;auto loaded=resolve_loaded_query(resolver);assert(loaded.query==query&&loaded.handle==1);assert(read(loaded.query).model==Model::pro);
 wanted=0x2001;loaded=resolve_loaded_query(resolver);assert(loaded.query==query&&loaded.handle==0x2001);
 mode=2;loaded=resolve_loaded_query(resolver);assert(loaded.by_nid&&loaded.query==query);
 wanted=77;loaded=resolve_loaded_query(resolver,modules);assert(loaded.query==query&&loaded.handle==77&&loaded.attempt_count==3&&loaded.module_count==5);
 list_mode=1;assert(!resolve_loaded_query(resolver,modules).query);list_mode=2;assert(!resolve_loaded_query(resolver,modules).query);list_mode=0;
 mode=3;loaded=resolve_loaded_query(resolver,modules);assert(!loaded.query&&loaded.attempt_count==3&&loaded.record_count==3&&loaded.records[2].name_result==0&&!loaded.records[2].name_pointer);
 list_mode=3;mode=0;loaded=resolve_loaded_query(resolver,modules);assert(!loaded.query&&loaded.attempt_count==514&&loaded.record_count==8);list_mode=0;
 mode=0;loaded=resolve_loaded_query(resolver,modules);assert(!loaded.query&&loaded.records[0].name_result==-2&&loaded.records[0].name_pointer);
 for(const char* s:{"CFI-1016A","CFI-1115B","CFI-1215A01","CFI-2015B-30","CFI-2115A","CFI-2014 A01X"})assert(classify(s,std::strlen(s)+1)==Model::standard);
 for(const char* s:{"CFI-7019","CFI-7119","CFI-7019B-30","CFI-7019 B01X"})assert(classify(s,std::strlen(s)+1)==Model::pro);
 for(const char* s:{"","CFI-7219","CFI-3015","CFI-7019XYZ","CFI-2014 A01Y","CFI-2014 C01X","CFI-2014 A0X","CFI-7019 B01Xextra","CFI-7019-","CFI-7019\n","Pro","NAVI21","100-000001020","CFI-70190","CFI-7019-3","CFI-7019A-"})assert(classify(s,std::strlen(s)+1)==Model::unknown);
 assert(classify(nullptr,0)==Model::unknown);char tiny[4]={'C','F','I','-'};assert(classify(tiny,sizeof(tiny))==Model::unknown);
 assert(read(nullptr).status==Status::unavailable);auto r=read(query);assert(r.model==Model::pro&&r.status==Status::recognized);
 answer="CFI-2015B";assert(read(query).model==Model::standard);answer="Unknown";assert(read(query).status==Status::unrecognized);
 rc=-1;r=read(query);assert(r.model==Model::unknown&&r.status==Status::failed&&r.native_result==-1);
 rc=1;assert(read(query).status==Status::failed);rc=0;terminated=false;assert(read(query).status==Status::malformed);
 for(int n=0;n<1000;n++){char bytes[1000];std::memset(bytes,'X',sizeof(bytes));bytes[n]=0;assert(classify(bytes,sizeof(bytes))==Model::unknown);}
 puts("PASS model fixtures: documented standard/Pro families,unknown/missing/failed query,bounded termination,malformed and future revisions; optional loaded-kernel resolver handles/errors/null outputs; no real console test");
}
'''
with tempfile.TemporaryDirectory(prefix='ps5-model-') as temp:
    root=Path(temp);src=root/'check.cpp';src.write_text('#include <initializer_list>\n'+SOURCE)
    subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'java25/platform'),str(src),'-o',str(root/'check')],check=True)
    subprocess.run([str(root/'check')],check=True)
