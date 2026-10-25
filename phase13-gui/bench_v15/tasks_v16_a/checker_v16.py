# -*- coding: utf-8 -*-
"""
checker_v16.py — TASK-20 / B16-A checker (8 task moi, doc DOM/JS state that).

Giong checker B15/B15.5: moi task tra ve {success, score, reason, state} doc truc
tiep tu trang (page.evaluate), verify lap trong Python, khong tin co-flag.

SPEC_JS (placeholders + toa do normalized 0..1000) lay bang mot evaluate luc runner
moi trang. Toa do chi cho policy Script (self-test); model chi nhan anh + instruction.

Chay:
    python checker_v16.py --self-test     # 24 success + 24 fail qua bench runner
"""
import json
import os
import re
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))

_POS = """
  const c = (id) => { const e = document.getElementById(id); if (!e) return null;
    const r = e.getBoundingClientRect();
    return [Math.round(((r.left + r.width/2)/1280*1000)*10)/10,
            Math.round(((r.top + r.height/2)/720*1000)*10)/10]; };
  const r2n = (r) => [Math.round(((r.left + r.width/2)/1280*1000)*10)/10,
                      Math.round(((r.top + r.height/2)/720*1000)*10)/10];
"""

SPEC_JS = {
    "T19_wizardsum": "() => {" + _POS + """
      return {vars:{},
              n1:+document.body.dataset.n1, n2:+document.body.dataset.n2,
              n3:+document.body.dataset.n3, n4:+document.body.dataset.n4,
              sum:+document.body.dataset.sum,
              pos:{next1:c('next1'),next2:c('next2'),next3:c('next3'),
                   next4:c('next4'),ans:c('ans'),sub:c('subbtn')}};
    }""",
    "T20_distractor": "() => {" + _POS + """
      const pos={};
      document.querySelectorAll('.opt').forEach((e,i)=>{ pos['opt'+i]=r2n(e.getBoundingClientRect()); });
      return {vars:{}, correct:document.body.dataset.correct,
              pos:Object.assign({target:c('target')}, pos)};
    }""",
    "T21_hiddenval": "() => {" + _POS + """
      return {vars:{}, code:document.body.dataset.code,
              pos:{hide:c('hidebtn'),ans:c('ans'),sub:c('subbtn')}};
    }""",
    "T22_keynav": "() => {" + _POS + """
      return {vars:{}, targetrow:+document.body.dataset.targetrow,
              targetcol:+document.body.dataset.targetcol,
              pos:{grid:c('grid')}};
    }""",
    "T23_undoredo": "() => {" + _POS + """
      return {vars:{}, pos:{f1:c('f1'),f2:c('f2'),f3:c('f3'),
                   undo:c('undo'),save:c('save')}};
    }""",
    "T24_multifilter": "() => {" + _POS + """
      const pos={};
      document.querySelectorAll('.filt').forEach((e,i)=>{ pos['filt'+i]=r2n(e.getBoundingClientRect()); });
      // items
      const items=Array.from(document.querySelectorAll('.item:not(.hidden)'));
      const pos2={};
      items.forEach((e,i)=>{ pos2['item'+i]=r2n(e.getBoundingClientRect()); });
      return {vars:{}, pos:Object.assign({sub:c('subbtn')}, pos, pos2),
              nitems:items.length};
    }""",
    "T25_compute": "() => {" + _POS + """
      return {vars:{}, a:+document.body.dataset.a, b:+document.body.dataset.b,
              result:+document.body.dataset.result,
              pos:{ans:c('ans'),sub:c('subbtn')}};
    }""",
    "T26_distractorlist": "() => {" + _POS + """
      const pos={};
      const all=document.querySelectorAll('.item');
      all.forEach((e,i)=>{ pos['item'+i]=r2n(e.getBoundingClientRect()); });
      return {vars:{}, targetlist:document.body.dataset.targetlist,
              targetitem:document.body.dataset.targetitem,
              pos:Object.assign({sub:c('subbtn')}, pos)};
    }""",
}

_CUR_JS = ("() => { const e = document.getElementById('%s');"
           " const r = e.getBoundingClientRect();"
           " return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
           "         Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")

# ---------------------------------------------------------------------------
# Check functions
# ---------------------------------------------------------------------------
def check_t19(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {n1:+b.dataset.n1,n2:+b.dataset.n2,n3:+b.dataset.n3,n4:+b.dataset.n4,
              sum:+b.dataset.sum, submitted:b.dataset.submitted,
              answer:(g('ans')||{}).value?g('ans').value.trim():'',
              step:b.dataset.step};
    }""")
    expected = st["n1"]+st["n2"]+st["n3"]+st["n4"]
    tests = {
        "submitted": st["submitted"] == "1",
        "answer == sum (recomputed)": st["answer"] == str(expected),
        "sum matches dataset": st["sum"] == expected,
    }
    return tests, st

def check_t20(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {correct:b.dataset.correct, picked:b.dataset.picked,
              wrongclick:+b.dataset.wrongclick, submitted:b.dataset.submitted};
    }""")
    tests = {
        "picked correct button": st["picked"] == "Option "+st["correct"],
        "no wrong clicks": st["wrongclick"] == 0,
    }
    return tests, st

