#!/usr/bin/env python3
"""Check actual verifier signed bytecode decoding with sanitizer-hard failures."""
from pathlib import Path
import re,subprocess
R=Path(__file__).resolve().parents[1];W=R/'build/java25/verifier-decoding-test';W.mkdir(parents=True,exist_ok=True)
s=(R/'.tools/java25/openjdk/src/java.base/share/native/libverify/check_code.c').read_text()
a=s.index('static jint _ck_ntohl(');b=s.index('\n}',a)+2;ntoh=s[a:b]
expressions=[e for e in re.findall(r'int jump = ([^;]+);',s) if 'code[offset' in e]
assert len(expressions)==2
p=W/'test.c';p.write_text('''#include <stdint.h>
#include <string.h>
#include <assert.h>
#include <stdio.h>
typedef int32_t jint;
'''+ntoh+'\nstatic int read16(unsigned char*code){int offset=0;return '+expressions[0]+';}\nstatic int read32(unsigned char*code){int offset=0;return '+expressions[1]+''';}
int main(void){unsigned char code[5]={0};
 for(int value=-32768;value<=32767;++value){uint16_t bits=(uint16_t)value;code[1]=bits>>8;code[2]=bits;assert(read16(code)==value);}
 int32_t cases[]={INT32_MIN,INT32_MIN+1,-16777216,-65536,-32768,-256,-1,0,1,255,32767,65535,16777216,INT32_MAX};
 for(unsigned i=0;i<sizeof(cases)/sizeof(cases[0]);++i){uint32_t n=(uint32_t)cases[i];code[1]=n>>24;code[2]=n>>16;code[3]=n>>8;code[4]=n;assert(read32(code)==cases[i]);jint input;memcpy(&input,code+1,4);assert(_ck_ntohl(input)==cases[i]);}
 puts("PASS: actual verifier 16-bit branches exhaustively and 32-bit/switch signed boundaries decode without UB");
}
''')
subprocess.run(['clang','-std=c11','-O2','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(W/'test')],check=True)
subprocess.run([str(W/'test')],check=True)
