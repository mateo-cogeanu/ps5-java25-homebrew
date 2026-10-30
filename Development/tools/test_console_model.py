#!/usr/bin/env python3
"""Native model-query fixtures, never evidence of physical-console detection."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
SOURCE=r'''
#include "console_model.hpp"
#include <cassert>
#include <cstdio>
using namespace ps5::console;
static const char* answer="CFI-7019";static int rc=0;static bool terminated=true;
static int query(char* p){if(terminated)std::strcpy(p,answer);else std::memset(p,'X',1000);return rc;}
int main(){
 for(const char* s:{"CFI-1016A","CFI-1115B","CFI-1215A01","CFI-2015B-30","CFI-2115A"})assert(classify(s,std::strlen(s)+1)==Model::standard);
 for(const char* s:{"CFI-7019","CFI-7119","CFI-7019B-30"})assert(classify(s,std::strlen(s)+1)==Model::pro);
 for(const char* s:{"","CFI-7219","CFI-3015","CFI-7019XYZ","CFI-7019-","CFI-7019\n","Pro","NAVI21","100-000001020","CFI-70190","CFI-7019-3","CFI-7019A-"})assert(classify(s,std::strlen(s)+1)==Model::unknown);
 assert(classify(nullptr,0)==Model::unknown);char tiny[4]={'C','F','I','-'};assert(classify(tiny,sizeof(tiny))==Model::unknown);
 assert(read(nullptr).status==Status::unavailable);auto r=read(query);assert(r.model==Model::pro&&r.status==Status::recognized);
 answer="CFI-2015B";assert(read(query).model==Model::standard);answer="Unknown";assert(read(query).status==Status::unrecognized);
 rc=-1;r=read(query);assert(r.model==Model::unknown&&r.status==Status::failed&&r.native_result==-1);
 rc=1;assert(read(query).status==Status::failed);rc=0;terminated=false;assert(read(query).status==Status::malformed);
 for(int n=0;n<1000;n++){char bytes[1000];std::memset(bytes,'X',sizeof(bytes));bytes[n]=0;assert(classify(bytes,sizeof(bytes))==Model::unknown);}
 puts("PASS model fixtures: documented standard/Pro families,unknown/missing/failed query,bounded termination,malformed and future revisions; no real console test");
}
'''
with tempfile.TemporaryDirectory(prefix='ps5-model-') as temp:
    root=Path(temp);src=root/'check.cpp';src.write_text('#include <initializer_list>\n'+SOURCE)
    subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT/'java25/platform'),str(src),'-o',str(root/'check')],check=True)
    subprocess.run([str(root/'check')],check=True)