def check_t21(page):
    st = page.evaluate("""() => {
      const b=document.body, g=id=>document.getElementById(id);
      return {code:b.dataset.code, hidden:b.dataset.hidden,
              typed:b.dataset.typed, submitted:b.dataset.submitted};
    }""")
    tests = {
        "code was hidden": st["hidden"] == "1",
        "typed == code (recomputed)": st["typed"] == st["code"] and st["code"] != "",
        "submitted": st["submitted"] == "1",
    }
    return tests, st

def check_t22(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {targetrow:+b.dataset.targetrow, targetcol:+b.dataset.targetcol,
              selected:b.dataset.selected, submitted:b.dataset.submitted};
    }""")
    tests = {
        "selected target cell": st["selected"] == "r%dc%d" % (st["targetrow"], st["targetcol"]),
        "submitted": st["submitted"] == "1",
    }
    return tests, st

def check_t23(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {f1:b.dataset.f1, f2:b.dataset.f2, f3:b.dataset.f3,
              saved:b.dataset.saved};
    }""")
    tests = {
        "field1 non-empty": st["f1"] != "",
        "field2 empty after undo": st["f2"] == "",
        "field3 empty after undo": st["f3"] == "",
        "saved": st["saved"] == "1",
    }
    return tests, st

def check_t24(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {f1:b.dataset.f1, f2:b.dataset.f2, picked:b.dataset.picked,
              submitted:b.dataset.submitted};
    }""")
    tests = {
        "filter color applied": st["f1"] == "1",
        "filter size applied": st["f2"] == "1",
        "picked Apple": st["picked"] == "Apple",
        "submitted": st["submitted"] == "1",
    }
    return tests, st

def check_t25(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {a:+b.dataset.a, b:+b.dataset.b, result:+b.dataset.result,
              typed:b.dataset.typed, submitted:b.dataset.submitted};
    }""")
    expected = st["a"] + st["b"]
    tests = {
        "typed == a+b (recomputed)": st["typed"] == str(expected),
        "result matches": st["result"] == expected,
        "submitted": st["submitted"] == "1",
    }
    return tests, st

def check_t26(page):
    st = page.evaluate("""() => {
      const b=document.body;
      return {targetlist:b.dataset.targetlist, targetitem:b.dataset.targetitem,
              picked:b.dataset.picked, submitted:b.dataset.submitted};
    }""")
    tests = {
        "picked correct item@list": st["picked"] == st["targetitem"] + "@" + st["targetlist"],
        "submitted": st["submitted"] == "1",
    }
    return tests, st

CHECKS = {
    "T19_wizardsum": check_t19, "T20_distractor": check_t20,
    "T21_hiddenval": check_t21, "T22_keynav": check_t22,
    "T23_undoredo": check_t23, "T24_multifilter": check_t24,
    "T25_compute": check_t25, "T26_distractorlist": check_t26,
}


def check_task(page, task_id):
    fn = CHECKS[task_id]
    tests, state = fn(page)
    failed = [k for k, v in tests.items() if not v]
    ok = not failed
    return {"success": ok, "score": 1.0 if ok else 0.0,
            "reason": "all %d checks pass" % len(tests) if ok
                      else "failed: " + ", ".join(failed),
            "state": {"tests": tests, **state}}


# ---------------------------------------------------------------------------
# Scripted success policies
# ---------------------------------------------------------------------------
def fmt(v):
    s = "%.1f" % float(v)
    return s[:-2] if s.endswith(".0") else s


def _click(p):
    return "CLICK " + fmt(p[0]) + " " + fmt(p[1])


def _queue_policy(acts):
    st = {"i": 0}
    def fn(obs):
        i = st["i"]; st["i"] += 1
        if i >= len(acts):
            return "DONE"
        a = acts[i]
        return a(obs) if callable(a) else a
    return fn


def policy_t19(spec, peek):
    P = spec["pos"]
    s = spec["sum"]
    return _queue_policy([
        lambda o: _click(peek(_CUR_JS % "next1")),
        lambda o: _click(peek(_CUR_JS % "next2")),
        lambda o: _click(peek(_CUR_JS % "next3")),
        lambda o: _click(peek(_CUR_JS % "next4")),
        lambda o: _click(peek(_CUR_JS % "ans")),
        "TYPE " + str(s),
        lambda o: _click(peek(_CUR_JS % "subbtn")),
    ])


