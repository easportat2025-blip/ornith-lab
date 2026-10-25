# -*- coding: utf-8 -*-
"""
checker.py — TASK-11 / B15 checker (doc DOM/JS state that, khong tin self-report).

Moi task tra ve {success, score, reason, state} doc truc tiep tu trang
(page.evaluate). Nhieu task duoc verify LAP trong Python thay vi chi doc
co-flag "correct" cua trang:
  - T09 tinh lai ma giam gia tu data-price/data-disc, doi chieu visible text;
  - T10 hit-test canvas (circle/square/triangle, topmost truoc) tu #geo JSON
    + data-clickx/clicky, khong tin data-correct;
  - T08 regex lai name/email/qty; T05 doi chieu dst vs src value;
  - T03 doi chieu timestamp clickedat >= appearedat;
  - T06/T12 doi chieu submitted vs ma doc duoc tu trang.

SPEC_JS (target values + toa do normalized 0..1000 cua controls) lay bang
mot evaluate luc runner moi trang. Toa do chi cho policy Script (self-test);
model chi nhan anh + instruction.

Chay:
    python checker.py --self-test     # 36 success + 36 fail qua bench runner
"""
import json
import math
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

# ---------------------------------------------------------------------------
# SPEC_JS: moi task mot evaluate tra {vars (placeholders cho instruction),
# pos (toa do normalized cua element), gia tri target neu can}.
# ---------------------------------------------------------------------------
_POS = """
  const c = (id) => { const e = document.getElementById(id); if (!e) return null;
    const r = e.getBoundingClientRect();
    return [Math.round(((r.left + r.width/2)/1280*1000)*10)/10,
            Math.round(((r.top + r.height/2)/720*1000)*10)/10]; };
  const cjs = (id) => { const e = document.getElementById(id); const r = e.getBoundingClientRect();
    return [Math.round(((r.left + r.width/2)/1280*1000)*10)/10,
            Math.round(((r.top + r.height/2)/720*1000)*10)/10]; };
"""

SPEC_JS = {
    "T01_signup": "() => {" + _POS + """
      return {vars:{MINCHARS:String(document.body.dataset.min)},
              pos:{email:c('email'),pass:c('pass'),confirm:c('confirm'),
                   terms:c('terms'),submit:c('submit')}};
    }""",
    "T02_login": "() => {" + _POS + """
      return {vars:{},
              pos:{user:c('user'),pass:c('pass'),signin:c('signin')},
              user:document.getElementById('note_user').textContent,
              pass:document.getElementById('note_pass').textContent};
    }""",
    "T03_delayed": "() => {" + _POS + """
      const pos={}; for (let i=0;i<12;i++) pos['tile'+i]=c('tile'+i);
      return {vars:{}, target:+document.body.dataset.target,
              delay:+document.body.dataset.delay, pos:pos};
    }""",
    "T04_slider": "() => {" + _POS + """
      const sl=document.getElementById('slider'); const r=sl.getBoundingClientRect();
      const tgt=+document.body.dataset.target; const th=16;
      const f=(tgt/100*(r.width-th)+th/2)/r.width;
      const nx=Math.round(((r.left+r.width*f)/1280*1000)*10)/10;
      const ny=Math.round(((r.top+r.height/2)/720*1000)*10)/10;
      return {vars:{TARGET:String(tgt)}, target:tgt, pos:{slider_click:[nx,ny]}};
    }""",
    "T05_shortcut": "() => {" + _POS + """
      return {vars:{}, pos:{src:c('src'),dst:c('dst')},
              text:document.getElementById('src').value};
    }""",
    "T06_tabcode": "() => {" + _POS + """
      return {vars:{}, code:document.getElementById('code_text').textContent,
              pos:{tab_code:c('tab_code'),tab_home:c('tab_home'),
                   code_in:c('code_in'),submit:c('submit_code')}};
    }""",
    "T07_scroll": "() => {" + _POS + """
      return {vars:{}, total:+document.body.dataset.total, pos:{list:c('list')}};
    }""",
    "T08_errorfix": "() => {" + _POS + """
      return {vars:{}, pos:{sub:c('sub'),name:c('name'),email:c('email'),qty:c('qty')}};
    }""",
    "T09_coupon": "() => {" + _POS + """
      const b=document.body; const tgt=+b.dataset.targetplan;
      const price=+b.dataset.price, disc=+b.dataset.disc;
      return {vars:{TARGETPLAN:b.dataset.targetname, CODE:b.dataset.code,
                    EXPECTED:(price*(1-disc)).toFixed(2)},
              expected:(price*(1-disc)).toFixed(2),
              pos:{plan:c('plan'+tgt),coupon:c('coupon_in'),
                   apply:c('apply'),confirm:c('confirm')}};
    }""",
    "T10_canvas": "() => {" + _POS + """
      const cv=document.getElementById('cv');
      const shapes=JSON.parse(document.getElementById('geo').textContent);
      const tc=document.body.dataset.targetcolor, tt=document.body.dataset.targettype;
      const ti=shapes.findIndex(s=>s.color.name===tc && s.type===tt);
      const hit=(px,py)=>{for(let i=shapes.length-1;i>=0;i--){const s=shapes[i];
        if(s.type==='circle'){if(Math.hypot(px-s.x,py-s.y)<=s.r) return i;}
        else if(s.type==='square'){if(Math.abs(px-s.x)<=s.r&&Math.abs(py-s.y)<=s.r) return i;}
        else {const t=py-(s.y-s.r); if(t>=0&&t<=2*s.r&&Math.abs(px-s.x)<=t) return i;}
      } return -1;};
      const s=shapes[ti]; let px=s.x, py=s.y;
      const cands=[[0,0]];
      for(let a=0;a<12;a++){const th=a/12*2*Math.PI; cands.push([0.45*s.r*Math.cos(th),0.45*s.r*Math.sin(th)]);}
      for(const cd of cands){ if(hit(s.x+cd[0], s.y+cd[1])===ti){px=s.x+cd[0]; py=s.y+cd[1]; break;} }
      const r=cv.getBoundingClientRect();
      const nx=Math.round(((r.left+px)/1280*1000)*10)/10;
      const ny=Math.round(((r.top+py)/720*1000)*10)/10;
      return {vars:{TARGETSHAPE:tc+' '+tt}, target:{color:tc,type:tt,idx:ti},
              pos:{shape:[nx,ny]}};
    }""",
    "T11_counter": "() => {" + _POS + """
      return {vars:{}, target:+document.body.dataset.targetcount,
              pos:{inc:c('inc'),sub:c('sub')}};
    }""",
    "T12_pagecode": "() => {" + _POS + """
      return {vars:{}, code:document.getElementById('code1').textContent,
              pos:{to2:c('to2')}};
    }""",
}

