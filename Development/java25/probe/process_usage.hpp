/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cerrno>
#include <cstdio>
#include <fcntl.h>
#include <sys/resource.h>
#include <unistd.h>
namespace ps5::process_usage {
// Raw OS counters: do not assume ru_maxrss units or infer a container limit.
// Fixed stack storage and descriptor IO; no JVM/JNI access from the UI thread.
inline bool append(const char* path,long long elapsed) {
 int saved_errno=errno;struct rusage usage{};errno=0;
 int result=getrusage(RUSAGE_SELF,&usage),error=result ? errno : 0;
 char line[1536];int length;
 if(result==0)length=std::snprintf(line,sizeof(line),"elapsed_s=%lld getrusage=0 maxrss_raw=%lld minflt=%lld majflt=%lld user_us=%lld system_us=%lld\n",elapsed,(long long)usage.ru_maxrss,(long long)usage.ru_minflt,(long long)usage.ru_majflt,(long long)usage.ru_utime.tv_sec*1000000+usage.ru_utime.tv_usec,(long long)usage.ru_stime.tv_sec*1000000+usage.ru_stime.tv_usec);
 else length=std::snprintf(line,sizeof(line),"elapsed_s=%lld getrusage=%d errno=%d counters=unavailable\n",elapsed,result,error);
 // Limits describe process policy, not currently available physical/flexible memory.
 // Sample at startup and once per minute; never change a limit from diagnostics.
 if(length>0&&(size_t)length<sizeof(line)&&elapsed%60==0) {
  const int resources[]={RLIMIT_DATA,RLIMIT_AS,RLIMIT_RSS};
  const char* names[]={"data","as","rss"};
  for(unsigned i=0;i<3;++i) {
   struct rlimit limits{};errno=0;
   int rc=getrlimit(resources[i],&limits),limit_error=rc?errno:0;
   int added=std::snprintf(line+length,sizeof(line)-(size_t)length,
    "elapsed_s=%lld rlimit=%s result=%d errno=%d soft_raw=%llu hard_raw=%llu soft_infinite=%d hard_infinite=%d\n",
    elapsed,names[i],rc,limit_error,(unsigned long long)limits.rlim_cur,
    (unsigned long long)limits.rlim_max,rc==0&&limits.rlim_cur==RLIM_INFINITY,
    rc==0&&limits.rlim_max==RLIM_INFINITY);
   if(added<0||(size_t)added>=sizeof(line)-(size_t)length){length=-1;break;}
   length+=added;
  }
 }
 bool ok=length>0&&(size_t)length<sizeof(line);int fd=-1;
 if(ok)fd=::open(path,O_CREAT|O_WRONLY|O_APPEND,0600);
 if(fd<0)ok=false;
 size_t written=0;
 while(ok&&written<(size_t)length){ssize_t n=::write(fd,line+written,(size_t)length-written);if(n<0&&errno==EINTR)continue;if(n<=0){ok=false;break;}written+=(size_t)n;}
 if(fd>=0&&::close(fd)!=0)ok=false;
 errno=saved_errno;return ok;
}
}
