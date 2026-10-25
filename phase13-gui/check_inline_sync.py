"""check_inline_sync.py - kiem tra KERNEL co INLINE khop voi file repo khong.

Ly do: Kaggle CHI upload `code_file` -> moi module phai INLINE trong kernel.
Neu sua file trong repo, kernel van chay ban CU -> tham so moi (vd done_rate)
bi bo qua IM LANG (khong loi, khong hieu qua).

Hai dang inline duoc ho tro:
  A) CODE INLINE (kernel SFT): marker `# ==== <mod>.py (INLINE: ...) ====` roi
     den het file -> so sanh phan code.
  B) STRING LITERAL (kernel desktop-bench): `<NAME>_SRC = '...'` -> so sanh
     noi dung chuoi voi file repo (module duoc exec voi __name__ khac
     "__main__" nen block __main__ trong literal AN TOAN).

Ranh buoc QUAN TRONG (dung cho ca 2 dang):
  - A) phai CAT block `if __name__ == "__main__":` cua module, neu inline nguyen
    file vao kernel thi block do CHAY (kernel __name__ == "__main__") ->
    argparse cua module parse argv cua Kaggle -> SystemExit -> KERNEL CHET.
  - B) khong can cat (module exec voi __name__ khac) ✔.

Dung: python phase13-gui/check_inline_sync.py [dir_kernel ...]
Exit: 0 = tat ca khop, 1 = co lech (dung lam gate truoc khi push).
Chi doc, khong GPU/key/mang.
"""
import ast
import hashlib
import io
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DEFAULT_DIRS = [r"phase13-gui\kernel_v22", r"phase13-gui\kernel_v22_B"]

MARK_RE = re.compile(r"^\s*#\s*=+.*INLINE", re.I)
MAIN_RE = re.compile(r'^\s*if\s+__name__\s*==\s*["\']__main__["\']\s*:', re.M)

# module nao can check + bien (chuoi) tuong ung trong kernel dang B
# DUONG DAN TUONG MINH (co nhieu file cung ten: phase13-gui/harness.py KHAC
# phase14-desktop/harness.py -> phai tro dung file)
MODULES = [
    (r"phase13-gui\gen_synth_targeted.py", "GEN_SYNTH_TARGETED_SRC"),
    (r"phase13-gui\gen_synth_long.py", "GEN_SYNTH_LONG_SRC"),
    (r"phase14-desktop\harness.py", "HARNESS_SRC"),
    (r"phase14-desktop\env.py", "ENV_SRC"),
    (r"phase13-gui\exp_kernel\exp_h2_matrix.py", "EXP_SRC"),
]

REPO_DIRS = [
    HERE,                                              # phase13-gui/
    os.path.join(HERE, "exp_kernel"),                   # phase13-gui/exp_kernel/
    os.path.join(ROOT, "phase14-desktop"),               # phase14-desktop/
]


def log(m):
    print("[inlinesync] %s" % m, flush=True)


def find_repo_file(rel):
    """Duong dan TUONG MINH tuong doi voi ROOT."""
    p = os.path.join(ROOT, rel)
    return p if os.path.exists(p) else None


def read(p):
    return io.open(p, encoding="utf-8", errors="replace").read()


def body_without_main(text):
    """Cat phan THAN module (bo block `if __name__ == "__main__":`)."""
    out = []
    for l in text.splitlines():
        if l.startswith('if __name__ == "__main__":'):
            break
        out.append(l)
    return "\n".join(out)


def norm(text):
    lines = [l.rstrip() for l in text.splitlines()]
    out = []
    for l in lines:
        s = l.strip()
        if not s:
            continue
        if MARK_RE.match(l):
            continue
        out.append(s)
    return "\n".join(out)


def sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def first_diff(a, b):
    la, lb = a.splitlines(), b.splitlines()
    for i in range(max(len(la), len(lb))):
        x = la[i] if i < len(la) else "<EOF>"
        y = lb[i] if i < len(lb) else "<EOF>"
        if x != y:
            return i + 1, x, y
    return None, None, None


def literal_blocks(src):
    """Dang B: cac bien gan chuoi (ast) -> [(var_name, noi_dung)]."""
    out = []
    try:
        tree = ast.parse(src)
    except Exception as e:
        log("parse file loi: %s: %s" % (type(e).__name__, str(e)[:120]))
        return out
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and isinstance(node.value, ast.Constant) \
                    and isinstance(node.value.value, str) and len(node.value.value) > 500:
                out.append((t.id, node.value.value))
    return out