# JS lay toa do normalized hien tai cua 1 element (dung khi layout thay doi)
_CUR_JS = ("() => { const e = document.getElementById('%s');"
           " const r = e.getBoundingClientRect();"
           " return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
           "         Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")

# ---------------------------------------------------------------------------
# Check functions — doc DOM that, verify lap trong Python
# ---------------------------------------------------------------------------
def check_t01(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {created:b.dataset.created, min:+b.dataset.min,
              email:g('email').value.trim(), pass:g('pass').value,
              conf:g('confirm').value, terms:g('terms').checked};
    }""")
    tests = {
        "email has @": "@" in st["email"],
        "password long enough": len(st["pass"]) >= st["min"],
        "passwords match": st["conf"] == st["pass"] and st["pass"] != "",
        "terms checked": bool(st["terms"]),
        "form submitted ok": st["created"] == "1",
    }
    return tests, st


def check_t02(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {loggedin:b.dataset.loggedin, attempts:+b.dataset.attempts,
              errorshown:b.dataset.errorshown,
              user:document.getElementById('user').value.trim(),
              pass:document.getElementById('pass').value,
              note_user:document.getElementById('note_user').textContent,
              note_pass:document.getElementById('note_pass').textContent};
    }""")
    tests = {
        "username matches note": st["user"] == st["note_user"],
        "password matches note": st["pass"] == st["note_pass"],
        "logged_in flag": st["loggedin"] == "1",
        "attempts >= 1": st["attempts"] >= 1,
    }
    return tests, st


def check_t03(page):
    st = page.evaluate("""() => {
      const b=document.body, t=+b.dataset.target;
      const tile=document.getElementById('tile'+t);
      return {appeared:b.dataset.appeared, correct:b.dataset.correct,
              appearedat:parseFloat(b.dataset.appearedat||'0'),
              clickedat:parseFloat(b.dataset.clickedat||'0'),
              target:t, tileactive:tile.classList.contains('active')};
    }""")
    tests = {
        "tile appeared": st["appeared"] == "1",
        "correct flag": st["correct"] == "1",
        "tile is the active one": st["tileactive"],
        "clicked after appeared": st["clickedat"] >= st["appearedat"] > 0,
    }
    return tests, st


