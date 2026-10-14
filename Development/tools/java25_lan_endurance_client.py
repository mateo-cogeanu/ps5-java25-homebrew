#!/usr/bin/env python3
"""Discover PS5 IPv6 and exercise external IPv6 / 60-second LAN probes."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import ipaddress
from pathlib import Path
import re
import socket
import struct
import subprocess
import threading
import time
from java25_inbound_client import PAYLOAD

def read_exact(sock,count):
    data=b''
    while len(data)<count:
        part=sock.recv(count-len(data))
        if not part:raise ConnectionError('TCP peer closed')
        data+=part
    return data

def target(host,port,family,kind):
    return socket.getaddrinfo(host,port,family,kind)[0][4]

def ipv6_tcp(host,port):
    with socket.socket(socket.AF_INET6) as s:
        s.settimeout(3);s.connect(target(host,port,socket.AF_INET6,socket.SOCK_STREAM));s.settimeout(5)
        s.sendall(struct.pack('!I',len(PAYLOAD))+PAYLOAD)
        length=struct.unpack('!I',read_exact(s,4))[0]
        if length>4096 or read_exact(s,length)!=b'PS5_TCP_ACK '+PAYLOAD:raise ValueError('IPv6 TCP reply')
        s.sendall(struct.pack('!I',0x25ACCE55))

def ipv6_udp(host,port):
    with socket.socket(socket.AF_INET6,socket.SOCK_DGRAM) as s:
        s.settimeout(1);s.connect(target(host,port,socket.AF_INET6,socket.SOCK_DGRAM));s.send(PAYLOAD)
        if s.recv(4096)!=b'PS5_UDP_ACK '+PAYLOAD:raise ValueError('IPv6 UDP reply')
        s.send(b'MAC_UDP_VERIFIED')

def tcp_load(host,port,seconds):
    # Four independent connections exercise concurrency on the actual LAN.
    def client(identity):
        s=socket.socket();s.settimeout(3)
        try:
            s.connect((host,port));s.settimeout(5);s.setsockopt(socket.IPPROTO_TCP,socket.TCP_NODELAY,1)
            s.sendall(struct.pack('!I',identity));start=time.monotonic();sequence=0
            print('TCP worker '+str(identity)+' connected; verifying traffic for '+str(seconds)+' seconds',flush=True)
            while time.monotonic()-start<seconds+1 or sequence<128:
                data=bytes(((identity*31+sequence+i)&255) for i in range(4096))
                s.sendall(struct.pack('!ii',sequence,len(data))+data)
                header=struct.unpack('!ii',read_exact(s,8))
                if header!=(sequence,len(data)) or read_exact(s,len(data))!=data:raise ValueError('TCP sequence/bytes')
                sequence+=1
                time.sleep(.002)
            s.sendall(struct.pack('!ii',-1,0));count,elapsed=struct.unpack('!iq',read_exact(s,12))
            if count!=sequence or elapsed<seconds*1000:raise ValueError('TCP duration/count')
            s.sendall(struct.pack('!I',0x25ACCE55))
            return {'worker':identity,'frames':count,'server_ms':elapsed,'bytes_each_direction':count*4096}
        finally:s.close()
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures=[pool.submit(client,i) for i in range(4)]
        return [f.result() for f in futures]

def udp_load(host,port,seconds):
    hello=b'PS5_LAN_LOAD_UDP'
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as s:
        s.settimeout(1);s.connect((host,port));s.send(hello)
        if s.recv(1024)!=hello:raise ValueError('UDP hello reply')
        start=time.monotonic();sequence=0;retries=0
        print('UDP helper handshake complete; verifying traffic for '+str(seconds)+' seconds',flush=True)
        while time.monotonic()-start<seconds+1 or sequence<128:
            packet=struct.pack('!i',sequence)+bytes(((sequence+i)&255) for i in range(512))
            for attempt in range(5):
                s.send(packet)
                try:
                    deadline=time.monotonic()+1
                    while True:
                        reply=s.recv(1024)
                        if reply==packet:break
                        # Ignore a delayed duplicate of an already verified reply.
                        if len(reply)==516 and struct.unpack('!i',reply[:4])[0]<sequence and time.monotonic()<deadline:continue
                        raise ValueError('UDP sequence/bytes')
                    break
                except socket.timeout:
                    retries+=1
                    if attempt==4:raise
            sequence+=1;time.sleep(.002)
        s.settimeout(5);s.send(struct.pack('!i',-1));summary=s.recv(1024)
        count,elapsed,duplicates=struct.unpack('!iqi',summary)
        if count!=sequence or elapsed<seconds*1000:raise ValueError('UDP count/duration')
        s.send(b'MAC_UDP_VERIFIED')
        return {'round_trips':count,'server_ms':elapsed,'retries':retries,'server_duplicates':duplicates}

def discover_ipv6(ipv4,verbose=False):
    """Match NDP entries to the PS5's IPv4 ARP MAC, without guessing IPv6."""
    def command(args):
        try:
            result=subprocess.run(args,capture_output=True,text=True,timeout=4)
            if verbose and getattr(result,'returncode',0)!=0:
                print('DISCOVERY: '+args[0]+' returned '+str(result.returncode)+'; '+getattr(result,'stderr','').strip(),flush=True)
            return result.stdout
        except (OSError,subprocess.TimeoutExpired) as error:
            if verbose:print('DISCOVERY: '+args[0]+': '+str(error),flush=True)
            return ''
    route=command(['route','-n','get',ipv4]);interface=re.search(r'interface:\s*(\w+)',route)
    if not interface:
        if verbose:print('DISCOVERY: no route interface found for the supplied IPv4 address',flush=True)
        return []
    interface=interface.group(1)
    command(['ping','-c','1','-W','1000',ipv4])
    arp=command(['arp','-n',ipv4]);mac=re.search(r' at ([0-9a-f:]+) on ',arp,re.I)
    if not mac:
        if verbose:print('DISCOVERY: no IPv4 ARP hardware address found for the PS5',flush=True)
        return []
    normalize=lambda text:':'.join(part.zfill(2).lower() for part in text.split(':'))
    wanted=normalize(mac.group(1))
    if verbose:print('DISCOVERY: matching PS5 hardware address '+wanted+' on '+interface,flush=True)
    command(['ping6','-c','2','-I',interface,'ff02::1'])
    found=[]
    for line in command(['ndp','-an']).splitlines():
        fields=line.split()
        if len(fields)<3 or fields[2]!=interface or normalize(fields[1])!=wanted:continue
        address=fields[0]
        try:parsed=ipaddress.IPv6Address(address.split('%')[0])
        except ValueError:continue
        if parsed.is_link_local and '%' not in address:address+='%'+interface
        if not parsed.is_loopback and not parsed.is_multicast:found.append(address)
    return sorted(set(found),key=lambda value:ipaddress.IPv6Address(value.split('%')[0]).is_link_local)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ps5-ipv4',required=True)
    parser.add_argument('--ps5-ipv6',help='Optional discovered address, with %%interface for link-local')
    parser.add_argument('--discover',action='store_true')
    parser.add_argument('--discover-only',action='store_true',help='Print IPv6 neighbor evidence without starting any traffic tests')
    parser.add_argument('--timeout',type=float,default=1800)
    args=parser.parse_args();ipaddress.IPv4Address(args.ps5_ipv4)
    host6=args.ps5_ipv6
    if (args.discover or args.discover_only) and not host6:
        candidates=discover_ipv6(args.ps5_ipv4,verbose=True)
        print('IPv6 discovery:',', '.join(candidates) if candidates else 'no PS5 neighbor address found',flush=True)
        if candidates:host6=candidates[0]
    if args.discover_only:
        print('Discovery finished. No address found does not prove IPv6 is disabled; it means no matching neighbor was observed.',flush=True)
        return
    stop=threading.Event();results={};deadline=time.monotonic()+args.timeout
    def worker(label,operation):
        last=None;reported=0;attempt=0
        while not stop.is_set() and time.monotonic()<deadline:
            attempt+=1
            try:
                info=operation();results[label]=True;print(label+' PASS: '+str(info or 'verified IPv6 exchange'),flush=True);return
            except (OSError,ValueError,ConnectionError) as error:
                detail=type(error).__name__+': '+str(error);now=time.monotonic()
                if detail!=last or now-reported>=30:
                    print(label+' WAIT/ERROR attempt '+str(attempt)+': '+detail,flush=True);last=detail;reported=now
                stop.wait(.75)
    tasks=[('LAN TCP 60s',lambda:tcp_load(args.ps5_ipv4,38030,60)),('LAN UDP 60s',lambda:udp_load(args.ps5_ipv4,38031,60))]
    if host6:
        tasks.extend([('IPv6 TCP',lambda:ipv6_tcp(host6,38028)),('IPv6 UDP',lambda:ipv6_udp(host6,38029))])
    else:print('IPv6 LAN cannot be verified without a discovered/current PS5 IPv6 address. Skip that console row for now; IPv4 load tests remain available.',flush=True)
    print('READY: keep Terminal open; run console rows in order. Load tests take about 61 seconds each.',flush=True)
    threads=[threading.Thread(target=worker,args=task,daemon=True) for task in tasks]
    for t in threads:t.start()
    try:
        while time.monotonic()<deadline and len(results)<len(tasks):stop.wait(.2)
    except KeyboardInterrupt:pass
    finally:stop.set()
    print('RESULTS:',results,'IPv6 destination:',host6 or 'not discovered',flush=True)
if __name__=='__main__':main()
