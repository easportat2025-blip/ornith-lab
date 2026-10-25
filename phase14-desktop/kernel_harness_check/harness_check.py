"""harness_check.py - chung minh DESKTOP-ENV harness tren Kaggle CPU (0 GPU-quota).

Self-contained (Kaggle CHI upload code_file -> moi thu vien phai inline):
  - Xvfb 1280x720 + chup man hinh (import -window root) + xdotool (phim THAT)
  - mini WebSocket client (stdlib) -> CDP Runtime.evaluate -> doc state app THAT
  - app 2048 inline -> phim mui ten THAT lam diem TANG -> reward doc qua CDP
  - vong harness: obs (anh chup) -> action that -> env -> reward

Fail LOUD: thieu chromium / X11 / CDP / diem khong tang -> raise SystemExit.
Khong dung GPU. Internet ON de apt-get cai chromium.
"""
import base64
import json
import os
import re
import socket
import subprocess
import sys
import time
import urllib.request
import shutil

WORK = "/kaggle/working/desktop"
SHOTS = os.path.join(WORK, "shots")
APPS = os.path.join(WORK, "apps")
W, H = 1280, 720
DISPLAY = ":99"
CDP_PORT = 9222

GAME_2048_HTML = '<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<title>2048 — desktop env</title>\n<style>\n  body{margin:0;background:#faf8ef;font:16px system-ui,sans-serif;display:flex;\n       flex-direction:column;align-items:center;justify-content:center;height:100vh}\n  h1{font-size:22px;margin:0 0 4px}\n  #score{font-size:15px;margin-bottom:10px;color:#776e65}\n  #board{display:grid;grid-template-columns:repeat(4,64px);gap:8px;\n         background:#bbada0;padding:8px;border-radius:6px}\n  .t{width:64px;height:64px;display:flex;align-items:center;justify-content:center;\n     font-size:26px;font-weight:700;border-radius:4px;background:#cdc1b4;color:#776e65}\n  .v2{background:#eee4da}.v4{background:#ede0c8}.v8{background:#f2b179;color:#f9f6f2}\n  .v16{background:#f59563;color:#f9f6f2}.v32{background:#f67c5f;color:#f9f6f2}\n  .v64{background:#f65e3b;color:#f9f6f2}.v128{background:#edcf72;color:#f9f6f2}\n  .v256{background:#edcc61;color:#f9f6f2}.v512{background:#edc850;color:#f9f6f2}\n  .v1024{background:#edc53f;color:#f9f6f2}\n  #hint{margin-top:12px;color:#776e65;font-size:13px}\n</style>\n</head>\n<body>\n<h1>2048</h1>\n<div id="score">Score: <span id="s">0</span></div>\n<div id="board"></div>\n<div id="hint">Arrow keys / WASD to move. Goal: reach 2048.</div>\n<script>\nconst N=4;\nlet grid, score;\nfunction reset(){grid=Array.from({length:N},()=>Array(N).fill(0));score=0;\n  const b=document.getElementById(\'board\');b.innerHTML=\'\';\n  for(let i=0;i<N*N;i++){const d=document.createElement(\'div\');d.className=\'t\';d.id=\'c\'+i;b.appendChild(d);}render();}\nfunction render(){for(let i=0;i<N*N;i++){const v=grid[(i/N)|0][i%N];\n  const el=document.getElementById(\'c\'+i);el.textContent=v||\'\';el.className=\'t\'+(v?\' v\'+v:\'\');}\n  document.getElementById(\'s\').textContent=score;window.__score=score;\n  window.__grid=grid.map(r=>r.slice());}\nfunction slide(row){const a=row.filter(x=>x);for(let i=a.length-1;i>0;i--){if(a[i]===a[i-1]){a[i]*=2;a[i-1]=0;score+=a[i];}}\n  while(a.length<N)a.push(0);return a;}\nfunction move(dir){const old=JSON.stringify(grid);\n  if(dir===\'l\'){for(let r=0;r<N;r++)grid[r]=slide(grid[r]);}\n  else if(dir===\'r\'){for(let r=0;r<N;r++)grid[r]=slide(grid[r].reverse()).reverse();}\n  else if(dir===\'u\'){for(let c=0;c<N;c++){const col=grid.map(r=>r[c]);const s=slide(col);for(let r=0;r<N;r++)grid[r][c]=s[r];}}\n  else if(dir===\'d\'){for(let c=0;c<N;c++){const col=grid.map(r=>r[c]).reverse();const s=slide(col).reverse();for(let r=0;r<N;r++)grid[r][c]=s[r];}}\n  if(JSON.stringify(grid)!==old){addTile();render();}}\nfunction addTile(){const e=[];for(let r=0;r<N;r++)for(let c=0;c<N;c++)if(!grid[r][c])e.push([r,c]);\n  if(!e.length)return;const p=e[Math.floor(Math.random()*e.length)];grid[p[0]][p[1]]=2;}\naddEventListener(\'keydown\',e=>{const k=e.key.toLowerCase();\n  if([\'arrowleft\',\'arrowright\',\'arrowup\',\'arrowdown\',\'a\',\'d\',\'w\',\'s\'].includes(k)){\n    e.preventDefault();\n    move(k===\'arrowleft\'||k===\'a\'?\'l\':k===\'arrowright\'||k===\'d\'?\'r\':k===\'arrowup\'||k===\'w\'?\'u\':\'d\');}});\nreset();addTile();render();\n</script>\n</body>\n</html>\n'


