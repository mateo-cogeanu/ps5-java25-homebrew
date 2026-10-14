#!/bin/zsh
set -eu
set -o pipefail
cd "${0:A:h}/.."
printf 'Current PS5 IPv4 address: '
IFS= read -r ps5_probe_ipv4
[[ -n "$ps5_probe_ipv4" ]] || exit 1
printf 'PS5 IPv6 address (optional; press Enter for discovery): '
IFS= read -r ps5_probe_ipv6
probe_args=(--ps5-ipv4 "$ps5_probe_ipv4")
if [[ -n "$ps5_probe_ipv6" ]]; then
    probe_args+=(--ps5-ipv6 "$ps5_probe_ipv6")
else
    probe_args+=(--discover)
fi
mkdir -p build/java25
probe_log="${PWD}/build/java25/lan-endurance-terminal.log"
printf '\nPreparing IPv6 LAN test. Output will be saved to %s\n' "$probe_log"
probe_exit=0
python3 tools/java25_lan_endurance_client.py "${probe_args[@]}" 2>&1 | tee "$probe_log" || probe_exit=$?
printf '\nHelper exited with code %s. Log: %s\n' "$probe_exit" "$probe_log"
printf 'Press Enter to close this window. '
IFS= read -r probe_close
exit "$probe_exit"
