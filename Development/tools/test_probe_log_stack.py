#!/usr/bin/env python3
"""Actual report handler on native64KiB pthread stacks, separate from main stack."""
import argparse
import os
from pathlib import Path
import signal
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--cc', default=os.environ.get('CXX', 'clang++'))
    parser.add_argument('--baseline-header-dir', type=Path, help='Optional explicit historical header: expected small-stack fault at O0')
    args = parser.parse_args()
    with tempfile.TemporaryDirectory(prefix='probe-log-stack-') as temporary:
        work = Path(temporary)
        data = work / 'data'
        data.write_bytes(b'x' * (1024 * 1024))
        for optimization in ('-O0', '-O2'):
            output = work / optimization[1:]
            subprocess.run([args.cc, optimization, '-std=c++17', '-pthread', '-I' + str(ROOT / 'java25/probe'),
                            str(ROOT / 'java25/tests/log_share_small_stack.cpp'), '-o', str(output)], check=True)
            subprocess.run([str(output), str(data)], check=True)
        if args.baseline_header_dir:
            output = work / 'historical-negative'
            subprocess.run([args.cc, '-O0', '-DLEGACY_ONLY', '-std=c++17', '-pthread', '-I' + str(args.baseline_header_dir),
                            str(ROOT / 'java25/tests/log_share_small_stack.cpp'), '-o', str(output)], check=True)
            run = subprocess.run([str(output), str(data)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if run.returncode not in (-signal.SIGSEGV, -signal.SIGBUS):
                raise AssertionError('Historical small-stack negative did not fault: ' + str(run.returncode))
            print('PASS historical O0 small-stack fault reproduced:', run.returncode)
    print('PASS O0/O2 real64KiB pthread index/full512row snapshot/streaming/allowlist/busy-refusal/recovery')


if __name__ == '__main__':
    main()
