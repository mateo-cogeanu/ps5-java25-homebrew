/* SPDX-License-Identifier: GPL-3.0-or-later */
#define PS5_TRACK_FILE_ACTIVITY 1
#include "log_share.hpp"
#include <cassert>
#include <string>
#include <sys/resource.h>
struct Call {int fd; const char* file;};
static void* handle(void* p){auto* c=static_cast<Call*>(p);ps5::log_share::Entry entry{"/test.log",c->file};ps5::log_share::serve(c->fd,&entry,1);close(c->fd);return nullptr;}
static std::string request(const char* target,const char* file){
 int fd[2];assert(socketpair(AF_UNIX,SOCK_STREAM,0,fd)==0);std::string query=std::string("GET ")+target+" HTTP/1.1\r\n\r\n";assert(write(fd[0],query.data(),query.size())==(ssize_t)query.size());shutdown(fd[0],SHUT_WR);
 pthread_attr_t attr;assert(!pthread_attr_init(&attr));assert(!pthread_attr_setstacksize(&attr,64*1024));assert(!pthread_attr_setguardsize(&attr,16384));Call c{fd[1],file};pthread_t worker;assert(!pthread_create(&worker,&attr,handle,&c));assert(!pthread_attr_destroy(&attr));
 std::string out;char bytes[4096];ssize_t n;while((n=read(fd[0],bytes,sizeof(bytes)))>0)out.append(bytes,n);close(fd[0]);assert(!pthread_join(worker,nullptr));return out;
}
int main(int argc,char** argv){assert(argc==2);rlimit core{0,0};assert(!setrlimit(RLIMIT_CORE,&core));assert(request("/",argv[1]).find("200 OK")!=std::string::npos);
#ifndef LEGACY_ONLY
 for(int i=0;i<512;i++)ps5::file_activity::open_result(i+300,"/test/path");
 auto full=request("/file-activity-all.txt",argv[1]);assert(full.find("fd=811 ")!=std::string::npos);assert(full.find("tracked_live=512")!=std::string::npos);
 ps5::log_share::extended_snapshot_busy.test_and_set();assert(request("/file-activity-all.txt",argv[1]).find("503 Service Unavailable")!=std::string::npos);ps5::log_share::extended_snapshot_busy.clear();assert(request("/file-activity-all.txt",argv[1]).find("200 OK")!=std::string::npos);
 auto file=request("/test.log",argv[1]);assert(file.substr(file.find("\r\n\r\n")+4)==std::string(1024*1024,'x'));assert(request("/../private",argv[1]).find("404 Not Found")!=std::string::npos);
 assert(request("/file-activity.txt",argv[1]).find("200 OK")!=std::string::npos);assert(request("/resource-status.txt",argv[1]).find("200 OK")!=std::string::npos);
#endif
 puts("PASS native64KiB worker stack HTTP requests");}
