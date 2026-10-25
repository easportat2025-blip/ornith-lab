# -*- coding: utf-8 -*-
"""
dummy_mimo.py - 4 dummy policy cho 4 app cua MiMo (TASK-26), de smoke test
desktop-bench THAT SU (dummy cua @GLM chi click, khong go text -> khong kiem
duoc app co nhan dung gia tri ngau nhien hay khong).

CACH DUNG: paste 4 class duoi day vao harness.py (ngay sau class DummyKeys),
roi them vao bang task (xem cuoi file).

API (khop harness.py cua @GLM):
    _page_state(expr)         -> doc DOM qua CDP (chuoi: JSON.stringify(...))
    parse_action_v2(str)      -> (verb, arg)
    act(self, shot, task, t)  -> (mo ta, (verb, arg))
Moi app co `window.__targets` (toa do normalized, luc load) + `window.__state`
(trang thai cuoi). Dummy doc GIA TRI NGAU NHIEN tu DOM roi go that.
"""
import json  # de file nay chay doc lap (khi paste vao harness.py thi bi thua nhung an toan)


def _mimo_rect(sel):
    """Live rect cua 1 element -> (x, y) normalized 0..1000 (doc qua DOM)."""
    js = ("(function(){const e=document.querySelector('%s'); if(!e) return null;"
          " const r=e.getBoundingClientRect();"
          " return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
          "         Math.round(((r.top+r.height/2)/720*1000)*10)/10];})()"
          % sel)
    try:
        r = _page_state("JSON.stringify(%s)" % js)
    except Exception:
        r = None
    if not r:
        return None
    try:
        v = json.loads(r)
    except Exception:
        v = None
    if not v or len(v) < 2:
        return None
    return [int(v[0]), int(v[1])]


def _mimo_click(sel):
    p = _mimo_rect(sel)
    return ("click", [p[0], p[1]]) if p else None


def _mimo_text(sel):
    try:
        r = _page_state("JSON.stringify((document.querySelector('%s')||{}).textContent||'')"
                        % sel)
    except Exception:
        return ""
    if not r:
        return ""
    try:
        return json.loads(r).strip()
    except Exception:
        return ""


def _mimo_top_row():
    """Toa do dong co score cao nhat (doc live, vi bang co the da cuon)."""
    js = ("(function(){const rows=Array.from(document.querySelectorAll('#tb tr'));"
          "let best=null,bv=-1;rows.forEach(tr=>{"
          "const sc=parseInt(tr.children[2].textContent.trim(),10)||0;"
          "if(sc>bv){bv=sc;best=tr;}});if(!best) return null;"
          "const r=best.getBoundingClientRect();"
          "return [Math.round(((r.left+r.width/2)/1280*1000)*10)/10,"
          "       Math.round(((r.top+r.height/2)/720*1000)*10)/10];})()")
    try:
        r = _page_state("JSON.stringify(%s)" % js)
        v = json.loads(r) if r else None
    except Exception:
        v = None
    return [int(v[0]), int(v[1])] if v and len(v) >= 2 else None


class DummyFormDesktop:
    """T21_form_desktop: doc user/email/password tu o vang -> go vao 4 field
    -> tick terms -> Submit. MOI BUOC = 1 action (click field roi moi type)."""

    def __init__(self):
        self.i = 0

    def _plan(self):
        user = _mimo_text("#nu")
        email = _mimo_text("#ne")
        pwd = _mimo_text("#np")
        return [("click", "#u"), ("type", user), ("click", "#e"), ("type", email),
                ("click", "#p"), ("type", pwd), ("click", "#p2"), ("type", pwd),
                ("click", "#terms"), ("click", "#submit")]

    def act(self, shot, task, t=0):
        plan = self._plan()
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if not val:
            return "(scripted) empty value", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


class DummyCalc:
    """T22_calc: doc 2 bieu thuc tu DOM, tinh lai, go dap an + bam Check."""

    def __init__(self):
        self.i = 0

    @staticmethod
    def _solve(expr):
        import re as _re
        m = _re.search(r"(\d+)\s*([+-])\s*(\d+)", expr or "")
        if not m:
            return None
        a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
        return str(a + b if op == "+" else a - b)

    def _plan(self):
        e1 = _mimo_text("#e1")
        e2 = _mimo_text("#e2")
        return [("click", "#a1"), ("type", self._solve(e1)), ("click", "#c1"),
                ("click", "#a2"), ("type", self._solve(e2)), ("click", "#c2"),
                ("click", "#submit")]

    def act(self, shot, task, t=0):
        plan = self._plan()
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if not val:
            return "(scripted) cannot solve", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


class DummyTableSort:
    """T23_table_sort: SCROLL 5 (chuot xe) -> click header Score (2 lan) ->
    click dong co score cao nhat -> Confirm."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        plan = [("scroll", "5"), ("click", "#hscore"), ("click", "#hscore"),
                ("row", None), ("click", "#confirm")]
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "scroll":
            return "(scripted) scroll down", ("scroll", "5")
        if kind == "row":
            p = _mimo_top_row()
            return ("(scripted) pick top row",
                    ("click", p) if p else ("done", None))
        a = _mimo_click(val)
        return ("(scripted) click %s" % val, a or ("done", None))


class DummyTextEdit:
    """T24_text_edit: click textarea -> ctrl+a -> go cau moi -> Save."""

    def __init__(self):
        self.i = 0

    def act(self, shot, task, t=0):
        want = _mimo_text("#want")
        plan = [("click", "#ta"), ("key", "ctrl+a"), ("type", want),
                ("click", "#save")]
        if self.i >= len(plan):
            return "(scripted) done", ("done", None)
        kind, val = plan[self.i]
        self.i += 1
        if kind == "click":
            a = _mimo_click(val)
            return ("(scripted) click %s" % val, a or ("done", None))
        if kind == "key":
            return "(scripted) key %s" % val, ("key", val)
        if not val:
            return "(scripted) no target text", ("done", None)
        return ("(scripted) type %r" % val, ("type", val))


# --------------------------------------------------------------------------
# Wire vao bang task (trong harness.py). Vi du:
#   TASK_TABLE = {
#       ...
#       "T21_form_desktop": (DummyFormDesktop, 14),
#       "T22_calc":         (DummyCalc, 12),
#       "T23_table_sort":   (DummyTableSort, 18),
#       "T24_text_edit":    (DummyTextEdit, 10),
#   }
# --------------------------------------------------------------------------
