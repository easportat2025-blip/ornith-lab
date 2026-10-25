# DEPLOY ORNITH LÊN VPS (thay cho HF Docker Space)

> **22/10/2026 — quyết định của user: BỎ HF PRO.** ⇒ HF Docker Space không dùng được
> (Space mới cần PRO → 402/403; Space cũ bị "Flagged as abusive" → bị disable).
> ⇒ **đường đi duy nhất cho bản web "sống" là VPS** (Docker + Caddy + OpenCode).
> **Space tĩnh (static) vẫn chạy** làm dashboard/mirror: `himagayem-ornith-agent.static.hf.space`
> (`scripts/space_sync_loop.py` còn chạy ✓, đã dừng `space_revive` + `space_sync_docker_loop` ✓).

---

## 1. VPS tối thiểu

| hạng mục | cần |
|---|---|
| OS | Ubuntu 22.04/24.04 hoặc Debian 12 |
| CPU / RAM | 2 vCPU / 4 GB (OpenCode server + watchdog + Caddy) |
| Ổ đĩa | 20 GB (project + log + dataset cache) |
| Mạng | **cổng 80 + 443 mở** (Caddy tự lấy chứng thư Let's Encrypt) |
| GPU | KHÔNG cần (chỉ phục vụ web/agent; train vẫn ở Kaggle) |

Provider gợi ý: Hetzner CX22 / VPS 22 (giá rẻ nhất ở EU), DigitalOcean Basic, Vultr,
hoặc VPS Việt Nam (VNPT/VNG) nếu cần IP nội địa.

## 2. Deploy trong 1 lệnh (sau khi có IP + user + key)

```bash
# trên VPS (đã cài Docker + Docker Compose)
git clone <repo-cua-ban> ornith && cd ornith
cp -r phase14-space/_push_docker/. ./deploy/
# đặt file env (KHÔNG ghi key vào repo)
cat > deploy/.env <<'EOF'
OPENCODE_API_KEY=...        # key provider (đặt qua secret manager nếu có)
HF_TOKEN=...                # nếu cần mirror Space
DOMAIN=ornith.example.com
EOF
docker compose -f deploy/docker-compose.yml up -d
```

`deploy/docker-compose.yml` (đã tạo sẵn trong `phase14-space/_push_docker/`):

```yaml
services:
  opencode:
    build: .
    restart: unless-stopped
    env_file: [.env]
    ports: ["127.0.0.1:4096:4096"]
    volumes:
      - ./app:/app
      - /var/log/ornith:/app/logs
  caddy:
    image: caddy:2
    restart: unless-stopped
    ports: ["80:80", "443:443"]
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
volumes: { caddy_data: {} }
```

`Caddyfile`:
```
{$DOMAIN} {
    reverse_proxy opencode:4096
    encode gzip
}
```

## 3. Kiểm tra sau khi deploy

```bash
curl -s https://$DOMAIN/health        # OpenCode server
docker compose -f deploy/docker-compose.yml logs -f opencode
tail -f /var/log/ornith/watchdog.log
```

## 4. Việc còn lại cho user (không làm được nếu thiếu quyền truy cập VPS)

1. **Cấp quyền truy cập VPS**: IP + user + port + key (hoặc chuẩn bị sẵn 1 image
   docker trên VPS rồi báo lại để mình đẩy).
2. **Tên miền** (không bắt buộc: dùng IP + `http://` cũng chạy ✓).
3. **Key provider cho OpenCode** (đã có sẵn trong `~/.config/opencode/service.json` ở máy local ✓ —
   copy sang VPS qua secret, **không commit vào repo** ✓).

## 5. Trong khi chờ VPS — dùng gì?

- **Dashboard sống (public)**: Space tĩnh `himagayem-ornith-agent.static.hf.space` ✓ (đã chạy ✓)
- **Bản web "sống" đầy đủ (OpenCode server + bus + agent)**: chạy tại máy local ✓
  (`http://127.0.0.1:4096` ✓) — có bus nội bộ, watchdog A/B, LOBBY, agent phụ ✓
- **Train**: Kaggle (acc A hết quota tới 24/10 → chuyển sang acc B `dieniw` ✓)
