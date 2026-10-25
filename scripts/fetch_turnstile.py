"""Lay Turnstile local (streaming, cap 15k) + append vao gamedata5.jsonl."""
import hashlib
import json
import os

BASE = r"C:\Users\Admin\Desktop\New folder\data\r5\files"
JSONL = os.path.join(BASE, "gamedata5.jsonl")
N_SHARDS = 40
CAP = 15000


def shard_of(text):
    return int(hashlib.md5(text.encode("utf-8")).hexdigest(), 16) % N_SHARDS


def main():
    from datasets import load_dataset
    ds = load_dataset("amazon/Turnstile-Synthetic-Domains",
                      split="train")
    it = iter(ds)
    row0 = next(it)
    print("KEYS:", list(row0.keys()))
    inter = row0.get("interaction")
    print("interaction type:", type(inter).__name__)
    if isinstance(inter, list) and inter:
        print("item0:", str(inter[0])[:400])
    n = 0
    out = open(JSONL, "a", encoding="utf-8")
    try:
        for row in ds:
            if n >= CAP:
                break
            inter = row.get("interaction")
            instr, out_txt = "", ""
            if isinstance(inter, list) and inter:
                if isinstance(inter[0], dict):
                    roles = {}
                    for m in inter:
                        rk = str(m.get("role", m.get("ROLE", ""))).upper()
                        rv = str(m.get("content", m.get("text",
                                                       m.get("value", ""))))
                        if not rk.strip("?") or not rv:
                            for k, v in m.items():
                                if v and str(v).strip():
                                    rk = str(k).upper()
                                    rv = str(v)
                                    break
                        roles.setdefault(rk or "?", []).append(rv)
                    users = roles.get("USER", [])
                    assts = [v for k, vs in roles.items()
                             for v in vs if k not in ("USER", "SYSTEM", "?")]
                    syst = " ".join(roles.get("SYSTEM", []))
                    if users and assts:
                        instr = (syst + "\n" + users[0]).strip()
                        out_txt = assts[-1]
                else:
                    strs = [str(m) for m in inter]
                    instr = strs[0]
                    out_txt = strs[-1] if len(strs) > 1 else ""
            elif isinstance(inter, str):
                instr, out_txt = "Hoan thanh hoi thoai tool sau", inter
            if instr and out_txt:
                apis = row.get("api_names", "")
                if apis:
                    instr = instr[:2500] + f"\nTools: {str(apis)[:1500]}"
                rec = {"instruction": "[turnstile] " + instr[:4000],
                       "input": "",
                       "output": out_txt[:8000],
                       "shard": shard_of(instr + out_txt)}
                out.write(json.dumps(rec, ensure_ascii=False) + "\n")
                n += 1
    finally:
        out.close()
    print(f"TURNSTILE: +{n}")


if __name__ == "__main__":
    main()
