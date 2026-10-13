#!/usr/bin/env python3
"""Send our ELF to an already running TCP payload loader and show its output."""
import argparse
from pathlib import Path
import socket
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("host", help="PS5 address with an existing TCP ELF loader")
    parser.add_argument("--port", type=int, default=9021)
    parser.add_argument("--elf", type=Path,
                        default=Path(__file__).resolve().parents[1] /
                        "build/controller-tester.elf")
    args = parser.parse_args()
    try:
        payload = args.elf.read_bytes()
        if not payload.startswith(b"\x7fELF"):
            parser.error("Input is not an ELF file")
        with socket.create_connection((args.host, args.port), timeout=10) as conn:
            conn.sendall(payload)
            conn.shutdown(socket.SHUT_WR)
            conn.settimeout(135)
            while True:
                data = conn.recv(8192)
                if not data:
                    break
                sys.stdout.buffer.write(data)
                sys.stdout.buffer.flush()
    except (OSError, KeyboardInterrupt) as exc:
        print(f"Sender stopped: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
