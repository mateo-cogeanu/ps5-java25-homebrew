/* SPDX-License-Identifier: GPL-3.0-or-later
 * Checks probe logic using macOS APIs, not PS5 OS compatibility.
 */
#define main java25_probe_app_main
#include "../java25/probe/runtime.cpp"
#undef main

int main() {
 for(int i=0;i<test_count;++i) {
  run_test(i);
  std::printf("%s: %s (%s)\n",names[i],status[i]==1?"PASS":"FAIL",messages[i]);
  if(status[i]!=1) return 1;
 }
 return 0;
}
