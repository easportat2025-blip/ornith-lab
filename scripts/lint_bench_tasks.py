# -*- coding: utf-8 -*-
"""
lint_bench_tasks.py - quet task benchmark tim cac loi DA LAM SAN DUOC TRONG SFT
(TASK-15/17/19/20/26).

Moi loi duoc tach tu mot buoc thuc te (12/10):
  L1 LO DAP AN   : thong diep loi in ra gia tri dung (vd "Wrong, expected 42")
                    -> model sai 1 lan la bi cap dap an.
  L2 TARGET BI AN : gia tri muc tieu chi nam trong body dataset, KHONG xuat hien
                    tren man hinh -> agent khong the biet can chon gi
                    (loai nay lam task KHONG GIAI DUOC).
  L3 LOI CU       : trang co loi validate nhung KHONG tinh lai khi go ->
                    loi cu ton => man hinh TU MAU THUAN voi noi dung.
  L4 SCROLL TRONG : panel trong (overflow auto) ma trang KHONG tu focus ->
                    agent phai "click roi moi bam phim" -> lap prose, khong commit.
  L5 SCROLL IM    : trang cao hon viewport nhung cau lenh KHONG noi cach cuon
                    (action space khong co chuot xe).
  L6 INSTRUCTION  : cau lenh mau thuan noi ra (vd "click Submit ... while the
                    count is wrong") -> agent khong bam.

Dung:
    python scripts/lint_bench_tasks.py phase13-gui/bench_v15/tasks_v15_5/tasks
    python scripts/lint_bench_tasks.py phase13-gui/bench_v15/tasks_v16_a/tasks
Exit 0 = khong loi nghiem trong, 1 = co loi (can sua truoc khi eval).
ASCII-only source.
"""
import io
import json
import os
import re
import sys

# mau loi "lo dap an" (chung)
LEAK_RX = re.compile(r"expected\s+", re.I)
# cau lenh mau thuan
CONTRA_RX = re.compile(r"while the count is wrong|it rejects you", re.I)
# panel trong (co overflow) - can quet trong file HTML
SCROLL_RX = re.compile(r"overflow(-y)?\s*:\s*(auto|scroll)", re.I)
FOCUS_RX = re.compile(r"\.focus\(\)|autofocus", re.I)
REVALID_RX = re.compile(r"addEventListener\(\s*[\"'](input|blur)[\"']", re.I)
ERR_RX = re.compile(r"class=[\"'][^\"']*\berr\b|\bid=[\"']e_", re.I)

TASK_ID_RX = re.compile(r'"task_id"\s*:\s*"([^"]+)"')
FILE_RX = re.compile(r'"file"\s*:\s*"([^"]+)"')


def visible_text(page):
    return page.evaluate("() => (document.body.innerText||'')").replace("\n", " ")


