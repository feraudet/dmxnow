#!/bin/sh
# dmxnow Pi installer (SPEC 4.11): venv in /opt/dmxnow, service user, configuration,
# network key, udev rule, systemd service. Idempotent: run again to upgrade; the
# configuration, the key and the counters already in place are kept.
#
#   sudo ./install.sh [--dongle-serial MAC] [--no-key] [--no-start]
set -eu

PREFIX=/opt/dmxnow
ETC=/etc/dmxnow
HERE=$(cd "$(dirname "$0")" && pwd)
SERIAL=""
KEY=1
START=1

while [ $# -gt 0 ]; do
    case "$1" in
        --dongle-serial) SERIAL="$2"; shift 2 ;;
        --no-key) KEY=0; shift ;;
        --no-start) START=0; shift ;;
        -h|--help) sed -n '2,8p' "$0"; exit 0 ;;
        *) echo "unknown option: $1" >&2; exit 2 ;;
    esac
done

[ "$(id -u)" -eq 0 ] || { echo "run as root (sudo)" >&2; exit 1; }

echo "== packages"
if ! python3 -c 'import sys, venv, ensurepip; sys.exit(sys.version_info < (3, 11))' 2>/dev/null; then
    apt-get update -q
    apt-get install -y -q python3 python3-venv
fi

echo "== user dmxnow"
if ! id dmxnow >/dev/null 2>&1; then
    useradd --system --no-create-home --home-dir /nonexistent --shell /usr/sbin/nologin dmxnow
fi
usermod -a -G dialout dmxnow

echo "== $PREFIX"
[ -x "$PREFIX/bin/python3" ] || python3 -m venv "$PREFIX"
"$PREFIX/bin/pip" install -q --upgrade "$HERE"
cp "$HERE/README.md" "$PREFIX/README.md"
ln -sf "$PREFIX/bin/dmxnow" /usr/local/bin/dmxnow

echo "== $ETC"
install -d -m 0755 "$ETC"
if [ ! -f "$ETC/dmxnowd.toml" ]; then
    # a random network id, so that two installations never share one by default
    NET=$(python3 -c 'import secrets; print(secrets.randbelow(65535) + 1)')
    sed "s/^net_id = .*/net_id = $NET             # random, chosen by install.sh/" \
        "$HERE/dmxnowd.toml.example" > "$ETC/dmxnowd.toml"
    echo "   created $ETC/dmxnowd.toml (net_id $NET)"
fi
if [ "$KEY" -eq 1 ] && [ ! -f "$ETC/net_key" ]; then
    (umask 077; python3 -c 'import secrets; print(secrets.token_hex(32))' > "$ETC/net_key")
    echo "   created $ETC/net_key (command authentication, A4)"
fi
[ -f "$ETC/net_key" ] && chown dmxnow:dmxnow "$ETC/net_key" && chmod 0600 "$ETC/net_key"

echo "== udev"
if [ -z "$SERIAL" ]; then
    # the dongle plugged in now: 303a:1001 with a serial number
    for d in /sys/bus/usb/devices/*; do
        [ -f "$d/idVendor" ] || continue
        if [ "$(cat "$d/idVendor")" = "303a" ] && [ "$(cat "$d/idProduct")" = "1001" ] && [ -f "$d/serial" ]; then
            if [ -n "$SERIAL" ]; then
                echo "   several ESP32 on USB: pass --dongle-serial" >&2; SERIAL=""; break
            fi
            SERIAL=$(cat "$d/serial")
        fi
    done
fi
if [ -n "$SERIAL" ]; then
    sed "s/@SERIAL@/$SERIAL/" "$HERE/udev/99-dmx-dongle.rules.in" > /etc/udev/rules.d/99-dmx-dongle.rules
    command -v udevadm >/dev/null && udevadm control --reload && udevadm trigger --subsystem-match=tty || true
    echo "   /dev/dmx-dongle -> dongle $SERIAL"
elif [ ! -f /etc/udev/rules.d/99-dmx-dongle.rules ]; then
    echo "   dongle not found: plug it in and run install.sh again (or --dongle-serial MAC)"
fi

echo "== systemd"
install -m 0644 "$HERE/systemd/dmxnowd.service" /etc/systemd/system/dmxnowd.service
if [ -d /run/systemd/system ]; then
    systemctl daemon-reload
    systemctl enable dmxnowd.service
    [ "$START" -eq 1 ] && systemctl restart dmxnowd.service
    systemctl --no-pager --lines=0 status dmxnowd.service || true
else
    echo "   systemd not running: service installed, not started"
fi

echo "== done. 'dmxnow status' (root or a member of the dmxnow group: usermod -a -G dmxnow \$USER)"
