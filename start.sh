#!/data/data/com.termux/files/usr/bin/bash
cd "$(dirname "$0")" || exit 1
# Open the local page while keeping the server and its messages in the terminal.
if command -v termux-open-url >/dev/null 2>&1; then
  (sleep 2; termux-open-url http://127.0.0.1:8000) &
fi
exec python -u luci_di_casa_mobile.py