def lint_dir(d, verbose=True):
    d = os.path.abspath(d)
    problems = []
    tasks_json = os.path.join(d, "tasks.json")
    task_ids = []
    instr_by_id = {}
    if os.path.exists(tasks_json):
        raw = io.open(tasks_json, encoding="utf-8").read()
        task_ids = TASK_ID_RX.findall(raw)
        for m in CONTRA_RX.finditer(raw):
            problems.append(("L6", tasks_json, "instruction mau thuan: %r" % m.group(0)))
        # L7: instruction cua task cao hon viewport phai noi cach cuon
        for m in re.finditer(r'"task_id"\s*:\s*"([^"]+)"[^{}]*?"instruction"\s*:\s*"((?:[^"\\]|\\.)*)"',
                             raw, re.S):
            instr_by_id[m.group(1)] = m.group(2).replace('\\"', '"')
    try:
        from playwright.sync_api import sync_playwright
    except Exception as e:
        problems.append(("L0", d, "khong co playwright: %s" % e))
        return problems
    with sync_playwright() as p:
        b = p.chromium.launch(headless=True)
        page = b.new_page(viewport={"width": 1280, "height": 720})
        for fn in sorted(os.listdir(d)):
            if not fn.endswith(".html"):
                continue
            path = os.path.join(d, fn)
            src = io.open(path, encoding="utf-8", errors="replace").read()
            # L1 lo dap an trong HTML
            for m in LEAK_RX.finditer(src):
                problems.append(("L1", fn, "thong diep co the lo gia tri: %r" % m.group(0)))
            # L3 loi validate cu
            if ERR_RX.search(src) and not REVALID_RX.search(src):
                problems.append(("L3", fn, "co loi validate nhung khong co tai validate lai khi go (input/blur)"))
            # L4 panel trong khong focus
            if SCROLL_RX.search(src) and not FOCUS_RX.search(src):
                problems.append(("L4", fn, "co panel trong (overflow) nhung khong tu focus() -> agent phai click roi moi bam phim"))
            try:
                page.goto("file:///" + path.replace("\\", "/"))
                page.wait_for_timeout(180)
                vis = visible_text(page)
                h = page.evaluate("() => document.body.scrollHeight")
                # L2 target bi an: gia tri muc tieu PHAI xuat hien tren man hinh
                # theo cach CO THAY (mot phan tu hoac mot phan sau dau ':')
                # -- kiem bang "co substring trong body.innerText" thi duoc
                # (T26 co "Alpha" trong danh sach nen khong bat duoc loi).
                data = page.evaluate("() => Object.assign({}, document.body.dataset)")
                parts = page.evaluate("""() => {
                  const out=[];
                  document.querySelectorAll('*').forEach(e=>{
                    if(e.children.length) return;          // chi la text leaf
                    const t=(e.textContent||'').trim();
                    if(t) out.push(t);
                  });
                  return out;
                }""")
                pieces = set()
                for t in parts:
                    pieces.add(t)
                    for piece in t.replace("=", ":").split(":"):
                        pieces.add(piece.strip())
                for k, v in data.items():
                    if not isinstance(v, str) or len(v) < 3:
                        continue
                    if not re.match(r"^(target|want|answer|expected|code|ref|sum|n\d)", k, re.I):
                        continue
                    if v in pieces:
                        continue
                    if re.match(r"^\d+(\.\d+)?$", v):
                        continue
                    problems.append(("L2", fn, "gia tri '%s'=%r KHONG xuat hien tren man hinh "
                                     "(chi nam trong body dataset) -> agent khong biet can lam gi"
                                     % (k, v)))
                # L5 trang cao + cau lenh khong noi cach cuon
                if h > 720:
                    if not re.search(r"scroll|end key|page down|page_down|SCROLL",
                                     vis, re.I):
                        problems.append(("L5", fn, "trang cao %dpx > 720 nhung cau lenh KHONG noi cach cuon (End/Page Down/SCROLL)" % h))
                    else:
                        print("   [L5-ok] %-24s trang cao %dpx, cau lenh da noi cach cuon" % (fn, h))
                    # L7: instruction cua task (tasks.json) cung phai noi cach cuon
                    for tid, ins in instr_by_id.items():
                        if fn.lower().startswith(tid.lower()[:12]):
                            if not re.search(r"scroll|end key|page down|SCROLL",
                                             ins, re.I):
                                problems.append(("L7", fn, "trang cao %dpx > 720 nhung INSTRUCTION cua %s khong noi cach cuon -> agent khong lam duoc" % (h, tid)))
                            else:
                                print("   [L7-ok] %-24s instruction cua %s da noi cach cuon" % (fn, tid))
            except Exception as e:
                problems.append(("L0", fn, "khong load duoc: %s" % str(e)[:80]))
        b.close()
    return problems


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/lint_bench_tasks.py <tasks_dir> [...]")
        return 2
    bad = 0
    for d in sys.argv[1:]:
        print("=" * 70)
        print("LINT", d)
        probs = lint_dir(d)
        if not probs:
            print("   OK - khong phat hien loi")
        for code, where, msg in probs:
            print("   [%s] %-28s %s" % (code, where, msg))
            bad += 1
    print("=" * 70)
    print("TONG loi: %d" % bad)
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
