/* SPDX-License-Identifier: GPL-3.0-or-later */
#include "demo_renderer.hpp"
#include "../../native/menu_audio.hpp"
#include "pad.h"
#include <atomic>
#include <cstdarg>
#include <cerrno>
#include <cstdio>
#include <cstring>
#include <fcntl.h>
#include <pthread.h>
#include <signal.h>
#include "jni.h"
#include "native_trace.hpp"
using Initializer=void (*)();
extern "C" Initializer __jvm_init_array_start[],__jvm_init_array_end[];
#include <sys/mman.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <time.h>
#include <unistd.h>
extern "C" std::uint64_t sceKernelGetProcessTime();
extern "C" int sceKernelUsleep(std::uint32_t);
// File-open diagnostics specific to this probe; the real platform API is used.
static char native_open_error[192]{};
#ifdef __PROSPERO__
extern "C" int __real_open(const char *,int,...);
extern "C" int __wrap_open(const char *path,int flags,...) {
 mode_t mode=0;
 if(flags&O_CREAT) {va_list args;va_start(args,flags);mode=static_cast<mode_t>(va_arg(args,int));va_end(args);}
 int fd=__real_open(path,flags,mode);
 int error=errno;
 if(fd<0 && ps5_native_trace::enabled.load() &&
    pthread_equal(ps5_native_trace::owner,pthread_self()) &&
    !ps5_vm_trace_io_active() && path && std::strncmp(path,"/download0/",11)==0) {
  // IO guard prevents the trace writer's own open from replacing this result.
  Ps5TraceIOScope guard;
  std::snprintf(native_open_error,sizeof(native_open_error),
    "Native open: flags=0x%X mode=0%o fd=%d errno=%d",flags,static_cast<unsigned>(mode),fd,error);
  ps5_vm_trace(native_open_error);
 }
 errno=error;return fd;
}
#endif
namespace {
using ps5::demo::Canvas;
constexpr std::uint32_t rgb(unsigned r,unsigned g,unsigned b) {return 0xff000000u|r|(g<<8)|(b<<16);}
constexpr int test_count=4;
const char *names[]={"Initialize embedded core runtime","Create Java 25 VM (interpreter mode)","ZIP entries and JAR class / resource loading","Destroy Java VM"};
int status[test_count]{}; // 0 untested, 1 pass, -1 fail, 2 running
char messages[test_count][104]{};
int selected=0,pending=-1,pad=-1;
std::uint32_t previous=0;
bool initialized=false;
JavaVM *java_vm=nullptr;
JNIEnv *java_env=nullptr;
FILE *startup_log=nullptr;
char exception_detail[768]{};
char previous_log[7][160]={{},{},{},{},{},{},"No previous startup log."};
struct NativeTraceScope {
 NativeTraceScope() {
#ifdef __PROSPERO__
  ps5_vm_reset_native_call_record();
#endif
  ps5_native_trace::enable();
 }
 ~NativeTraceScope() {ps5_native_trace::disable();}
};
void log_stage(const char *stage) {
#ifdef __PROSPERO__
 ps5_vm_trace(stage);
#endif
 if(startup_log) {std::fprintf(startup_log,"STAGE: %s\n",stage);std::fflush(startup_log);}
}
int vm_print(FILE *,const char *format,va_list arguments) {
 if(!startup_log) return 0;
 int count=std::vfprintf(startup_log,format,arguments);std::fflush(startup_log);return count;
}
void vm_exit(int code) {
 if(startup_log) {std::fprintf(startup_log,"VM EXIT: %d\n",code);std::fflush(startup_log);}
}
void vm_abort() {log_stage("VM ABORT");}
bool read_last_line(const char *path) {
 FILE *file=std::fopen(path,"r");if(!file) return false;
 bool found=false;char line[256]{};
 char recent[7][160]{};
 while(std::fgets(line,sizeof(line),file)) {
  size_t length=std::strlen(line);while(length && (line[length-1]=='\n'||line[length-1]=='\r')) line[--length]='\0';
  if(length) {
   for(int i=0;i<6;++i) std::memcpy(recent[i],recent[i+1],sizeof(recent[i]));
   std::snprintf(recent[6],sizeof(recent[6]),"%.159s",line);found=true;
  }
 }
 if(found) std::memcpy(previous_log,recent,sizeof(previous_log));
 std::fclose(file);return found;
}
void read_previous_log() {
 read_last_line("/download0/java25-startup.log");
 read_last_line("/download0/java25-vm-trace.log");
}

void result(int i,int rc,const char *message) {
 status[i]=rc==0?1:-1;
 std::snprintf(messages[i],sizeof(messages[i]),"%s / code %08X",message,static_cast<unsigned>(rc));
}
void java_failure(int i,int code,const char* phase) {
 // Keep the original exception alive while obtaining its actual Java text.
 jthrowable original=java_env->ExceptionOccurred();
 java_env->ExceptionClear();
 char detail[768]="Java exception text unavailable";
 if(original) {
  jclass type=java_env->GetObjectClass(original);
  jmethodID method=type?java_env->GetMethodID(type,"toString","()Ljava/lang/String;"):nullptr;
  jstring text=method?static_cast<jstring>(java_env->CallObjectMethod(original,method)):nullptr;
  if(text&&!java_env->ExceptionCheck()) {
   const char* utf=java_env->GetStringUTFChars(text,nullptr);
   if(utf) {std::snprintf(detail,sizeof(detail),"%s",utf);java_env->ReleaseStringUTFChars(text,utf);}
  }
  if(java_env->ExceptionCheck()) java_env->ExceptionClear();
  if(text) java_env->DeleteLocalRef(text);
  if(type) java_env->DeleteLocalRef(type);
  java_env->Throw(original);
  java_env->ExceptionDescribe();java_env->ExceptionClear();
  java_env->DeleteLocalRef(original);
 }
 std::snprintf(exception_detail,sizeof(exception_detail),"%s: %s",phase,detail);
 char message[80];std::snprintf(message,sizeof(message),"%.20s: %.48s",phase,detail);
 if(startup_log) {std::fprintf(startup_log,"ZIP/JAR FAILURE: %s: %s / code %08X\n",phase,detail,static_cast<unsigned>(code));std::fflush(startup_log);}
 result(i,code,message);
}
void skip_vm_dependents() {
 for(int i=2;i<test_count;++i) {
  status[i]=3;
  std::snprintf(messages[i],sizeof(messages[i]),"Not run: VM creation did not succeed.");
 }
}
void run_test(int i) {
 if(i==0) {
  startup_log=std::fopen("/download0/java25-startup.log","a");
  if(!startup_log) {result(i,errno,"Cannot open persistent startup log");return;}
  log_stage("Begin embedded core constructors");
  size_t count=0;
  for(auto *fn=__jvm_init_array_start;fn!=__jvm_init_array_end;++fn) {if(*fn) {(*fn)();++count;}}
  initialized=true;log_stage("Embedded constructors complete");
  long page_size=sysconf(_SC_PAGESIZE);
  if(startup_log) {std::fprintf(startup_log,"Runtime constructors: %zu; page size: %ld bytes\n",count,page_size);std::fflush(startup_log);}
  char text[80]{};std::snprintf(text,sizeof(text),"%zu constructors; OS page size: %ld bytes",count,page_size);
  result(i,0,text);
 } else if(!initialized) {
  result(i,-1301,"Initialize runtime first, then relaunch to retry");
 } else if(i==1) {
  // Check the actual read operation; access() may have different sandbox
  // permission behavior. Distinguish preflight errors from JNI returns.
  log_stage("Opening packaged Java core image");
  errno=0;
  FILE *image=std::fopen("/app0/assets/java25/lib/modules","rb");
  if(!image) {
   int error=errno?errno:-1310;
   if(startup_log) {std::fprintf(startup_log,"PREFLIGHT: core image fopen failed, code %08X\n",static_cast<unsigned>(error));std::fflush(startup_log);}
   result(i,error,"Before JVM: core image fopen failed");skip_vm_dependents();read_previous_log();return;
  }
  unsigned char header[4]{};
  size_t read=std::fread(header,1,sizeof(header),image);
  int error=errno;
  std::fclose(image);
  const unsigned char magic[]={0xda,0xda,0xfe,0xca};
  if(read!=sizeof(header)||std::memcmp(header,magic,sizeof(magic))!=0) {
   int code=read!=sizeof(header)?(error?error:-1311):-1312;
   log_stage("Core image read or magic check failed before JNI call");
   result(i,code,"Before JVM: core image read / magic failed");skip_vm_dependents();read_previous_log();return;
  }
  log_stage("Core image opened and JIMAGE header verified");
  JavaVMOption options[]={
   {const_cast<char *>("-Xint"),nullptr},
   {const_cast<char *>("-XX:UseAVX=0"),nullptr},
   {const_cast<char *>("-XX:UseSSE=2"),nullptr},
   {const_cast<char *>("-Xms16m"),nullptr},
   {const_cast<char *>("-Xmx128m"),nullptr},
   // Bootstrap class metadata needs far less than the default 1 GiB reservation.
   {const_cast<char *>("-XX:CompressedClassSpaceSize=32m"),nullptr},
   {const_cast<char *>("-Xshare:off"),nullptr},
   {const_cast<char *>("-XX:+UseSerialGC"),nullptr},
   {const_cast<char *>("-XX:ActiveProcessorCount=2"),nullptr},
   {const_cast<char *>("-XX:-UsePerfData"),nullptr},
   {const_cast<char *>("-XX:ErrorFile=/download0/hs_err_java25_%p.log"),nullptr},
   {const_cast<char *>("-Djava.class.path=/app0/assets/java25/classes"),nullptr},
   {const_cast<char *>("-Djava.io.tmpdir=/download0"),nullptr},
   {const_cast<char *>("-Duser.home=/download0"),nullptr},
   {const_cast<char *>("-Duser.dir=/app0"),nullptr},
   // Always resolve relative paths against user.dir. UnixFileSystem then
   // skips its desktop getcwd comparison in the native title sandbox.
   {const_cast<char *>("-Dsun.nio.fs.chdirAllowed=true"),nullptr},
   {const_cast<char *>("-Dsun.nio.fs.ps5Sandbox=true"),nullptr},
   {const_cast<char *>("-Duser.timezone=UTC"),nullptr},
   {const_cast<char *>("vfprintf"),reinterpret_cast<void *>(&vm_print)},
   {const_cast<char *>("exit"),reinterpret_cast<void *>(&vm_exit)},
   {const_cast<char *>("abort"),reinterpret_cast<void *>(&vm_abort)}
  };
  JavaVMInitArgs args{};args.version=JNI_VERSION_24;
  args.nOptions=sizeof(options)/sizeof(options[0]);args.options=options;args.ignoreUnrecognized=JNI_FALSE;
  // Verify the raw diagnostic write path before entering JVM code. Each
  // VM milestone then appends a line without stdio or JVM allocation.
  int trace_fd=open("/download0/java25-vm-trace.log",O_CREAT|O_WRONLY|O_TRUNC,0600);
  if(trace_fd<0) {result(i,errno,"Before JVM: cannot open checkpoint trace");skip_vm_dependents();return;}
  const char begin[]="APP: entering JNI_CreateJavaVM\n";
  ssize_t traced=write(trace_fd,begin,sizeof(begin)-1);
  int trace_error=errno;close(trace_fd);
  if(traced!=sizeof(begin)-1) {result(i,trace_error?trace_error:-1313,"Before JVM: checkpoint write failed");skip_vm_dependents();return;}
  log_stage("Calling real JNI_CreateJavaVM");
  ps5_native_trace::enable();
  int rc=JNI_CreateJavaVM(&java_vm,reinterpret_cast<void **>(&java_env),&args);
  ps5_native_trace::disable();
  if(startup_log) {std::fprintf(startup_log,"JNI_CreateJavaVM returned %d\n",rc);std::fflush(startup_log);}
  if(rc==JNI_OK && (!java_vm||!java_env)) rc=-1302;
  if(rc!=JNI_OK) {java_vm=nullptr;java_env=nullptr;skip_vm_dependents();read_previous_log();}
  result(i,rc,"Real JNI_CreateJavaVM, -Xint, 128 MiB max heap");
 } else if(!java_vm||!java_env) {
  result(i,-1303,"Create the VM first; relaunch to retry");
 } else if(i==2) {
  NativeTraceScope trace_scope;
  log_stage("Reading packaged ZipJar25 bytecode directly");
  // Bootstrap bytecode execution independently of desktop class-path file discovery.
  static unsigned char class_bytes[64*1024];
  FILE* class_file=std::fopen("/app0/assets/java25/classes/ZipJar25.class","rb");
  if(!class_file) {result(i,errno?errno:-1314,"ZipJar25 bytecode fopen failed");return;}
  size_t class_size=std::fread(class_bytes,1,sizeof(class_bytes),class_file);
  bool bad_read=std::ferror(class_file)||!std::feof(class_file);
  std::fclose(class_file);
  if(bad_read||class_size<8||class_bytes[0]!=0xca||class_bytes[1]!=0xfe||
     class_bytes[2]!=0xba||class_bytes[3]!=0xbe||class_bytes[6]!=0||class_bytes[7]!=69) {
   result(i,-1315,"ZipJar25 read / Java 25 format check failed");return;
  }
  log_stage("Obtaining actual system class loader");
  jclass loader_class=java_env->FindClass("java/lang/ClassLoader");
  jmethodID get_loader=loader_class?java_env->GetStaticMethodID(loader_class,"getSystemClassLoader","()Ljava/lang/ClassLoader;"):nullptr;
  jobject loader=get_loader?java_env->CallStaticObjectMethod(loader_class,get_loader):nullptr;
  if(!loader||java_env->ExceptionCheck()) {
   java_failure(i,-1316,"system class loader");
   if(loader_class) java_env->DeleteLocalRef(loader_class);
   if(loader) java_env->DeleteLocalRef(loader);
   return;
  }
  log_stage("Defining ZipJar25 in the system class loader");
  jclass klass=java_env->DefineClass("ZipJar25",loader,reinterpret_cast<const jbyte*>(class_bytes),static_cast<jsize>(class_size));
  java_env->DeleteLocalRef(loader);java_env->DeleteLocalRef(loader_class);
  if(!klass||java_env->ExceptionCheck()) {java_failure(i,-1304,"DefineClass ZipJar25");return;}
  jmethodID method=java_env->GetStaticMethodID(klass,"main","([Ljava/lang/String;)V");
  if(!method||java_env->ExceptionCheck()) {java_failure(i,-1305,"main method lookup");java_env->DeleteLocalRef(klass);return;}
  jclass string_class=java_env->FindClass("java/lang/String");
  jobjectArray arguments=string_class?java_env->NewObjectArray(0,string_class,nullptr):nullptr;
  if(!arguments||java_env->ExceptionCheck()) {java_failure(i,-1306,"argument array");if(string_class) java_env->DeleteLocalRef(string_class);java_env->DeleteLocalRef(klass);return;}
  log_stage("Calling ZipJar25.main");
  java_env->CallStaticVoidMethod(klass,method,arguments);
  bool failed=java_env->ExceptionCheck();
  if(failed) java_failure(i,-1307,"ZipJar25.main");
  java_env->DeleteLocalRef(arguments);java_env->DeleteLocalRef(string_class);java_env->DeleteLocalRef(klass);
  log_stage(failed?"ZipJar25 threw exception":"ZipJar25 returned normally");
  if(!failed) result(i,0,"Stored / deflated ZIP, JAR class and resource PASS");
 } else {
  NativeTraceScope trace_scope;
  log_stage("Calling DestroyJavaVM");
  int rc=java_vm->DestroyJavaVM();
  if(rc==JNI_OK) {java_vm=nullptr;java_env=nullptr;}
  log_stage(rc==JNI_OK?"DestroyJavaVM complete":"DestroyJavaVM returned an error");
  result(i,rc,"Real DestroyJavaVM, application UI stays active");
 }
}
bool update() noexcept {
 if(pending>=0) {int i=pending;pending=-1;run_test(i);return true;}
 if(pad<0) return false;
 static int last_audio=0;
 int current_audio=ps5::menu_audio::state.load();
 bool changed=current_audio!=last_audio;last_audio=current_audio;
 PadSample batch[64]{};int count=scePadRead(pad,batch,64);
 if(count<0||count>64) return false;
 for(int i=0;i<count;++i) {
  auto buttons=batch[i].connected && !(batch[i].buttons&0x80000000u)?batch[i].buttons:0;
  auto pressed=buttons&~previous;previous=buttons;
  if(pressed&0x10) {selected=(selected+test_count-1)%test_count;ps5::menu_audio::selected();changed=true;}
  if(pressed&0x40) {selected=(selected+1)%test_count;ps5::menu_audio::selected();changed=true;}
  if((pressed&0x4000)&&status[selected]==0) {
   ps5::menu_audio::selected();
   status[selected]=2;pending=selected;
   // Present RUN before calling the OS, and schedule only one test per batch.
   return true;
  }
 }
 return changed;
}
void draw(Canvas &c) noexcept {
 c.gradient(rgb(18,29,49),rgb(8,13,23));
 c.label(100,64,"Java 25 - ZIP / JAR 01.000.000",64,rgb(238,242,250));
 c.label(103,163,"Experimental VM creation and ZipJar25. Run one stage at a time.",24,rgb(139,153,178));
 for(int i=0;i<test_count;++i) {
  int y=248+i*112;
  if(selected==i) c.rounded(95,y-4,1730,100,22,rgb(109,156,255));
  c.rounded(100,y,1720,92,19,rgb(25,34,51));
  c.label(124,y+8,names[i],30,rgb(238,242,250));
  c.label(125,y+52,messages[i][0]?messages[i]:"Select and press X to run this test.",20,rgb(139,153,178));
  c.label(1650,y+25,status[i]==1?"PASS":status[i]==-1?"FAIL":status[i]==2?"RUN":status[i]==3?"SKIP":"--",24,status[i]==1?rgb(105,215,172):status[i]==-1?rgb(230,176,91):rgb(139,153,178));
 }
 int audio_state=ps5::menu_audio::state.load();
 if(audio_state<0) {
  char audio_error[80];std::snprintf(audio_error,sizeof(audio_error),"Audio: %s / code %08X",ps5::menu_audio::phase_name(),static_cast<unsigned>(audio_state));
  c.label(103,736,audio_error,20,rgb(230,176,91));
 }
 if(exception_detail[0]) {
  c.label(103,768,"Java exception (full message):",24,rgb(230,176,91));
  // Fixed-width chunks keep native method signatures visible on the TV.
  for(size_t offset=0,line=0;exception_detail[offset]&&line<7;++line) {
   char chunk[105]{};
   size_t count=std::strlen(exception_detail+offset);if(count>104) count=104;
   std::memcpy(chunk,exception_detail+offset,count);offset+=count;
   c.label(103,800+static_cast<int>(line)*21,chunk,18,rgb(238,242,250));
  }
 } else {
  c.label(103,768,"Last startup checkpoints (oldest to newest):",24,rgb(139,153,178));
  for(int i=0;i<7;++i) c.label(103,800+i*21,previous_log[i],18,rgb(238,242,250));
 }
 if(native_open_error[0]) c.label(103,925,native_open_error,18,rgb(230,176,91));
 c.label(103,954,"D-pad: select   X: run selected test   PS: close game",24,rgb(139,153,178));
 c.label(103,1004,"After a crash, relaunch and photograph the seven startup checkpoints shown above.",20,rgb(139,153,178));
}
}
int main() {
 read_previous_log();
 sceUserServiceInitialize(nullptr);std::int32_t user=-1;
 if(sceUserServiceGetInitialUser(&user)>=0 && scePadInit()>=0) pad=scePadOpen(user,0,0,nullptr);
 ps5::menu_audio::start(user);
 ps5::demo::run_ui(draw,update,"Java 25 VM startup attempt ready");
 ps5::menu_audio::stop();
}
