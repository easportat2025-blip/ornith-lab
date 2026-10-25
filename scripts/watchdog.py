"""watchdog.py — theo doi kernel Kaggle + HANG DOI GPU (tu push khi quota con).

Vai tro:
  1. Poll trang thai cac kernel trong scripts/watchdog_targets.json.
     - COMPLETE/ERROR -> tai output (UTF-8) -> chay post-action (neu co).
     - Marker luu lastRunTime -> version MOI duoc xu ly lai (fix bug marker
       cu ghi cho version cu -> bo qua version moi).
     - Fetch FAIL -> KHONG ghi marker -> thu lai vong sau (fix bug mat output).
  2. Hang doi GPU (scripts/gpu_queue.json): khi QUOTA GPU con (>1h) va so
     session dang chay < 2 -> push kernel tiep theo (theo 'after' de phu thuoc).
     Day la thu tu: quota GPU 30h/tuan het -> 24/10 00:00 moi co GPU; hang doi
     tu dong chay tiep khi con quota.

Chay: python scripts/watchdog.py   (dung bang file scripts/watchdog.stop)
"""
import io
import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
# Cho phep chay 2 watchdog doc lap (acc A / acc B): CFG/STATE/LOG rieng theo env.
CFG = os.environ.get("WATCH_TARGETS",
                     os.path.join(HERE, "watchdog_targets.json"))
QUEUE = os.environ.get("GPU_QUEUE", os.path.join(HERE, "gpu_queue.json"))
QSTATE = os.environ.get(
    "GPU_QUEUE_STATE",
    os.path.join(HERE, os.path.basename(QUEUE).replace(".json", "_state.json")))
STOP = os.path.join(HERE, "watchdog.stop")
STATE = os.environ.get("WATCH_STATE",
                       os.path.join(HERE, "watchdog_state.json"))
LOG = os.environ.get("WATCH_LOG", os.path.join(HERE, "watchdog.log"))

ENV = dict(os.environ)
ENV["PYTHONUTF8"] = "1"
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONLEGACYWINDOWSSTDIO"] = "0"

POLL_SEC = int(os.environ.get("POLL_SEC", "60"))
QUOTA_EVERY = 300          # 5 phong kiem tra 1 lan (tránh ton API)
GPU_MIN_HOURS = 1.0        # can it nhat 1 GPU-gio con de push
MAX_SESSIONS = 2


def bus_post(text, tag=""):
    """Day tin len BUS de agent nhan NGAY (khong can cho vong poll)."""
    try:
        import json as _json
        import urllib.request as _u
        body = _json.dumps({"from": "watchdog", "text": str(text)[:800],
                            "tag": tag}).encode("utf-8")
        req = _u.Request(os.environ.get("BUS_URL",
                                         "http://127.0.0.1:8777") + "/post",
                         data=body,
                         headers={"Content-Type": "application/json"},
                         method="POST")
        _u.urlopen(req, timeout=6).read()
        return True
    except Exception:
        return False


def log(msg):
    line = time.strftime("%m-%d %H:%M:%S") + " " + msg
    try:
        with io.open(LOG, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except Exception:
        pass
    print(line, flush=True)


def run(cmd, timeout=1800):
    p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout,
                       creationflags=(0x08000000 if os.name == "nt" else 0))
    return p.returncode, (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def load_json(path, default):
    try:
        with io.open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except Exception:
        return default


def status_of(kernel):
    rc, out, err = run(["kaggle", "kernels", "status", kernel], timeout=120)
    m = re.search(r'KernelWorkerStatus\.(\w+)', out + err)
    return m.group(1) if m else "UNKNOWN"


def last_run_times():
    """lastRunTime moi kernel cua TAT CA acc (truoc day chi parse 'hhjiji/' ->
    acc A/B khong co entry -> marker logic tu cho la 'da fetch' va BO SUNG
    QUA ket qua moi cua kernel chay lai)."""
    rc, out, err = run(["kaggle", "kernels", "list", "--mine",
                         "--page-size", "200"], timeout=240)
    d = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) >= 4 and "/" in parts[0] and parts[0].count("/") == 1:
            # cot co the lech do tieu de co space -> tim token dang NGAY
            for i, p in enumerate(parts):
                if re.match(r"^\d{4}-\d{2}-\d{2}$", p):
                    d[parts[0]] = " ".join(parts[i:i + 2])
                    break
    return d


