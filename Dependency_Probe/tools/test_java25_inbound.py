#!/usr/bin/env python3
"""Exercise packaged Java server fixtures using the actual Python client protocol."""
from pathlib import Path
import socket
import struct
import subprocess
import time
import java25_inbound_client as helper
ROOT=Path(__file__).resolve().parents[1]
classes=ROOT/'build/java25/inbound-assets/java25/classes'
base=['/opt/homebrew/opt/openjdk@25/bin/java','-Xint','-Xms16m','-Xmx128m',
      '-Djava.net.preferIPv4Stack=true','-cp',str(classes)]

def port_for(kind):
    with socket.socket(socket.AF_INET,kind) as sock:
        sock.bind(('127.0.0.1',0));return sock.getsockname()[1]

for proto,kind,fixture,operation in [('Tcp',socket.SOCK_STREAM,'InboundTcp25',helper.tcp_attempt),
                                   ('Udp',socket.SOCK_DGRAM,'InboundUdp25',helper.udp_attempt)]:
    port=port_for(kind)
    process=subprocess.Popen([*base,'-Dps5.probe.inbound'+proto+'Port='+str(port),fixture],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        deadline=time.monotonic()+12
        while True:
            try:operation('127.0.0.1',None,port);break
            except (OSError,ConnectionError):
                if process.poll() is not None or time.monotonic()>deadline:
                    raise AssertionError(process.communicate(timeout=2))
                time.sleep(.05)
        output,error=process.communicate(timeout=8)
        assert process.returncode==0 and 'JAVA_INBOUND_'+proto.upper()+'_OK' in output,output+error
        print('PASS: actual '+proto.upper()+' listener, verified client protocol, resource shutdown')
    finally:
        if process.poll() is None:process.terminate();process.communicate(timeout=5)

port=port_for(socket.SOCK_STREAM)
process=subprocess.Popen([*base,'-Dps5.probe.inboundTcpPort='+str(port),'InboundTcp25'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    deadline=time.monotonic()+5
    while True:
        try:
            connection=socket.create_connection(('127.0.0.1',port),timeout=.5);break
        except OSError:
            if time.monotonic()>deadline:raise
            time.sleep(.05)
    with connection:connection.sendall(struct.pack('!I',len(helper.PAYLOAD)+1))
    output,error=process.communicate(timeout=8)
    assert process.returncode!=0 and 'Inbound TCP frame length' in error,output+error
    print('PASS: malformed inbound frame fails instead of reporting success')
finally:
    if process.poll() is None:process.terminate();process.communicate(timeout=5)
