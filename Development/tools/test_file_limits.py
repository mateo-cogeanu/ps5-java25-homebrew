#!/usr/bin/env python3
"""Exercise actual descriptor policy with controlled failures and real child limits."""
from pathlib import Path
import subprocess,tempfile
ROOT=Path(__file__).resolve().parents[1]
source=r'''
#include <sys/resource.h>
#include <cerrno>
#include <cassert>
#include <cstdio>
static rlimit value{64,512};static int fail_get,fail_set,calls;
static int fixture_get(int resource,rlimit*out){assert(resource==RLIMIT_NOFILE);if(fail_get){errno=ENOTSUP;return -1;}*out=value;return 0;}
static int fixture_set(int resource,const rlimit*in){assert(resource==RLIMIT_NOFILE&&in->rlim_max==value.rlim_max);calls++;if(fail_set){errno=EPERM;return -1;}value=*in;return 0;}
#define getrlimit fixture_get
#define setrlimit fixture_set
#include "file_limits.hpp"
#undef getrlimit
#undef setrlimit
int main(){errno=EBUSY;auto r=ps5::file_limits::prepare(8192);assert(r.before==64&&r.after==512&&r.hard==512&&r.change==0&&calls==1&&errno==EBUSY);
 r=ps5::file_limits::prepare(64);assert(r.after==512&&calls==1);value={64,512};fail_set=1;r=ps5::file_limits::prepare(8192);assert(r.after==64&&r.error==EPERM);fail_get=1;r=ps5::file_limits::prepare(8192);assert(r.query==-1&&r.error==ENOTSUP&&calls==2&&errno==EBUSY);
 fail_get=0;fail_set=0;value={RLIM_INFINITY,RLIM_INFINITY};r=ps5::file_limits::prepare(8192);assert(calls==2&&r.after==RLIM_INFINITY);
 char text[512];value={64,512};ps5::file_limits::snapshot(text,sizeof(text));assert(errno==EBUSY);
 puts("PASS actual descriptor policy:soft-only raise capped by existing hard limit,no reduction/no hard-limit changes,query/set failures preserved and no errno pollution");}
'''
with tempfile.TemporaryDirectory(prefix='fd-limit-')as folder:
 w=Path(folder);(w/'test.cpp').write_text(source);subprocess.run(['clang++','-std=c++17','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(w/'test.cpp'),'-o',str(w/'test')],check=True);subprocess.run([str(w/'test')],check=True)
 (w/'real.cpp').write_text(r'''#include "file_limits.hpp"
#include <cassert>
#include <cstdio>
int main(){rlimit original{};assert(getrlimit(RLIMIT_NOFILE,&original)==0);rlimit lower=original;lower.rlim_cur=64;assert(original.rlim_max>=128&&setrlimit(RLIMIT_NOFILE,&lower)==0);auto r=ps5::file_limits::prepare(128);assert(r.before==64&&r.after==128&&r.hard==original.rlim_max);assert(setrlimit(RLIMIT_NOFILE,&original)==0);puts("PASS actual child process soft-limit raise64->128 while preserving/restoring original hard limit");}
''');subprocess.run(['clang++','-std=c++17','-I'+str(ROOT/'java25/probe'),str(w/'real.cpp'),'-o',str(w/'real')],check=True);subprocess.run([str(w/'real')],check=True)