def log(m):
    print("[hcheck] %s" % m, flush=True)


def sh(cmd, timeout=900, env=None):
    e = dict(os.environ)
    e["DISPLAY"] = DISPLAY
    if env:
        e.update(env)
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, env=e,
                           timeout=timeout)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
            (p.stderr or b"").decode("utf-8", "replace")
    except Exception as ex:
        return -1, "", str(ex)


# ------------------------------------------------------------------ display
def install():
    log("apt-get: xvfb x11-utils xdotool imagemagick x11-apps chromium")
    rc, o, e = sh("apt-get update -qq && apt-get install -y -qq xvfb x11-utils "
                  "xdotool imagemagick x11-apps chromium "
                  ">/dev/null 2>&1", timeout=1800)
    log("apt rc=%s" % rc)
    for b in ("Xvfb", "xdotool", "import", "chromium"):
        import shutil
        log("  %-9s %s" % (b, "OK" if shutil.which(b) else "THIEU"))
    cands = []
    # Uu tien chromium tu bundle offline-browsers (da biet chay duoc tren
    # Kaggle - dung chinh browser cho cac bench kernel).
    pb = bundle_chromium()
    if pb:
        cands.append(pb)
        log("  -> bundle chromium = %s" % pb)
    for b in ("chromium", "chromium-browser", "google-chrome"):
        p = shutil.which(b)
        if p:
            cands.append(p)
            log("  -> %s = %s" % (b, p))
    if not cands:
        raise SystemExit("FAIL: khong co chromium -> khong chung minh duoc")
    cands = list(dict.fromkeys(cands))
    log("chromium candidates: %s" % cands)
    return cands


