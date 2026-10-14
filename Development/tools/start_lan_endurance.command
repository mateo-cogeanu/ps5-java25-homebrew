#!/bin/zsh
set -eu
set -o pipefail
cd "${0:A:h}/.."
printf 'Current PS5 IPv4 address: '
IFS= read -r ps5_probe_ipv4
[[ -n "$ps5_probe_ipv4" ]] || exit 1
mkdir -p build/java25
probe_log="${PWD}/build/java25/lan-endurance-terminal.log"
printf '\nTrying IPv6 neighbor discovery. Output will be saved to %s\n' "$probe_log"
probe_exit=0
python3 tools/java25_lan_endurance_client.py --ps5-ipv4 "$ps5_probe_ipv4" --discover 2>&1 | tee "$probe_log" || probe_exit=$?
printf '\nHelper exited with code %s. Log: %s\n' "$probe_exit" "$probe_log"
printf 'Press Enter to close this window. '
IFS= read -r probe_close
exit "$probe_exit"
