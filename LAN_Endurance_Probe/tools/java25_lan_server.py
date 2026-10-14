#!/usr/bin/env python3
"""Small bounded TCP/UDP echo helper for the PS5 Java LAN probe."""
import argparse
from pathlib import Path
import os
import signal
import socket
import struct
import subprocess
import sys
import threading
import time
ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bind',required=True,help='Mac IPv4 address on the PS5 LAN')
    parser.add_argument('--port',type=int,default=38025)
    parser.add_argument('--background',action='store_true')
    args=parser.parse_args()
    if args.background:
        work=ROOT/'build/java25';work.mkdir(parents=True,exist_ok=True)
        log=work/'lan-server.log'
        with log.open('w') as output:
            process=subprocess.Popen([sys.executable,str(Path(__file__).resolve()),'--bind',args.bind,'--port',str(args.port)],
                stdout=output,stderr=subprocess.STDOUT,start_new_session=True)
        for _ in range(40):
            if process.poll() is not None:raise SystemExit(log.read_text())
            if 'READY' in log.read_text():break
            time.sleep(.05)
        else:
            process.terminate();raise SystemExit('LAN helper failed to become ready')
        (work/'lan-server.pid').write_text(str(process.pid)+'\n')
        print(log.read_text().strip());return
    stop=threading.Event()
    def finish(*_):stop.set()
    signal.signal(signal.SIGTERM,finish);signal.signal(signal.SIGINT,finish)
    def read_exact(connection,count):
        result=b''
        while len(result)<count:
            data=connection.recv(count-len(result))
            if not data:raise ConnectionError('TCP peer closed')
            result+=data
        return result
    def serve(connection,peer):
        try:
            with connection:
                connection.settimeout(5)
                count=struct.unpack('!I',read_exact(connection,4))[0]
                if count>4096:raise ValueError('TCP frame exceeds probe limit')
                data=read_exact(connection,count)
                connection.sendall(struct.pack('!I',count)+data)
                print('TCP ECHO OK',peer,count,'bytes',flush=True)
        except (OSError,ValueError,ConnectionError) as error:print('TCP ERROR',str(error),flush=True)
    with socket.socket() as tcp,socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as udp:
        tcp.bind((args.bind,args.port));udp.bind((args.bind,args.port))
        tcp.listen(4);tcp.settimeout(.25);udp.settimeout(.25)
        def receive_udp():
            while not stop.is_set():
                try:
                    data,peer=udp.recvfrom(4097)
                    if len(data)<=4096:udp.sendto(data,peer);print('UDP ECHO OK',peer,len(data),'bytes',flush=True)
                except socket.timeout:pass
                except OSError:
                    if not stop.is_set():raise
        thread=threading.Thread(target=receive_udp,daemon=True);thread.start()
        print(f'READY TCP/UDP {args.bind}:{args.port}',flush=True)
        while not stop.is_set():
            try:
                connection,peer=tcp.accept()
                threading.Thread(target=serve,args=(connection,peer),daemon=True).start()
            except socket.timeout:pass
        thread.join(1)
if __name__=='__main__':main()
