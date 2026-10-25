# -*- coding: utf-8 -*-
"""
prepush_gate.py - GATE TRUOC KHI PUSH 1 KERNEL SFT (offline, khong GPU/key).

Vay la "vet bao ve" cho vu v22: kernel v22 da bi PUSH roi va CHET ngay o
buoc load data (dataset attach sai owner + dataset upload thieu anh) => mat
1 slot GPU + 1 vong train. Gate nay bat duoc loi do TRUOC khi push.

Kiem tra (voi 1 thu muc kernel):
  G1  required dataset (tu load_ds_rows(..., required=True)) PHAI duoc attach
  G2  owner khop: dataset-metadata.json cua staging local phai trung slug
      attach trong kernel-metadata.json  (bat loi "sai owner")
  G3  offline simulate layout Kaggle (zip bi STRIP -> <base>/<ten-zip>/):
      moi row phai resolve duoc anh (bat loi "upload thieu shots.zip")
  G4  inline block trong kernel phai KHOP repo (bat loi "STALE inline")
  G5  neu module inline co tham so done_rate, call site phai TRUON it
      (bat loi "silent no-op": truyen sai/khong truyen)
  G6  thong ke mix: rows / P(DONE) / steps uoc luong (canh bao ngoai nham)

Dung:
    python scripts/prepush_gate.py phase13-gui/kernel_v23a
    python scripts/prepush_gate.py phase13-gui/kernel_v22          # se FAIL
Exit 0 = PASS, 1 = FAIL.
ASCII-only source. KHONG push, KHONG dung key.
"""
import io
import json
import os
import re
import sys
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# slug dataset -> thu muc staging local (de verify offline)
STAGING = {
    "ornith-gui-train3d-hard": "phase14-blender/train3d_hard_dataset_accA",
    "ornith-gui-train3d": "phase14-blender/train3d_dataset",
    "ornith-policy-replay-data": "phase13-gui/policy_replay_dataset",
    "gui-selfplay": "phase13-gui/selfplay_dataset",
    "ornith-gui-traj": "phase13-gui/out_traj",
    "ornith-gui-real-ui": "phase13-gui/real_ui_dataset",
    "ornith-gui-real-fixtures": "phase13-gui/real_fixtures_dataset",
}
# slug co remote nhung khong co staging local -> chi bao "khong verify duoc"
NO_LOCAL = {"ornith-gui-real-ui", "ornith-gui-real-fixtures"}

# Dataset trong mix ma NOI DUNG duoc doi bang lenh upload rieng (version
# rieng) => neu lenh upload that bai, dataset online van la ban CU va kernel
# VAN CHAY BINH THUONG (khong loi) => chi so bi sai ma khong ai biet.
# 'ornith-gui-traj': ban 816 row/60 DONE (v22) -> R2 972 row/216 DONE.
#
# LUU Y: required=True KHONG chan duoc case nay (dataset cu van ton tai =>
# van mount duoc => van khong loi). Cai chan duoc la GUARD SO ROW:
#   traj_rows = load_ds_rows("ornith-gui-traj", "traj.jsonl", required=True)
#   if len(traj_rows) < 900: raise SystemExit("FAIL: traj cu, R2 chua upload")
CRITICAL_MIX = {
    "ornith-gui-traj": {
        "min_rows": 900,
        "why": "R2 = 972 row / 216 DONE; ban cu (v22) = 816 row / 60 DONE",
    },
}

# Account NAO that su co ban R2 (972 row) cua dataset traj.
# Chi kernel attach acc nay moi co y nghia co guard < 900. Acc khac van dung
# ban CU (816 row) -> ep guard 900 se lam FAIL o acc do.
# Hien tai: staging R2 chi co phase13-gui/traj_ds_staging/khoadangnguye__ornith-gui-traj
TRAJ_R2_OWNERS = {"khoadangnguye"}

# Dataset da duoc chung minh TON TAI tren acc dich bang bang chung khac
# (khong phai do gate tu kiem duoc) => chi ghi NOTE, kem ly do cua minh.
KNOWN_REMOTE_OK = {
    "ornith-gui-train3d":
        "v22 train duoc tren acc A voi 300 row train3d + 300 train3d-hard "
        "=> ca 2 dataset 3D ton tai tren acc A",
}

_STAGING_INDEX = {}


