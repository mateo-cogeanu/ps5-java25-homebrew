#!/usr/bin/env python3
"""Download the probe's read-only LAN log endpoints into a local ZIP."""
import argparse
import datetime
import hashlib
import ipaddress
import json
from pathlib import Path
import tempfile
import urllib.error
import urllib.request
import zipfile

NAMES=('build.txt','session.txt','startup.log','vm-trace.log','native-stderr.log','previous-native-stderr.log','server.log','abort.txt','exception.txt','verification-exception.txt','server-exception.txt','hs-error.log','class-load.log','process-usage.log','jit.log','gc.log','gc-rotated.log','previous-gc.log','previous-gc-rotated.log','exceptions.log','exceptions-rotated.log')
def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('address',type=ipaddress.IPv4Address,help='Current PS5 IPv4 address (never saved in the app)')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--output',type=Path,default=Path('probe-logs-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S')+'.zip'))
    args=parser.parse_args()
    if not 1<=args.port<=65535:parser.error('Invalid port')
    if args.output.exists():parser.error('Output already exists; choose a new filename')
    opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
    report={'collected_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'files':{}}
    with tempfile.TemporaryDirectory() as temporary:
        root=Path(temporary)
        for name in NAMES:
            try:
                with opener.open(f'http://{args.address}:{args.port}/{name}',timeout=30) as response:
                    expected=int(response.headers['Content-Length'])
                    if not 0<=expected<=128*1024*1024:raise ValueError('Invalid or oversized Content-Length')
                    size=0;digest=hashlib.sha256()
                    with (root/name).open('wb') as output:
                        while chunk:=response.read(65536):
                            size+=len(chunk)
                            if size>expected:raise ValueError('Response exceeds declared length')
                            output.write(chunk);digest.update(chunk)
                    if size!=expected:raise ValueError('Incomplete download')
                report['files'][name]={'status':'downloaded','bytes':size,'sha256':digest.hexdigest()}
                print(f'Downloaded {name}: {size} bytes')
            except (OSError,ValueError,urllib.error.URLError) as error:
                (root/name).unlink(missing_ok=True)
                report['files'][name]={'status':'unavailable','reason':str(error)}
                print(f'Unavailable {name}: {error}')
        if not any(v['status']=='downloaded' for v in report['files'].values()):
            raise SystemExit('No logs retrieved. Keep the probe open and check its log-sharing status and the PS5 address.')
        (root/'manifest.json').write_text(json.dumps(report,indent=2)+'\n')
        args.output.parent.mkdir(parents=True,exist_ok=True)
        with zipfile.ZipFile(args.output,'x',compression=zipfile.ZIP_DEFLATED) as archive:
            for file in sorted(root.iterdir()):archive.write(file,file.name)
    print('Saved',args.output.resolve())
    if any(v['status']=='unavailable' for v in report['files'].values()):print('Some logs are unavailable; see manifest.json. Files may not exist before their test runs.')
if __name__=='__main__':main()
