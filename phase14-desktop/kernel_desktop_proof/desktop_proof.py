"""desktop_proof.py - CHUNG MINH DESKTOP-ENV tren Kaggle CPU (0 GPU-quota).

Pipeline:
  Xvfb 1280x720  ->  chromium HEADFUL (playwright, tu lo flag) tren display that
  ->  anh chup bang `import -window root` (cai agent se THAY)
  ->  xdotool bam chuot THAT vao o giua cua 1 o so (SU KIEN OS THAT)
  ->  doc trang thai app bang playwright.evaluate (window.__grid)
  ->  ket luan: chuot THAT co doi trang thai app khong?

Khong dung raw CDP: chromium bundle khong mo port remote-debugging (thu 4 lan).
Playwright launch(headless=False) = cua so X11 that, xdotool van toc duoc ✓.
"""
import json
import os
import shutil
import subprocess
import sys
import time

WORK = "/kaggle/working/desktop"
SHOTS = os.path.join(WORK, "shots")
W, H = 1280, 720
DISPLAY = ":99"

GAME = """<!doctype html><html><head><meta charset="utf-8"><title>2048</title>
<style>body{margin:0;background:#faf8ef;font:16px system-ui;display:flex;
flex-direction:column;align-items:center;justify-content:center;height:100vh}
#big{width:220px;height:70px;background:#d9534f;color:#fff;font-size:26px;font-weight:700;
display:flex;align-items:center;justify-content:center;border-radius:8px;margin-bottom:18px;
cursor:pointer;user-select:none}
#board{display:grid;grid-template-columns:repeat(4,72px);gap:8px;background:#bbada0;padding:8px}
.t{width:72px;height:72px;display:flex;align-items:center;justify-content:center;
font-size:26px;font-weight:700;background:#cdc1b4;border-radius:4px}</style></head>
<body><div id="big">BAM TOI (+1)</div><div id="score">0</div><div id="board"></div><script>
const N=4;let g,sc,clicks=0;
const big=document.getElementById('big');
big.addEventListener('click',()=>{clicks++;big.textContent='BAM TOI (+1) x'+clicks;
window.__clicks=clicks;});
function reset(){g=Array.from({length:N},()=>Array(N).fill(0));sc=0;const b=
document.getElementById('board');b.innerHTML='';for(let i=0;i<N*N;i++){const d=
document.createElement('div');d.className='t';d.id='c'+i;b.appendChild(d);}render();}
function render(){for(let i=0;i<N*N;i++){const v=g[(i/N)|0][i%N];const e=
document.getElementById('c'+i);e.textContent=v||'';}document.getElementById('score')
.textContent=sc;window.__grid=g.map(r=>r.slice());window.__score=sc;}
function slide(row){const a=row.filter(x=>x);for(let i=a.length-1;i>0;i--){if(a[i]===a[i-1])
{a[i]*=2;a[i-1]=0;sc+=a[i];}}while(a.length<N)a.push(0);return a;}
function move(d){const o=JSON.stringify(g);if(d==='l'){for(let r=0;r<N;r++)g[r]=slide(g[r]);}
else if(d==='r'){for(let r=0;r<N;r++)g[r]=slide(g[r].reverse()).reverse();}
else if(d==='u'){for(let c=0;c<N;c++){const col=g.map(r=>r[c]);const s=slide(col);
for(let r=0;r<N;r++)g[r][c]=s[r];}}else if(d==='d'){for(let c=0;c<N;c++){const col=g.map(r=>r[c])
.reverse();const s=slide(col).reverse();for(let r=0;r<N;r++)g[r][c]=s[r];}}
if(JSON.stringify(g)!==o){add();render();}}
function add(){const e=[];for(let r=0;r<N;r++)for(let c=0;c<N;c++)if(!g[r][c])e.push([r,c]);
if(e.length){const p=e[Math.floor(Math.random()*e.length)];g[p[0]][p[1]]=2;}}
addEventListener('keydown',e=>{const k=e.key.toLowerCase();if(['arrowleft','arrowright',
'arrowup','arrowdown'].includes(k)){e.preventDefault();move(k==='arrowleft'?'l':k==='arrowright'
?'r':k==='arrowup'?'u':'d');}});
reset();add();render();</script></body></html>"""


