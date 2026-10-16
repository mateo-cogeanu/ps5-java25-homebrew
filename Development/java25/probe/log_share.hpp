/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <atomic>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <pthread.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <netinet/in.h>
#include <unistd.h>

// Fixed allowlist: never interpret a URL as a filesystem path. No upload routes.
namespace ps5::log_share {
struct Entry {const char *url,*path;};
inline constexpr Entry files[]={
 {"/build.txt","/download0/probe-build.txt"},
 {"/session.txt","/download0/probe-session.txt"},
 {"/previous-exception.txt","/download0/previous-probe-exception.txt"},
 {"/previous-abort.txt","/download0/previous-mc-bootstrap-abort.txt"},
 {"/previous-server.log","/download0/mc-server-start/previous-server-console.log"},
 {"/startup.log","/download0/java25-startup.log"},
 {"/vm-trace.log","/download0/java25-vm-trace.log"},
 {"/server.log","/download0/mc-server-start/server-console.log"},
 {"/abort.txt","/download0/mc-bootstrap-abort.txt"},
 {"/hs-error.log","/download0/hs_err_java25.log"},
 {"/previous-hs-error.log","/download0/previous-hs_err_java25.log"},
 {"/exception.txt","/download0/probe-exception.txt"}};
// Preserve the last failure before starting a new run. On relaunch these
// files are left alone until the user explicitly initializes another run.
inline bool write_note(const char *path,const char *text) {
 FILE *file=std::fopen(path,"wb");if(!file)return false;
 size_t length=std::strlen(text);bool ok=std::fwrite(text,1,length,file)==length;
 return std::fclose(file)==0&&ok;
}
inline bool archive_report(const char *path,const char *previous) {
 FILE *input=std::fopen(path,"rb");if(!input)return errno==ENOENT;
 FILE *output=std::fopen(previous,"wb");if(!output){std::fclose(input);return false;}
 bool ok=true;char bytes[4096];size_t count;
 while((count=std::fread(bytes,1,sizeof(bytes),input))>0)if(std::fwrite(bytes,1,count,output)!=count){ok=false;break;}
 if(std::ferror(input))ok=false;
 if(std::fclose(output)!=0)ok=false;std::fclose(input);return ok;
}
inline bool begin_session(const char *build,const char *run,const char *root="/download0") {
 char path[640],backup[640],note[512];bool ok=true;
 const char *current[]={"probe-exception.txt","mc-bootstrap-abort.txt","mc-server-start/server-console.log","hs_err_java25.log"};
 const char *old[]={"previous-probe-exception.txt","previous-mc-bootstrap-abort.txt","mc-server-start/previous-server-console.log","previous-hs_err_java25.log"};
 for(size_t i=0;i<4;++i){
  std::snprintf(path,sizeof(path),"%s/%s",root,current[i]);std::snprintf(backup,sizeof(backup),"%s/%s",root,old[i]);
  if(!archive_report(path,backup)){ok=false;continue;}
  if(i==3){if(::unlink(path)!=0&&errno!=ENOENT)ok=false;continue;}
  std::snprintf(note,sizeof(note),"Build: %s\nRun: %s\nNo %s captured yet in this run. See session.txt and startup.log.\n",build,run,i==0?"Java exception":i==1?"VM abort":"server output");
  // Missing server directory is normal before the first server attempt.
  if(!write_note(path,note)&&!(i==2&&errno==ENOENT))ok=false;
 }
 std::snprintf(path,sizeof(path),"%s/probe-session.txt",root);
 std::snprintf(note,sizeof(note),"Build: %s\nRun: %s\nNew run initialized. Previous reports archived; startup.log retains run history.\nArchive status: %s\n",build,run,ok?"OK":"incomplete; some files may be from a prior run");
 return write_note(path,note)&&ok;
}
inline std::atomic<int> state{0}; // 1 listening; negative errno on startup failure
inline std::atomic<bool> stopping{false};
inline int listener=-1;
inline pthread_t thread{};
inline bool send_all(int fd,const char *data,size_t size) {
 while(size) {
#ifdef MSG_NOSIGNAL
  ssize_t n=send(fd,data,size,MSG_NOSIGNAL);
#else
  ssize_t n=send(fd,data,size,0);
#endif
  if(n<0&&errno==EINTR)continue;
  if(n<=0)return false;
  data+=n;size-=static_cast<size_t>(n);
 }
 return true;
}
inline bool header(int fd,int code,const char *reason,const char *type,long long length) {
 char text[512];int n=std::snprintf(text,sizeof(text),
  "HTTP/1.1 %d %s\r\nContent-Type: %s\r\nContent-Length: %lld\r\nCache-Control: no-store\r\nX-Content-Type-Options: nosniff\r\nConnection: close\r\n\r\n",code,reason,type,length);
 return send_all(fd,text,static_cast<size_t>(n));
}
inline void reply(int fd,int code,const char *reason,const char *body,const char *type="text/plain; charset=utf-8") {
 if(header(fd,code,reason,type,std::strlen(body)))send_all(fd,body,std::strlen(body));
}
inline void serve(int fd,const Entry *available=files,size_t count=sizeof(files)/sizeof(files[0])) {
 timeval timeout{5,0};setsockopt(fd,SOL_SOCKET,SO_RCVTIMEO,&timeout,sizeof(timeout));setsockopt(fd,SOL_SOCKET,SO_SNDTIMEO,&timeout,sizeof(timeout));
#ifdef SO_NOSIGPIPE
 int yes=1;setsockopt(fd,SOL_SOCKET,SO_NOSIGPIPE,&yes,sizeof(yes));
#endif
 char request[4096]{};size_t used=0;
 while(used<sizeof(request)-1&&!std::strstr(request,"\r\n\r\n")) {
  ssize_t n=recv(fd,request+used,sizeof(request)-1-used,0);
  if(n<0&&errno==EINTR)continue;
  if(n<=0)return;
  used+=static_cast<size_t>(n);request[used]=0;
 }
 if(!std::strstr(request,"\r\n\r\n")){reply(fd,431,"Request Header Fields Too Large","Request too large\n");return;}
 char method[16]{},url[256]{},version[16]{};
 if(std::sscanf(request,"%15s %255s %15s",method,url,version)!=3){reply(fd,400,"Bad Request","Bad request\n");return;}
 if(std::strcmp(method,"GET")){reply(fd,405,"Method Not Allowed","GET only\n");return;}
 if(!std::strcmp(url,"/")) {
  reply(fd,200,"OK","<!doctype html><meta charset=utf-8><title>PS5 probe logs</title><h1>PS5 probe logs</h1><p>Read-only LAN downloads. Keep the probe open. Refresh to collect newer output. Missing files return 404. Build identifies the open app; session identifies the recorded run. Startup log contains historical runs.</p><ul><li><a href=/build.txt>Open app build</a><li><a href=/session.txt>Recorded run status</a><li><a href=/startup.log>Startup log</a><li><a href=/vm-trace.log>Native VM trace</a><li><a href=/server.log>Full Minecraft console</a><li><a href=/abort.txt>Last JVM abort</a><li><a href=/hs-error.log>JVM fatal error report</a><li><a href=/previous-hs-error.log>Previous JVM fatal error report</a><li><a href=/exception.txt>Current-run probe exception</a><li><a href=/previous-exception.txt>Previous-run exception</a><li><a href=/previous-abort.txt>Previous-run abort</a><li><a href=/previous-server.log>Previous-run server output</a></ul>","text/html; charset=utf-8");return;
 }
 const char *path=nullptr;for(size_t i=0;i<count;++i)if(!std::strcmp(url,available[i].url))path=available[i].path;
 if(!path){reply(fd,404,"Not Found","Unknown log\n");return;}
 int file=open(path,O_RDONLY);if(file<0){reply(fd,404,"Not Found","Log not created or unavailable\n");return;}
 struct stat info{};
 if(fstat(file,&info)||!S_ISREG(info.st_mode)||info.st_size<0){close(file);reply(fd,500,"Internal Server Error","Cannot read log\n");return;}
 // Bound this response to its initial size, even when the writer keeps appending.
 off_t left=info.st_size;
 if(header(fd,200,"OK","text/plain; charset=utf-8",static_cast<long long>(left))) {
  char block[16384];while(left>0){size_t size=left<static_cast<off_t>(sizeof(block))?static_cast<size_t>(left):sizeof(block);ssize_t n=read(file,block,size);if(n<0&&errno==EINTR)continue;if(n<=0||!send_all(fd,block,static_cast<size_t>(n)))break;left-=n;}
 }
 close(file);
}
inline void *worker(void *) {
 while(!stopping.load()) {int fd=accept(listener,nullptr,nullptr);if(fd<0){if(errno==EINTR)continue;break;}serve(fd);close(fd);}
 return nullptr;
}
inline void start(unsigned short port=8765) {
 listener=socket(AF_INET,SOCK_STREAM,0);if(listener<0){state=-errno;return;}
 int yes=1;setsockopt(listener,SOL_SOCKET,SO_REUSEADDR,&yes,sizeof(yes));
 sockaddr_in address{};
#if defined(__APPLE__) || defined(__FreeBSD__) || defined(__PROSPERO__)
 address.sin_len=sizeof(address);
#endif
 address.sin_family=AF_INET;address.sin_addr.s_addr=htonl(INADDR_ANY);address.sin_port=htons(port);
 if(bind(listener,reinterpret_cast<sockaddr *>(&address),sizeof(address))||listen(listener,4)){int error=errno;close(listener);listener=-1;state=-error;return;}
 stopping=false;int error=pthread_create(&thread,nullptr,worker,nullptr);
 if(error){close(listener);listener=-1;state=-error;return;}state=1;
}
inline void stop() {if(state!=1)return;stopping=true;shutdown(listener,SHUT_RDWR);pthread_join(thread,nullptr);close(listener);listener=-1;state=0;}
}
