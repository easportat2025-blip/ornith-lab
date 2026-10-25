# -*- coding: utf-8 -*-
"""
checker.py — TASK-15 / B15.5 checker (6 task moi, doc DOM/JS state that).

Giong checker.py cua B15 (DONG BANG, khong sua): moi task tra ve
{success, score, reason, state} doc truc tiep tu trang (page.evaluate),
verify lap trong Python chu khong tin co-flag "correct" cua trang:
  - T13 tinh lai min-chars/@/city/age 18-99, doi chieu step1err truoc;
  - T14 doi chieu picked label vs label doc duoc tu DOM + pickedat>=shownat;
  - T15 doi chieu scrolledat < ackedat (scroll truoc khi accept) + ref == ma hien;
  - T16 doi chieu 2 cap dst==src + paste counter x2;
  - T17 doc thu tu DOM cua queue vs target, khong tin saved flag;
  - T18 tinh lai so chip duoc chon tu DOM, khong tin data-count.

SPEC_JS (placeholders cho instruction + toa do normalized 0..1000) lay bang
mot evaluate luc runner moi trang. Toa do chi cho policy Script (self-test);
model that chi nhan anh + instruction.

Chay:
    python checker.py --self-test     # 18 success + 18 fail qua bench runner
"""
import json
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
  const r2n = (r) => [Math.round(((r.left + r.width/2)/1280*1000)*10)/10,
                      Math.round(((r.top + r.height/2)/720*1000)*10)/10];
