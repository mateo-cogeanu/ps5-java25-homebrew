#!/usr/bin/env python3
"""Check exact-neighbor IPv6 discovery without network traffic."""
import java25_lan_endurance_client as helper
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

# A failed single-address ARP query can use a strictly matched full-table entry.
def scoped_reply(arguments,**kwargs):
    output=''
    if arguments[0]=='route':output='interface: en0\n'
    if arguments[:2]==['arp','-an']:
        output='? (192.0.2.99) at aa:bb:cc:dd:ee:ff on en0\n? (192.0.2.45) at 0:1:2:3:4:5 on en0 ifscope [ethernet]\n'
    if arguments[0]=='ndp':output='2001:db8::45 00:01:02:03:04:05 en0 permanent R\n'
    return SimpleNamespace(stdout=output)
try:
    helper.subprocess.run=scoped_reply
    assert helper.discover_ipv6('192.0.2.45')==['2001:db8::45']
    assert helper.discover_ipv6('192.0.2.46')==[]
    print('PASS: full ARP fallback uses exact IPv4/interface; unrelated neighbor cannot become PS5 destination')
finally:helper.subprocess.run=original

try:
    helper.subprocess.run=lambda *args,**kwargs:SimpleNamespace(stdout='interface: en0\n')
    assert helper.scoped_ipv6('fe80::1234','192.0.2.45')=='fe80::1234%en0'
    assert helper.scoped_ipv6('fe80::1234%en1','192.0.2.45')=='fe80::1234%en1'
    assert helper.scoped_ipv6('2001:db8::45','192.0.2.45')=='2001:db8::45'
    for invalid in ['::1','::','ff02::1','fe80:1234']:
        try:helper.scoped_ipv6(invalid,'192.0.2.45')
        except ValueError:pass
        else:raise AssertionError('Invalid/external address accepted: '+invalid)
    helper.subprocess.run=lambda *args,**kwargs:SimpleNamespace(stdout='interface: utun4\n')
    try:helper.scoped_ipv6('fe80::1234','192.0.2.45')
    except ValueError:pass
    else:raise AssertionError('Tunnel selected for link-local LAN')
    print('PASS: runtime IPv6 validation, link-local LAN scope, explicit scope and tunnel rejection')
finally:helper.subprocess.run=original