def code_blocks(src):
    """Dang A: marker -> het file (hoac den dong `if __name__` cua kernel)."""
    lines = src.splitlines()
    out = []
    for i, l in enumerate(lines):
        if MARK_RE.match(l):
            j = i + 1
            while j < len(lines) and not lines[j].startswith(
                    'if __name__ == "__main__":'):
                j += 1
            out.append((i + 1, j, "\n".join(lines[i + 1:j])))
    return out


def check_kernel(kdir, problems):
    kpath = os.path.join(ROOT, kdir)
    if not os.path.isdir(kpath):
        log("KHONG co dir: %s" % kdir)
        problems.append("%s: thieu dir" % kdir)
        return
    pyfiles = [f for f in os.listdir(kpath) if f.endswith(".py")]
    if not pyfiles:
        log("%s: khong co file .py" % kdir)
        return
    kfile = os.path.join(kpath, pyfiles[0])
    src = read(kfile)
    lits = dict(literal_blocks(src))
    codes = code_blocks(src)
    log("=== %s (%s) | inline: %d literal + %d code block" %
        (kdir, pyfiles[0], len(lits), len(codes)))

    checked = set()
    # --- dang B: string literal ---
    for modname, var in MODULES:
        repo_p = find_repo_file(modname)
        if not repo_p:
            continue
        repo_body = norm(body_without_main(read(repo_p)))
        repo_h = sha(repo_body)
        content = lits.get(var)
        if content is None:
            # co the dang A: tim block co chua def tuong ung
            hit = None
            _fn = os.path.basename(modname).replace(".py", "")
            for (ln0, ln1, blk) in codes:
                if ("def %s(" % _fn) in blk:
                    hit = (ln0, ln1, blk)
            if hit is None:
                log("  [MISS]  %-24s khong inline trong kernel" % modname)
                continue
            ln0, ln1, blk = hit
            if MAIN_RE.search(blk):
                log("  [WARN]  %-24s inline (code) CON block __main__ cua module "
                    "-> CLI argparse se chay trong kernel (kernel chet)" % modname)
                problems.append("%s: %s inline chua cat __main__" % (kdir, modname))
            if norm(blk) == repo_body:
                log("  [OK]   %-24s inline (code) khop repo sha=%s" %
                    (modname, repo_h[:12]))
            else:
                d, x, y = first_diff(norm(blk), repo_body)
                log("  [STALE] %-24s (code) khac dong %s" % (modname, d))
                log("         inline: %s" % (x or "")[:96])
                log("         repo  : %s" % (y or "")[:96])
                problems.append("%s: %s STALE" % (kdir, modname))
            checked.add(modname)
            continue
        # dang B: module duoc exec voi __name__ khac "__main__" => block
        # __main__ trong literal AN TOAN => so sanh VOI FILE REPO DAU DU.
        if norm(content) == norm(read(repo_p)):
            log("  [OK]   %-24s literal khop repo sha=%s" %
                (modname, sha(norm(read(repo_p)))[:12]))
        else:
            d, x, y = first_diff(norm(content), norm(read(repo_p)))
            log("  [STALE] %-24s literal khac dong %s" % (modname, d))
            log("         inline: %s" % (x or "")[:96])
            log("         repo  : %s" % (y or "")[:96])
            problems.append("%s: %s STALE" % (kdir, modname))
        checked.add(modname)

    # --- call-site: module REPO co tham so done_rate nhung lOI GOI khong truyen ---
    repo_p = find_repo_file("gen_synth_targeted.py")
    repo_has_param = False
    if repo_p:
        m = re.search(r"^def\s+build_targeted\s*\(([^)]*)\)",
                      read(repo_p), re.M)
        repo_has_param = bool(m and "done_rate" in m.group(1))
    if repo_has_param:
        for (cl, cline) in [(i + 1, l.strip()) for i, l
                            in enumerate(src.splitlines())
                            if re.search(r"=\s*build_targeted\s*\(", l)]:
            if "done_rate" not in cline:
                log("  [WARN]  line %d goi %s nhung module REPO co `done_rate` "
                    "-> THAM SO CHET (silent no-op)" % (cl, cline[:60]))
                problems.append("%s: done_rate khong duoc truyen (line %d)"
                                % (kdir, cl))
            else:
                log("  [OK]   line %d goi %s" % (cl, cline[:60]))


def main():
    dirs = sys.argv[1:] or DEFAULT_DIRS
    problems = []
    for d in dirs:
        check_kernel(d, problems)
    log("--- KET QUA ---")
    if problems:
        seen = set()
        for p in problems:
            if p in seen:
                continue
            seen.add(p)
            log("LECH: %s" % p)
        return 1
    log("tat ca khop")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