"""

SPEC_JS = {
    "T13_wizard": "() => {" + _POS + """
      return {vars:{MINCHARS:String(document.body.dataset.min)},
              pos:{next1:c('next1'),user:c('user'),email:c('email'),
                   next2:c('next2'),city:c('city'),age:c('age'),
                   agree:c('agree'),submit:c('submit')}};
    }""",
    "T14_alerts": "() => {" + _POS + """
      return {vars:{DYNLABEL:document.body.dataset.label},
              label:document.body.dataset.label,
              pos:{feedhead:c('feedhead'),feed:c('feed')}};
    }""",
    "T15_dialog": "() => {" + _POS + """
      return {vars:{REFCODE:document.getElementById('refbox').textContent.trim()},
              refcode:document.getElementById('refbox').textContent.trim(),
              pos:{openbtn:c('openbtn'),ref:c('ref'),subbtn:c('subbtn')}};
    }""",
    "T16_clipboard2": "() => {" + _POS + """
      return {vars:{},
              src1:document.getElementById('srcA').value,
              src2:document.getElementById('srcB').value,
              pos:{srcA:c('srcA'),srcB:c('srcB'),dst1:c('dst1'),dst2:c('dst2'),
                   verify:c('verifybtn')}};
    }""",
    "T17_reorder": "() => {" + _POS + """
      const names=(sel)=>Array.from(document.querySelectorAll(sel)).map(e=>e.textContent);
      return {vars:{}, start:names('#queue .name'), target:names('#target .name'),
              pos:{save:c('savebtn')}};
    }""",
    "T18_countsubmit": "() => {" + _POS + """
      const pos={};
      document.querySelectorAll('#grid .chip').forEach((e,i)=>{ pos['chip'+i]=r2n(e.getBoundingClientRect()); });
      return {vars:{TARGETCOUNT:document.body.dataset.targetcount},
              target:+document.body.dataset.targetcount, pos:Object.assign({sub:c('subbtn')}, pos)};
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
def check_t13(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {min:+b.dataset.min, step:b.dataset.step, step1err:b.dataset.step1err,
              errcount:+b.dataset.errcount, submitted:b.dataset.submitted,
              user:g('user').value.trim(), email:g('email').value.trim(),
              city:g('city').value.trim(), age:g('age').value.trim(),
              agree:g('agree').checked};
    }""")
    age_ok = bool(re.match(r"^\d{1,3}$", st["age"])) and 18 <= int(st["age"]) <= 99 \
        if re.match(r"^\d{1,3}$", st["age"]) else False
    tests = {
        "errors revealed first (step1err)": st["step1err"] == "1",
        "username >= MINCHARS chars": len(st["user"]) >= st["min"],
        "email contains @": "@" in st["email"],
        "city non-empty": st["city"] != "",
        "age whole number 18-99": age_ok,
        "confirmation ticked": bool(st["agree"]),
        "reached step 3": st["step"] == "3" or st["submitted"] == "1",
        "submitted": st["submitted"] == "1",
    }
    return tests, st


def check_t14(page):
    st = page.evaluate("""() => {
      const b=document.body, tile=document.getElementById('alerttile');
      const feed=document.getElementById('feed');
      return {label:b.dataset.label, picked:b.dataset.picked||'',
              pickedat:parseFloat(b.dataset.pickedat||'0'),
              shownat:parseFloat(b.dataset.shownat||'0'),
              alertshown:b.dataset.alertshown, wrongclick:+b.dataset.wrongclick,
              alerttext:tile.textContent, shown:tile.classList.contains('shown'),
              pickedcls:tile.classList.contains('picked'),
              scrolled:b.dataset.scrolled,
              atbottom:(feed.scrollTop+feed.clientHeight>=feed.scrollHeight-12)};
    }""")
    tests = {
        "feed scrolled to bottom": st["scrolled"] == "1" and st["atbottom"],
        "alert tile was created": st["alertshown"] == "1" and st["shown"],
        "alert text carries the label": st["label"] != "" and st["label"] in st["alerttext"],
        "clicked the alert tile": st["picked"] == st["label"] and st["pickedcls"],
        "clicked after it appeared": st["shownat"] > 0 and st["pickedat"] >= st["shownat"],
        "no wrong clicks": st["wrongclick"] == 0,
    }
    return tests, st


def check_t15(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      const terms=g('terms');
      return {scrolled:b.dataset.scrolled,
              scrolledat:parseFloat(b.dataset.scrolledat||'0'),
              ackedat:parseFloat(b.dataset.ackedat||'0'),
              ack:b.dataset.ack, submitted:b.dataset.submitted,
              confirmed:b.dataset.confirmed,
              ref:g('ref').value.trim(),
              refcode:g('refbox').textContent.trim(),
              termsbottom:(terms.scrollTop+terms.clientHeight>=terms.scrollHeight-4),
              modal:g('modal').style.display, confirm:g('confirm').style.display};
    }""")
    tests = {
        "terms scrolled to bottom": st["scrolled"] == "1" and st["termsbottom"],
        "scrolled before accepting": 0 < st["scrolledat"] < st["ackedat"],
        "terms accepted": st["ack"] == "1",
        "reference == shown code": st["ref"] != "" and st["ref"] == st["refcode"],
        "submit clicked": st["submitted"] == "1",
        "final confirm clicked": st["confirmed"] == "1",
    }
    return tests, st