def bundle_chromium():
    """Lay chromium headful tu bundle offline-browsers (da mount trong input).

    Uu tien goi setup_playwright_offline.py cua bundle (copy browsers + replay
    deps + ldconfig); fallback: tu giai nen bundle.zip + deps_out.zip.
    """
    import glob
    import zipfile
    # --- 1) dung helper chinh thuc cua bundle
    for root, _d, files in os.walk("/kaggle/input"):
        if "setup_playwright_offline.py" in files:
            if root not in sys.path:
                sys.path.insert(0, root)
            try:
                from setup_playwright_offline import setup_playwright_offline
                info = setup_playwright_offline()
                log("setup_playwright_offline OK: %s" % str(info)[:220])
                break
            except Exception as e:
                log("setup_playwright_offline loi: %s" % e)
    # --- 2) tim binary chromium (da copy san hoac tu giai nen)
    dest = "/tmp/pw-browsers"
    hits = glob.glob(os.path.join(dest, "**", "chrome-linux64", "chrome"),
                     recursive=True)
    if not hits:
        cands = []
        for root, _d, files in os.walk("/kaggle/input"):
            for f in files:
                if f in ("bundle.zip", "deps_out.zip"):
                    cands.append(os.path.join(root, f))
        for zp in cands:
            try:
                with zipfile.ZipFile(zp) as z:
                    for nm in z.namelist():
                        if nm.endswith("chrome") or "/chrome-linux64/" in nm:
                            try:
                                z.extract(nm, dest)
                            except Exception:
                                pass
                        elif zp.endswith("deps_out.zip") and (
                                nm.startswith("usr/lib") or nm.startswith("etc/")):
                            try:
                                z.extract(nm, "/")
                            except Exception:
                                pass
            except Exception as e:
                log("extract %s loi: %s" % (zp, e))
        sh("ldconfig >/dev/null 2>&1")
        hits = glob.glob(os.path.join(dest, "**", "chrome-linux64", "chrome"),
                         recursive=True)
    hits = [h for h in hits if os.path.exists(h)]
    if not hits:
        log("bundle_chromium: khong tim thay binary")
        return None
    p = hits[0]
    os.chmod(p, 0o755)
    return p


def start_display():
    os.makedirs(SHOTS, exist_ok=True)
    os.makedirs(APPS, exist_ok=True)
    sh("pkill -f 'Xvfb %s' 2>/dev/null" % DISPLAY)
    sh("nohup Xvfb %s -screen 0 %dx%dx24 -ac +extension GLX +render -noreset "
       "> /kaggle/working/xvfb.log 2>&1 &" % (DISPLAY, W, H), timeout=60)
    time.sleep(4)
    for i in range(8):
        rc, o, e = sh("xdpyinfo -display %s >/dev/null 2>&1 && echo OK || echo FAIL"
                      % DISPLAY)
        if "OK" in o:
            log("display OK")
            return True
        time.sleep(2)
    rc, o, e = sh("head -5 /kaggle/working/xvfb.log 2>/dev/null")
    log("display FAIL: %s" % (o or e)[:200])
    raise SystemExit("FAIL: Xvfb khong len")


def shot(path):
    rc, o, e = sh("import -window root %s" % path, timeout=120)
    if rc != 0 or not os.path.exists(path):
        rc, o, e = sh("xwd -root -silent | convert xwd:- %s" % path, timeout=120)
    return os.path.exists(path)


def px(n, total):
    return max(1, min(total - 1, int(round(float(n) / 1000.0 * total))))


def do_action(a):
    """CLICK x y | TYPE | KEY name (env.do_action cua harness) - xdotool THAT."""
    parts = a.split(" ", 1)
    verb = parts[0].upper()
    rest = parts[1] if len(parts) > 1 else ""
    if verb == "CLICK":
        p = rest.split()
        if len(p) < 2:
            return False, "click need 2 nums"
        sh("xdotool mousemove %d %d sleep 0.15 click 1"
           % (px(p[0], W), px(p[1], H)))
        return True, "click(%d,%d)" % (px(p[0], W), px(p[1], H))
    if verb == "TYPE":
        sh("xdotool type --delay 12 \"%s\"" % rest.replace('"', '\\"'))
        return True, "type(%s)" % rest[:30]
    if verb == "KEY":
        km = {"enter": "Return", "tab": "Tab", "esc": "Escape", "space": "space",
              "up": "Up", "down": "Down", "left": "Left", "right": "Right",
              "backspace": "BackSpace", "delete": "Delete",
              "ctrl+a": "ctrl+a", "ctrl+c": "ctrl+c", "ctrl+v": "ctrl+v"}
        k = km.get(rest.lower(), rest)
        sh("xdotool key %s" % k)
        return True, "key(%s)" % k
    return False, "unsupported verb %s" % verb


