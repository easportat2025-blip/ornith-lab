"""audit_datasets.py - quet TAT CA dataset tren Kaggle (acc A/B/C) va bao cao
chat luong: so file, co jsonl/zip khong, anh co resolve duoc khong (mo phong
DUNG logic _resolve cua loader `phase13-gui/kernel_v23b/gui_sft_v23.py`).

Dung:
  python scripts/audit_datasets.py [--accounts A,B,C] [--max-ds-mb 150]
                                   [--out scripts/dataset_audit]

Key:
  acc A (khoadangnguye): KAGGLE_KEY_A trong HKCU\\Environment (fallback env)
  acc B (dieniw):        KAGGLE_KEY_B trong HKCU\\Environment (fallback env)
  acc C (hhjiji):        KAGGLE_USERNAME/KAGGLE_KEY trong env (session hien tai)

KHONG key vao file. Khong push. Chi DOC dataset.

Logic _resolve (ban sao TU loader v24 - gui_sft_v23.py dong 377-394):
  1. base/rel      (base = thu muc mount chua file jsonl)
  2. ext/rel       (ext = noi giai nen TAT CA .zip trong base)
  3. basename(rel) bat ky trong ext (walk)
  4. basename(rel) bat ky trong base (walk) - BO SUNG v24, xu ly anh o subdir
     (vd traj_images/xxx.png trong khi jsonl chi ghi basename)
Luu y loader: jsonl phai nam O TOP-LEVEL cua dataset (sau do moi giai nen
zip) -> neu jsonl chi nam TRONG zip, loader KHONG tim thay (bao canh bao rieng).

Ghi chu phu (sua sau run2):
  - SDK Kaggle: f.ref rong '' -> ten file that nam o f.name (dung f.name).
  - Dataset copy sang acc B co the bi 404 o endpoint tai TOAN BO (zip dong goi)
    -> fallback tai TUNG file (jsonl/zip); anh lay duong dan tu listing.
  - Copy jsonl trung dung (top + nested, cung hash) -> loader chi doc 1 ban
    -> chi dem 1 lan (khong nhan doi row).
"""
import argparse
import csv
import hashlib
import io
import json
import os
import shutil
import sys
import zipfile

IMG_EXT = (".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif")

ACCT = {
    "A": ("khoadangnguye", "KAGGLE_KEY_A"),
    "B": ("dieniw", "KAGGLE_KEY_B"),
    "C": (os.environ.get("KAGGLE_USERNAME") or "hhjiji", "KAGGLE_KEY"),
}


def read_key(env_name):
    """Doc key tu HKCU\\Environment (Windows) truoc, fallback os.environ."""
    try:
        import winreg
        reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER, "Environment")
        try:
            return winreg.QueryValueEx(reg, env_name)[0]
        finally:
            winreg.CloseKey(reg)
    except Exception:
        return os.environ.get(env_name)


def make_api(user, key_env):
    key = read_key(key_env)
    if not key:
        print("  [SKIP] acc %s: khong co key (%s)" % (user, key_env))
        return None
    os.environ["KAGGLE_USERNAME"] = user
    os.environ["KAGGLE_KEY"] = key
    from kaggle.api.kaggle_api_extended import KaggleApi
    api = KaggleApi()
    api.authenticate()
    return api


def list_all_datasets(api):
    """Dataset cua MINH (ke ca private) - phan trang."""
    out, seen = [], set()
    page = 1
    while page < 50:
        ds = api.dataset_list(mine=True, page=page, sort_by="updated") or []
        if not ds:
            break
        for d in ds:
            if d.ref not in seen:
                seen.add(d.ref)
                out.append(d)
        page += 1
    return out