def check_t16(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {src1:g('srcA').value.trim(), src2:g('srcB').value.trim(),
              dst1:g('dst1').value.trim(), dst2:g('dst2').value.trim(),
              pasted1:+b.dataset.pasted1, pasted2:+b.dataset.pasted2,
              copied:+b.dataset.copied, verified:b.dataset.verified};
    }""")
    tests = {
        "target1 == source1": st["src1"] != "" and st["dst1"] == st["src1"],
        "target2 == source2": st["src2"] != "" and st["dst2"] == st["src2"],
        "paste used for target1": st["pasted1"] >= 1,
        "paste used for target2": st["pasted2"] >= 1,
        "copy happened": st["copied"] >= 1,
        "verified": st["verified"] == "1",
    }
    return tests, st


def check_t17(page):
    st = page.evaluate("""() => {
      const b=document.body;
      const names=(sel)=>Array.from(document.querySelectorAll(sel)).map(e=>e.textContent);
      return {cur:names('#queue .name'), target:names('#target .name'),
              saved:b.dataset.saved, n:+b.dataset.count};
    }""")
    tests = {
        "row count intact": len(st["cur"]) == st["n"] == len(st["target"]),
        "queue order == target order": st["cur"] == st["target"],
        "saved flag": st["saved"] == "1",
    }
    return tests, st


def check_t18(page):
    st = page.evaluate("""() => {
      const b=document.body;
      const chips=Array.from(document.querySelectorAll('#grid .chip'));
      return {target:+b.dataset.targetcount, submitted:b.dataset.submitted,
              rejected:+b.dataset.rejected,
              sel:chips.filter(c=>c.dataset.on==='1').length,
              selcls:chips.filter(c=>c.classList.contains('sel')).length,
              meter:(document.getElementById('counter').textContent||'').replace(/\\s+/g,' ').trim()};
    }""")
    want = "Selected: %d / %d" % (st["target"], st["target"])
    tests = {
        "recomputed selected count == target": st["sel"] == st["target"],
        "selected class count matches": st["selcls"] == st["target"],
        "meter text matches": st["meter"] == want,
        "submitted": st["submitted"] == "1",
    }
    return tests, st


CHECKS = {
    "T13_wizard": check_t13, "T14_alerts": check_t14, "T15_dialog": check_t15,
    "T16_clipboard2": check_t16, "T17_reorder": check_t17,
    "T18_countsubmit": check_t18,
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
            "state": {"tests": tests, **state}}


# ---------------------------------------------------------------------------
# Scripted success policies (self-test). Chi dung cho --self-test: nhan
# spec + peek (page.evaluate) de doc state; model that khong co 2 cai nay.
# ---------------------------------------------------------------------------
def fmt(v):
    s = "%.1f" % float(v)
    return s[:-2] if s.endswith(".0") else s


def _click(p):
    return "CLICK " + fmt(p[0]) + " " + fmt(p[1])


def _queue_policy(acts):
    """acts co the la string hoac callable(obs) -> string (lazy: xai khi can)."""
    st = {"i": 0}
    def fn(obs):
        i = st["i"]; st["i"] += 1
        if i >= len(acts):
            return "DONE"
        a = acts[i]
        return a(obs) if callable(a) else a
    return fn


def policy_t13(spec, peek):
    # Vi tri doi khi error banner / step an hien -> xai vi tri LIVE (peek)
    # Va vi _queue_policy dung list eager, phai truyen callable de peek luc chay.
    def c(el):
        return lambda obs: _click(peek(_CUR_JS % el))
    return _queue_policy([
        c("next1"),                                # reveal errors first
        c("user"), "TYPE Alexanderthegreat",
        c("email"), "TYPE user@example.com",
        c("next1"),
        c("city"), "TYPE Berlin",
        c("age"), "TYPE 30",
        c("next2"),
        c("agree"),
        c("submit"),
    ])


def policy_t14(spec, peek):
    P = spec["pos"]
    st = {"n": 0}
    def fn(obs):
        st["n"] += 1
        if st["n"] == 1:
            return _click(P["feedhead"])          # focus the feed
        if st["n"] == 2:
            return "KEY End"                      # scroll feed to bottom
        if st["n"] == 3:
            for _ in range(30):                   # 500ms delay cua loadbtn
                if peek("() => document.getElementById('loadbtn').classList.contains('shown')"):
                    break
                time.sleep(0.1)
            return _click(peek(_CUR_JS % "loadbtn"))
        if st["n"] == 4:
            for _ in range(20):                   # alert tile after click
                if peek("() => document.body.dataset.alertshown") == "1":
                    break
                time.sleep(0.1)
            time.sleep(0.25)                      # scrollIntoView (50ms)
            return _click(peek(_CUR_JS % "alerttile"))
        return "DONE"
    return fn


def policy_t15(spec, peek):
    ref = spec["refcode"]; st = {"n": 0}
    # Form/confirm an luc load -> xai vi tri LIVE (peek)
    def c(el):
        return _click(peek(_CUR_JS % el))
    def fn(obs):
        st["n"] += 1
        if st["n"] == 1:
            return c("openbtn")
        if st["n"] == 2:
            return c("terms")
        if st["n"] == 3:
            return "KEY End"
        if st["n"] == 4:
            return c("ack")
        if st["n"] == 5:
            return c("contbtn")
        if st["n"] == 6:
            return c("ref")
        if st["n"] == 7:
            return "TYPE " + ref
        if st["n"] == 8:
            return c("subbtn")
        if st["n"] == 9:
            return c("yesbtn")
        return "DONE"
    return fn


def policy_t16(spec, peek):
    P = spec["pos"]
    return _queue_policy([
        _click(P["srcA"]), "KEY ctrl+a", "KEY ctrl+c",
        _click(P["dst1"]), "KEY ctrl+v",
        _click(P["srcB"]), "KEY ctrl+a", "KEY ctrl+c",
        _click(P["dst2"]), "KEY ctrl+v",
        _click(P["verify"]),
    ])


_UP_JS = ("() => { const li=document.querySelectorAll('#queue li')[%d];"
          " const b=li.querySelector('button.up'); const r=b.getBoundingClientRect();"
          " return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
          "         Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")


def policy_t17(spec, peek):
    target = spec["target"]; P = spec["pos"]
    st = {"saved": False}
    def fn(obs):
        cur = peek("() => Array.from(document.querySelectorAll('#queue .name')).map(e=>e.textContent)")
        if cur == target:
            if not st["saved"]:
                st["saved"] = True
                return _click(P["save"])
            return "DONE"
        # selection-sort: dua target[i] len vi tri i bang cach bam up tai j
        i = next(k for k in range(len(target)) if cur[k] != target[k])
        j = cur.index(target[i])
        return _click(peek(_UP_JS % j))
    return fn


def policy_t18(spec, peek):
    P = spec["pos"]; n = spec["target"]
    return _queue_policy([_click(P["chip%d" % i]) for i in range(n)] + [
        _click(P["sub"]),
    ])


POLICIES = {
    "T13_wizard": policy_t13, "T14_alerts": policy_t14, "T15_dialog": policy_t15,
    "T16_clipboard2": policy_t16, "T17_reorder": policy_t17,
    "T18_countsubmit": policy_t18,
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
    from bench_v155 import run_suite, load_tasks
    tids = [t["task_id"] for t in load_tasks()]
    total = len(tids) * 3
    print("[self-test] success policies over %d task x variant ..." % total)
    ok_pol = _Dispatcher(lambda tid, spec, peek: POLICIES[tid](spec, peek))
    res_ok = run_suite(ok_pol, tasks=tids, variants=(0, 1, 2), peek=True)
    print("[self-test] fail policies over %d task x variant ..." % total)
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
        print("  %-15s v%d  success:%s (%s)  fail-rejected:%s  %s" % (
            a["task_id"], a["variant"], "PASS" if a["success"] else "FAIL",
            a.get("reason", "")[:48], "yes" if not b["success"] else "NO",
            "" if good else "<-- PROBLEM"))

    passed = (n_ok_pass == total and n_fail_pass == total)
    out = os.path.join(HERE, "self_test_report.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump({"success_policies_pass": n_ok_pass, "success_total": total,
                   "fail_policies_rejected": n_fail_pass, "fail_total": total,
                   "passed": passed, "rows": rows}, f, ensure_ascii=False, indent=1)
    print("[self-test] success %d/%d, fail rejected %d/%d -> %s => %s" % (
        n_ok_pass, total, n_fail_pass, total, out, "PASS" if passed else "FAIL"))
    return 0 if passed else 1


if __name__ == "__main__":
    if "--self-test" in sys.argv:
        sys.exit(self_test())
    print("usage: python checker.py --self-test")
    sys.exit(1)
