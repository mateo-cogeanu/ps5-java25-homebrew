#!/usr/bin/env python3
"""Compile actual PS5 histogram gate and output loop with host fixtures."""
from pathlib import Path
import subprocess
r=Path(__file__).resolve().parents[1];src=r/'.tools/java25/openjdk/src/hotspot/share'
gc=(src/'gc/shared/collectedHeap.cpp').read_text();begin=gc.index('    static unsigned ps5_histogram_eligible');end=gc.index('    log_trace(gc, classhisto)("PS5 retained histogram',begin);gate=gc[begin:end].replace('return;','return false;')
heap=(src/'memory/heapInspection.cpp').read_text();begin=heap.index('void KlassInfoHisto::print_elements(');end=heap.index('\nclass HierarchyClosure',begin);body=heap[begin:end]
code=r'''
#include <cassert>
#include <cstdint>
#include <cstddef>
#include <cstdarg>
#include <cstdio>
#include <string>
#include <vector>
#define __PROSPERO__ 1
#define INT64_FORMAT_W(n) "%lld"
#define UINT64_FORMAT_W(n) "%llu"
constexpr size_t M=1024*1024,HeapWordSize=8;
struct outputStream {
 std::string text;
 void print(const char* f,...){char b[1024];va_list a;va_start(a,f);vsnprintf(b,sizeof b,f,a);va_end(a);text+=b;}
 void print_cr(const char*f,...){char b[1024];va_list a;va_start(a,f);vsnprintf(b,sizeof b,f,a);va_end(a);text+=b;text+='\n';}
};
static unsigned rows=0;
struct Entry{long long count(){return 3;}unsigned long long words(){return 7;}void print_on(outputStream*s){++rows;s->print_cr("entry");}};
struct Entries{std::vector<Entry*>v;int length(){return v.size();}Entry*at(int i){return v.at(i);}};
struct KlassInfoHisto{Entries*e;Entries*elements()const{return e;}void print_elements(outputStream*)const;};
'''
code+='bool sample(bool before,size_t retained){auto used=[&](){return retained;};\n'+gate+'return true;\n}\n'+body
code+=r'''
int main(){
 for(int i=0;i<100;i++){assert(!sample(true,768*M));assert(!sample(false,512*M-1));}
 assert(sample(false,512*M));for(int i=0;i<15;i++)assert(!sample(false,768*M));
 assert(sample(false,768*M));for(int i=0;i<15;i++)assert(!sample(false,768*M));
 assert(sample(false,768*M));for(int i=0;i<100;i++)assert(!sample(false,768*M));
 Entry row;Entries entries;for(int i=0;i<55;i++)entries.v.push_back(&row);
 outputStream out;KlassInfoHisto h{&entries};h.print_elements(&out);
 assert(rows==40);assert(out.text.find("remaining 15 class rows omitted")!=std::string::npos);
 assert(out.text.find("Total 165  3080")!=std::string::npos);
 entries.v.resize(2);rows=0;outputStream small;h.print_elements(&small);assert(rows==2&&small.text.find("omitted")==std::string::npos);
 puts("PASS actual PS5 histogram gate/output: no before/below512MiB samples, stride16, cap3; top40rows with all55class totals retained, small histograms complete; ASan/UBSan fixtures, not live PS5 heap walk");
}
'''
w=r/'build/java25/retained-histogram-test';w.mkdir(parents=True,exist_ok=True);(w/'test.cpp').write_text(code)
subprocess.run(['clang++','-std=c++17','-O1','-g','-fsanitize=address,undefined',str(w/'test.cpp'),'-o',str(w/'check')],check=True)
subprocess.run([str(w/'check')],check=True)