# --------------------------------------------------- CDP client (tu harness.py)
def _http_json(url, timeout=5):
    with urllib.request.urlopen(url, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))

def _ws_connect(ws_url, timeout=8):
    if not ws_url.startswith("ws://"):
        raise ValueError("chi ho tro ws:// (ws nho, khong TLS)")
    rest = ws_url[5:]
    hostport, _, path = rest.partition("/")
    path = "/" + path
    host, _, port = hostport.partition(":")
    port = int(port or 80)
    s = socket.create_connection((host, port), timeout=timeout)
    key = base64.b64encode(os.urandom(16)).decode()
    req = ("GET %s HTTP/1.1\r\nHost: %s:%d\r\nUpgrade: websocket\r\n"
           "Connection: Upgrade\r\nSec-WebSocket-Key: %s\r\n"
           "Sec-WebSocket-Version: 13\r\n\r\n" % (path, host, port, key))
    s.sendall(req.encode())
    buf = b""
    while b"\r\n\r\n" not in buf:
        chunk = s.recv(4096)
        if not chunk:
            raise IOError("ws handshake: peer closed")
        buf += chunk
    head, _, leftover = buf.partition(b"\r\n\r\n")
    if b" 101 " not in head.split(b"\r\n")[0] + b" ":
        raise IOError("ws handshake failed: %r" % head[:120])
    return s, leftover

def _ws_send(s, payload):
    data = payload.encode("utf-8")
    mask = os.urandom(4)
    n = len(data)
    hdr = bytearray([0x81])
    if n < 126:
        hdr.append(0x80 | n)
    elif n < 65536:
        hdr.append(0x80 | 126)
        hdr += n.to_bytes(2, "big")
    else:
        hdr.append(0x80 | 127)
        hdr += n.to_bytes(8, "big")
    hdr += mask
    s.sendall(bytes(hdr) + bytes(b ^ mask[i % 4] for i, b in enumerate(data)))

def _ws_recv(s, leftover=b"", timeout=8):
    buf = bytearray(leftover)

    def need(n):
        while len(buf) < n:
            s.settimeout(timeout)
            chunk = s.recv(65536)
            if not chunk:
                raise IOError("ws closed")
            buf.extend(chunk)

    need(2)
    b0, b1 = buf[0], buf[1]
    opcode = b0 & 0x0F
    masked = b1 & 0x80
    ln = b1 & 0x7F
    off = 2
    if ln == 126:
        need(4)
        ln = int.from_bytes(buf[2:4], "big")
        off = 4
    elif ln == 127:
        need(10)
        ln = int.from_bytes(buf[2:10], "big")
        off = 10
    mask = b""
    if masked:
        need(off + 4)
        mask = bytes(buf[off:off + 4])
        off += 4
    need(off + ln)
    payload = bytes(buf[off:off + ln])
    del buf[:off + ln]
    if masked:
        payload = bytes(b ^ mask[i % 4] for i, b in enumerate(payload))
    if opcode == 0x9:  # ping -> pong
        s.sendall(bytes([0x8A, 0x80]) + os.urandom(4))
        return _ws_recv(s, bytes(buf), timeout)
    if opcode == 0x8:
        raise IOError("ws closed by peer")
    return opcode, payload, bytes(buf)


