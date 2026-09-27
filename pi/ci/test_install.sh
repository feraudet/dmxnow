#!/bin/sh
# Runs pi/install.sh in a Debian Bookworm container with systemd, then checks that the
# service is active, answers the CLI, and is restarted after being killed (SPEC 8.5).
#   pi/ci/test_install.sh        (needs docker, privileged containers)
set -eu
cd "$(dirname "$0")/../.."
IMG=dmxnow-bookworm-systemd
NAME=dmxnow-install-test
docker build -q -t "$IMG" -f pi/ci/Dockerfile.bookworm pi/ci >/dev/null
docker rm -f "$NAME" >/dev/null 2>&1 || true
# behind a TLS-intercepting proxy (development machines), pass it and its CA to pip
EXTRA=""
if [ -n "${HTTPS_PROXY:-}" ] && [ -f "${SSL_CERT_FILE:-}" ]; then
    EXTRA="--network host -e HTTPS_PROXY -e PIP_CERT=/proxy-ca.crt -v $SSL_CERT_FILE:/proxy-ca.crt:ro"
fi
# shellcheck disable=SC2086
docker run -d --name "$NAME" --privileged --cgroupns=host -v /sys/fs/cgroup:/sys/fs/cgroup:rw \
    -v "$PWD/pi:/src:ro" --tmpfs /run --tmpfs /run/lock $EXTRA "$IMG" >/dev/null
trap 'docker rm -f "$NAME" >/dev/null 2>&1 || true' EXIT
x() { docker exec -e HTTPS_PROXY="${HTTPS_PROXY:-}" -e PIP_CERT="${EXTRA:+/proxy-ca.crt}" "$NAME" sh -c "$1"; }

for i in $(seq 30); do x 'systemctl is-system-running 2>/dev/null | grep -qE "running|degraded"' && break; sleep 1; done
x 'cp -r /src /tmp/pi && /tmp/pi/install.sh --dongle-serial 24:0A:C4:00:00:01'
echo "--- second run (idempotent)"
x '/tmp/pi/install.sh --dongle-serial 24:0A:C4:00:00:01 >/dev/null'

x 'systemctl is-active dmxnowd'
x 'test -f /etc/dmxnow/net_key && test "$(stat -c %a:%U /etc/dmxnow/net_key)" = "600:dmxnow"'
x 'grep -q "24:0A:C4:00:00:01" /etc/udev/rules.d/99-dmx-dongle.rules'
for i in $(seq 20); do x 'test -S /run/dmxnow/control.sock' && break; sleep 0.5; done
echo "--- CLI (dongle absent)"
x 'dmxnow --json status' | tee /dev/stderr | grep -q '"dongle_connected": false'

echo "--- automatic restart"
PID1=$(x 'systemctl show -p MainPID --value dmxnowd')
x 'systemctl kill -s KILL dmxnowd'
sleep 3
PID2=$(x 'systemctl show -p MainPID --value dmxnowd')
x 'systemctl is-active dmxnowd'
[ "$PID2" != "0" ] && [ "$PID1" != "$PID2" ] || { echo "not restarted ($PID1 -> $PID2)"; exit 1; }
echo "restarted: $PID1 -> $PID2, NRestarts=$(x 'systemctl show -p NRestarts --value dmxnowd')"
echo "install test OK"