def list_all_files(api, slug):
    files, token = [], None
    while True:
        try:
            res = api.dataset_list_files(slug, page_token=token) if token \
                else api.dataset_list_files(slug)
        except Exception as e:
            if token is None and not files:
                # retry 1 lan (transient network)
                import time as _t
                _t.sleep(5)
                try:
                    res = api.dataset_list_files(slug)
                except Exception as e2:
                    return None, "list_files loi: %r" % (e2,)
            else:
                return None, "list_files loi: %r" % (e,)
        for f in (res.dataset_files or []):
            # SDK 2.2.4: f.ref rong '' -> ten file that nam o f.name
            # (day du duong dan tu root dataset, khop member trong zip - da doi chieu)
            nm = (getattr(f, "name", "") or getattr(f, "ref", "") or "")
            nm = nm.replace("\\", "/").lstrip("./")
            if nm:
                files.append({"name": nm, "size": f.total_bytes or 0})
        token = getattr(res, "next_page_token", None)
        if not token:
            break
    return files, None


def norm(p):
    return p.replace("\\", "/").lstrip("./")


def is_project(slug):
    """Dataset thuoc du an Ornith hay khong (de khong nhan nham 'RONG' cho
    text-data cua du an khac)."""
    b = slug.split("/")[-1].lower()
    return "Y" if (b.startswith("ornith") or b.startswith("gui-")) else "N"


# Dataset du an nhung dung schema KHAC anh-trajectory (khong phai loi) - ghi ro ly do
SCHEMA_KHAC = {
    "hhjiji/ornith-blender-gen-data":
        "jsonl schema Blender (glb/render/script) - khong phai du lieu anh-trajectory",
}


def read_jsonl_bytes(b):
    rows = []
    try:
        for line in io.BytesIO(b).read().decode("utf-8", "replace").splitlines():
            line = line.strip()
            if line:
                try:
                    rows.append(json.loads(line))
                except Exception:
                    pass
    except Exception:
        pass
    return rows


def download_dataset(api, slug, tmp, max_mb, size_bytes):
    """Tai toan bo dataset (1 file zip ngoai) -> (members, err).
    members: danh sach (ten_trong_zip, bytes)."""
    if size_bytes and size_bytes > max_mb * 1024 * 1024:
        return None, "BO QUA: dataset %.0f MB > nguong %d MB" % (
            size_bytes / 1e6, max_mb)
    d = os.path.join(tmp, slug.replace("/", "__"))
    os.makedirs(d, exist_ok=True)
    try:
        api.dataset_download_files(slug, path=d, quiet=True)
    except Exception as e:
        return None, "tai that bai: %r" % (e,)
    zs = [f for f in os.listdir(d) if f.lower().endswith(".zip")]
    if not zs:
        return None, "khong co zip nao sau khi tai"
    members = []
    for zn in zs:
        p = os.path.join(d, zn)
        try:
            with zipfile.ZipFile(p) as z:
                for info in z.infolist():
                    if info.is_dir():
                        continue
                    name = norm(info.filename)
                    if name.lower().endswith(".zip"):
                        # zip long ben trong: mo de lay namelist (khong can extract)
                        try:
                            with zipfile.ZipFile(io.BytesIO(z.read(info))) as z2:
                                for i2 in z2.infolist():
                                    if not i2.is_dir():
                                        members.append((norm(i2.filename),
                                                        z2.read(i2), True))
                        except Exception as e:
                            print("      [WARN] mo zip long %s loi: %r" % (name, e))
                        continue
                    members.append((name, z.read(info), False))
        except Exception as e:
            return None, "doc zip %s loi: %r" % (zn, e)
        finally:
            try:
                os.remove(p)
            except OSError:
                pass
    return members, None


def _open_zip_members(z, members, depth=0):
    """Doc namelist cua 1 .zip ben trong dataset (jsonl lay bytes, file khac
    chi can duong dan). inzip=True = thanh cua ext (loader giai nen vao ext)."""
    for info in z.infolist():
        if info.is_dir():
            continue
        name = norm(info.filename)
        if name.lower().endswith(".zip") and depth < 2:
            try:
                with zipfile.ZipFile(io.BytesIO(z.read(info))) as z2:
                    _open_zip_members(z2, members, depth + 1)
            except Exception as e:
                print("      [WARN] mo zip long %s loi: %r" % (name, e))
            continue
        if name.lower().endswith(".jsonl"):
            members.append((name, z.read(info), True))
        else:
            members.append((name, None, True))