def cdp_eval(expr, port=CDP_PORT, timeout=8):
    """Runtime.evaluate trong page app -> value hoac None."""
    try:
        tabs = _http_json("http://127.0.0.1:%d/json" % port)
    except Exception as e:
        log("cdp /json loi: %s" % str(e)[:120])
        return None
    page = None
    for t in tabs:
        if t.get("type") == "page" and str(t.get("url", "")).startswith("file://"):
            page = t
            break
    if page is None:
        for t in tabs:
            if t.get("type") == "page":
                page = t
                break
    if page is None:
        log("cdp: khong thay page target")
        return None
    s = None
    try:
        s, leftover = _ws_connect(page["webSocketDebuggerUrl"], timeout=timeout)
        _ws_send(s, json.dumps({
            "id": 1, "method": "Runtime.evaluate",
            "params": {"expression": expr, "returnByValue": True}}))
        for _ in range(24):
            opcode, payload, leftover = _ws_recv(s, leftover, timeout)
            if opcode != 0x1:
                continue
            try:
                msg = json.loads(payload.decode("utf-8", "replace"))
            except Exception:
                continue
            if msg.get("id") == 1:
                res = msg.get("result") or {}
                if res.get("exceptionDetails"):
                    return None
                return (res.get("result") or {}).get("value")
    except Exception as e:
        log("cdp eval loi: %s" % str(e)[:120])
        return None
    finally:
        if s is not None:
            try:
                s.close()
            except Exception:
                pass
    return None


# ------------------------------------------------------- 2048 greedy (scripted)
def _slide(row):
    a = [v for v in row if v]
    for i in range(len(a) - 1, 0, -1):
        if a[i] == a[i - 1]:
            a[i] *= 2
            a[i - 1] = 0
    while len(a) < 4:
        a.append(0)
    return a


def _sim(g, m):
    ng = [row[:] for row in g]
    if m == "left":
        ng = [_slide(r) for r in g]
    elif m == "right":
        ng = [_slide(r[::-1])[::-1] for r in g]
    elif m == "up":
        for c in range(4):
            col = _slide([g[r][c] for r in range(4)])
            for r in range(4):
                ng[r][c] = col[r]
    elif m == "down":
        for c in range(4):
            col = _slide([g[r][c] for r in range(4)][::-1])[::-1]
            for r in range(4):
                ng[r][c] = col[r]
    return None if ng == g else ng


def pick_move(g):
    best, best_score = None, -1
    for m in ("left", "down", "right", "up"):
        ng = _sim(g, m)
        if ng is None:
            continue
        score = sum(v for row in ng for v in row)
        score += sum(1 for row in ng for v in row if not v) * 2
        score += max(ng[0][0], ng[-1][-1], ng[0][-1], ng[-1][0]) * 3
        if score > best_score:
            best_score, best = score, m
    return best


