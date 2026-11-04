/* SPDX-License-Identifier: GPL-3.0-or-later */
#pragma once
#include <cstdint>
namespace ps5::demo::detail {
struct RefreshResult {unsigned selected_hz=60;std::uint64_t period_us=0;int status=0;bool changed=false,safe=true;};
// Opt-in only. Mode15 and restore1 are the existing native VideoOut protocol.
// Real vblank measurements, never the configure return alone, admit120Hz.
template<class Support,class Configure,class Wait,class Clock>
RefreshResult negotiate_refresh(unsigned requested,Support support,Configure configure,Wait wait,Clock clock){
 RefreshResult result;if(requested!=120)return result;
 if(support()<=0){result.status=1;return result;}
 if(configure(15)!=0){result.status=2;return result;}
 bool valid=wait()==0;std::uint64_t before=clock(),periods[6]{};
 for(unsigned i=0;valid&&i<6;i++){if(wait()!=0){valid=false;break;}auto now=clock();periods[i]=now>=before?now-before:0;before=now;if(!periods[i])valid=false;}
 if(valid){for(unsigned i=1;i<6;i++)for(unsigned j=i;j&&periods[j-1]>periods[j];j--){auto temp=periods[j];periods[j]=periods[j-1];periods[j-1]=temp;}result.period_us=periods[3];valid=result.period_us>=7000&&result.period_us<=10000;}
 if(valid){result.selected_hz=120;result.changed=true;return result;}
 result.status=3;result.safe=configure(1)==0;if(!result.safe)result.status=4;return result;
}
}
