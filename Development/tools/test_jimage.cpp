/* SPDX-License-Identifier: GPL-2.0-only
 * Run the actual patched image reader on the host. Inject mapping failures
 * to exercise the PS5 fallback; this is not console VM execution evidence.
 */
#include "jimage.hpp"
#include "imageDecompressor.hpp"
#include <cstdlib>
#include <cstdint>
#include <sys/mman.h>
#include <cerrno>
#include <cassert>
#include <cstdio>
#include <vector>
#include <fstream>
#include <iterator>
#include <string>
#include <zlib.h>
#include <cstring>
extern "C" void zip_test_mode(int,int);
extern "C" int zip_test_live();
extern "C" int zip_test_maps();
extern "C" jboolean ZIP_InflateFully(void*,jlong,void*,jlong,char**);
static bool image_deny=false;
static int image_budget=-1,image_live=0,image_maps=0;
extern "C" void* image_test_malloc(size_t n) {if(image_deny){errno=ENOMEM;return nullptr;}return malloc(n);}
extern "C" void image_test_free(void* p) {free(p);}
extern "C" void* image_test_map(void* p,size_t n,int prot,int flags,int fd,off_t off) {
 assert(fd==-1&&n%16384==0);if(image_budget==0){errno=ENOMEM;return MAP_FAILED;}if(image_budget>0)--image_budget;
 p=mmap(p,n,prot,flags,fd,off);if(p!=MAP_FAILED){++image_live;++image_maps;}return p;
}
extern "C" int image_test_unmap(void* p,size_t n) {int rc=munmap(p,n);if(!rc)--image_live;return rc;}
static bool reject_file=false,reject_anonymous=false;
static unsigned file_mappings=0,anonymous_mappings=0;
extern "C" void *ps5_test_mmap(void *p,size_t size,int protection,int flags,int fd,off_t offset) {
 if(fd>=0) ++file_mappings; else ++anonymous_mappings;
 if((fd>=0 && reject_file)||(fd<0 && reject_anonymous)) {errno=EPERM;return MAP_FAILED;}
 return mmap(p,size,protection,flags,fd,offset);
}
void read_object(const char *expected_root) {
 jint error=0;
 auto *image=JIMAGE_Open("build/java25/boot-image/lib/modules",&error);
 assert(image);
 jlong size=0;
 auto location=JIMAGE_FindResource(image,"java.base","25","java/lang/Object.class",&size);
 assert(location && size>8);
 std::vector<unsigned char> bytes(static_cast<size_t>(size));
 assert(JIMAGE_GetResource(image,location,reinterpret_cast<char *>(bytes.data()),size)==size);
 assert(bytes[0]==0xca && bytes[1]==0xfe && bytes[2]==0xba && bytes[3]==0xbe);
 assert(bytes[6]==0 && bytes[7]==69);
 const char *resources[][2]={{"java.base","java/lang/String.class"},{"java.base","java/lang/Object.class"},{"java.base","sun/security/ssl/SSLSocketImpl.class"},{"java.base","sun/security/ssl/DTLSInputRecord.class"},{"java.base","javax/net/ssl/HttpsURLConnection$DefaultHostnameVerifier.class"},{"java.base","sun/net/www/protocol/https/DelegateHttpsURLConnection.class"},{"jdk.jfr","jdk/jfr/internal/types/metadata.bin"},{"java.desktop","java/awt/Color.class"}};
 for(auto &resource:resources){
  auto location=JIMAGE_FindResource(image,resource[0],"25",resource[1],&size);assert(location && size>0);
  std::vector<char> actual(static_cast<size_t>(size));assert(JIMAGE_GetResource(image,location,actual.data(),size)==size);
  std::ifstream input(std::string(expected_root)+"/"+resource[0]+"/"+resource[1],std::ios::binary);assert(input);
  std::vector<char> expected((std::istreambuf_iterator<char>(input)),{});assert(actual==expected);
 }
 JIMAGE_Close(image);
}
void test_tiny_terminal() {
 unsigned char name[]={'z','i','p',0};ImageStrings strings(name,sizeof(name));
 for(size_t length: {size_t(1),size_t(8),size_t(28)}) {
  std::vector<unsigned char> data(length,0x42);uLongf count=compressBound(length);
  std::vector<unsigned char> packed(29+count);assert(compress2(packed.data()+29,&count,data.data(),length,6)==Z_OK);
  auto put=[&](size_t at,uint64_t value,int bytes){for(int i=0;i<bytes;i++)packed[at+i]=(value>>(8*i))&255;};
  put(0,0xCAFEFAFA,4);put(4,count,8);put(12,length,8);put(20,0,4);put(24,0,4);packed[28]=1;
  std::vector<unsigned char> output(length);assert(ImageDecompressor::decompress_resource(packed.data(),output.data(),length,&strings,Endian::get_handler(false)));assert(output==data);
 }
}
void test_inflater() {
 std::vector<unsigned char> input(50000);for(size_t i=0;i<input.size();i++)input[i]=(i*31+i/101)&255;
 uLongf n=compressBound(input.size());std::vector<unsigned char> compressed(n);assert(compress2(compressed.data(),&n,input.data(),input.size(),6)==Z_OK);compressed.resize(n);
 std::vector<unsigned char> output(input.size());char *error=nullptr;
 for(int denied=0;denied<2;denied++) {zip_test_mode(denied,-1);assert(ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(output==input);assert(zip_test_live()==0);}
 zip_test_mode(1,0);assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);
 zip_test_mode(1,-1);assert(!ZIP_InflateFully(compressed.data(),n-2,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);
 compressed[0]^=255;assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size(),&error));assert(error&&zip_test_live()==0);compressed[0]^=255;
 assert(!ZIP_InflateFully(compressed.data(),n,output.data(),output.size()-1,&error));assert(error&&zip_test_live()==0);
 zip_test_mode(0,-1);
}
int main(int argc,char **argv) {
 assert(argc==2);
 test_inflater();
 test_tiny_terminal();
 read_object(argv[1]);
 reject_file=true;
 read_object(argv[1]);
 assert(file_mappings==0 && anonymous_mappings==2);
 zip_test_mode(1,-1);read_object(argv[1]);assert(zip_test_maps()>0&&zip_test_live()==0);
 jint image_error=0;auto *image=JIMAGE_Open("build/java25/boot-image/lib/modules",&image_error);assert(image);
 jlong bytes=0;auto location=JIMAGE_FindResource(image,"java.base","25","sun/security/ssl/DTLSInputRecord.class",&bytes);assert(location);
 std::vector<char> buffer(bytes,0x5a);zip_test_mode(1,0);assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==0);
 for(char b:buffer)assert(b==0x5a);assert(zip_test_live()==0);
 zip_test_mode(1,-1);assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==bytes);assert((unsigned char)buffer[0]==0xca);assert(zip_test_live()==0);JIMAGE_Close(image);
 // Resident images need one decoded resource buffer. Its allocation refusal
 // must return0, preserve caller bytes and release all mappings.
 image_deny=true;image_budget=-1;read_object(argv[1]);assert(image_maps>0&&image_live==0);
 image=JIMAGE_Open("build/java25/boot-image/lib/modules",&image_error);assert(image);
 location=JIMAGE_FindResource(image,"java.base","25","sun/net/www/protocol/https/DelegateHttpsURLConnection.class",&bytes);assert(location);
 for(int budget: {0}) {
  buffer.assign(bytes,0x5a);image_budget=budget;assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==0);
  for(char b:buffer)assert(b==0x5a);assert(image_live==0);
 }
 image_budget=1;assert(JIMAGE_GetResource(image,location,buffer.data(),bytes)==bytes);assert(image_live==0);
 JIMAGE_Close(image);image_deny=false;
 assert(file_mappings==0 && anonymous_mappings==6);
 reject_anonymous=true;
 jint error=0;
 assert(!JIMAGE_Open("build/java25/boot-image/lib/modules",&error));
 assert(file_mappings==0 && anonymous_mappings==7);
 std::puts("Real JIMAGE reader PASS: direct anonymous copies, zero file mappings, actual ZIP and image-buffer allocation fallback/refusal/cleanup/recovery; truncated/corrupt controls; DTLS/classes/TLS/JFR/desktop identity; failed decode returns0 without publishing bytes; mapping rejection");
}
