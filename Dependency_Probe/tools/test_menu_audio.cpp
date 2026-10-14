/* SPDX-License-Identifier: GPL-3.0-or-later */
// Test actual streaming/mixing loop through a synthetic AudioOut sink.
#include "../native/menu_audio.hpp"
#include <cassert>
#include <unistd.h>
std::atomic<bool> clean_music{false},effect_mix{false};
int init_result=0,open_result=19;
pthread_t setup_thread{};
extern "C" int sceAudioOutInit(){assert(pthread_equal(pthread_self(),setup_thread));return init_result;}
extern "C" int sceAudioOutOpen(int user,int type,int index,unsigned frames,unsigned rate,unsigned format) {
 assert(pthread_equal(pthread_self(),setup_thread));
 assert(user==0xff&&type==0&&index==0&&frames==256&&rate==48000&&format==1);return open_result;
}
extern "C" int sceAudioOutOutput(int port,const void* data) {
 assert(port==19);if(!data)return 0;
 auto* samples=static_cast<const std::int16_t*>(data);
 if(samples[0]==7000)clean_music.store(true);
 assert(samples[0]==7000);
 usleep(1000);return 0;
}
extern "C" int sceAudioOutClose(int port){assert(port==19);return 0;}
int main() {
 using namespace ps5::menu_audio;
 assert(mix(-32768,-32768)==-32768);assert(mix(32767,32767)==32767);assert(mix(20000,0)==7000);
 auto write_pcm=[](const char* path,int value,int count){
  FILE* f=std::fopen(path,"wb");assert(f);std::int16_t v=static_cast<std::int16_t>(value);
  for(int i=0;i<count;++i)assert(std::fwrite(&v,2,1,f)==1);
  std::fclose(f);
 };
 music_path="build/java25/test-music.pcm";select_path="build/java25/test-sel.pcm";
 write_pcm(music_path,20000,1024);write_pcm(select_path,30000,512);
 setup_thread=pthread_self();
 init_result=static_cast<int>(0x80260011u);start(7);
 assert(!started&&state.load()==init_result&&phase.load()==1);
 init_result=0;open_result=static_cast<int>(0x80260011u);start(7);
 assert(!started&&state.load()==open_result&&phase.load()==2);
 open_result=19;start(7);
 for(int i=0;i<1000&&!clean_music.load();++i)usleep(1000);
 assert(clean_music.load());selected();
 assert(selection.load()==0);
 usleep(10000);
 stop();assert(!started);
 std::remove(music_path);std::remove(select_path);
 std::puts("PASS: setup thread, SYSTEM user, init/open error stages, stereo output config, 35% music gain, streaming loop, disabled selection effects and shutdown");
}