_GATE_CACHE = {"key": None, "t": 0, "ok": True, "out": ""}


def gate_check(kdir):
    """Chay prepush_gate.py (G1-G12) truoc khi push. Tra (ok, blob).

    FIX 22/10 (MiMo): 2 kernel chet ngay ton GPU vi code khong khop metadata
    va adapter 'bai' (slug giong, weights khac) => chan o day, 0 GPU.
    Cache theo (dir, mtime metadata) trong 15' de khong goi Kaggle nhieu lan.
    """
    mp = os.path.join(kdir, "kernel-metadata.json")
    try:
        stamp = int(os.path.getmtime(mp))
    except Exception:
        stamp = 0
    key = (kdir, stamp)
    if (_GATE_CACHE.get("key") == key and
            time.time() - _GATE_CACHE.get("t", 0) < 900):
        return _GATE_CACHE["ok"], _GATE_CACHE["out"]
    rc, out, err = run([sys.executable,
                        os.path.join(HERE, "prepush_gate.py"), kdir],
                       timeout=900)
    blob = (out or "") + (err or "")
    ok = ("KET QUA: 0 FAIL" in blob)
    _GATE_CACHE.update({"key": key, "t": time.time(), "ok": ok,
                        "out": blob})
    return ok, blob


def fetch(kernel, outdir, pattern):
    os.makedirs(outdir, exist_ok=True)
    cmd = ["kaggle", "kernels", "output", kernel, "-p", outdir, "--force"]
    if pattern:
        cmd += ["--file-pattern", pattern]
    rc, out, err = run(cmd)
    ok = rc == 0
    return ok, (err or out)[-300:]


def dataset_ready(slug):
    rc, out, err = run(["kaggle", "datasets", "status", slug], timeout=120)
    txt = out + err
    return bool(re.search(r'ready|active', txt)) and \
        not re.search(r'processing|in_progress', txt)


_KACC = {"user": None}


def kaggle_account():
    """Account ma CLI Kaggle dang chay voi (kaggle config view)."""
    if _KACC["user"]:
        return _KACC["user"]
    try:
        rc, out, err = run(["kaggle", "config", "view"], timeout=60)
        m = re.search(r"username:\s*(\S+)", (out or "") + (err or ""))
        if m:
            _KACC["user"] = m.group(1)
    except Exception:
        pass
    return _KACC["user"] or ""


_DS_CACHE = {}
_DS_TTL = 1800   # 30 phut - xem ghi chu duoi


def dataset_exists(owner, slug, acc):
    """CACHE 30' (rat quan trong: 9 dataset x 13 muc queue x moi 60s = 117
    lenh Kaggle/phut => 429 'Too Many Requests' => lam chay download adapter
    465MB). Dataset ton tai dai => khong can check lai moi vong."""
    key = "%s/%s" % (owner, slug)
    hit = _DS_CACHE.get(key)
    if hit and (time.time() - hit[0]) < _DS_TTL:
        return hit[1], hit[2]
    state, n = _dataset_exists_raw(owner, slug, acc)
    _DS_CACHE[key] = (time.time(), state, n)
    return state, n


