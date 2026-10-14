#!/usr/bin/env python3
"""Exercise actual Java LAN fixtures/protocols with shortened host durations."""
from pathlib import Path
import socket
import subprocess
import time
import java25_lan_endurance_client as helper
ROOT=Path(__file__).resolve().parents[1]
classes=ROOT/'build/java25/lan-endurance-assets/java25/classes'
base=['/opt/homebrew/opt/openjdk@25/bin/java','-Xint','-Xms16m','-Xmx128m','-Djava.net.preferIPv4Stack=false','-cp',str(classes)]
def port(family,kind):
    with socket.socket(family,kind) as s:
        s.bind(('::1' if family==socket.AF_INET6 else '127.0.0.1',0));return s.getsockname()[1]
def retry(operation,process):
    end=time.monotonic()+5
    while True:
        try:return operation()
        except (ConnectionRefusedError,socket.timeout):
            if process.poll() is not None or time.monotonic()>end:raise
            time.sleep(.05)
def finish(process,marker):
    out,err=process.communicate(timeout=15)
    assert process.returncode==0 and marker in out,out+err
    print('PASS:',marker)
def stop(process):
    if process.poll() is None:process.terminate();process.communicate(timeout=5)

tcp=port(socket.AF_INET6,socket.SOCK_STREAM);udp=port(socket.AF_INET6,socket.SOCK_DGRAM)
p=subprocess.Popen([*base,'-Dps5.probe.allowLoopbackTest=true',f'-Dps5.probe.ipv6TcpPort={tcp}',f'-Dps5.probe.ipv6UdpPort={udp}','Ipv6Lan25'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    retry(lambda:helper.ipv6_tcp('::1',tcp),p);retry(lambda:helper.ipv6_udp('::1',udp),p)
    finish(p,'JAVA_IPV6_LAN_OK')
finally:stop(p)

# Default production fixture must reject loopback masquerading as a LAN pass.
tcp=port(socket.AF_INET6,socket.SOCK_STREAM)
p=subprocess.Popen([*base,f'-Dps5.probe.ipv6TcpPort={tcp}','Ipv6Lan25'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    try:retry(lambda:helper.ipv6_tcp('::1',tcp),p)
    except (ConnectionError,OSError):pass
    out,err=p.communicate(timeout=8)
    assert p.returncode!=0 and 'Actual external IPv6 peer required' in err,out+err
    print('PASS: default IPv6 LAN fixture rejects a loopback peer')
finally:stop(p)

for fixture,kind,property_name,operation,marker in [
    ('LanTcpLoad25',socket.SOCK_STREAM,'loadTcpPort',helper.tcp_load,'JAVA_LAN_TCP_LOAD_OK'),
    ('LanUdpLoad25',socket.SOCK_DGRAM,'loadUdpPort',helper.udp_load,'JAVA_LAN_UDP_LOAD_OK')]:
    number=port(socket.AF_INET,kind)
    p=subprocess.Popen([*base,'-Dps5.probe.allowLoopbackTest=true','-Dps5.probe.loadSeconds=2',f'-Dps5.probe.{property_name}={number}',fixture],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
    try:
        stats=retry(lambda:operation('127.0.0.1',number,2),p)
        finish(p,marker);print('Verified client counters:',stats)
    finally:stop(p)

number=port(socket.AF_INET,socket.SOCK_DGRAM)
p=subprocess.Popen([*base,'-Dps5.probe.allowLoopbackTest=true','-Dps5.probe.loadSeconds=2',f'-Dps5.probe.loadUdpPort={number}','LanUdpLoad25'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
try:
    try:retry(lambda:helper.udp_load('127.0.0.1',number,0),p)
    except (OSError,ValueError):pass
    out,err=p.communicate(timeout=8)
    assert p.returncode!=0 and 'Insufficient UDP duration/frames' in err,out+err
    print('PASS: shorter-than-required traffic cannot receive a console PASS')
finally:stop(p)

# Discovery must match the actual IPv4 neighbor's MAC, not guess an IPv6 address.
from types import SimpleNamespace
original=helper.subprocess.run
def discovery_reply(arguments,**kwargs):
    command=arguments[0]
    output={'route':'interface: en0\n','arp':'? (192.0.2.45) at 0:1:2:3:4:5 on en0 ifscope [ethernet]\n',
            'ndp':'2001:db8::45 00:01:02:03:04:05 en0 permanent R\nfe80::45 0:1:2:3:4:5 en0 permanent R\n2001:db8::99 aa:bb:cc:dd:ee:ff en0 permanent R\n'}.get(command,'')
    return SimpleNamespace(stdout=output)
try:
    helper.subprocess.run=discovery_reply
    assert helper.discover_ipv6('192.0.2.45')==['2001:db8::45','fe80::45%en0']
    helper.subprocess.run=lambda *args,**kwargs:SimpleNamespace(stdout='')
    assert helper.discover_ipv6('192.0.2.45')==[]
    print('PASS: discovery matches neighbor MAC, retains link-local scope and never guesses an address')
finally:helper.subprocess.run=original
