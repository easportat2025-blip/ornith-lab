"""patch_bench.py - fix _agg bug + add setup retry, apply to both bench kernel files."""
import sys

OLD_SETUP = """    try:
        setup_playwright_v2()
    except Exception as e:
        log(f"OFFLINE PW FAIL: {type(e).__name__}: {str(e)[:300]}")
        _dump({"error": "pw_offline_fail", "msg": str(e)[:500],
               "t_sec": round(time.time() - t0, 1)})
        return
"""

NEW_SETUP = """    _pw_ok = False
    _pw_last = None
    for _pw_att in range(3):
        try:
            setup_playwright_v2()
            _pw_ok = True
            break
        except Exception as e:
            _pw_last = e
            log(f"OFFLINE PW attempt {_pw_att+1}/3 FAIL: "
                f"{type(e).__name__}: {str(e)[:200]}")
            if _pw_att < 2:
                time.sleep(8)
    if not _pw_ok:
        log("OFFLINE PW FAIL (3 attempts) -> abort")
        _dump({"error": "pw_offline_fail",
               "msg": str(_pw_last)[:500] if _pw_last else "unknown",
               "t_sec": round(time.time() - t0, 1)})
        return
"""

OLD_AGG_CALL = "    agg = _agg(calls)\n"
NEW_AGG_CALL = "    agg = _agg(results)\n"

OLD_AGG = """def _agg(results):
    steps = [t for r in results for t in r["trace"]]
    n = max(len(steps), 1)
    modes = {"action": 0, "legacy": 0, "none": 0}
    prose = 0
    nn = []
    for t in steps:
        modes[t["mode"]] = modes.get(t["mode"], 0) + 1
        if t["prose_lines"] > 0:
            prose += 1
        nn.append(t["n_new"])
    return {"steps": len(steps), "modes": modes,
            "parse_rate": (modes["action"] + modes["legacy"]) / n,
            "prose_leak_rate": prose / n,
            "mean_new": round(sum(nn) / max(len(nn), 1), 1)}
"""

NEW_AGG = """def _agg(results):
    steps = []
    for r in results:
        if isinstance(r, dict) and "trace" in r:
            steps.extend(r.get("trace") or [])
        else:
            steps.append(r)
    n = max(len(steps), 1)
    modes = {"action": 0, "legacy": 0, "none": 0}
    prose = 0
    nn = []
    for t in steps:
        m = t.get("mode", "none") if isinstance(t, dict) else "none"
        modes[m] = modes.get(m, 0) + 1
        if (t.get("prose_lines") if isinstance(t, dict) else 0) or 0 > 0:
            prose += 1
        nn.append((t.get("n_new") if isinstance(t, dict) else 0) or 0)
    return {"steps": len(steps), "modes": modes,
            "parse_rate": (modes.get("action", 0) + modes.get("legacy", 0)) / n,
            "prose_leak_rate": prose / n,
            "mean_new": round(sum(nn) / max(len(nn), 1), 1)}
"""

for f in ['phase13-gui/kernel_bench_v15/bench_v15_kernel.py',
          'phase13-gui/kernel_bench_v15_v20/bench_v15_kernel.py']:
    s = open(f, encoding='utf-8').read()
    assert OLD_SETUP in s, f"OLD_SETUP not found in {f}"
    assert OLD_AGG_CALL in s, f"OLD_AGG_CALL not found in {f}"
    assert OLD_AGG in s, f"OLD_AGG not found in {f}"
    s = s.replace(OLD_SETUP, NEW_SETUP)
    s = s.replace(OLD_AGG_CALL, NEW_AGG_CALL)
    s = s.replace(OLD_AGG, NEW_AGG)
    open(f, 'w', encoding='utf-8').write(s)
    print("patched", f)
print("done")