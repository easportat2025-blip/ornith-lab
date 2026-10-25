"""upload_adapter_dataset.py - tao dataset adapter (LoRA) tren Kaggle.

QUAN TRONG: kaggle CLI BO QUA thu muc khi upload dataset (chi lay file o cap
goc) + CLI tra exit 0 KE CA khi loi -> phai (1) gom file thanh 1 ZIP, (2) kiem
CHUOI output chu khong phai exit code.

Dung: python scripts/upload_adapter_dataset.py <kernel_id> <dir_adapter> <dataset_id> [title]
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import zipfile

ENV = dict(os.environ)
ENV["PYTHONIOENCODING"] = "utf-8"
ENV["PYTHONUTF8"] = "1"
FLAGS = 0x08000000 if os.name == "nt" else 0
ERR_MARK = ("403", "401", "404", "forbidden", "not found", "must be")


def kaggle(args):
    p = subprocess.run(["kaggle"] + args, capture_output=True, env=ENV,
                       timeout=3600, creationflags=FLAGS)
    return (p.stdout or b"").decode("utf-8", "replace"), \
        (p.stderr or b"").decode("utf-8", "replace")


def ok(out, err):
    low = (out + "\n" + err).lower()
    for m in ("upload successful", "dataset version", "successfully",
              "is being created", "creating"):
        if m in low:
            return True
    for m in ERR_MARK:
        if m in low:
            return False
    return False


def main():
    if len(sys.argv) < 4:
        print("dung: upload_adapter_dataset.py <kernel_id> <dir> <dataset_id> [title]")
        return 1
    kernel, src, ds_id = sys.argv[1], sys.argv[2], sys.argv[3]
    title = sys.argv[4] if len(sys.argv) > 4 else ds_id.split("/")[-1]
    user = os.environ.get("KAGGLE_USERNAME", "khoadangnguye")
    tmp = tempfile.mkdtemp(prefix="lora_")
    try:
        out, err = kaggle(["kernels", "output", kernel, "-p", tmp,
                            "--file-pattern", "gui_lora/.*", "--force"])
        src_dir = None
        for root, _dirs, files in os.walk(tmp):
            if "adapter_config.json" in files:
                src_dir = root
                break
        if not src_dir:
            # CLI co the in ra loi nhung van tai duoc file -> kiem file that su
            print("tai adapter that bai:", (err or out)[-200:])
            return 1
        zb = os.path.join(tmp, "lora_bundle.zip")
        with zipfile.ZipFile(zb, "w", zipfile.ZIP_DEFLATED) as z:
            for f in os.listdir(src_dir):
                z.write(os.path.join(src_dir, f), f)
        for f in os.listdir(tmp):
            p = os.path.join(tmp, f)
            if os.path.isdir(p):
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            elif f not in ("lora_bundle.zip", "dataset-metadata.json"):
                os.remove(p)
        meta = {"title": title, "id": ds_id, "licenses": [{"name": "other"}]}
        with open(os.path.join(tmp, "dataset-metadata.json"), "w",
                  encoding="utf-8") as fh:
            json.dump(meta, fh)
        out, err = kaggle(["datasets", "create", "-p", tmp])
        if not ok(out, err):
            out, err = kaggle(["datasets", "version", "-p", tmp, "-m",
                               "adapter %s" % title])
        if not ok(out, err):
            print("upload that bai:", (err or out)[-250:])
            return 1
        print("OK -> %s (user %s)" % (ds_id, user))
        return 0
    finally:
        import shutil
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
