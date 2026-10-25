# -*- coding: utf-8 -*-
"""
test_infra_guard.py - CHUNG MINH guard fail-loud cua desktop-bench hoat dong.

Tinh huong (dung de tao loi "anh den"):
  - task co 'app' tro toi file KHONG TON TAI
  - khong mo browser => X11 chi co Xvfb trong => anh chup ra MANH HINH DEN
  - model thay den => DONE reward=-1 => 20 ep bi tinh nham la "model that"

Kiem tra 3 dieu:
  1) episode bi BO QUA (khong goi model, khong ton GPU)
  2) loi duoc ghi vao harness.INFRA_ERRORS (reason=app_missing)
  3) episode do KHONG duoc ghi vao actions.jsonl => khong lam nhieu diem
     (by_task cua task do khong xuat hien)

Chay: python phase14-desktop/test_infra_guard.py
ASCII-only source.
"""
import io
import json
import os
import shutil
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ENV_WORK", os.path.join(tempfile.gettempdir(),
                                               "mimo_infra_guard"))
os.environ["DB_HEADLESS"] = "1"      # import an toan (khong can X11)
import harness  # noqa: E402

harness.HEADLESS = False             # ep gioi hanh benh: co X11 that
harness.INFRA_ERRORS.clear()


class _Dummy:
    """Policy dummy: neu bi goi => fail (khong duoc goi)."""

    def __init__(self):
        self.calls = 0

    def act(self, shot, instr, step):
        self.calls += 1
        return "DONE"


def main():
    tmp = tempfile.mkdtemp(prefix="mimo_infra_")
    try:
        task = {"app": "tXX_khong_ton_tai.html", "instruction": "x",
                "reward_js": "0", "threshold": 1, "_tasks_dir": tmp}
        pol = _Dummy()
        rows, best, success = harness.run_episode("TXX_test", task, pol, tmp,
                                                   0, 3)
        errs = harness.INFRA_ERRORS
        ok = True
        if pol.calls != 0:
            print("FAIL: policy bi goi %d lan (phai 0)" % pol.calls)
            ok = False
        else:
            print("OK  : policy KHONG bi goi (episode bo qua)")
        if rows != []:
            print("FAIL: rows khong rong: %r" % (rows,))
            ok = False
        else:
            print("OK  : rows rong (khong co buoc nao ghi vao actions.jsonl)")
        if not errs or errs[0].get("reason") != "app_missing":
            print("FAIL: INFRA_ERRORS khong dung: %r" % (errs,))
            ok = False
        else:
            print("OK  : INFRA_ERRORS ghi app_missing: %s" %
                  json.dumps(errs[0], ensure_ascii=False))
        if best is not None or success:
            print("FAIL: best/success phai None/False")
            ok = False
        else:
            print("OK  : best=None success=False (khong co diem am)")
        print("== %s ==" % ("PASS" if ok else "FAIL"))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.exit(main())