def _find_downloaded(sub, name):
    cands = [os.path.join(sub, *name.split("/")),
             os.path.join(sub, os.path.basename(name))]
    for p in cands:
        if os.path.exists(p):
            return p
    return None


def download_fallback(api, slug, files, tmp, max_mb, max_dl=40):
    """Tai TUNG file khi endpoint tai toan bo tra 404 (dataset copy moi...
    zip dong goi chua duoc build). Chi lay bytes jsonl/zip; anh dung DUONG DAN
    tu listing (f.name = duong dan mount, khop member trong zip - da doi chieu).
    max_dl = gioi han so file tai (an toan, khong lam cham).
    -> (members, err, zip_missing): zip_missing = so zip khong mo duoc
    (anh co the nam trong do -> khong duoc ket luan THIEU ANH)."""
    d = os.path.join(tmp, slug.replace("/", "__"), "_perfile")
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d, exist_ok=True)
    members, errs, zip_missing, n_dl = [], [], 0, 0
    try:
        for f in files:
            name = norm(f["name"])
            low = name.lower()
            if low.endswith(".zip") or low.endswith(".jsonl"):
                if n_dl >= max_dl:
                    if low.endswith(".zip"):
                        zip_missing += 1
                    else:
                        errs.append("vuot gioi han %d file tai (%s)"
                                    % (max_dl, name))
                    continue
                n_dl += 1
            if low.endswith(".zip"):
                if f["size"] and f["size"] > max_mb * 1024 * 1024:
                    zip_missing += 1
                    continue
                sub = os.path.join(d, "z%03d" % len(members))
                os.makedirs(sub, exist_ok=True)
                try:
                    api.dataset_download_file(slug, name, path=sub, quiet=True)
                    zp = _find_downloaded(sub, name)
                    if zp is None:
                        raise FileNotFoundError("khong tim thay zip da tai")
                    with zipfile.ZipFile(zp) as z:
                        _open_zip_members(z, members)
                except Exception as e:
                    zip_missing += 1
                    errs.append("zip %s: %r" % (name, e))
                continue
            if low.endswith(".jsonl"):
                sub = os.path.join(d, "j%03d" % len(members))
                os.makedirs(sub, exist_ok=True)
                try:
                    api.dataset_download_file(slug, name, path=sub, quiet=True)
                    jp = _find_downloaded(sub, name)
                    if jp is None:
                        raise FileNotFoundError("khong tim thay jsonl da tai")
                    with open(jp, "rb") as fh:
                        members.append((name, fh.read(), False))
                except Exception as e:
                    errs.append("jsonl %s: %r" % (name, e))
                continue
            # anh/file khac: chi can duong dan (khong can bytes)
            members.append((name, None, False))
    finally:
        shutil.rmtree(d, ignore_errors=True)
    err = ""
    if errs:
        err = "tai tung file loi: " + "; ".join(errs[:3])
    if zip_missing:
        err += (" | " if err else "") + "%d zip khong mo duoc" % zip_missing
    return members, (err or None), zip_missing


