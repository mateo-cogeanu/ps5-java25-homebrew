#!/bin/zsh
# Run in the user's Terminal so LAN access and retry errors are visible.
set -eu
cd "${0:A:h}/.."
printf 'PS5 address (from Settings > Network > Connection Status): '
IFS= read -r ps5_probe_host
if [[ -z "$ps5_probe_host" ]]; then
    printf 'An address is required. Close this window and try again.\n'
    exit 1
fi
printf '\nKeep this window open, launch the inbound app, then run rows 1–5.\n'
printf 'TCP and UDP should each report PASS here. Press Ctrl-C to stop.\n\n'
python3 tools/java25_inbound_client.py --ps5-host "$ps5_probe_host"