def policy_t20(spec, peek):
    P = spec["pos"]; correct = spec["correct"]
    # find the opt button whose data-label matches "Option X"
    def find_opt(obs):
        for i in range(4):
            key = "opt%d" % i
            if key in P:
                # peek its data-label
                lbl = peek("() => document.querySelectorAll('.opt')[%d].dataset.label" % i)
                if lbl == "Option " + correct:
                    return _click(peek("() => { const e=document.querySelectorAll('.opt')[%d]; const r=e.getBoundingClientRect(); return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10, Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }" % i))
        return "DONE"
    return _queue_policy([find_opt])


def policy_t21(spec, peek):
    code = spec["code"]
    return _queue_policy([
        lambda o: _click(peek(_CUR_JS % "hidebtn")),
        lambda o: _click(peek(_CUR_JS % "ans")),
        "TYPE " + code,
        lambda o: _click(peek(_CUR_JS % "subbtn")),
    ])


def policy_t22(spec, peek):
    tr = spec["targetrow"]; tc = spec["targetcol"]
    acts = []
    # navigate from (0,0) to (tr,tc)
    for _ in range(tr):
        acts.append("KEY ArrowDown")
    for _ in range(tc):
        acts.append("KEY ArrowRight")
    acts.append("KEY Enter")
    return _queue_policy(acts)


def policy_t23(spec, peek):
    return _queue_policy([
        lambda o: _click(peek(_CUR_JS % "f1")),
        "TYPE aaa",
        lambda o: _click(peek(_CUR_JS % "f2")),
        "TYPE bbb",
        lambda o: _click(peek(_CUR_JS % "f3")),
        "TYPE ccc",
        lambda o: _click(peek(_CUR_JS % "undo")),
        lambda o: _click(peek(_CUR_JS % "undo")),
        lambda o: _click(peek(_CUR_JS % "save")),
    ])


def policy_t24(spec, peek):
    # apply filter color=red, size=large, click Apple, submit
    def click_filt(label):
        def fn(obs):
            js = ("() => { const bs=Array.from(document.querySelectorAll('.filt'));" +
                  " const b=bs.find(x=>x.textContent.includes('%s'));" % label +
                  " const r=b.getBoundingClientRect(); return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10, Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")
            return _click(peek(js))
        return fn
    def click_apple(obs):
        js = ("() => { const it=Array.from(document.querySelectorAll('.item:not(.hidden)'));" +
              " const t=it.find(x=>x.textContent.includes('Apple'));" +
              " const r=t.getBoundingClientRect(); return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10, Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")
        return _click(peek(js))
    return _queue_policy([
        click_filt("Color: red"),
        click_filt("Size: large"),
        click_apple,
        lambda o: _click(peek(_CUR_JS % "subbtn")),
    ])


def policy_t25(spec, peek):
    res = spec["result"]
    return _queue_policy([
        lambda o: _click(peek(_CUR_JS % "ans")),
        "TYPE " + str(res),
        lambda o: _click(peek(_CUR_JS % "subbtn")),
    ])


def policy_t26(spec, peek):
    target = spec["targetitem"]; tl = spec["targetlist"]
    def click_target(obs):
        js = ("() => { const lists=document.querySelectorAll('.card');" +
              " const idx=%s==='A'?0:1;" % repr(tl) +
              " const items=lists[idx].querySelectorAll('.item');" +
              " const t=Array.from(items).find(x=>x.textContent.startsWith('%s'));" % target +
              " const r=t.getBoundingClientRect(); return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10, Math.round(((r.top+r.height/2)/720*1000)*10)/10]; }")
        return _click(peek(js))
    return _queue_policy([
        click_target,
        lambda o: _click(peek(_CUR_JS % "subbtn")),
    ])


POLICIES = {
    "T19_wizardsum": policy_t19, "T20_distractor": policy_t20,
    "T21_hiddenval": policy_t21, "T22_keynav": policy_t22,
    "T23_undoredo": policy_t23, "T24_multifilter": policy_t24,
    "T25_compute": policy_t25, "T26_distractorlist": policy_t26,
}


def fail_policy(obs):
    return "CLICK 10 10" if obs["step"] == 0 else "DONE"


class _Dispatcher:
    def __init__(self, builder):
        self.builder = builder
        self.cache = {}
    def __call__(self, obs):
        key = (obs["task_id"], obs["variant"])
        if key not in self.cache:
            self.cache[key] = self.builder(obs["task_id"], obs["spec"], obs["peek"])
        return self.cache[key](obs)


def self_test():
    from bench_v16 import run_suite, load_tasks
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
        print("  %-18s v%d  success:%s (%s)  fail-rejected:%s  %s" % (
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
    print("usage: python checker_v16.py --self-test")
    sys.exit(1)
