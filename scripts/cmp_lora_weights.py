# -*- coding: utf-8 -*-
"""
cmp_lora_weights.py - so SUNG TRONG SO 2 adapter (khong so byte).
Byte khac (hash) co the chi do cach serialize lai => weights giong.
Dung: python scripts/cmp_lora_weights.py A.safetensors B.safetensors [...]
ASCII-only source.
"""
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def load(p):
    from safetensors.torch import safe_open
    out = {}
    with safe_open(p, framework="pt", device="cpu") as f:
        for k in f.keys():
            out[k] = f.get_tensor(k)
    return out


def cmp(a, b):
    ta, tb = load(a), load(b)
    ka, kb = set(ta), set(tb)
    only_a, only_b = sorted(ka - kb), sorted(kb - ka)
    same, diff = 0, []
    max_abs = 0.0
    for k in sorted(ka & kb):
        x, y = ta[k], tb[k]
        if x.shape != y.shape:
            diff.append("%s (shape %s vs %s)" % (k, tuple(x.shape),
                                                 tuple(y.shape)))
            continue
        d = (x.float() - y.float()).abs().max().item()
        max_abs = max(max_abs, d)
        if d == 0.0:
            same += 1
        else:
            diff.append("%s (max|diff|=%.3g)" % (k, d))
    return {
        "n_a": len(ka), "n_b": len(kb), "same": same, "diff": diff,
        "only_a": only_a, "only_b": only_b, "max_abs": max_abs,
    }


def main():
    if len(sys.argv) < 3:
        print("dung: python scripts/cmp_lora_weights.py A.safetensors B...")
        return 2
    base = sys.argv[1]
    others = sys.argv[2:]
    tb = load(base)
    print("A = %s (%d tensor)" % (os.path.basename(base), len(tb)))
    for o in others:
        r = cmp(base, o)
        verdict = "WEIGHTS GIONG" if (not r["diff"] and not r["only_a"]
                                      and not r["only_b"]) else "KHAC"
        print("-" * 70)
        print("B = %s" % os.path.basename(o))
        print("   tensor: A=%d B=%d | giong y het = %d | max|diff| = %g"
              % (r["n_a"], r["n_b"], r["same"], r["max_abs"]))
        if r["only_a"]:
            print("   chi co o A: %s" % r["only_a"][:5])
        if r["only_b"]:
            print("   chi o B: %s" % r["only_b"][:5])
        for d in r["diff"][:8]:
            print("   khac: %s" % d)
        print("   => %s" % verdict)
    return 0


if __name__ == "__main__":
    sys.exit(main())
