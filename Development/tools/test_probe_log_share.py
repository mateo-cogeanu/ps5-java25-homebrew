#!/usr/bin/env python3
"""Exercise actual native HTTP handler and collector, including binary/large logs."""
from pathlib import Path
import json
import socket
import subprocess
import tempfile
import zipfile
ROOT=Path(__file__).resolve().parents[1]
with tempfile.TemporaryDirectory() as directory:
    root=Path(directory);payload=b'full console\n'+bytes(range(256))*8192
    (root/'data').write_bytes(payload)
    (root/'server.cpp').write_text(r'''
#include "log_share.hpp"
int main(int argc,char **argv){
 ps5::log_share::start(0);if(ps5::log_share::state!=1)return 2;ps5::log_share::stop();
 int listener=socket(AF_INET,SOCK_STREAM,0);sockaddr_in a{};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 if(bind(listener,(sockaddr*)&a,sizeof(a))||listen(listener,8))return 3;
 socklen_t length=sizeof(a);getsockname(listener,(sockaddr*)&a,&length);printf("%u\n",ntohs(a.sin_port));fflush(stdout);
 ps5::log_share::Entry entries[]={{"/startup.log",argv[1]},{"/server.log",argv[1]}};
 for(;;){int client=accept(listener,nullptr,nullptr);if(client<0)break;ps5::log_share::serve(client,entries,2);close(client);}
}
''')
    subprocess.run(['clang++','-std=c++17','-pthread','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(root/'server.cpp'),'-o',str(root/'server')],check=True)
    process=subprocess.Popen([str(root/'server'),str(root/'data')],stdout=subprocess.PIPE,text=True)
    try:
        port=int(process.stdout.readline())
        def request(data):
            with socket.create_connection(('127.0.0.1',port),timeout=10) as connection:
                connection.sendall(data);result=b''
                while True:
                    try:chunk=connection.recv(65536)
                    except ConnectionResetError:break
                    if not chunk:break
                    result+=chunk
                return result
        response=request(b'GET /startup.log HTTP/1.1\r\nHost: test\r\n\r\n');headers,body=response.split(b'\r\n\r\n',1)
        assert b'200 OK' in headers and body==payload
        for target in (b'/../data',b'/%2e%2e/data',b'/startup.log?path=/etc/passwd',b'/etc/passwd'):
            assert b'404 Not Found' in request(b'GET '+target+b' HTTP/1.1\r\n\r\n')
        assert b'405 Method Not Allowed' in request(b'POST /startup.log HTTP/1.1\r\n\r\n')
        assert b'431 Request Header Fields Too Large' in request(b'GET / HTTP/1.1\r\nX: '+b'a'*4100)
        assert b'PS5 probe logs' in request(b'GET / HTTP/1.1\r\n\r\n')
        # An abandoned download must not terminate the listener.
        with socket.create_connection(('127.0.0.1',port)) as connection:connection.sendall(b'GET /server.log HTTP/1.1\r\n\r\n')
        output=root/'logs.zip'
        subprocess.run(['python3',str(ROOT/'tools/fetch_probe_logs.py'),'127.0.0.1','--port',str(port),'--output',str(output)],check=True)
        with zipfile.ZipFile(output) as archive:
            assert archive.read('server.log')==payload
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest['files']['vm-trace.log']['status']=='unavailable'
            assert manifest['files']['startup.log']['bytes']==len(payload)
        print('PASS: native start/stop, HTTP download, bounded large binary streaming, allowlist, disconnect survival and ZIP collector')
    finally:process.terminate();process.wait(timeout=10)