def audit_one(api, acc, slug, size_bytes, tmp, max_mb):
    r = {"acc": acc, "dataset": slug, "size_mb": round((size_bytes or 0) / 1e6, 1)}
    files, err = list_all_files(api, slug)
    if files is None:
        r.update(n_files=0, ket_luan="LOI", note=err)
        return r
    r["n_files"] = len(files)
    r["n_zip_top"] = sum(1 for f in files if f["name"].lower().endswith(".zip"))
    r["n_jsonl_top"] = sum(1 for f in files if f["name"].lower().endswith(".jsonl"))
    r["n_img_top"] = sum(1 for f in files if f["name"].lower().endswith(IMG_EXT))

    members, derr = download_dataset(api, slug, tmp, max_mb, size_bytes)
    zip_missing = 0
    fb_notes = []
    if members is None and (derr or "").startswith("BO QUA"):
        # qua lon - KHONG fallback (truoc day fallback lam cham rat nang voi
        # dataset 400-750 file) - dung listing de phan doan
        if r["n_jsonl_top"]:
            kl = "CHUA KIEM TRA (bo qua size)"
        elif r["n_img_top"]:
            kl = "ANH KHONG CO JSONL (khong dung cho train traj)"
        else:
            kl = "KHONG PHAI DATA ANH"
        r.update(n_jsonl=0, n_jsonl_inzip=0, n_img=0, img_refs=0, img_ok=0,
                 ket_luan=kl, note=derr or "")
        return r
    if members is None:
        # endpoint tai TOAN BO loi (404 dataset copy moi...) ->
        # fallback tai TUNG file, dung listing cho duong dan anh
        fb_notes.append("tai toan bo loi (%s) -> tai tung file" % ((derr or "")[:70],))
        members, fb_err, zip_missing = download_fallback(
            api, slug, files, tmp, max_mb)
        if fb_err:
            fb_notes.append(fb_err)
        if members is None:
            members = []

    # --- mo phong loader: base = file top-level (khong zip); ext = noi zip ---
    # (loader v24: _resolve = base/rel -> ext/rel -> basename trong ext ->
    #  basename trong base - bo sung quet base de xu ly anh o subdir)
    base = {n for n, _b, inzip in members if not inzip}
    ext = {n for n, _b, inzip in members if inzip}
    ext_base = {os.path.basename(n) for n in ext}
    base_base = {os.path.basename(n) for n in base}

    jsonls = [(n, b, False) for n, b, iz in members
              if n.lower().endswith(".jsonl") and not iz]
    jsonls += [(n, b, True) for n, b, iz in members
               if n.lower().endswith(".jsonl") and iz]
    n_img_all = sum(1 for n, _b, iz in members
                    if n.lower().endswith(IMG_EXT) and not iz)
    r["n_jsonl"] = len(jsonls)
    r["n_jsonl_inzip"] = sum(1 for _n, _b, iz in jsonls if iz)
    r["n_img"] = n_img_all

    if r["n_jsonl_top"] and not jsonls:
        # listing co jsonl nhung khong doc duoc bytes -> KHONG nhan nham
        # "KHONG PHAI DATA ANH"
        r.update(n_rows=0, img_refs=0, img_ok=0, ket_luan="CHUA KIEM TRA",
                 note=" | ".join(fb_notes + [
                     "listing co %d jsonl nhung khong doc duoc bytes"
                     % r["n_jsonl_top"]]))
        return r

    # dataset copy (acc B) co 2 ban jsonl CUNG NOI DUNG (top + nested) ->
    # loader chi doc 1 ban -> chi dem 1 lan, khong nhan doi row
    seen_hash, uniq = set(), []
    for item in jsonls:
        h = hashlib.sha256(item[1] or b"").hexdigest()
        if h in seen_hash:
            continue
        seen_hash.add(h)
        uniq.append(item)
    if len(uniq) < len(jsonls):
        fb_notes.append("%d jsonl trung dung (copy) - loader chi doc 1 ban"
                        % (len(jsonls) - len(uniq)))
    jsonls = uniq
    # cung ten nhung KHAC noi dung: loader walk top-down chi doc ban NON NHAT
    by_bn = {}
    for item in jsonls:
        by_bn.setdefault(os.path.basename(item[0]), []).append(item)
    picked, dups = [], []
    for bn, items in sorted(by_bn.items()):
        if len(items) > 1:
            items.sort(key=lambda it: it[0].count("/"))
            dups.append(bn)
        picked.append(items[0])
    if dups:
        fb_notes.append("nhieu jsonl cung ten khac noi dung (%s) - loader chi "
                        "doc ban non nhat, cac ban khac KHONG duoc tinh row"
                        % ",".join(dups))
    jsonls = picked

    rows, refs = 0, 0
    ok = 0
    fail_samples = []
    for name, b, inzip in jsonls:
        for row in read_jsonl_bytes(b):
            rows += 1
            rel = row.get("image")
            if not rel:
                continue
            refs += 1
            rel = norm(str(rel))
            bn = os.path.basename(rel)
            if rel in base or rel in ext or bn in ext_base or bn in base_base:
                ok += 1
            elif len(fail_samples) < 3:
                fail_samples.append("%s (tu %s)" % (rel, "zip" if inzip else "top"))
    r["n_rows"] = rows
    r["img_refs"] = refs
    r["img_ok"] = ok

    notes = []
    if r["n_jsonl_inzip"]:
        notes.append("CO JSONL CHI NAM TRONG ZIP (loader v23b KHONG tim thay - "
                     "can fix loader hoac upload jsonl phang)")
    if fail_samples:
        notes.append("vd anh thieu: " + "; ".join(fail_samples))

    if not files:
        r["ket_luan"] = "RONG"
    elif not jsonls:
        r["ket_luan"] = "KHONG PHAI DATA ANH" if not n_img_all else \
            "ANH KHONG CO JSONL (khong dung cho train traj)"
    elif refs == 0:
        r["ket_luan"] = "RONG (jsonl khong co row anh)"
    elif ok == refs:
        r["ket_luan"] = "OK"
    elif zip_missing and fail_samples:
        # con zip chua mo duoc -> anh thieu co the nam trong do, khong ket luan
        # THIEU ANH duoc
        r["ket_luan"] = "CHUA KIEM TRA (%d zip khong mo duoc)" % zip_missing
        notes.append("anh co the nam trong zip chua mo duoc")
    elif ok == 0:
        r["ket_luan"] = "THIEU ANH"
    else:
        r["ket_luan"] = "THIEU ANH MOT PHAN (%d/%d)" % (refs - ok, refs)
    r["note"] = " | ".join(fb_notes + notes)
    return r


