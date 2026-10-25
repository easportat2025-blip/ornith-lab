"""check_kernel_slugs.py - phat hien kernel se bi Kaggle tu cho 409 (GLM, 22/10).

Ly do: Kaggle YEU cau **title unique** tren moi account. Khi tao kernel moi
bang cach copy thu muc cu (chi doi `id`, quen doi `title`) => title trung voi
kernel da co => `409 Conflict ... slug da ton tai` => push that bai, mat slot.

Vi du that (22/10): phase13-gui/kernel_v23 co
    id    = khoadangnguye/ornith-gui-sft-v23
    title = ornith-gui-sft-v22      <-- stale, trung voi kernel v22 da co

Tool nay (chi doc, khong can key/GPU/mang):
  1) quet phase13-gui/kernel_*/kernel-metadata.json
  2) canh bao:
     - title != phan cuoi cua id            -> co nguy co 409
     - title trung voi kernel khac (id khac) -> 409 CHAC
     - id trung voi kernel khac             -> 409 CHAC
  3) doi chieu voi danh sach slug da biet tu watchdog (targets/state) =>
     slug da tung push => KHONG nen tao lai bang id cu.

Dung: python phase13-gui/check_kernel_slugs.py
"""
import collections
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P13 = os.path.join(ROOT, "phase13-gui")
SCRIPTS = os.path.join(ROOT, "scripts")


def load_json(p):
    try:
        return json.load(io.open(p, encoding="utf-8"))
    except Exception:
        return None


def known_slugs():
    """Slug da biet (watchdog targets/state) - de canh bao 'dung id cu'."""
    out = set()
    for f in ("watchdog_targets.json", "watchdog_targets_B.json",
              "watchdog_state.json", "watchdog_state_B.json"):
        d = load_json(os.path.join(SCRIPTS, f))
        if not d:
            continue
        if isinstance(d, list):
            for e in d:
                if isinstance(e, dict) and e.get("kernel"):
                    out.add(e["kernel"])
        elif isinstance(d, dict):
            out |= set(d.keys())
    return out


def main():
    only = None
    argv = sys.argv[1:]
    if "--only" in argv:
        i = argv.index("--only")
        only = argv[i + 1] if i + 1 < len(argv) else None
        argv = argv[:i] + argv[i + 2:]
    rows = []
    for d in sorted(os.listdir(P13)):
        if not d.startswith("kernel_"):
            continue
        if only and only not in d:
            continue
        mp = os.path.join(P13, d, "kernel-metadata.json")
        if not os.path.isfile(mp):
            continue
        m = load_json(mp) or {}
        rows.append((d, m.get("id") or "", m.get("title") or ""))
    if not rows:
        print("[slug] khong tim thay kernel nao")
        return 1
    print("[slug] quet %d kernel\n" % len(rows))
    known = known_slugs()
    by_id = collections.defaultdict(list)
    by_title = collections.defaultdict(list)
    for d, i, t in rows:
        by_id[i].append(d)
        by_title[t].append(d)
    problems = 0
    n_version = 0
    for d, i, t in rows:
        notes = []
        slug = i.split("/")[-1] if "/" in i else ""
        if not i:
            notes.append("THIEU id")
        if t and slug and t != slug:
            notes.append("TITLE khong khop id: title=%r (id cuoi=%r) -> 409 neu "
                         "title da ton tai" % (t, slug))
        if len(by_title[t]) > 1 and len(set(by_id[t])) > 1:
            others = [x for x in by_title[t] if x != d]
            notes.append("TITLE TRUNG voi %s" % others)
        if len(by_id[i]) > 1:
            notes.append("ID TRUNG voi %s" % [x for x in by_id[i] if x != d])
        ver = bool(i) and i in known
        if ver:
            n_version += 1
        if notes:
            problems += 1
            print("  %-28s %-42s %s" %
                  (d, i, "(slug da push truoc -> version moi)" if ver else ""))
            for n in notes:
                print("       - %s" % n)
    print()
    print("[slug] %d kernel da tung push (push lai = version moi, OK)" % n_version)
    if problems:
        print("[slug] %d kernel CAN XEM LAI (409 = 'slug da ton tai')" % problems)
    else:
        print("[slug] OK: khong co trung title/id")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