def staging_index():
    """Index tat ca thu muc staging local theo id trong dataset-metadata.json.

    G2 truoc day dung map cung (slug -> thu muc), nen kiem owner sai khi
    cung 1 slug co staging cho nhieu account (vd gui-selfplay: staging cua
    acc A la selfplay_dataset_v21, cua acc B la selfplay_dataset). Index
    nay tu chon staging co DUNG id ma kernel can.
    """
    if _STAGING_INDEX:
        return _STAGING_INDEX
    for root, dirs, files in os.walk(ROOT):
        if "dataset-metadata.json" not in files:
            continue
        p = os.path.join(root, "dataset-metadata.json")
        try:
            did = json.load(io.open(p, encoding="utf-8")).get("id") or ""
        except Exception:
            continue
        if did and did not in _STAGING_INDEX:
            _STAGING_INDEX[did] = os.path.relpath(root, ROOT).replace("\\", "/")
    return _STAGING_INDEX

INLINE_MARK = "# ==== %s (INLINE: Kaggle chi upload code_file) ===="

FAILS = []
WARNS = []
INFOS = []


def log(s):
    print(s, flush=True)


def fail(m):
    FAILS.append(m)
    log("  [FAIL] " + m)


def warn(m):
    WARNS.append(m)
    log("  [WARN] " + m)


def info(m):
    INFOS.append(m)
    log("  [info] " + m)


# ----------------------------------------------------------------- kaggle sim
def kaggle_layout(base):
    """Kaggle STRIP zip trong dataset -> noi dung giai nen vao <base>/<ten-zip>/."""
    ext = os.path.join(base, "_prepush_ext")
    os.makedirs(ext, exist_ok=True)
    for f in os.listdir(base):
        if f.endswith(".zip"):
            try:
                with zipfile.ZipFile(os.path.join(base, f)) as z:
                    z.extractall(os.path.join(ext, f[:-4]))
            except Exception:
                pass
    return ext


def resolve(rel, base, ext):
    for p in (os.path.join(base, rel), os.path.join(ext, rel)):
        if os.path.exists(p):
            return p
    name = os.path.basename(rel)
    for root in (ext, base):
        for r, _d, files in os.walk(root):
            if name in files:
                return os.path.join(r, name)
    return None