def build_md(rows, out_path):
    cols_md = ["acc", "du_an", "dataset", "n_files", "size_mb", "n_jsonl",
               "n_jsonl_inzip", "n_zip_top", "n_jsonl_top", "n_img", "n_rows",
               "img_refs", "img_ok", "ket_luan", "note"]
    md = ["# Audit dataset Kaggle (acc A khoadangnguye / B dieniw / C hhjiji)",
          "",
          "Sinh boi `scripts/audit_datasets.py` - mo phong `_resolve` cua "
          "`gui_sft_v23.py` (base/rel -> ext/rel -> basename trong ext -> "
          "basename trong base).",
          "",
          "Cot `du_an`: Y = dataset Ornith/GUI cua du an; N = dataset khac "
          "(text/weights cua du an cu - khong lien quan).",
          "",
          "| " + " | ".join(cols_md) + "|",
          "|" + "---|" * len(cols_md)]
    for r in rows:
        md.append("| " + " | ".join(str(r.get(c, "")) for c in cols_md) + "|")
    proj = [r for r in rows if r.get("du_an") == "Y"]
    bad = [r for r in proj if str(r.get("ket_luan", "")).startswith(
        ("RONG", "THIEU ANH", "LOI", "CHUA KIEM TRA"))
        and r.get("dataset", "") not in SCHEMA_KHAC]
    khac = [r for r in proj if r.get("dataset", "") in SCHEMA_KHAC]
    md += ["", "## Ket luan (chi tinh dataset DU AN - du_an=Y)", "",
           "- Tong dataset quet: %d (du an: %d)" % (len(rows), len(proj)),
           "- Dataset du an co van de: %d" % len(bad)]
    for r in bad:
        md.append("  - %s — %s (%s)" % (r.get("dataset"), r.get("ket_luan"),
                                        r.get("note", "")))
    if khac:
        md.append("- Loai tru (schema khac, KHONG phai loi):")
        for r in khac:
            md.append("  - %s — %s" % (r.get("dataset"),
                                       SCHEMA_KHAC.get(r.get("dataset", ""))))
    ok_ds = [r for r in proj if r.get("ket_luan") == "OK"]
    md.append("- Dataset du an OK: %d" % len(ok_ds))
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("\n".join(md) + "\n")
    return bad, ok_ds


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--accounts", default="A,B,C")
    ap.add_argument("--max-ds-mb", type=int, default=150,
                    help="bo qua dataset lon hon nguong nay (ghi ro trong bao cao)")
    ap.add_argument("--out", default="scripts/dataset_audit")
    ap.add_argument("--md-from", default="",
                    help="duong dan CSV co san - dung lai chi de sinh lai .md")
    args = ap.parse_args()

    tmp = os.path.join(os.environ.get("TEMP", "."), "ds_audit")
    os.makedirs(tmp, exist_ok=True)
    os.makedirs(args.out, exist_ok=True)

    if args.md_from:
        import csv as _csv
        with open(args.md_from, encoding="utf-8") as f:
            rows = list(_csv.DictReader(f))
        for r in rows:
            r["du_an"] = is_project(r.get("dataset", ""))
        bad, _ok = build_md(rows, os.path.join(args.out, "dataset_audit.md"))
        print("Sinh lai MD tu %s - du an co van de: %d" % (args.md_from, len(bad)))
        sys.exit(1 if bad else 0)

    rows = []
    csv_path = os.path.join(args.out, "dataset_audit.csv")
    md_path = os.path.join(args.out, "dataset_audit.md")
    cols = ["acc", "du_an", "dataset", "n_files", "size_mb", "n_jsonl",
            "n_jsonl_inzip", "n_zip_top", "n_jsonl_top", "n_img_top", "n_img",
            "n_rows", "img_refs", "img_ok", "ket_luan", "note"]

    def flush_csv():
        """Ghi CSV/MD hien tai (goi sau tung dataset - chet giua van con ket qua)."""
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
            w.writeheader()
            for r in rows:
                w.writerow(r)
        build_md(rows, md_path)

    for tag in args.accounts.split(","):
        tag = tag.strip().upper()
        if tag not in ACCT:
            print("acc %s khong biet, bo qua" % tag)
            continue
        user, key_env = ACCT[tag]
        api = make_api(user, key_env)
        if api is None:
            continue
        print("== acc %s (%s)" % (tag, user))
        try:
            dss = list_all_datasets(api)
        except Exception as e:
            print("  list dataset loi: %r" % (e,))
            continue
        print("  %d dataset" % len(dss))
        for d in dss:
            try:
                r = audit_one(api, tag, d.ref, d.total_bytes, tmp, args.max_ds_mb)
            except Exception as e:
                r = {"acc": tag, "dataset": d.ref, "ket_luan": "LOI",
                     "note": "exception: %r" % (e,)}
            rows.append(r)
            r["du_an"] = is_project(r.get("dataset", ""))
            print("   %-52s %-28s files=%s img=%s/%s" % (
                r.get("dataset", "?"), r.get("ket_luan", "?"),
                r.get("n_files", "?"), r.get("img_ok", "?"),
                r.get("img_refs", "-")))
            flush_csv()

    bad, ok_ds = build_md(rows, md_path)

    print("\nTong dataset: %d | du an OK: %d | du an co van de: %d" % (
        len(rows), len(ok_ds), len(bad)))
    print("Da ghi: %s , %s" % (csv_path, md_path))
    sys.exit(1 if bad else 0)


if __name__ == "__main__":
    main()