def check_t04(page):
    st = page.evaluate("""() => {
      const b=document.body, sl=document.getElementById('slider');
      return {target:+b.dataset.target, dsvalue:+b.dataset.value,
              elvalue:+sl.value, cur:document.getElementById('cur').textContent};
    }""")
    tests = {
        "dataset value == target": st["dsvalue"] == st["target"],
        "element value == target": st["elvalue"] == st["target"],
        "visible text matches": st["cur"] == str(st["target"]),
    }
    return tests, st


def check_t05(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {src:document.getElementById('src').value,
              dst:document.getElementById('dst').value,
              pasted:+b.dataset.pasted, copied:+b.dataset.copied,
              match:b.dataset.match};
    }""")
    tests = {
        "target content == source": st["dst"] == st["src"] and st["src"] != "",
        "paste event was used": st["pasted"] >= 1,
        "copy happened": st["copied"] >= 1,
    }
    return tests, st


def check_t06(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {submitted:(b.dataset.submitted||'').trim(), correct:b.dataset.correct,
              code:document.getElementById('code_text').textContent.trim()};
    }""")
    tests = {
        "submitted == shown code": st["submitted"] == st["code"] and st["code"] != "",
        "correct flag": st["correct"] == "1",
    }
    return tests, st


def check_t07(page):
    st = page.evaluate("""() => {
      const b=document.body;
      const items=document.querySelectorAll('#list .item');
      const last=document.getElementById('item'+(+b.dataset.total-1));
      return {loaded:+b.dataset.loaded, total:+b.dataset.total,
              domcount:items.length, clicked:b.dataset.clicked,
              clickedcount:+b.dataset.clickedcount,
              lastclicked:!!last && last.classList.contains('clicked')};
    }""")
    tests = {
        "all items loaded": st["loaded"] == st["total"] and st["domcount"] == st["total"],
        "last item was clicked": st["clicked"] == str(st["total"] - 1),
        "click happened after full load": st["clickedcount"] == st["total"],
        "last item marked clicked": st["lastclicked"],
    }
    return tests, st


def check_t08(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {errorsshown:b.dataset.errorsshown, submittedok:b.dataset.submittedok,
              submitcount:+b.dataset.submitcount,
              name:g('name').value.trim(), email:g('email').value.trim(),
              qty:g('qty').value.trim()};
    }""")
    tests = {
        "errors were shown first": st["errorsshown"] == "1" and st["submitcount"] >= 2,
        "valid submit after": st["submittedok"] == "1",
        "name non-empty": st["name"] != "",
        "email has @": "@" in st["email"],
        "qty whole number 1-9": bool(re.match(r"^[1-9]$", st["qty"])),
    }
    return tests, st


def check_t09(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {selected:+b.dataset.selected, applied:b.dataset.applied,
              confirmed:b.dataset.confirmed, total:b.dataset.total,
              targetplan:+b.dataset.targetplan, price:+b.dataset.price,
              disc:+b.dataset.disc, visibletotal:g('total').textContent,
              coupon:g('coupon_in').value.trim().toUpperCase(),
              code:b.dataset.code, planname:b.dataset.targetname,
              sels:document.querySelectorAll('.plan.sel').length};
    }""")
    expected = round(st["price"] * (1 - st["disc"]), 2)
    try:
        shown = float(st["total"])
    except (TypeError, ValueError):
        shown = None
    tests = {
        "target plan selected": st["selected"] == st["targetplan"] and st["sels"] == 1,
        "coupon accepted": st["applied"] == "1" and st["coupon"] == st["code"],
        # tinh lap lai ma giam gia, khong tin co-flag
        "total == recomputed": shown is not None and abs(shown - expected) < 0.005,
        "visible total text matches": st["visibletotal"] == "$%.2f" % expected,
        "order confirmed": st["confirmed"] == "1",
    }
    return tests, st


def _hit(shapes, px, py):
    """Hit-test giong trang (topmost = ve sau cung)."""
    for i in range(len(shapes) - 1, -1, -1):
        s = shapes[i]
        if s["type"] == "circle":
            if math.hypot(px - s["x"], py - s["y"]) <= s["r"]:
                return i
        elif s["type"] == "square":
            if abs(px - s["x"]) <= s["r"] and abs(py - s["y"]) <= s["r"]:
                return i
        else:  # triangle (apex len)
            t = py - (s["y"] - s["r"])
            if 0 <= t <= 2 * s["r"] and abs(px - s["x"]) <= t:
                return i
    return -1


