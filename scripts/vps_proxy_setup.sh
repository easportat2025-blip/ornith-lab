#!/usr/bin/env bash
# vps_proxy_setup.sh - CAI PROXY TREN VPS (dung cho nhieu acc Google Colab)
#
# Muc dich: moi acc Colab ra mot IP khac nhau (tranh Google flag nhieu acc
# cung IP + tang do doc lap). 3 PORT proxy tren 1 VPS; neu can IP KHAC NHAU
# THAT su => 3 VPS (hoac proxy residential/mobile) - 3 port tren 1 VPS chi
# doi duong, khong doi IP.
#
# Chay tren VPS (Ubuntu/Debian, can root):
#   bash vps_proxy_setup.sh <user1> <pass1> <user2> <pass2> <user3> <pass3>
#
# Ket qua: 3 proxy SOCKS5 + 3 proxy HTTP:
#   127.0.0.1:1081/1082/1083  (socks5)   user1/user2/user3
#   127.0.0.1:8081/8082/8083  (http)     cung user/pass
# + 3 port "tunnel" SSH (-D) neu can 1 IP cho moi acc qua 3 VPS khac nhau.
set -e

if [ "$#" -lt 6 ]; then
  echo "dung: bash vps_proxy_setup.sh u1 p1 u2 p2 u3 p3"
  exit 1
fi

echo "=== cai 3proxy ==="
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq 3proxy openssh-server >/dev/null
mkdir -p /etc/3proxy

i=0
for pair in "$@"; do
  i=$((i+1))
  [ $((i % 2)) -eq 0 ] && continue
  USER="$pair"
  PASS="${!i}"
  # lay pass = tham so ke tiep
  :
done

# tach cap (user pass) tu danh sach tham so
USERS=(); PASSES=()
while [ "$#" -gt 0 ]; do
  USERS+=("$1"); shift
  PASSES+=("$1"); shift
done

idx=0
for u in "${USERS[@]}"; do
  idx=$((idx+1))
  p="${PASSES[$((idx-1))]}"
  SOCKS=$((1080+idx))
  HTTP=$((8080+idx))
  cat > /etc/3proxy/$idx.cfg <<EOF
daemon
pidfile /var/run/3proxy-$idx.pid
logfile /var/log/3proxy-$idx.log
users $u:$p
allow $u
port $SOCKS
socks
EOF
  cat > /etc/3proxy/$idx-http.cfg <<EOF
daemon
pidfile /var/run/3proxy-$idx-http.pid
logfile /var/log/3proxy-$idx-http.log
users $u:$p
allow $u
port $HTTP
EOF
  echo "  port $SOCKS (socks5) + $HTTP (http) cho user '$u'"
done

echo "=== systemd units ==="
for f in /etc/3proxy/*.cfg; do
  base=$(basename "$f" .cfg)
  cat > /etc/systemd/system/3proxy-$base.service <<EOF
[Unit]
Description=3proxy $base
After=network.target
[Service]
ExecStart=/usr/bin/3proxy /etc/3proxy/$base.cfg
Restart=always
[Install]
WantedBy=multi-user.target
EOF
  systemctl enable 3proxy-$base >/dev/null 2>&1 || true
  systemctl restart 3proxy-$base >/dev/null 2>&1 || true
done

echo "=== mo firewall ==="
for f in /etc/3proxy/*.cfg; do
  base=$(basename "$f" .cfg)
  grep -oE 'port [0-9]+' /etc/3proxy/$base.cfg | awk '{print $2}'
done | sort -u | while read prt; do
  ufw allow "$prt/tcp" >/dev/null 2>&1 || true
  ufw allow "$prt/udp" >/dev/null 2>&1 || true
  echo "  ufw allow $prt"
done

echo
echo "XONG. Tren may local, dat proxy cho tung acc:"
echo '  python scripts\set_acc_proxy.py 1 socks5 user1:pass1@VPS_IP:1081'
echo '  python scripts\set_acc_proxy.py 2 socks5 user2:pass2@VPS_IP:1082'
echo '  python scripts\set_acc_proxy.py 3 socks5 user3:pass3@VPS_IP:1083'
echo "(hoac dung proxy HTTP: http://user:pass@VPS_IP:8081)"
