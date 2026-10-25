import json
import subprocess


def sh(cmd, t=180):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=t)
    return {"rc": r.returncode, "out": (r.stdout or "")[-400:],
            "err": (r.stderr or "")[-400:]}


res = {}
res["os"] = sh("head -2 /etc/os-release; whoami")
res["curl_pypi"] = sh("curl -sS -m 20 -o /dev/null -w '%{http_code}' https://pypi.org/simple/")
res["pip_download"] = sh("python -m pip download --no-deps --dest /tmp/pipnet six 2>&1 | tail -2")
res["apt_update"] = sh("apt-get update 2>&1 | tail -2")
print(json.dumps(res, indent=1))
with open("/kaggle/working/pw_net_probe.json", "w", encoding="utf-8") as f:
    f.write(json.dumps(res, indent=1))
