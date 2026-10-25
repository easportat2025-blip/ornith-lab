"""fix_seed_constraint.py - thuc thi "YEU CAU CUNG DUY NHAT" (PLAN.md §X):

    "Moi lan train: seed moi, ma tran moi - khong de mot khuc tham so hoc qua nhieu."

Sua kernel_v22 + kernel_v22_B (+ v21 cho cac run sau):
  1. SEED = random.randint(1, 1e9)  -> MOI RUN khac nhau
  2. Log SEED + ghi vao gui_result.json (de truy vet)
  3. Synth / eval / targeted / tap mau eval lay seed tu SEED (khong hard-code)
  4. Trainer seed=SEED (thu tu shuffle moi moi run)
  5. Adapter luon init MOI tu base (get_peft_model tren base) - da co san ✓
"""
import io
import re

TARGETS = [
    "phase13-gui/kernel_v22/gui_sft_v22.py",
    "phase13-gui/kernel_v22_B/gui_sft_v22.py",
    "phase13-gui/kernel_v21/gui_sft_v21.py",
]

BLOCK = '''# ==== YEU CAU CUNG DUY NHAT (PLAN.md X): seed MOI + ma tran MOI moi run ====
# Moi run lay seed ngau nhien -> anh/synth/eval/thu tu tap mau deu khac nhau,
# khong "moc tham so" (overfit mot khoang tham so cu the).
SEED = random.randint(1, 10 ** 9)
log("SEED=%d (moi run lai seed khac - yeu cau cung PLAN.md X)" % SEED)
'''

REPL = [
    # 1) them khoi SEED ngay truoc ham log
    (r"(def log\(m\):\n(?:    .*\n|\n)*?\n)",
     r"\1" + BLOCK + "\n"),
    # 2) synth/eval/targeted lay seed tu SEED
    (r"synth_rows = build_data\(N_TRAIN, \d+, 0\)",
     "synth_rows = build_data(N_TRAIN, SEED, 0)"),
    (r"eval_rows = build_data\(N_EVAL, \d+, 90000\)",
     "eval_rows = build_data(N_EVAL, SEED + 1, 90000)"),
    (r"build_targeted\(N_TARGETED, \d+, tdir\)",
     "build_targeted(N_TARGETED, SEED + 2, tdir)"),
    (r"rng = random\.Random\(7\)", "rng = random.Random(SEED + 3)"),
    (r"seed=\d+,", "seed=SEED,"),
    # 3) ghi seed vao result json
    (r'("n_policy_replay": len\(pr_rows\),\n)',
     r'\1        "seed": SEED,\n'),
]

for p in TARGETS:
    try:
        s = io.open(p, encoding="utf-8").read()
    except Exception as e:
        print("skip", p, e)
        continue
    if "SEED = random.randint" in s:
        print("da co SEED:", p)
        continue
    orig = s
    for pat, rep in REPL:
        s, n = re.subn(pat, rep, s, count=1)
    io.open(p, "w", encoding="utf-8", newline="\n").write(s)
    chg = sum(1 for a, b in zip(orig.splitlines(), s.splitlines()) if a != b)
    print("patched %-42s (dong doi: %d)" % (p, chg))
    for l in s.splitlines():
        if "SEED" in l and ("random.randint" in l or "build_data" in l
                            or "build_targeted" in l or "seed=SEED" in l
                            or '"seed"' in l):
            print("    ", l.strip()[:100])
