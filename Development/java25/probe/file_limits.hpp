/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <sys/resource.h>
namespace ps5::file_limits {
struct Result {int query=-1,change=0,error=0;rlim_t before=0,after=0,hard=0;};
// Explicit consumer policy only: raise the soft limit within the existing hard cap.
inline Result prepare(rlim_t requested) {
 int saved=errno;Result r;struct rlimit limit{};r.query=getrlimit(RLIMIT_NOFILE,&limit);
 if(r.query){r.error=errno;errno=saved;return r;}
 r.before=r.after=limit.rlim_cur;r.hard=limit.rlim_max;
 rlim_t wanted=limit.rlim_max==RLIM_INFINITY?requested:(requested<limit.rlim_max?requested:limit.rlim_max);
 if(limit.rlim_cur!=RLIM_INFINITY&&wanted>limit.rlim_cur){
  limit.rlim_cur=wanted;r.change=setrlimit(RLIMIT_NOFILE,&limit);
  if(r.change)r.error=errno;
  struct rlimit actual{};if(getrlimit(RLIMIT_NOFILE,&actual)==0)r.after=actual.rlim_cur;
 }
 errno=saved;return r;
}
inline int snapshot(char *text,size_t capacity) {
 int saved=errno;struct rlimit limit{};int rc=getrlimit(RLIMIT_NOFILE,&limit),error=rc?errno:0;
 unsigned bound=rc?0:limit.rlim_cur==RLIM_INFINITY||limit.rlim_cur>8192?8192:(unsigned)limit.rlim_cur;
 unsigned open=0,unknown=0;int highest=-1;
 for(unsigned fd=0;fd<bound;fd++){errno=0;if(fcntl((int)fd,F_GETFD)>=0){open++;highest=(int)fd;}else if(errno!=EBADF)unknown++;}
 int n=std::snprintf(text,capacity,"nofile_query=%d errno=%d soft=%llu hard=%llu scanned=%u open=%u unknown=%u highest=%d\n",rc,error,(unsigned long long)limit.rlim_cur,(unsigned long long)limit.rlim_max,bound,open,unknown,highest);
 errno=saved;return n;
}
}
