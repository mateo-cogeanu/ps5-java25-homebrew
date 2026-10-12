/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <atomic>
#include <cstdint>
#include <cstdio>
#include <pthread.h>
extern "C" {
int sceAudioOutInit();
int sceAudioOutOpen(int,int,int,unsigned,unsigned,unsigned);
int sceAudioOutOutput(int,const void*);
int sceAudioOutClose(int);
}
namespace ps5::menu_audio {
// One paced output stream; files are converted to 48 kHz stereo S16LE at packaging.
inline constexpr bool effects_enabled=false;
inline std::atomic<bool> running{false};
inline std::atomic<unsigned> selection{0};
inline std::atomic<int> state{0}; // 1 playing, negative platform error
inline pthread_t thread{};
inline bool started=false;
inline int port=-1;
inline std::atomic<int> phase{0}; // 1 init, 2 open, 3 output, 4 worker, 5 music file, 6 selection file
inline const char* phase_name() {
 switch(phase.load()) {
 case 1:return "AudioOutInit";case 2:return "AudioOutOpen";case 3:return "AudioOutOutput";
 case 4:return "audio thread";case 5:return "music file";case 6:return "selection file";
 default:return "starting";
 }
}
inline void log_result(const char* operation,int code) {
 FILE* f=std::fopen("/download0/java25-audio.log","a");
 if(f) {std::fprintf(f,"%s: %08X\n",operation,static_cast<unsigned>(code));std::fclose(f);}
}
inline const char* music_path="/app0/assets/sounds/menu_music.pcm";
inline const char* select_path="/app0/assets/sounds/sel.pcm";
inline std::int16_t mix(std::int16_t music,std::int16_t effect) {
 int value=static_cast<int>(music)*35/100+static_cast<int>(effect)*70/100;
 return static_cast<std::int16_t>(value>32767?32767:value<-32768?-32768:value);
}
inline void* worker(void*) {
 FILE* music=std::fopen(music_path,"rb");
 FILE* effect=effects_enabled?std::fopen(select_path,"rb"):nullptr;
 if(!music||(effects_enabled&&!effect)) {
  phase.store(!music?5:6);state.store(-1);log_result(phase_name(),-1);
  if(music) std::fclose(music);
  if(effect) std::fclose(effect);
  sceAudioOutClose(port);return nullptr;
 }
 int rc=0;
 phase.store(3);
 state.store(1);
 unsigned seen=0;bool effect_active=false;
 alignas(64) std::int16_t background[512]{},fx[512]{},out[512]{};
 while(running.load()) {
  unsigned requested=selection.load();
  if(requested!=seen) {seen=requested;std::rewind(effect);effect_active=true;}
  size_t count=std::fread(background,sizeof(background[0]),512,music);
  if(count<512) {
   if(std::ferror(music)) {state.store(-2);break;}
   std::rewind(music);
   size_t more=std::fread(background+count,sizeof(background[0]),512-count,music);
   for(size_t i=count+more;i<512;++i) background[i]=0;
  }
  size_t n=effect_active?std::fread(fx,sizeof(fx[0]),512,effect):0;
  if(n<512) effect_active=false;
  for(size_t i=0;i<512;++i) out[i]=mix(background[i],i<n?fx[i]:0);
  rc=sceAudioOutOutput(port,out);
  if(rc<0) {state.store(rc);log_result("AudioOutOutput",rc);break;}
 }
 sceAudioOutOutput(port,nullptr);sceAudioOutClose(port);
 std::fclose(music);if(effect) std::fclose(effect);return nullptr;
}
inline void start(int) {
 if(started) return;
 // Match the PS5 SDL setup: initialize/open before the streaming thread and
 // use SYSTEM (0xff), independently of the controller's logged-in user.
 phase.store(1);
 int rc=sceAudioOutInit();log_result("AudioOutInit",rc);
 if(rc<0) {state.store(rc);return;}
 phase.store(2);
 port=sceAudioOutOpen(0xff,0,0,256,48000,1);log_result("AudioOutOpen SYSTEM",port);
 if(port<0) {state.store(port);return;}
 running.store(true);phase.store(4);
 rc=pthread_create(&thread,nullptr,worker,nullptr);
 if(rc) {running.store(false);state.store(-rc);log_result("audio thread",-rc);sceAudioOutClose(port);return;}
 started=true;
}
inline void selected() {if(effects_enabled) selection.fetch_add(1);}
inline void stop() {
 if(!started) return;
 running.store(false);pthread_join(thread,nullptr);started=false;
}
}