# --------------------------------------------------------------------- main
def main():
    t0 = time.time()
    os.makedirs(SHOTS, exist_ok=True)
    os.makedirs(APPS, exist_ok=True)
    cands = install()
    start_display()

    app_path = os.path.join(APPS, "game_2048.html")
    with open(app_path, "w", encoding="utf-8") as fh:
        fh.write(GAME_2048_HTML)
    url = "file://" + app_path
    log("app: %s" % url)
    blog = os.path.join(WORK, "chrome.log")
    cdp_ok = False
    for chrome in cands:
        sh("pkill -f 'remote-debugging-port=%d' 2>/dev/null" % CDP_PORT)
        sh("rm -rf %s" % os.path.join(WORK, "chrome_profile"))
        log("launch chromium: %s" % chrome)
        sh("%s --no-sandbox --disable-gpu --window-size=%d,%d --window-position=0,0 "
           "--kiosk --disable-dev-shm-usage --remote-debugging-port=%d "
           "--remote-allow-origins=* --user-data-dir=%s '%s' > %s 2>&1 &"
           % (chrome, W, H, CDP_PORT, os.path.join(WORK, "chrome_profile"), url,
              blog),
           timeout=60)
        for i in range(90):
            time.sleep(1)
            if cdp_eval("1+1") is not None:
                cdp_ok = True
                log("CDP ready sau %ds (candidate %s)" % (i + 1, chrome))
                break
        if cdp_ok:
            break
        try:
            with io.open(blog, encoding="utf-8", errors="replace") as fh:
                tail = fh.read()[-1500:]
            log("candidate %s fail. chrome.log:\n%s" % (chrome, tail))
        except Exception:
            pass
        alive = sh("pgrep -f 'remote-debugging-port=%d' | head -2" % CDP_PORT)
        log("process con song? %s" % alive[1].strip()[:120])
    try:
        shutil.copyfile(blog, os.path.join(WORK, "chrome_launch.log"))
    except Exception:
        pass
    if not cdp_ok:
        p = bundle_chromium()
        if p:
            log("thu bundle chromium: %s" % p)
            sh("%s --no-sandbox --disable-gpu --window-size=%d,%d --kiosk "
               "--disable-dev-shm-usage --remote-debugging-port=%d "
               "--remote-allow-origins=* --user-data-dir=%s '%s' > %s 2>&1 &"
               % (p, W, H, CDP_PORT, os.path.join(WORK, "chrome_profile"), url,
                  blog), timeout=60)
            for i in range(25):
                time.sleep(1)
                if cdp_eval("1+1") is not None:
                    cdp_ok = True
                    log("CDP ready (bundle) sau %ds" % (i + 1))
                    break
    if not cdp_ok:
        raise SystemExit("FAIL: CDP khong phan hoi (chromium co --remote-debugging-port?)")

    before_shot = os.path.join(SHOTS, "before.png")
    if not shot(before_shot):
        raise SystemExit("FAIL: chup man hinh that khong duoc")
    score0 = cdp_eval("window.__score || 0")
    log("score ban dau: %s" % score0)

    n_keys = 0
    score1 = score0
    for step in range(40):
        gj = cdp_eval("JSON.stringify(window.__grid || null)")
        move = None
        if gj:
            try:
                move = pick_move(json.loads(gj))
            except Exception:
                move = None
        if move is None:
            move = ["left", "down", "right", "up"][step % 4]
        ok, desc = do_action("KEY %s" % move)
        if not ok:
            raise SystemExit("FAIL: khong gui duoc phim: %s" % desc)
        n_keys += 1
        time.sleep(0.25)
        s = cdp_eval("window.__score || 0")
        try:
            s = float(s)
        except Exception:
            s = score1
        score1 = s
        log("  step %02d KEY %-5s -> %s | score=%s" % (step, move, desc, s))
        if s and s > (score0 or 0):
            break

    after_shot = os.path.join(SHOTS, "after.png")
    ok_after = shot(after_shot)
    diff = None
    try:
        from PIL import Image, ImageChops
        a0 = Image.open(before_shot).convert("RGB")
        a1 = Image.open(after_shot).convert("RGB")
        diff = str(ImageChops.difference(a0, a1).getbbox())
    except Exception as e:
        log("pixel diff loi: %s" % e)

    rep = {"score_before": score0, "score_after": score1,
           "n_keys_sent": n_keys, "shot_before": os.path.exists(before_shot),
           "shot_after": ok_after, "pixel_diff": diff,
           "cdp_ok": cdp_ok, "screen": [W, H],
           "t_sec": round(time.time() - t0, 1)}
    with open(os.path.join(WORK, "harness_check.json"), "w",
              encoding="utf-8") as fh:
        json.dump(rep, fh, ensure_ascii=False, indent=1)
    log("REPORT: %s" % json.dumps(rep, ensure_ascii=False))
    if not score1 or score1 <= (score0 or 0):
        raise SystemExit("FAIL: diem 2048 khong tang -> harness loop co van de")
    if not diff:
        raise SystemExit("FAIL: anh khong doi -> khong co gi bi thao tac that")
    log("HARNESS CHECK PASS")


if __name__ == "__main__":
    main()
