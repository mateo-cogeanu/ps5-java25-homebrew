#!/usr/bin/env python3
"""Real host sockets/TLS: verify trust, hostname rejection, IPv6 and load fixtures."""
from pathlib import Path
import http.server
import ssl
import subprocess
import tempfile
import threading
ROOT=Path(__file__).resolve().parents[1]
JDK=Path('/opt/homebrew/opt/openjdk@25/bin')
classes=ROOT/'build/java25/advanced-network-assets/java25/classes'
base=[str(JDK/'java'),'-Xint','-Xms16m','-Xmx128m','-Djava.net.preferIPv4Stack=false','-cp',str(classes)]

def run(fixture,*options,expect=None):
    result=subprocess.run([*base,*options,fixture],capture_output=True,text=True,timeout=90)
    output=result.stdout+result.stderr
    if expect:
        assert result.returncode!=0 and expect in output,output
    else:
        assert result.returncode==0 and 'JAVA_' in output,output
    return output

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        body=b'Java25 local TLS fixture\n'
        self.send_response(200);self.send_header('Content-Length',str(len(body)));self.end_headers();self.wfile.write(body)
    def log_message(self,*args):pass

with tempfile.TemporaryDirectory() as directory:
    work=Path(directory);cert=work/'cert.pem';key=work/'key.pem';store=work/'trust.jks'
    subprocess.run(['openssl','req','-x509','-newkey','rsa:2048','-nodes','-keyout',str(key),'-out',str(cert),'-days','1','-subj','/CN=localhost','-addext','subjectAltName=DNS:localhost'],check=True,capture_output=True)
    subprocess.run([str(JDK/'keytool'),'-importcert','-noprompt','-alias','fixture','-file',str(cert),'-keystore',str(store),'-storetype','JKS','-storepass','changeit'],check=True,capture_output=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),Handler)
    context=ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER);context.load_cert_chain(cert,key)
    server.socket=context.wrap_socket(server.socket,server_side=True)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    try:
        endpoint='https://localhost:'+str(server.server_port)+'/'
        run('Https25','-Dps5.probe.httpsUrl='+endpoint,'-Dps5.probe.trustStore='+str(store))
        print('PASS: actual TLS handshake, trusted certificate, HTTPS 200 and body')
        run('Https25','-Dps5.probe.httpsUrl='+endpoint,'-Dps5.probe.trustStore='+str(ROOT/'build/java25/advanced-network-assets/java25/lib/security/cacerts'),expect='PKIX path building failed')
        print('PASS: untrusted certificate rejected')
        run('Https25','-Dps5.probe.httpsUrl=https://127.0.0.1:'+str(server.server_port)+'/','-Dps5.probe.trustStore='+str(store),expect='No subject alternative names matching IP address')
        print('PASS: trusted certificate with wrong hostname rejected')
    finally:server.shutdown();server.server_close();thread.join(3)
run('Ipv625');print('PASS: real IPv6 ::1 TCP/UDP request and reply')
run('NetworkLoad25');print('PASS: four concurrent TCP workers (512 frames / 2 MiB each direction), 256 UDP round trips')