def log(m):
    print("[proof] %s" % m, flush=True)


def sh(cmd, timeout=900):
    e = dict(os.environ)
    e["DISPLAY"] = DISPLAY
    try:
        p = subprocess.run(cmd, shell=True, capture_output=True, env=e,
                           timeout=timeout)
        return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
            (p.stderr or b"").decode("utf-8", "replace")
    except Exception as ex:
        return -1, "", str(ex)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    # --- 0) cai X11 tools (image Kaggle khong co san)
    for b in ("Xvfb", "xdotool", "import"):
        if not shutil.which(b):
            log("cai %s ..." % b)
            sh("apt-get update -qq && apt-get install -y -qq xvfb x11-utils "
               "xdotool imagemagick >/dev/null 2>&1", timeout=1800)
            break
    log("tools: Xvfb=%s xdotool=%s import=%s" %
        (bool(shutil.which("Xvfb")), bool(shutil.which("xdotool")),
         bool(shutil.which("import"))))
    # --- 1) setup browser (bundle offline-browsers) + deps
    helper = None
    for root, _d, files in os.walk("/kaggle/input"):
        if "setup_playwright_offline.py" in files:
            helper = root
            break
    if not helper:
        log("FAIL: thay setup_playwright_offline.py")
        return 1
    sys.path.insert(0, helper)
    from setup_playwright_offline import setup_playwright_offline
    info = setup_playwright_offline()
    log("offline browsers: %s" % str(info)[:150])
    # --- 2) Xvfb
    sh("pkill -f 'Xvfb %s' 2>/dev/null" % DISPLAY)
    sh("nohup Xvfb %s -screen 0 %dx%dx24 -ac +extension GLX +render -noreset "
       "> /kaggle/working/xvfb.log 2>&1 &" % (DISPLAY, W, H), timeout=60)
    time.sleep(4)
    rc, o, e = sh("xdpyinfo -display %s >/dev/null 2>&1 && echo OK || echo FAIL"
                  % DISPLAY)
    log("display %s: %s" % (DISPLAY, o.strip()))
    if "OK" not in o:
        log("FAIL: Xvfb khong chay")
        return 1
    # QUAN TRONG: process chinh phai co DISPLAY - chromium cua playwright
    # thua env cua process (khai bao loi "Missing X server or $DISPLAY").
    os.environ["DISPLAY"] = DISPLAY
    # --- 3) app + playwright headful
    app = os.path.join(WORK, "game.html")
    with open(app, "w", encoding="utf-8") as fh:
        fh.write(GAME)
    from playwright.sync_api import sync_playwright
    b = None
    grid0 = None
    with sync_playwright() as p:
        log("launch chromium headful...")
        b = p.chromium.launch(headless=False, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu",
            "--window-size=%d,%d" % (W, H), "--window-position=0,0",
            "--kiosk"])
        ctx = b.new_context(viewport={"width": W, "height": H})
        pg = ctx.new_page()
        pg.goto("file://" + app)
        pg.wait_for_timeout(1200)
        grid0 = pg.evaluate("window.__grid")
        log("grid ban dau: %s" % json.dumps(grid0))
        # --- 4) chup man hinh (cai agent thay)
        shot0 = os.path.join(SHOTS, "before.png")
        sh("import -window root %s" % shot0, timeout=120)
        log("shot before: %s (%s B)" % (os.path.exists(shot0),
                                       os.path.getsize(shot0)
                                       if os.path.exists(shot0) else 0))
        # --- 5) TIM VI TRI o tren man hinh (qua bounding box cua DOM -> pixel)
        box = pg.evaluate("""() => {
            const e = document.querySelector('#board');
            const r = e.getBoundingClientRect();
            return {x: r.left, y: r.top, w: r.width, h: r.height};
        }""")
        log("board box: %s" % json.dumps(box))
        # --- 6) xdotool: bam chuot THAT vao nut lon (app co handler click)
        # OFFSET: trinh duyet co thanh cong cu (tab + address) ~86px -> toa do
        # CSS cua trang lech so voi toa do MAN HINH. Do lech = window_h -
        # window.innerHeight (viewport).
        inner_h = pg.evaluate("window.innerHeight")
        off_y = max(0, H - int(inner_h))
        log("viewport cao=%s -> OFFSET man hinh = %d px (thanh cong cu browser)"
            % (inner_h, off_y))
        btn = pg.evaluate("""() => {
            const r = document.getElementById('big').getBoundingClientRect();
            return {x: r.left + r.width/2, y: r.top + r.height/2};
        }""")
        log("nut lon (toa do CSS): %s" % json.dumps(btn))
        bx, by = int(btn["x"]), int(btn["y"] + off_y)
        sh("xdotool mousemove %d %d sleep 0.3 click 1" % (bx, by), timeout=60)
        time.sleep(0.8)
        clicks = pg.evaluate("window.__clicks || 0")
        log("so lan bam chuot THAT nhan duoc: %s (click tai %d,%d)" %
            (clicks, bx, by))
        # --- 6b) xdotool: bam chuot THAT vao o co gia tri (game 2048)
        target = None
        for r in range(4):
            for c in range(4):
                v = grid0[r][c]
                if v:
                    target = (r, c, v)
        if not target:
            log("FAIL: khong co o nao co gia tri de test")
            return 1
        r, c, v = target
        cell = 72 + 8  # 1 o + gap
        px = int(box["x"] + c * cell + cell / 2)
        py = int(box["y"] + r * cell + cell / 2 + off_y)
        log("bam chuot THAT tai (%d,%d) [o r=%d c=%d value=%d]" % (px, py, r, c, v))
        sh("xdotool mousemove %d %d sleep 0.3 click 1" % (px, py), timeout=60)
        time.sleep(0.6)
        grid1 = pg.evaluate("window.__grid")
        shot1 = os.path.join(SHOTS, "after.png")
        sh("import -window root %s" % shot1, timeout=120)
        # CROP anh theo vung viewport = CAI AGENT THAY (toan bo trang, khong
        # co thanh cong cu -> toa do agent khop CSS cua trang)
        try:
            from PIL import Image
            im = Image.open(shot1)
            im.crop((0, off_y, W, H)).save(os.path.join(SHOTS, "agent_view.png"))
            log("agent_view.png: crop (0,%d)-(%d,%d)" % (off_y, W, H))
        except Exception as e:
            log("crop loi: %s" % e)
        log("grid sau khi bam: %s" % json.dumps(grid1))
        # --- 7) phim that (KEY) -> thay doi state
        pg.keyboard.press("ArrowLeft")
        time.sleep(0.5)
        grid2 = pg.evaluate("window.__grid")
        log("grid sau khi bam phim: %s" % json.dumps(grid2))
        # so anh co doi khong
        try:
            from PIL import Image, ImageChops
            a0 = Image.open(shot0).convert("RGB")
            a1 = Image.open(shot1).convert("RGB")
            n = sum(1 for px_ in ImageChops.difference(a0, a1).getdata()
                    if px_ != (0, 0, 0))
            log("pixel diff before/after: %d" % n)
        except Exception as e:
            log("pixel diff loi: %s" % e)
            n = -1
        res = {"grid0": grid0, "grid1": grid1, "grid2": grid2,
               "clicks": clicks,
               "shot0": os.path.exists(shot0), "shot1": os.path.exists(shot1),
               "pixel_changed": n, "click_changed_state": grid0 != grid1,
               "key_changed_state": grid1 != grid2,
               "MOUSE_THAT_WORKS": clicks >= 1}
        with open(os.path.join(WORK, "proof.json"), "w", encoding="utf-8") as fh:
            json.dump(res, fh, ensure_ascii=False, indent=1)
        log("KET LUAN: CHUOT_THAT=%s (clicks=%s) PHIM_THAT=%s anh_doi=%s" %
            (res["MOUSE_THAT_WORKS"], clicks, res["key_changed_state"], n))
        b.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