def check_t10(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {geo:document.getElementById('geo').textContent,
              clickx:b.dataset.clickx, clicky:b.dataset.clicky,
              targetcolor:b.dataset.targetcolor, targettype:b.dataset.targettype};
    }""")
    shapes = json.loads(st["geo"])
    px, py = float(st["clickx"] or -999), float(st["clicky"] or -999)
    i = _hit(shapes, px, py)
    hit_ok = (i >= 0 and shapes[i]["color"]["name"] == st["targetcolor"]
              and shapes[i]["type"] == st["targettype"])
    tests = {
        "click hit the target shape": hit_ok,
        "a click was registered": st["clickx"] != "",
    }
    st["hit_index"] = i
    st["hit_desc"] = (shapes[i]["color"]["name"] + ":" + shapes[i]["type"]) if i >= 0 else "none"
    return tests, st


def check_t11(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {count:+b.dataset.count, submitted:b.dataset.submitted,
              target:+b.dataset.targetcount,
              visible:document.getElementById('count').textContent};
    }""")
    tests = {
        "submitted flag": st["submitted"] == "1",
        "dataset count == 5": st["count"] == 5,
        "visible counter shows 5": st["visible"] == "5",
    }
    return tests, st


def check_t12(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {page:b.dataset.page, submitted:(b.dataset.submitted||'').trim(),
              correct:b.dataset.correct, code:document.getElementById('code1').textContent.trim()};
    }""")
    tests = {
        "submitted == page-1 code": st["submitted"] == st["code"] and st["code"] != "",
        "correct flag": st["correct"] == "1",
        "was on page 2": st["page"] == "2" or st["correct"] == "1",
    }
    return tests, st


CHECKS = {
    "T01_signup": check_t01, "T02_login": check_t02, "T03_delayed": check_t03,
    "T04_slider": check_t04, "T05_shortcut": check_t05, "T06_tabcode": check_t06,
    "T07_scroll": check_t07, "T08_errorfix": check_t08, "T09_coupon": check_t09,
    "T10_canvas": check_t10, "T11_counter": check_t11, "T12_pagecode": check_t12,
}


def check_task(page, task_id):
    """Tra ve {success, score, reason, state} cho 1 trang da load."""
    fn = CHECKS[task_id]
    tests, state = fn(page)
    failed = [k for k, v in tests.items() if not v]
    ok = not failed
    return {"success": ok, "score": 1.0 if ok else 0.0,
            "reason": "all %d checks pass" % len(tests) if ok
                      else "failed: " + ", ".join(failed),
            "state": {"tests": tests, **{k: v for k, v in state.items()
                                         if k != "geo"}}}


# ---------------------------------------------------------------------------
# Scripted success policies (self-test). Chi dung cho --self-test: nhan
# spec + peek (page.evaluate) de doc state; model that khong co 2 cai nay.
# ---------------------------------------------------------------------------
def fmt(v):
    s = "%.1f" % float(v)
    return s[:-2] if s.endswith(".0") else s


def _queue_policy(acts):
    st = {"i": 0}
    def fn(obs):
        i = st["i"]; st["i"] += 1
        return acts[i] if i < len(acts) else "DONE"
    return fn


def policy_t01(spec, peek):
    pw = "S3cretPass!word"
    P = spec["pos"]
    return _queue_policy([
        "CLICK " + fmt(P["email"][0]) + " " + fmt(P["email"][1]), "TYPE user@example.com",
        "CLICK " + fmt(P["pass"][0]) + " " + fmt(P["pass"][1]), "TYPE " + pw,
        "CLICK " + fmt(P["confirm"][0]) + " " + fmt(P["confirm"][1]), "TYPE " + pw,
        "CLICK " + fmt(P["terms"][0]) + " " + fmt(P["terms"][1]),
        "CLICK " + fmt(P["submit"][0]) + " " + fmt(P["submit"][1]),
    ])


def policy_t02(spec, peek):
    P = spec["pos"]
    return _queue_policy([
        "CLICK " + fmt(P["user"][0]) + " " + fmt(P["user"][1]), "TYPE " + spec["user"],
        "CLICK " + fmt(P["pass"][0]) + " " + fmt(P["pass"][1]), "TYPE " + spec["pass"],
        "CLICK " + fmt(P["signin"][0]) + " " + fmt(P["signin"][1]),
    ])


def policy_t03(spec, peek):
    P = spec["pos"]; t = spec["target"]; delay = spec["delay"]
    st = {"n": 0}
    def fn(obs):
        if st["n"] == 0:
            time.sleep(delay / 1000.0 + 0.6)
            st["n"] = 1
            return "CLICK " + fmt(P["tile%d" % t][0]) + " " + fmt(P["tile%d" % t][1])
        return "DONE"
    return fn


def policy_t04(spec, peek):
    tgt = spec["target"]; P = spec["pos"]; st = {"clicked": False}
    def fn(obs):
        if not st["clicked"]:
            st["clicked"] = True
            return "CLICK " + fmt(P["slider_click"][0]) + " " + fmt(P["slider_click"][1])
        v = int(peek("() => +document.getElementById('slider').value"))
        d = tgt - v
        if d == 0:
            return "DONE"
        return "KEY " + ("ArrowRight" if d > 0 else "ArrowLeft")
    return fn


def policy_t05(spec, peek):
    P = spec["pos"]
    return _queue_policy([
        "CLICK " + fmt(P["src"][0]) + " " + fmt(P["src"][1]),
        "KEY ctrl+a", "KEY ctrl+c",
        "CLICK " + fmt(P["dst"][0]) + " " + fmt(P["dst"][1]),
        "KEY ctrl+v",
    ])


def policy_t06(spec, peek):
    P = spec["pos"]
    return _queue_policy([
        "CLICK " + fmt(P["tab_code"][0]) + " " + fmt(P["tab_code"][1]),
        "CLICK " + fmt(P["tab_home"][0]) + " " + fmt(P["tab_home"][1]),
        "CLICK " + fmt(P["code_in"][0]) + " " + fmt(P["code_in"][1]),
        "TYPE " + spec["code"],
        "CLICK " + fmt(P["submit"][0]) + " " + fmt(P["submit"][1]),
    ])


def policy_t07(spec, peek):
    P = spec["pos"]; total = spec["total"]; st = {"n": 0, "clicked": False}
    ready_js = ("() => { const li=document.getElementById('item%d');"
                " const l=document.getElementById('list'); if(!li) return 0;"
                " const ir=li.getBoundingClientRect(), lr=l.getBoundingClientRect();"
                " return (+document.body.dataset.loaded>=%d && ir.top>=lr.top"
                "         && ir.bottom<=lr.bottom) ? 1 : 0; }"
                % (total - 1, total))
    def fn(obs):
        if st["clicked"]:
            return "DONE"
        if st["n"] == 0:
            st["n"] = 1
            return "CLICK " + fmt(P["list"][0]) + " " + fmt(P["list"][1])
        st["n"] += 1
        time.sleep(0.12)
        # End den khi: load het + item cuoi nam trong vung nhin thay cua list
        if peek(ready_js) or st["n"] > 7:
            r = peek(_CUR_JS % ("item%d" % (total - 1)))
            st["clicked"] = True
            return "CLICK " + fmt(r[0]) + " " + fmt(r[1])
        return "KEY End"
    return fn


def policy_t08(spec, peek):
    st = {"n": 0}
    def fn(obs):
        st["n"] += 1
        if st["n"] == 1:
            return "CLICK " + " ".join(fmt(x) for x in spec["pos"]["sub"])
        if st["n"] == 2:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "name"))
        if st["n"] == 3:
            return "TYPE Ada Lovelace"
        if st["n"] == 4:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "email"))
        if st["n"] == 5:
            return "TYPE ada@example.com"
        if st["n"] == 6:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "qty"))
        if st["n"] == 7:
            return "TYPE 7"
        if st["n"] == 8:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "sub"))
        return "DONE"
    return fn


def policy_t09(spec, peek):
    P = spec["pos"]; st = {"i": 0, "confirm": False}
    base = [
        "CLICK " + fmt(P["plan"][0]) + " " + fmt(P["plan"][1]),
        "CLICK " + fmt(P["coupon"][0]) + " " + fmt(P["coupon"][1]),
        "TYPE " + spec["vars"]["CODE"],
        "CLICK " + fmt(P["apply"][0]) + " " + fmt(P["apply"][1]),
    ]
    def fn(obs):
        if st["i"] < len(base):
            a = base[st["i"]]; st["i"] += 1
            return a
        total = peek("() => document.body.dataset.total")
        if total == spec["expected"] and not st["confirm"]:
            st["confirm"] = True
            return "CLICK " + fmt(P["confirm"][0]) + " " + fmt(P["confirm"][1])
        return "DONE"
    return fn


def policy_t10(spec, peek):
    P = spec["pos"]
    return _queue_policy([
        "CLICK " + fmt(P["shape"][0]) + " " + fmt(P["shape"][1]),
    ])


def policy_t11(spec, peek):
    P = spec["pos"]
    inc = "CLICK " + fmt(P["inc"][0]) + " " + fmt(P["inc"][1])
    return _queue_policy([inc] * 5 + [
        "CLICK " + fmt(P["sub"][0]) + " " + fmt(P["sub"][1]),
    ])


def policy_t12(spec, peek):
    P = spec["pos"]; st = {"n": 0}
    def fn(obs):
        st["n"] += 1
        if st["n"] == 1:
            return "CLICK " + " ".join(fmt(x) for x in P["to2"])
        if st["n"] == 2:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "code_in"))
        if st["n"] == 3:
            return "TYPE " + spec["code"]
        if st["n"] == 4:
            return "CLICK " + " ".join(fmt(x) for x in peek(_CUR_JS % "sub2"))
        return "DONE"
    return fn


POLICIES = {
    "T01_signup": policy_t01, "T02_login": policy_t02, "T03_delayed": policy_t03,
    "T04_slider": policy_t04, "T05_shortcut": policy_t05, "T06_tabcode": policy_t06,
    "T07_scroll": policy_t07, "T08_errorfix": policy_t08, "T09_coupon": policy_t09,
    "T10_canvas": policy_t10, "T11_counter": policy_t11, "T12_pagecode": policy_t12,
}


def fail_policy(obs):
    """Policy that that: click goc man hinh roi DONE."""
    return "CLICK 10 10" if obs["step"] == 0 else "DONE"


class _Dispatcher:
    """Xay policy per (task,variant) tu spec + peek cua obs dau tien."""
    def __init__(self, builder):
        self.builder = builder
        self.cache = {}
    def __call__(self, obs):
        key = (obs["task_id"], obs["variant"])
        if key not in self.cache:
            self.cache[key] = self.builder(obs["task_id"], obs["spec"], obs["peek"])
        return self.cache[key](obs)


def self_test():
    from bench_v15 import run_suite, load_tasks
    tids = [t["task_id"] for t in load_tasks()]
    print("[self-test] success policies over 36 task x variant ...")
    ok_pol = _Dispatcher(lambda tid, spec, peek: POLICIES[tid](spec, peek))
    res_ok = run_suite(ok_pol, tasks=tids, variants=(0, 1, 2), peek=True)
    print("[self-test] fail policies over 36 task x variant ...")
    res_fail = run_suite(fail_policy, tasks=tids, variants=(0, 1, 2), peek=True)

    rows = []
    n_ok_pass = n_fail_pass = 0
    for a, b in zip(res_ok, res_fail):
        assert a["task_id"] == b["task_id"] and a["variant"] == b["variant"]
        good = a["success"] and not b["success"]
        n_ok_pass += 1 if a["success"] else 0
        n_fail_pass += 1 if not b["success"] else 0
        rows.append({"task_id": a["task_id"], "variant": a["variant"],
                     "success_policy_pass": a["success"],
                     "success_reason": a.get("reason", ""),
                     "success_steps": a.get("steps"),
                     "fail_policy_rejected": not b["success"],
                     "fail_reason": b.get("reason", ""), "ok": good})
        print("  %-14s v%d  success:%s (%s)  fail-rejected:%s  %s" % (
            a["task_id"], a["variant"], "PASS" if a["success"] else "FAIL",
            a.get("reason", "")[:48], "yes" if not b["success"] else "NO",
            "" if good else "<-- PROBLEM"))

    passed = (n_ok_pass == 36 and n_fail_pass == 36)
    out = os.path.join(HERE, "self_test_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"success_policies_pass": n_ok_pass, "success_total": 36,
                   "fail_policies_rejected": n_fail_pass, "fail_total": 36,
                   "passed": passed, "rows": rows}, f, ensure_ascii=False, indent=1)
    print("[self-test] success %d/36, fail rejected %d/36 -> %s => %s" % (
        n_ok_pass, n_fail_pass, out, "PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print("usage: python checker.py --self-test")
    sys.exit(1)
