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
#define PS5_TRACK_FILE_ACTIVITY 1
#include "log_share.hpp"
#include <sys/resource.h>
static bool fail_limits=false;
static int controlled_getrlimit(int resource,struct rlimit* value) {
 if(fail_limits){errno=ENOTSUP;return -1;}return getrlimit(resource,value);
}
#define getrlimit controlled_getrlimit
#include "process_usage.hpp"
#undef getrlimit
#include <cassert>
int main(int argc,char **argv){
 assert(ps5::log_share::begin_session("test-build","test-run",argv[2]));
 assert(!ps5::log_share::begin_session("test-build","failed-archive",argv[5]));

 errno=EBUSY;assert(ps5::process_usage::append(argv[7],0));assert(errno==EBUSY);assert(ps5::process_usage::append(argv[7],17));assert(errno==EBUSY);fail_limits=true;assert(ps5::process_usage::append(argv[7],60));assert(errno==EBUSY);fail_limits=false;assert(!ps5::process_usage::append("/missing-parent-for-probe-test/usage.log",18));assert(errno==EBUSY);
 ps5::log_share::start(0);if(ps5::log_share::state!=1)return 2;ps5::log_share::stop();
 int listener=socket(AF_INET,SOCK_STREAM,0);sockaddr_in a{};a.sin_family=AF_INET;a.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
 if(bind(listener,(sockaddr*)&a,sizeof(a))||listen(listener,8))return 3;
 socklen_t length=sizeof(a);getsockname(listener,(sockaddr*)&a,&length);printf("%u\n",ntohs(a.sin_port));fflush(stdout);
 ps5::log_share::Entry entries[]={{"/exhausted.log",argv[1]},{"/verification-exception.txt",argv[8]},{"/server-exception.txt",argv[9]},{"/startup-tail.log",argv[1]},{"/startup.log",argv[1]},{"/server.log",argv[1]},{"/build.txt",argv[3]},{"/session.txt",argv[4]},{"/hs-error.log",argv[6]},{"/class-load.log",argv[1]},{"/process-usage.log",argv[7]},{"/gc.log",argv[1]},{"/gc-rotated.log",argv[1]},{"/previous-gc.log",argv[1]},{"/previous-gc-rotated.log",argv[1]},{"/jit.log",argv[1]},{"/exceptions.log",argv[1]},{"/exceptions-rotated.log",argv[1]},{"/native-stderr.log",argv[1]},{"/previous-native-stderr.log",argv[1]}};
 for(;;){int client=accept(listener,nullptr,nullptr);if(client<0)break;
 char peek[512]{};recv(client,peek,sizeof(peek)-1,MSG_PEEK);int filled[128],count=0;struct rlimit original{};
 bool exhaust=std::strstr(peek,"/exhausted.log")!=nullptr;
 if(exhaust){assert(getrlimit(RLIMIT_NOFILE,&original)==0);rlimit limited=original;if(limited.rlim_cur>128)limited.rlim_cur=128;assert(setrlimit(RLIMIT_NOFILE,&limited)==0);while(count<128){int n=open("/dev/null",O_RDONLY);if(n<0){assert(errno==EMFILE);break;}filled[count++]=n;}}
 ps5::log_share::serve(client,entries,sizeof(entries)/sizeof(entries[0]));
 if(exhaust){while(count)close(filled[--count]);assert(setrlimit(RLIMIT_NOFILE,&original)==0);}close(client);}

}
''')
    subprocess.run(['clang++','-std=c++17','-pthread','-fsanitize=address,undefined','-I'+str(ROOT/'java25/probe'),str(root/'server.cpp'),'-o',str(root/'server')],check=True)
    (root/'mc-server-start').mkdir()
    for name in ['probe-exception.txt','mc-bootstrap-abort.txt','mc-server-start/server-console.log','probe-verification-exception.txt','probe-server-exception.txt']:(root/name).write_text('prior report: '+name)
    (root/'probe-build.txt').write_text('test-build')
    (root/'hs_err_java25.log').write_text('previous real fatal report')
    (root/'fatal-test.log').write_text('current real fatal report')
    for name in ['java25-class-load.log','process-usage.log','java25-jit.log','java25-exceptions.log','java25-exceptions.log.0','probe-native-stderr.log','java25-gc.log','java25-gc.log.0']:(root/name).write_text('prior diagnostic: '+name)
    failed=root/'failed-archive';failed.mkdir();(failed/'previous-probe-exception.txt').mkdir();(failed/'probe-exception.txt').write_text('preserve me')
    (root/'verification-current').write_text('verification failure')
    (root/'server-current').write_text('server failure')
    process=subprocess.Popen([str(root/'server'),str(root/'data'),str(root),str(root/'probe-build.txt'),str(root/'probe-session.txt'),str(failed),str(root/'fatal-test.log'),str(root/'process-usage.log'),str(root/'verification-current'),str(root/'server-current')],stdout=subprocess.PIPE,text=True)
    try:
        port=int(process.stdout.readline())
        for name in ('probe-verification-exception.txt','probe-server-exception.txt'):
            assert (root/('previous-'+name)).read_text()=='prior report: '+name
            assert not (root/name).exists()
        for name,backup in [('probe-exception.txt','previous-probe-exception.txt'),('mc-bootstrap-abort.txt','previous-mc-bootstrap-abort.txt'),('mc-server-start/server-console.log','mc-server-start/previous-server-console.log')]:
            assert (root/backup).read_text()=='prior report: '+name
            assert 'test-run' in (root/name).read_text() and 'No ' in (root/name).read_text()
        assert (root/'previous-hs_err_java25.log').read_text()=='previous real fatal report'
        assert not (root/'hs_err_java25.log').exists()
        for name in ['java25-class-load.log','process-usage.log','java25-jit.log','java25-exceptions.log','java25-exceptions.log.0','probe-native-stderr.log','java25-gc.log','java25-gc.log.0']:assert (root/('previous-'+name)).read_text()=='prior diagnostic: '+name
        assert not (root/'java25-class-load.log').exists()
        assert 'elapsed_s=17 getrusage=0 maxrss_raw=' in (root/'process-usage.log').read_text()
        for kind in ['data','as','rss','nofile']:
            assert f'elapsed_s=0 rlimit={kind} result=0 errno=0 soft_raw=' in (root/'process-usage.log').read_text()
            assert f'elapsed_s=60 rlimit={kind} result=-1 errno=' in (root/'process-usage.log').read_text()
        assert 'test-build' in (root/'probe-session.txt').read_text()
        assert (failed/'probe-exception.txt').read_text()=='preserve me'
        assert 'incomplete' in (failed/'probe-session.txt').read_text()
        def request(data):
            with socket.create_connection(('127.0.0.1',port),timeout=10) as connection:
                connection.sendall(data);result=b''
                while True:
                    try:chunk=connection.recv(65536)
                    except ConnectionResetError:break
                    if not chunk:break
                    result+=chunk
                return result
        live=request(b'GET /resource-status.txt HTTP/1.1\r\n\r\n');assert b'200 OK' in live and b'nofile_query=0' in live and b'open=' in live
        activity=request(b'GET /file-activity.txt HTTP/1.1\r\n\r\n');assert b'200 OK' in activity and b'wrapped_open=' in activity and b'tracked_live=' in activity
        pressure=request(b'GET /exhausted.log HTTP/1.1\r\n\r\n');assert b'503 Service Unavailable' in pressure and b'open errno=24' in pressure and b'open=' in pressure
        response=request(b'GET /startup.log HTTP/1.1\r\nHost: test\r\n\r\n');headers,body=response.split(b'\r\n\r\n',1)
        assert b'200 OK' in headers and body==payload
        response=request(b'GET /startup-tail.log HTTP/1.1\r\n\r\n');headers,body=response.split(b'\r\n\r\n',1)
        assert body==payload[-512*1024:] and b'Content-Length: 524288' in headers
        (root/'data').write_bytes(b'short log\n')
        assert request(b'GET /startup-tail.log HTTP/1.1\r\n\r\n').split(b'\r\n\r\n',1)[1]==b'short log\n'
        (root/'data').write_bytes(payload)
        for target in (b'/../data',b'/%2e%2e/data',b'/startup.log?path=/etc/passwd',b'/startup-tail.log?path=/etc/passwd',b'/etc/passwd'):
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
            assert archive.read('native-stderr.log')==payload
            assert archive.read('previous-native-stderr.log')==payload
            assert (root/'previous-probe-native-stderr.log').read_text()=='prior diagnostic: probe-native-stderr.log'
            assert not (root/'probe-native-stderr.log').exists()
            assert archive.read('hs-error.log')==b'current real fatal report'
            assert archive.read('class-load.log')==payload
            assert archive.read('jit.log')==payload
            for name in ('gc.log','gc-rotated.log','previous-gc.log','previous-gc-rotated.log'):assert archive.read(name)==payload
            for name in ('java25-gc.log','java25-gc.log.0'):assert not (root/name).exists()
            assert archive.read('exceptions.log')==payload
            assert archive.read('exceptions-rotated.log')==payload
            assert b'elapsed_s=17 getrusage=0' in archive.read('process-usage.log')
            manifest=json.loads(archive.read('manifest.json'))
            assert manifest['files']['vm-trace.log']['status']=='unavailable'
            assert manifest['files']['startup.log']['bytes']==len(payload)
            assert archive.read('verification-exception.txt')==b'verification failure'
            assert archive.read('server-exception.txt')==b'server failure'
            assert archive.read('build.txt')==b'test-build'
            assert b'test-run' in archive.read('session.txt')
        print('PASS: native start/stop, HTTP download, bounded large binary streaming, allowlist, disconnect survival and ZIP collector')
    finally:process.terminate();process.wait(timeout=10)