def sim_rows(base, fname):
    """-> (ok, total, co_anh_local)
    co_anh_local = staging co zip/anh cuc bo hay khong (khong co => khong
    ket luan duoc viec anh resolve duoc hay khong)."""
    jf = os.path.join(base, fname)
    if not os.path.exists(jf):
        return None, 0, False
    rows = []
    with io.open(jf, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    ext = kaggle_layout(base)
    ok = sum(1 for r in rows if resolve(r["image"], base, ext))
    # co anh/zip cuc bo hay khong (khong co => KHONG ket luan duoc viec anh
    # resolve duoc; anh co the nam o dataset khac - vd gui-selfplay)
    has_img = any(f.lower().endswith((".png", ".jpg", ".jpeg", ".webp"))
                  for _r, _d, files in os.walk(base) for f in files)
    if not has_img:
        try:
            has_img = any(f.lower().endswith(".zip")
                          for f in os.listdir(base))
        except Exception:
            has_img = False
    return ok, len(rows), has_img


def current_user():
    """Username cua key Kaggle dang dung (env truoc, roi ~/.kaggle/kaggle.json)."""
    for k in ("KAGGLE_USERNAME", "KAGGLE_USER"):
        v = os.environ.get(k)
        if v:
            return v.strip()
    try:
        p = os.path.join(os.path.expanduser("~"), ".kaggle", "kaggle.json")
        if os.path.exists(p):
            d = json.load(io.open(p, encoding="utf-8"))
            u = d.get("username")
            if u:
                return str(u).strip()
    except Exception:
        pass
    return ""


def live_exists(owner, slug):
    """(ok|missing|unknown)

    DUNG 'kaggle datasets files' (quyet doan hon 'datasets status'):
    - 'status' tra 403/404 cho dataset DANG PROCESSING (vua upload) => quy
      tac "403 = khong ton tai" se FAIL NHAM.
    - 'files': >0 file => TON TAI; loi 403/404 + dataset thuoc CHINH acc
      dang chay voi => khong ton tai; con lai (acc khac / private) =>
      'unknown' (khong ket luan duoc).
    """
    import subprocess
    env = dict(os.environ)
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    own = bool(owner) and bool(current_user()) and \
        owner.lower() == current_user().lower()
    try:
        p = subprocess.run(["kaggle", "datasets", "files", "%s/%s" % (owner, slug)],
                           capture_output=True, env=env, timeout=180)
    except Exception:
        return "unknown"
    out = ((p.stdout or b"").decode("utf-8", "replace"))
    err = ((p.stderr or b"").decode("utf-8", "replace"))
    blob = (out + err).lower()
    if p.returncode == 0:
        n = 0
        for line in out.splitlines():
            parts = line.strip().split()
            if not parts or "." not in parts[0]:
                continue
            if parts[0].lower() in ("name", "size", "creationdate", "file"):
                continue
            n += 1
        return "ok" if n else "unknown"
    if re.search(r'403|404|not found|forbidden|cannot access', blob):
        return "missing" if own else "unknown"
    return "unknown"


# -------------------------------------------------------------------- checks
def check_kernel(kdir):
    kdir = kdir if os.path.isabs(kdir) else os.path.join(ROOT, kdir)
    log("=" * 70)
    log("PRE-PUSH GATE: %s" % kdir)
    if not os.path.isdir(kdir):
        fail("khong thay thu muc kernel %s" % kdir)
        return
    pyfiles = [f for f in os.listdir(kdir) if f.endswith(".py")]
    if not pyfiles:
        fail("khong co file .py trong %s" % kdir)
        return
    main_py = os.path.join(kdir, "gui_sft_v22.py")
    if not os.path.exists(main_py):
        cands = [f for f in pyfiles if "sft" in f or "kernel" in f]
        main_py = os.path.join(kdir, cands[0]) if cands else os.path.join(kdir, pyfiles[0])
    src = io.open(main_py, encoding="utf-8").read()
    log("  file: %s (%d dong)" % (os.path.basename(main_py), src.count("\n") + 1))

    # ---- G1/G2: dataset required vs attach vs staging id
    required = re.findall(
        r'load_ds_rows\(\s*["\']([^"\']+)["\']\s*,\s*["\']([^"\']+)["\']([^)]*)\)',
        src)
    attached = []
    mpath = os.path.join(kdir, "kernel-metadata.json")
    if os.path.exists(mpath):
        md = json.load(io.open(mpath, encoding="utf-8"))
        attached = md.get("dataset_sources", [])
    # dataset_sources la slug day du "owner/name" -> so san theo TEN
    attached_names = set(a.split("/")[-1] for a in attached)
    log("  dataset required: %d | attach: %d" % (len(required), len(attached)))
    for slug, fname, tail in required:
        is_req = "required=True" in tail.replace(" ", "")
        # loader goi bang TEN (hoac owner/slug) -> so san theo basename
        req_name = slug.split("/")[-1]
        # owner ma kernel thuc su attach (de biet dataset nao cua acc nao)
        a_owner = ""
        for a in attached:
            if a.split("/")[-1] == req_name:
                a_owner = a.split("/")[0]
                break
        # Chi ep guard khi acc do THAT SU co ban R2. Acc khac van dung ban
        # CU (816 row) -> them guard 900 se lam FAIL o acc do.
        if req_name in CRITICAL_MIX and a_owner not in TRAJ_R2_OWNERS:
            info("G8 skip '%s': acc attach '%s' khong co ban R2 (chi co %s) "
                 "-> khong ep guard so row" % (req_name, a_owner or "?",
                                              ", ".join(sorted(TRAJ_R2_OWNERS))))
            continue
        if not is_req:
            # G8: silent fallback - dataset co noi dung doi rieng nhung khong
            # required=True => upload that bai se bi bo qua im lang.
            if req_name in CRITICAL_MIX:
                fail("G8 SILENT FALLBACK: '%s' duoc attach + load nhung khong "
                     "required=True. Noi dung cua dataset nay duoc thay bang "
                     "lenh upload version rieng => neu upload that bai, kernel "
                     "van chay voi ban CU (khong loi) va chi so se sai ma khong "
                     "ai thay. Fix: them required=True vao load_ds_rows('%s', ...)"
                     % (req_name, req_name))
            else:
                continue
            # van chay G8b ben duoi de bao cao het phan con lai
        # G8b: guard so row cho dataset noi dung doi rieng (fail loud neu
        # con ban CU). KHONG co guard => fail im lang nguy hiem nhat.
        if req_name in CRITICAL_MIX:
            cm = CRITICAL_MIX[req_name]
            # ten bien nhan ket qua load (vd traj_rows)
            m_var = re.search(r"(\w+)\s*=\s*load_ds_rows\(\s*[\"']%s[\"']"
                              % re.escape(req_name), src)
            if not m_var:
                fail("G8b khong tim thay bien nhan ket qua cua load_ds_rows('%s')"
                     % req_name)
                continue
            var = m_var.group(1)
            # dang 1 (assert):  if len(var) >= N  /  assert len(var) >= N
            # dang 2 (guard):   if len(var) < N: raise SystemExit(...)
            m_assert = re.search(r"len\(\s*%s\s*\)\s*(?:>=|>)\s*(\d+)" % re.escape(var),
                                 src)
            thr = kind = None
            if m_assert:
                thr, kind = int(m_assert.group(1)), "assert"
            else:
                m_guard = re.search(
                    r"len\(\s*%s\s*\)\s*<\s*(\d+)\s*:[^\n]*\n?[^\n]*?raise"
                    % re.escape(var), src)
                if not m_guard:
                    m_guard = re.search(
                        r"len\(\s*%s\s*\)\s*<\s*(\d+)[^\n]*raise" % re.escape(var),
                        src)
                if m_guard:
                    thr, kind = int(m_guard.group(1)), "guard"
            if thr is None:
                fail("G8b THIEU GUARD SO ROW cho '%s' (bien '%s'): %s. Khong co "
                     "guard thi upload that bi se khong bi phat hien (dataset cu "
                     "van ton tai => kernel van chay binh thuong, chi so sai). "
                     "Fix: them 2 dong ngay sau khi load: "
                     "'if len(%s) < %d: raise SystemExit(\"FAIL: %s cu - R2 chua upload\")'"
                     % (req_name, var, cm["why"], var, cm["min_rows"], req_name))
            elif thr < cm["min_rows"]:
                fail("G8b GUARD SO ROW qua yeu cho '%s': can >= %d, hien tai %s "
                     "(sai) - se fail nham khi ban cu bi mount"
                     % (req_name, cm["min_rows"], thr))
            else:
                info("G8b guard so row cho '%s' (bien '%s', dang %s): >= %d "
                     "(can >= %d) OK"
                     % (req_name, var, kind, thr, cm["min_rows"]))
        if req_name not in attached_names:
            fail("G1 dataset bat buoc '%s' KHONG duoc attach trong kernel-metadata" % slug)
            continue
        # G7: dataset tren Kaggle co that khong? (can kiem neu account doc duoc)
        remote = ""
        if a_owner:
            remote = live_exists(a_owner, req_name)
            if remote == "missing":
                fail("G7 DATASET KHONG TON TAI tren Kaggle: %s/%s "
                     "(kernel se mount rong -> FAIL nhu v22)" % (a_owner, req_name))
            elif remote == "ok":
                info("G7 dataset ton tai tren Kaggle: %s/%s" % (a_owner, req_name))
            else:
                info("G7 khong kiem duoc %s/%s (account hien tai khong doc "
                     "duoc) - hay chay 'kaggle datasets status %s/%s' bang "
                     "key dung" % (a_owner, req_name, a_owner, req_name))
        # staging: uu tien staging co DUNG id (owner/slug) -> dung acc cua kernel
        stg = staging_index().get("%s/%s" % (a_owner, req_name)) if a_owner else None
        if not stg:
            stg = STAGING.get(req_name)
        if not stg:
            if req_name not in NO_LOCAL:
                warn("G2 '%s' khong co staging local de verify owner" % req_name)
            continue
        sp = os.path.join(ROOT, stg)
        if not os.path.isdir(sp):
            # staging local da bi don/sua doi => KHONG chan (check quyet doan
            # la G7/G9 tren remote); chi canh bao de cap nhat lai map.
            warn("G2 '%s': staging local '%s' khong con tren dia (khong chan) "
                 "- canh bao, xac nhan tren Kaggle bang 'datasets files'"
                 % (req_name, stg))
            continue
        meta = os.path.join(sp, "dataset-metadata.json")
        if os.path.exists(meta):
            mid = json.load(io.open(meta, encoding="utf-8")).get("id") or ""
            m_owner, m_name = (mid.split("/") + [""])[:2]
            a_owner, a_name = "", req_name
            for a in attached:
                if a.split("/")[-1] == req_name:
                    a_owner = a.split("/")[0]
                    break
            if m_name != a_name:
                fail("G2 TEN SAI: staging '%s' co id=%s nhung kernel can '%s'"
                     % (stg, mid, slug))
            elif m_owner and a_owner and m_owner != a_owner:
                # staging local thuoc acc khac (vd acc B staging cho acc A).
                # Neu G7 da xac nhan dataset TON TAI tren acc cua kernel thi
                # canh bao la thua (false alarm) -> chi ghi info.
                msg = ("staging id=%s, kernel can '%s/%s' - can xac nhan: "
                       "kaggle datasets status %s/%s"
                       % (mid, a_owner, req_name, a_owner, req_name))
                if remote == "ok":
                    info("G2 owner khac (DA XAC NHAN ton tai tren acc dich): %s" % msg)
                elif req_name in KNOWN_REMOTE_OK:
                    info("G2 owner khac (NOTE - da co bang chung: %s): %s"
                         % (KNOWN_REMOTE_OK[req_name], msg))
                else:
                    warn("G2 owner khac: %s" % msg)
            else:
                info("G2 owner khop: %s" % mid)
        else:
            warn("G2 staging '%s' khong co dataset-metadata.json (khong kiem owner)" % stg)
        res = sim_rows(sp, fname)
        if res is None:
            warn("G3 staging '%s' khong co file '%s' (khong chan)" % (stg, fname))
            continue
        ok, total, has_img = res
        if ok == total:
            info("G3 '%s': %d/%d row resolve OK" % (slug, ok, total))
        elif not has_img:
            # staging local khong co anh/zip => KHONG ket luan duoc (anh co
            # the nam o dataset khac). Chi canh bao, check remote moi quyet doan.
            warn("G3 '%s': 0/%d row resolve duoc anh va staging local '%s' co "
                 "KHONG co anh/zip (khong chan) - anh co the nam o dataset khac"
                 % (slug, total, stg))
        else:
            fail("G3 '%s': chi %d/%d row resolve duoc anh (thieu shots.zip? "
                 "sai layout?)" % (slug, ok, total))

    # ---- G10: kernel CO competition_sources KHONG duoc bat internet.
    # (22/10: da cham 4 lan - Kaggle tra 400 Bad Request khi SaveKernel,
    #  CLI KHONG in body loi => rat kho chan doan. Da loai tru het moi
    #  nguyen nhan khac roi moi ra duy nhat field enable_internet.)
    try:
        _md = json.load(io.open(os.path.join(kdir, "kernel-metadata.json"),
                                encoding="utf-8"))
    except Exception:
        _md = {}
    if _md.get("competition_sources") and _md.get("enable_internet"):
        fail("G10 enable_internet=true + competition_sources => Kaggle tra "
             "400 Bad Request khi luu kernel (CLI khong in body loi => rat kho "
             "chan doan). FIX: 'enable_internet': false. Cac thu can internet "
             "phai dua vao dataset offline (vd bundle xdotool) + enable_internet=false")
    elif _md.get("enable_internet"):
        info("G10 enable_internet=true (khong co competition) - OK")

    # ---- G12: dataset ma CODE yeu cau phai duoc ATTACH (cung ten).
    # (22/10: kernel b3 chet "FAIL: dataset thieu ... ['ornith-gui-lora-v21']"
    #  vi metadata mount lora-v22 con code require lora-v21 - G9 khong bat
    #  duoc vi ca 2 dataset deu TON TAI, chi khac ten.)
    try:
        _src = ""
        for _f in os.listdir(kdir):
            if _f.endswith(".py"):
                _src += io.open(os.path.join(kdir, _f), encoding="utf-8",
                                errors="replace").read()
        _req = set()
        for _m in re.finditer(r"require_datasets\(\s*\[([^\]]*)\]", _src):
            _body = _m.group(1)
            for _n in re.findall(r"[\"']([A-Za-z0-9_.-]{3,})[\"']", _body):
                _req.add(_n)
            # bien trong list (vd ADAPTER_NAME) -> resolve gia tri gan trong source
            for _v in re.findall(r"([A-Z_][A-Z0-9_]*)\b", _body):
                _mv = re.search(r"^\s*%s\s*=\s*[\"']([A-Za-z0-9_.-]{3,})[\"']"
                                % re.escape(_v), _src, re.M)
                if _mv:
                    _req.add(_mv.group(1))
        if _req:
            _att = set()
            for _a in (attached or []):
                if "/" in _a:
                    _att.add(_a.split("/", 1)[1])
                else:
                    _att.add(_a)
            _miss = sorted(n for n in _req if n not in _att)
            if _miss:
                fail("G12 code yeu cau dataset %s nhung KERNEL KHONG attach "
                     "dataset do (dang attach: %s). Kaggle se bo qua dataset "
                     "khong ton tai => kernel chet giua run. Sua metadata hoac "
                     "code yeu cau cho khop."
                     % (", ".join(_miss),
                        ", ".join(sorted(_att)) or "(khong co)"))
            else:
                info("G12 required dataset: %s -> da attach"
                     % ", ".join(sorted(_req)))
    except Exception as e:
        info("G12 khong doc duoc code kernel: %s" % e)

    # ---- G11: KHONG MOUNT NHAM ADAPTER LoRA (slug giong, weights khac).
    # (22/10: acc B co 'dieniw/ornith-gui-lora' = adapter CU (max|diff|=0.11
    #  so v21) va 'dieniw/ornith-gui-lora-v21' = v21 THAT. 2 kernel da mount
    #  nham -> ket qua do la cua MODEL KHAC, khong dung lam baseline ma
    #  khong ai biet. => chan tai thoi diem PUSH.)
    try:
        _fps = json.load(io.open(os.path.join(ROOT, "scripts",
                                              "lora_fingerprints.json"),
                                 encoding="utf-8"))
    except Exception:
        _fps = {}
    _traps = {}
    for _slug, _info in _fps.items():
        if "BAI" in (_info.get("note") or ""):
            _traps[_slug] = _info.get("note") or ""
    _adapters = [d for d in (attached or [])
                 if "/" in d and "gui-lora" in d.split("/", 1)[1].lower()]
    if _adapters:
        _bad = [a for a in _adapters if a in _traps]
        if _bad:
            fail("G11 adapter LoRA da bi chung minh SAI (weights khac): %s - "
                 "%s. Khong dung adapter nay cho phep do (ket qua se cua model "
                 "khac ma khong ai biet). Dung slug co version suffix dung."
                 % (", ".join(_bad),
                    " | ".join(_traps[a] for a in _bad)))
        _unk = [a for a in _adapters if a not in _fps]
        if _unk:
            warn("G11 adapter chua co trong lora_fingerprints.json (chua chung "
                 "minh trong so): %s. Hay chay: python scripts/lora_fingerprint.py "
                 "--slug %s --register" % (", ".join(_unk), _unk[0]))
        else:
            info("G11 adapter: %s (da chung minh trong so)"
                 % ", ".join(sorted(_adapters)))
        _exp = (_md or {}).get("expected_adapter")
        if _exp and _exp not in (attached or []):
            fail("G11 kernel khai bao expected_adapter='%s' nhung khong attach "
                 "slug do (dang attach: %s)" % (_exp, ", ".join(_adapters)))

    # ---- G9: MOI dataset trong metadata deu phai TON TAI tren Kaggle.    # Kaggle BO QUA dataset khong ton tai khi push van bao "successfully pushed"
    # -> kernel chay nhung THIEU dataset (adapter LoRA) -> assert fail giua run.
    # (Da gap that tren kernel bench-v22: 'khoadangnguye/ornith-gui-lora-v22'
    #  chua tung duoc upload.)
    if attached:
        n_missing = n_ok = n_unknown = 0
        missing = []
        for a in attached:
            if "/" not in a:
                continue
            a_owner, a_name = a.split("/", 1)
            stt = live_exists(a_owner, a_name)
            if stt == "missing":
                n_missing += 1
                missing.append(a)
            elif stt == "ok":
                n_ok += 1
            else:
                n_unknown += 1
                if "lora" in a_name.lower() or "adapter" in a_name.lower():
                    warn("G9 khong kiem duoc dataset adapter '%s' (403 voi key "
                         "nay) - CHAC CHUA TON TAI? phai 'kaggle datasets "
                         "version' truoc khi push" % a)
        if n_missing:
            fail("G9 %d/%d dataset attach KHONG TON TAI tren Kaggle: %s. "
                 "Kaggle se BO QUA chung (khong loi khi push) -> kernel chay "
                 "nhung THIEU dataset -> assert fail giua run. Upload truoc: "
                 "'kaggle datasets create/version -p <staging>'"
                 % (n_missing, n_missing + n_ok + n_unknown, ", ".join(missing)))
        else:
            info("G9 dataset attach: %d ton tai, %d khong kiem duoc (403)"
                 % (n_ok, n_unknown))

    # ---- G4: inline stale?
    for mod in ("gen_synth_targeted", "gen_synth_long"):
        repo = os.path.join(ROOT, "phase13-gui", mod + ".py")
        if not os.path.exists(repo):
            continue
        if INLINE_MARK % (mod + ".py") not in src:
            info("G4 %s: khong inline trong kernel (bo qua)" % mod)
            continue
        marker = INLINE_MARK % (mod + ".py")
        tail = src[src.index(marker):]
        # cat phan inline = den het file (module la duoi cuoi file)
        repo_src = io.open(repo, encoding="utf-8").read()
        # bo dong marker o dau, so san theo tung dong non-empty, bo qua comment
        def norm(t):
            return [l.strip() for l in t.splitlines()
                    if l.strip() and not l.strip().startswith("#")]
        # CHI so sanh THAN module: bo block `if __name__ == "__main__":`
        # (module co CLI argparse; neu inline NGUYEN file, CLI argparse cua
        #  module chay trong kernel -> parse_args() tren argv Kaggle ->
        #  SystemExit -> KERNEL CHET truoc ca buoc train).
        def cut_main(t):
            out = []
            for l in t.splitlines():
                if l.startswith('if __name__ == "__main__":'):
                    break
                out.append(l)
            return "\n".join(out)
        inline_raw = tail.split("\n", 1)[1] if tail.startswith(marker) else tail
        if "argparse.ArgumentParser" in inline_raw:
            warn("G4 %s: inline VAN chua CLI argparse cua module -> block "
                 "__main__ cua module se chay trong kernel (kernel chet)" % mod)
        a = norm(cut_main(repo_src))
        b = norm(cut_main(inline_raw))
        if a == b:
            info("G4 %s: inline khop repo OK" % mod)
        else:
            n = min(len(a), len(b))
            first = next((i for i in range(n) if a[i] != b[i]), n)
            fail("G4 INLINE STALE: %s repo vs kernel khac tu dong %d "
                 "(repo %d dong, inline %d dong)"
                 % (mod, first, len(a), len(b)))
            if first < n:
                info("G4   repo  : %s" % a[first][:90])
                info("G4   inline: %s" % b[first][:90])

    # ---- G5: call site phai truyen done_rate neu module co no
    m = re.search(r'def build_targeted\(([^)]*)\)', src)
    if m and "done_rate" in m.group(1):
        calls = re.findall(r'build_targeted\(([^)]*)\)', src)
        bad = [c for c in calls if "done_rate" not in c]
        if bad:
            fail("G5 build_targeted co tham so done_rate nhung call site KHONG truyen: %s"
                 % bad[:2])
        else:
            info("G5 call site truyen done_rate: OK")
    m = re.search(r'def build_long\(([^)]*)\)', src)
    if m and "done_rate" in m.group(1):
        calls = re.findall(r'build_long\(([^)]*)\)', src)
        bad = [c for c in calls if "done_rate" not in c]
        if bad:
            fail("G5 build_long co tham so done_rate nhung call site KHONG truyen: %s"
                 % bad[:2])
        else:
            info("G5 build_long call site truyen done_rate: OK")

    # ---- G6: thong ke mix (best effort, offline)
    try:
        sys.path.insert(0, kdir)
        n_targeted = 0
        mm = re.search(r'N_TARGETED\s*=\s*(\d+)', src)
        if mm:
            n_targeted = int(mm.group(1))
        info("G6 N_TARGETED=%d" % n_targeted)
    except Exception as e:
        warn("G6 khong doc duoc thong so mix: %s" % e)


def main():
    if len(sys.argv) < 2:
        print("usage: python scripts/prepush_gate.py <kernel_dir>")
        return 2
    check_kernel(sys.argv[1])
    log("=" * 70)
    log("KET QUA: %d FAIL, %d WARN" % (len(FAILS), len(WARNS)))
    for f in FAILS:
        log("  FAIL: " + f)
    return 1 if FAILS else 0


if __name__ == "__main__":
    raise SystemExit(main())
