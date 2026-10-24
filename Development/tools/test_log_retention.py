#!/usr/bin/env python3
"""Exercise opt-in diagnostic tail retention on real temporary files."""
from pathlib import Path
import subprocess
import tempfile
ROOT = Path(__file__).resolve().parents[1]
source = r'''
#include "java25/probe/log_retention.hpp"
#include <cassert>
#include <string>
#include <fstream>
#include <iterator>
std::string contents(const char* p) {std::ifstream in(p);return {std::istreambuf_iterator<char>(in),{}};}
int main() {
 char scratch[8192];
 assert(ps5::log_retention::retain_tail("missing",scratch,sizeof scratch));
 std::string original;for(int i=0;i<200000;i++)original+=char('A'+i%26);
 {std::ofstream out("history");out<<original;}
 struct stat before{},after{};assert(stat("history",&before)==0);
 assert(ps5::log_retention::retain_tail("history",scratch,sizeof scratch));
 assert(stat("history",&after)==0 && before.st_ino==after.st_ino);
 assert(contents("history")==original.substr(original.size()-sizeof scratch));
 assert(ps5::log_retention::retain_tail("history",scratch,sizeof scratch));
 assert(contents("history")==original.substr(original.size()-sizeof scratch));
 {std::ofstream out("small");out<<"short report\n";}
 assert(ps5::log_retention::retain_tail("small",scratch,sizeof scratch));
 assert(contents("small")=="short report\n");
 assert(!ps5::log_retention::retain_tail("small",scratch,0) && errno==EINVAL);
 assert(contents("small")=="short report\n");
 assert(!ps5::log_retention::retain_tail(".",scratch,sizeof scratch));
}
'''
with tempfile.TemporaryDirectory(prefix='ps5-log-retention-') as folder:
    work = Path(folder)
    (work/'test.cpp').write_text(source)
    subprocess.run(['clang++','-std=c++20','-Wall','-Wextra','-Werror','-fsanitize=address,undefined','-I'+str(ROOT),str(work/'test.cpp'),'-o',str(work/'test')],check=True)
    subprocess.run([str(work/'test')],cwd=work,check=True)
print('PASS diagnostic retention: exact tail, same inode, repeated call, small/missing files, invalid input; ASan/UBSan. Console full-storage recovery pending.')