def _dataset_exists_raw(owner, slug, acc):
    """(state, n_file) voi state = exists | missing | unknown.

    DUNG 'kaggle datasets files' chu KHONG dung 'datasets status':
    - 'status' tra 403/404 cho dataset DANG PROCESSING (vua upload xong)
      => quy tac "403 = khong ton tai" se chan NHAM (da chan nham adapter v21
      acc B ngay sau khi no vua duoc upload).
    - 'files' quyet doan: >0 file => TON TAI; loi 403/404 => khong ton tai.
    - acc khac (private) => 'unknown' (khong ket luan duoc).
    """
    rc, out, err = run(["kaggle", "datasets", "files", "%s/%s" % (owner, slug)],
                       timeout=180)
    blob = (out or "") + (err or "")
    low = blob.lower()
    if rc == 0:
        n = 0
        for line in (out or "").splitlines():
            parts = line.strip().split()
            if not parts:
                continue
            if "." not in parts[0]:
                continue
            if parts[0].lower() in ("name", "size", "creationdate", "file"):
                continue
            n += 1
        return "exists", n
    if re.search(r'403|404|not found|forbidden|cannot access', low):
        if acc and owner.lower() == acc:
            return "missing", 0
        return "unknown", 0
    return "unknown", 0


def kernel_missing_datasets(kdir, critical_only=False, all_owned=False):
    """Dataset ma kernel THAT su attach (kernel-metadata.json) ma KHONG ton tai.

    FIX (MiMo 22/10): truoc day watchdog chi kiem 'needs_dataset' (ghi tay
    trong queue) - 3 kernel bench-v22 gan nhung 'needs_dataset' la lora-**v21**
    (ton tai) trong khi kernel attach lora-**v22** (CHUA ton tai) => push
    xong kernel chay khong co adapter => assert fail, mat slot GPU.
    => phai kiem chinh dataset kernel attach.
    all_owned=True: tra ve MOI dataset thuoc acc dang chay voi ma khong ton
    tai (chan push khi dataset chua upload - tiet kiem slot GPU).
    """
    mp = os.path.join(kdir, "kernel-metadata.json")
    if not os.path.exists(mp):
        return []
    try:
        md = json.load(io.open(mp, encoding="utf-8"))
    except Exception:
        return []
    acc = (kaggle_account() or "").lower()
    missing = []
    for a in md.get("dataset_sources", []):
        if "/" not in a:
            continue
        owner, name = a.split("/", 1)
        is_crit = ("lora" in name.lower() or "adapter" in name.lower())
        if critical_only and not is_crit:
            continue
        state, n = dataset_exists(owner, name, acc)
        if state == "exists" and n > 0:
            log("dataset check: %s -> TON TAI (%d file)" % (a, n))
            continue
        if state == "exists" and n == 0:
            log("dataset check: %s -> TON TAI nhung 0 file (dang xu ly?)" % a)
            continue
        if state == "unknown":
            log("dataset check: %s -> khong kiem duoc (acc khac / private)" % a)
            continue
        # state == 'missing' (chi xay ra khi dataset thuoc CHINH acc dang chay
        # voi => ket luan duoc) => chan push
        missing.append(a)
    return missing



def quota_refresh_at():
    """Doc refreshAt tu bang quota (Kaggle tra) -> timestamp epoch (neu co)."""
    rc, out, err = run(["kaggle", "quota"], timeout=180)
    for line in (out + err).splitlines():
        parts = line.split()
        if parts and parts[0] == "GPU" and len(parts) >= 5:
            m = re.match(r"(\d{4}-\d{2}-\d{2})T(\d{2}:\d{2}:\d{2})", parts[4])
            if m:
                try:
                    import datetime
                    dt = datetime.datetime.strptime(
                        m.group(1) + " " + m.group(2),
                        "%Y-%m-%d %H:%M:%S").replace(
                            tzinfo=datetime.timezone.utc)
                    return dt.timestamp()
                except Exception:
                    return None
    return None

QUOTA_CACHE = {"h": None, "ts": 0.0}


def gpu_remaining_hours():
    """Quota GPU con lai (h). CACHE 6h (user: check quota 1 lan/ngay) ->
    khong spam API, nhung van push duoc hang doi ngay."""
    now = time.time()
    if QUOTA_CACHE["h"] is not None and now - QUOTA_CACHE["ts"] < 21600:
        return QUOTA_CACHE["h"]
    rc, out, err = run(["kaggle", "quota"], timeout=120)
    val = 0.0
    for line in out.splitlines():
        parts = line.split()
        if parts and parts[0] == "GPU" and len(parts) >= 3:
            for cand in (parts[2], parts[1]):
                if cand.endswith("h"):
                    try:
                        val = float(cand[:-1])
                        break
                    except ValueError:
                        pass
    QUOTA_CACHE["h"] = val
    QUOTA_CACHE["ts"] = now
    return val


