#!/usr/bin/env python3
"""Connect to PS5 inbound TCP/UDP probes when the console test rows start."""
import argparse
from pathlib import Path
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]
PAYLOAD='Mac -> PS5 Java inbound: café / 日本語 / 🎮\n'.encode()

def tcp_attempt(host,bind,port):
    def read_exact(sock,count):
        data=b''
        while len(data)<count:
            part=sock.recv(count-len(data))
            if not part:raise ConnectionError('TCP peer closed')
            data+=part
        return data
    with socket.socket() as sock:
        if bind: sock.bind((bind,0))
        sock.settimeout(3);sock.connect((host,port));sock.settimeout(5)
        sock.sendall(struct.pack('!I',len(PAYLOAD))+PAYLOAD)
        length=struct.unpack('!I',read_exact(sock,4))[0]
        if length>4096:raise ValueError('TCP response exceeds limit')
        if read_exact(sock,length)!=b'PS5_TCP_ACK '+PAYLOAD:raise ValueError('TCP response mismatch')
        sock.sendall(struct.pack('!I',0x25ACCE55))

def udp_attempt(host,bind,port):
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        if bind: sock.bind((bind,0))
        sock.settimeout(1)
        sock.sendto(PAYLOAD,(host,port))
        data,peer=sock.recvfrom(4096)
        if peer!=(host,port) or data!=b'PS5_UDP_ACK '+PAYLOAD:raise ValueError('UDP response/source mismatch')
        sock.sendto(b'MAC_UDP_VERIFIED',peer)

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ps5-host',required=True)
    parser.add_argument('--bind',help='Optional source address; omitted uses normal OS routing')
    parser.add_argument('--tcp-port',type=int,default=38026)
    parser.add_argument('--udp-port',type=int,default=38027)
    parser.add_argument('--timeout',type=float,default=1800,help='Maximum retry duration in seconds')
    parser.add_argument('--background',action='store_true')
    args=parser.parse_args()
    if args.background:
        work=ROOT/'build/java25';work.mkdir(parents=True,exist_ok=True);log=work/'inbound-client.log'
        with log.open('w') as output:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--ps5-host',args.ps5_host,
                '--tcp-port',str(args.tcp_port),'--udp-port',str(args.udp_port),'--timeout',str(args.timeout),*(['--bind',args.bind] if args.bind else [])],
                stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(40):
            if process.poll() is not None:raise SystemExit(log.read_text())
            if 'READY' in log.read_text():break
            time.sleep(.05)
        else:process.terminate();raise SystemExit('Inbound helper did not become ready')
        (work/'inbound-client.pid').write_text(str(process.pid)+'\n')
        print(log.read_text().strip());return
    stop=threading.Event();tcp_ok=threading.Event();udp_ok=threading.Event()
    signal.signal(signal.SIGTERM,lambda *_:stop.set());signal.signal(signal.SIGINT,lambda *_:stop.set())
    deadline=time.monotonic()+args.timeout
    def worker(label,operation,port,done):
        attempts=0;last_error=None;last_report=0
        while not stop.is_set() and time.monotonic()<deadline:
            attempts+=1
            try:
                operation(args.ps5_host,args.bind,port)
                done.set();print(label+' PASS: request/acknowledgement verified after '+str(attempts)+' attempts',flush=True);return
            except (OSError,ValueError,ConnectionError) as error:
                detail=type(error).__name__+': '+str(error)
                now=time.monotonic()
                if detail!=last_error or now-last_report>=30:
                    print(label+' WAIT: '+args.ps5_host+':'+str(port)+'; attempt '+str(attempts)+'; '+detail,flush=True)
                    last_error=detail;last_report=now
                stop.wait(.75)
    threads=[threading.Thread(target=worker,args=('TCP',tcp_attempt,args.tcp_port,tcp_ok),daemon=True),
             threading.Thread(target=worker,args=('UDP',udp_attempt,args.udp_port,udp_ok),daemon=True)]
    # Validate the chosen source address before announcing readiness.
    if args.bind:
        with socket.socket() as check:check.bind((args.bind,0))
    print('READY: target '+args.ps5_host+'; TCP '+str(args.tcp_port)+' / UDP '+str(args.udp_port)+
          '; source '+(args.bind or 'OS routing')+'; helper retries for '+str(int(args.timeout))+' seconds',flush=True)
    for thread in threads:thread.start()
    while not stop.is_set() and time.monotonic()<deadline:
        if tcp_ok.is_set() and udp_ok.is_set():
            print('COMPLETE: TCP and UDP verified',flush=True);return
        stop.wait(.2)
    stop.set()
    print('STOPPED: TCP='+str(tcp_ok.is_set())+' UDP='+str(udp_ok.is_set()),flush=True)
if __name__=='__main__':main()
