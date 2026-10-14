#!/bin/zsh
set -eu
cd "${0:A:h}/.."
printf 'Current PS5 IPv4 address: '
IFS= read -r ps5_probe_ipv4
[[ -n "$ps5_probe_ipv4" ]] || exit 1
printf '\nTrying IPv6 neighbor discovery. Keep this window open during the tests.\n'
python3 tools/java25_lan_endurance_client.py --ps5-ipv4 "$ps5_probe_ipv4" --discover