def post_action(label, script):
    pmarker = os.path.join(HERE, ".watchdog_done.%s.post" % label)
    if os.path.exists(pmarker):
        return
    log("%s chay post-action: %s" % (label, script))
    try:
        rc, out, err = run(["powershell", "-NoProfile", "-ExecutionPolicy",
                             "Bypass", "-WindowStyle", "Hidden",
                             "-File", script], timeout=7200)
        log("%s post rc=%s: %s" % (label, rc, out[-600:]))
        with io.open(pmarker, "w", encoding="utf-8") as fh:
            fh.write(str(rc))
    except Exception as e:
        log("%s post loi: %s" % (label, e))


def process_queue(qstate, lrt):
    """Push cac muc trong gpu_queue.json khi quota con + dieu kien dung."""
    q = load_json(QUEUE, [])
    if not q:
        return
    # so kernel GPU dang chay (theo muc da push roi)
    running = 0
    for item in q:
        kid = item.get("id")
        st = qstate.get(kid, {}).get("status")
        if st in ("RUNNING", "QUEUED", "PENDING"):
            # FIX 22/10 (MiMo): state cache CO THE CU (kernel da COMPLETE nhung
            # state chua cap nhat) => 'running' dem sai => "da du 2 session
            # GPU" 40' lien tuc trong khi 0 kernel dang chay => bay kernel
            # bi chan vo han. => hoi TRANG THAI SONG truoc khi tinh.
            try:
                live = (status_of(kid) or "").upper()
            except Exception:
                live = ""
            if live in ("RUNNING", "QUEUED", "PENDING"):
                running += 1
            else:
                qstate.setdefault(kid, {})["status"] = live or "UNKNOWN"
    rem = gpu_remaining_hours()
    if rem < GPU_MIN_HOURS:
        if qstate.get("_last_quota_log") != rem:
            log("quota GPU con %.2fh (< %.1fh) -> CHUA push gi" %
                (rem, GPU_MIN_HOURS))
            qstate["_last_quota_log"] = rem
        return
    # pre-flight: kiem tra moi muc san sang truoc khi push (loi code_file,
    # dataset chua READY...) -> fail LOUD, thu lai vong sau
    if not qstate.get("_preflight_ok"):
        rc, out, err = run([sys.executable,
                            os.path.join(HERE, "..", "phase13-gui",
                                         "preflight_queue.py")], timeout=900)
        if rc == 0:
            qstate["_preflight_ok"] = True
            log("pre-flight queue: PASS")
        else:
            log("pre-flight queue FAIL -> CHUA push:\n%s" % out[-900:])
            return
    for item in q:
        kid = item.get("id")
        rec = qstate.setdefault(kid, {})
        if item.get("paused"):
            log("queue %s: PAUSED (theo queue) - chi push khi bo pause" % kid)
            continue
        # FIX (MiMo 22/10): backoff da duoc GHI nhung khong bao gio duoc DOC
        # => moi loi (409 het slot GPU) bi spam bus moi 2-3 phut.
        nt = rec.get("next_try", 0) or 0
        if nt and nt > time.time():
            continue
        if rec.get("pushed"):
            continue
        after = item.get("after")
        if after:
            st = qstate.get(after, {}).get("status")
            if st != "COMPLETE":
                continue
        need_ds = item.get("needs_dataset")
        if need_ds and not dataset_ready(need_ds):
            log("queue %s: dataset %s chua READY" % (kid, need_ds))
            continue
        # FIX (MiMo 22/10): kernel CO competition_sources KHONG duoc bat
        # internet => Kaggle tra 400 Bad Request khi luu kernel (CLI khong in
        # body loi => rat kho chan doan; da cham 4 lan). Chan TRUOC khi push.
        try:
            _mp = os.path.join(item["dir"], "kernel-metadata.json")
            _md = json.load(io.open(_mp, encoding="utf-8")) if os.path.exists(_mp) else {}
        except Exception:
            _md = {}
        if _md.get("competition_sources") and _md.get("enable_internet"):
            log("queue %s: BO QUA push - enable_internet=true + competition "
                "sources => Kaggle se tra 400" % kid)
            bus_post("[watchdog] KHONG PUSH %s - enable_internet=true + "
                     "competition_sources => Kaggle tra 400 Bad Request. FIX: "
                     "enable_internet=false (dung bundle offline thay apt)" % kid,
                     tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 600
            continue
        # FIX (MiMo 22/10): kiem dataset kernel THAT SU attach TRUOC khi check
        # slot GPU (check re, va cho team thay ly do ngay chu khong phai doi
        # "da du 2 session GPU").
        # (a) adapter/LoRA: thieu => kernel CHAC CHAN crash bang 'assert lora'
        #     (da gap that 3 lan voi 3 kernel bench-v22).
        miss = kernel_missing_datasets(item["dir"], critical_only=True)
        if miss:
            log("queue %s: BO QUA push - adapter/dataset khong ton tai: %s "
                "(Kaggle se bo qua, kernel chay thieu adapter -> assert fail)"
                % (kid, ", ".join(miss)))
            bus_post("[watchdog] KHONG PUSH %s - dataset khong ton tai: %s. "
                     "Upload truoc: python scripts/upload_staging.py <staging>"
                     % (kid, ", ".join(miss)), tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 300
            continue
        # (b) MOI dataset thuoc acc dang chay voi: chua upload => kernel chay
        #     thieu du lieu (hoac preflight fail sau 30' apt) => bo qua push
        #     (desktop-bench vay 42' GPU slot cho 1 lan chay that bai).
        miss_any = kernel_missing_datasets(item["dir"], critical_only=False)
        if miss_any:
            log("queue %s: BO QUA push - dataset attach (cua acc nay) khong ton "
                "tai: %s" % (kid, ", ".join(miss_any)))
            bus_post("[watchdog] KHONG PUSH %s - dataset attach khong ton tai: %s "
                     "(kernel se chay thieu du lieu / preflight fail). Upload truoc: "
                     "python scripts/upload_staging.py <staging>"
                     % (kid, ", ".join(miss_any)), tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 300
            continue
        if running >= MAX_SESSIONS:
            log("queue %s: da du %d session GPU, cho" % (kid, running))
            continue
        # FIX (MiMo 22/10): kernel dang chay thi Kaggle TU CHOI luu version moi
        # (400 Bad Request) => don vao chay vao can, cho no xong roi push lai.
        # FIX (MiMo 22/10, tiep): dung trang thai SONG (status_of) thay vi doc
        # state cache (state co the cu => race => van push vao va gap 400).
        try:
            live = status_of(kid)
        except Exception:
            live = ""
        st = (live or rec.get("status") or "").upper()
        if st in ("RUNNING", "QUEUED", "PENDING"):
            log("queue %s: kernel dang %s (trang thai moi nhat) -> cho xong roi "
                "push lai" % (kid, st))
            rec["status"] = st
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 180
            continue
        # FIX (MiMo 22/10, sau khi desktop-bench vay 42' GPU slot/1 lan):
        # kiem MOI dataset attach (khong chi adapter) — dataset thuoc CHINH acc
        # dang chay voi ma KHONG ton tai => Kaggle bo qua => kernel chay thieu
        # du lieu (hoac preflight fail sau 30' apt) => BO QUA push, khong dot slot.
        miss_any = kernel_missing_datasets(item["dir"], critical_only=False,
                                           all_owned=True)
        if miss_any:
            log("queue %s: BO QUA push - dataset attach (cua acc nay) khong ton "
                "tai: %s" % (kid, ", ".join(miss_any)))
            bus_post("[watchdog] KHONG PUSH %s - dataset attach khong ton tai: %s "
                     "(kernel se chay thieu du lieu / preflight fail). Upload truoc: "
                     "python scripts/upload_staging.py <staging>"
                     % (kid, ", ".join(miss_any)), tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 300
            continue
        # FIX 22/10 (MiMo): GATE G1-G12 truoc khi push (chan loi "code doi
        # adapter" + "adapter bai" + "dataset thieu" o 0 GPU ton).
        g_ok, g_blob = gate_check(item["dir"])
        if not g_ok:
            g_lines = [l.strip() for l in g_blob.splitlines()
                       if "FAIL" in l or "G1" in l or "G9" in l or "G11" in l
                       or "G12" in l]
            log("queue %s: BO QUA push - GATE FAIL: %s"
                % (kid, " | ".join(g_lines[-4:])[:400]))
            bus_post("[watchdog] KHONG PUSH %s - GATE FAIL (G1-G12): %s"
                     % (kid, " | ".join(g_lines[-4:])[:400]), tag="queue")
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 600
            continue
        log("queue: push %s (%s)" % (kid, item.get("note", "")))
        rc, out, err = run(["kaggle", "kernels", "push", "-p",
                             item["dir"]], timeout=900)
        blob = (out + err)
        ok = (rc == 0 and "successfully pushed" in blob
              and "push error" not in blob.lower())
        # FIX (MiMo 22/10): Kaggle BO QUA dataset khong ton tai khi push va
        # VAN bao "successfully pushed" -> kernel chay nhung THIEU dataset
        # (vi du adapter lora-v22) -> assert fail giua run, mat ca slot GPU.
        # Day la FAIL chu khong phai OK.
        miss_ds = re.findall(
            r"could not be added to the kernel:\s*\[([^\]]*)\]", blob, re.I)
        miss_txt = ""
        if miss_ds:
            ok = False
            parts = [p.strip().strip("'\"") for p in miss_ds[0].split(",")]
            miss_txt = ", ".join(p for p in parts if p)
            log("queue %s push FAIL: Kaggle BO QUA dataset khong ton tai: %s "
                "(kernel se chay THIEU dataset do)" % (kid, miss_txt))
        log("queue %s push %s %s" % (kid, "OK" if ok else "FAIL",
                                     (blob[-1500:] if not ok else blob[-200:])
                                     .replace("\n", " ")))
        low = blob.lower()
        # FIX (MiMo 22/10): 2 case "FAIL" nua khong phai loi that:
        # (a) "Maximum batch GPU session count of N reached" => het slot GPU,
        #     phai cho va backoff, KHONG spam bus.
        # (b) 409 Conflict => slug kernel da ton tai (khong doi) => BLOCKED,
        #     khong hammer lai.
        if not ok and "maximum batch gpu session count" in low:
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 300
            log("queue %s: het slot GPU (batch limit) -> cho 5 phut" % kid)
            continue
        if not ok and ("409" in blob or "Conflict" in blob):
            rec["attempts"] = rec.get("attempts", 0) + 1
            rec["next_try"] = time.time() + 3600
            log("queue %s push FAIL 409 Conflict (slug da ton tai) -> BLOCKED 1h"
                % kid)
            bus_post("[watchdog] push %s FAIL 409 - slug da ton tai (khong doi "
                     "metadata) -> blocked 1h, can doi slug truoc" % kid,
                     tag="queue")
            continue
        if miss_txt:
            bus_post("[watchdog] push %s FAIL - Kaggle bo qua dataset khong "
                     "ton tai: %s (upload truoc khi push lai)" % (kid, miss_txt),
                     tag="queue")
        else:
            bus_post("[watchdog] push %s %s" % (kid, "OK" if ok else "FAIL"),
                     tag="queue")
        if ok:
            rec["pushed"] = True
            rec["pushed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            running += 1
            time.sleep(20)
    return


def main():
    log("WATCHDOG start (pid %d)" % os.getpid())
    qstate = load_json(QSTATE, {})
    last_quota_check = 0
    next_quota_check = 0
    while True:
        if os.path.exists(STOP):
            log("STOP file -> watchdog dung")
            return
        targets = load_json(CFG, [])
        lrt = last_run_times()
        for t in targets:
            kernel = t["kernel"]
            label = t.get("label") or kernel.split("/")[-1]
            marker = os.path.join(HERE, ".watchdog_done." +
                                  re.sub(r"[^A-Za-z0-9_.-]", "_", label))
            try:
                st = status_of(kernel)
            except Exception as e:
                log("%s status loi: %s" % (label, e))
                continue
            qstate.setdefault(kernel, {})["status"] = st
            if st in ("COMPLETE", "ERROR"):
                stamp = lrt.get(kernel, st)
                old = None
                if os.path.exists(marker):
                    try:
                        old = io.open(marker, encoding="utf-8").read().strip()
                    except Exception:
                        old = None
                if old != stamp:
                    ok, detail = fetch(kernel, t.get("outdir", "out_" + label),
                                       t.get("pattern", ""))
                    log("%s (%s) fetch %s %s" % (label, st,
                                                 "OK" if ok else "FAIL", detail))
                    bus_post("[watchdog] %s (%s) XONG - ket qua da tai ve: %s"
                             % (label, st, detail[:200]), tag="kernel")
                    if ok:
                        with io.open(marker, "w", encoding="utf-8") as fh:
                            fh.write(stamp)
                        post = t.get("post")
                        if post:
                            post_action(label, post)
                    # fetch FAIL -> giu marker cu -> vong sau thu lai
            with io.open(STATE, "w", encoding="utf-8") as fh:
                json.dump({t["kernel"]: qstate.get(t["kernel"], {}).get("status")
                           for t in targets}, fh, ensure_ascii=False, indent=1)
        # hang doi GPU: push BAT BUOC doc queue (moi 2 phut) -- quota chi la
        # dieu kien (cache, refresh 1 lan/ngay) KHONG duoc chan viec push.
        now = time.time()
        if now >= next_quota_check:
            last_quota_check = now
            _ra = quota_refresh_at()
            # FIX 24/10: sau reset, Kaggle tra refreshAt = ky TIEP THEO (tuan
            # sau), nen dieu kien '_ra <= now' khong bao gio dung => cache
            # 0.43h bi giu => watchdog thay het quota du GPU da ve 30h.
            # Moi lan check theo lich PHAI xoa cache de doc so moi.
            QUOTA_CACHE["h"] = None
            log("quota check -> xoa cache quota")
            if _ra and _ra > now + 60:
                next_quota_check = _ra + 300      # dung luc quota về (+5 phut)
                log("next quota check: %s" %
                    time.strftime("%m-%d %H:%M", time.localtime(next_quota_check)))
            else:
                next_quota_check = now + QUOTA_EVERY
        # FIX (MiMo 22/10): nạp LẠI state tu dia moi vong (TRUOC khi xu ly
        # queue). Truoc day watchdog nap 1 lan luc start => moi thay doi state
        # tu ben ngoai (vi du lenh scripts/reset_push_state.py de push lai
        # kernel) bi GHI DE khi watchdog luu state => lenh reset vo hieu.
        try:
            disk = load_json(QSTATE, {})
            for k, v in disk.items():
                if isinstance(v, dict) and isinstance(qstate.get(k), dict):
                    if v.get("pushed") != qstate[k].get("pushed"):
                        log("state: %s doi pushed %s -> %s (tu dia)"
                            % (k, qstate[k].get("pushed"), v.get("pushed")))
                    qstate[k]["pushed"] = v.get("pushed")
                    qstate[k]["pushed_at"] = v.get("pushed_at", "")
                    if v.get("status"):
                        qstate[k]["status"] = v["status"]
        except Exception as e:
            log("state reload loi: %s" % e)
        try:
            process_queue(qstate, lrt)
        except Exception as e:
            log("queue loi: %s" % e)
        with io.open(QSTATE, "w", encoding="utf-8") as fh:
            json.dump(qstate, fh, ensure_ascii=False, indent=1)
        time.sleep(POLL_SEC)


if __name__ == "__main__":
    sys.exit(main())
