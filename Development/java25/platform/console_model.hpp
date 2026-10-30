/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstddef>
#include <cstring>
namespace ps5::console {
enum class Model { unknown, standard, pro };
enum class Status { unavailable, failed, malformed, unrecognized, recognized };
struct Result { Model model=Model::unknown; Status status=Status::unavailable; int native_result=0; };
using Query=int(*)(char*);
// Query only loaded modules; no dlopen or system-library startup dependency.
using Resolver=int(*)(int,const char*,void**);
using ModuleList=int(*)(int*,std::size_t,std::size_t*);
struct Lookup {int handle=-1,name_result=-1,nid_result=-1;bool name_pointer=false,nid_pointer=false;};
struct Resolution {
 Query query=nullptr;int handle=-1,native_result=-1,list_result=-1;bool by_nid=false;
 std::size_t module_count=0,attempt_count=0,record_count=0;Lookup records[8]{};
};
inline Resolution resolve_loaded_query(Resolver resolve,ModuleList list=nullptr) {
 Resolution out;if(!resolve)return out;
 int handles[514]={1,0x2001};std::size_t count=2,listed=0;
 if(list){out.list_result=list(handles+2,512,&listed);out.module_count=listed;
  if(out.list_result==0&&listed<=512)count+=listed;}
 for(std::size_t i=0;i<count;i++){
  int handle=handles[i];if(handle<0)continue;
  bool duplicate=false;for(std::size_t j=0;j<i;j++)if(handles[j]==handle)duplicate=true;
  if(duplicate)continue;
  Lookup row;row.handle=handle;void* address=nullptr;
  row.name_result=resolve(handle,"sceKernelGetHwModelName",&address);row.name_pointer=address!=nullptr;
  if(row.name_result==0&&address){out.query=reinterpret_cast<Query>(address);out.handle=handle;out.native_result=0;}
  else {
   address=nullptr;
   // SDK nid_encode(name): SHA1(name+salt), reversed first8bytes, PS base64.
   row.nid_result=resolve(handle,"JC7I7J1bllQ",&address);row.nid_pointer=address!=nullptr;
   if(row.nid_result==0&&address){out.query=reinterpret_cast<Query>(address);out.handle=handle;out.native_result=0;out.by_nid=true;}
   else out.native_result=row.nid_result;
  }
  out.attempt_count++;
  if(out.record_count<8)out.records[out.record_count++]=row;
  if(out.query)return out;
 }
 return out;
}
// Only documented retail CFI families. Unknown revisions/devkits stay unknown.
inline Model classify(const char* text,std::size_t capacity) {
 if(!text)return Model::unknown;
 const char* end=static_cast<const char*>(std::memchr(text,0,capacity));
 if(!end)return Model::unknown;
 std::size_t n=static_cast<std::size_t>(end-text);
 if(n<8||n>13||std::memcmp(text,"CFI-",4))return Model::unknown;
 for(unsigned i=4;i<8;i++)if(text[i]<'0'||text[i]>'9')return Model::unknown;
 std::size_t i=8;
 // Native model example: CFI-2014 A01X. Only a bounded retail revision suffix.
 if(i<n&&text[i]==' '){
  if(n!=13||(text[9]!='A'&&text[9]!='B')||text[10]<'0'||text[10]>'9'||text[11]<'0'||text[11]>'9'||text[12]!='X')return Model::unknown;
  i=n;
 }
 if(i<n&&(text[i]=='A'||text[i]=='B'))i++;
 if(i<n&&text[i]=='-')i++;
 if(i<n){if(n-i!=2||text[i]<'0'||text[i]>'9'||text[i+1]<'0'||text[i+1]>'9')return Model::unknown;i+=2;}
 if(i!=n||text[n-1]=='-')return Model::unknown;
 if(text[4]=='7'&&(text[5]=='0'||text[5]=='1'))return Model::pro;
 if((text[4]=='1'&&(text[5]>='0'&&text[5]<='2'))||(text[4]=='2'&&(text[5]=='0'||text[5]=='1')))return Model::standard;
 return Model::unknown;
}
inline Result read(Query query) {
 Result out;if(!query)return out;
 // The pinned SDK hwinfo example uses 1000 bytes for this unsized native ABI.
 // Do not shrink this buffer. Never copy/log the raw response or call serial APIs.
 char text[1000];std::memset(text,0xff,sizeof(text));
 out.native_result=query(text);
 if(out.native_result!=0){out.status=Status::failed;return out;}
 if(!std::memchr(text,0,sizeof(text))){out.status=Status::malformed;return out;}
 out.model=classify(text,sizeof(text));
 out.status=out.model==Model::unknown?Status::unrecognized:Status::recognized;
 return out;
}
// Native PS5-only SoC query; never CPU-brand, GPU-name or firmware inference.
// PS5Dev/Byepervisor-Reborn uses 0x840fd0 for Pro and other PS5 SoCs for base.
// Restrict that split to the PS5 signature family; reject errors/unknown families.
using SocQuery=unsigned long long(*)();
struct SocResult { Model model=Model::unknown; unsigned long long id=0; };
inline SocResult read_soc(SocQuery query) {
 SocResult out;if(!query)return out;
 out.id=query();
 if((out.id&~0xffULL)==0x840f00ULL)
  out.model=out.id==0x840fd0ULL?Model::pro:Model::standard;
 return out;
}
inline const char* name(Model model) {
 switch(model){case Model::standard:return "PlayStation 5";case Model::pro:return "PlayStation 5 Pro";default:return "PlayStation 5 (model unknown)";}
}
}
