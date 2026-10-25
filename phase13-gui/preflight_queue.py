"""preflight_queue.py - kiem tra TOAN BO hang doi GPU truoc khi no chay:
  - thu muc ton tai, metadata id khop, code_file ton tai, code compile duoc
  - dataset trong metadata: READY tren Kaggle khong
  - kernel da ton tai tren Kaggle chua (push truoc -> status)
Exit != 0 neu co muc khong san sang.
"""
import json
import os
import py_compile
import re
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
ENV = dict(os.environ)
ENV['PYTHONUTF8'] = '1'
ENV['PYTHONIOENCODING'] = 'utf-8'


def sh(cmd, timeout=180):
    try:
        p = subprocess.run(cmd, capture_output=True, env=ENV, timeout=timeout,
                           creationflags=(0x08000000 if os.name == "nt" else 0))
        return ((p.stdout or b'').decode('utf-8', 'replace') +
                (p.stderr or b'').decode('utf-8', 'replace'))
    except Exception as e:
        return 'ERR ' + str(e)


def ds_ready(slug):
    out = sh(['kaggle', 'datasets', 'status', slug])
    return bool(re.search(r'ready|active', out)) and \
        not re.search(r'processing|in_progress', out)


def kaggle_account():
    """Account ma CLI dang chay voi (kaggle config view)."""
    out = sh(['kaggle', 'config', 'view'])
    m = re.search(r'username:\s*(\S+)', out)
    return (m.group(1) if m else '').lower()


def ds_state(slug, acc):
    """('ok'|'missing'|'unknown', ghi chu)
    - ok      : READY tren Kaggle
    - missing : KHONG ton tai (chi ket luan duoc khi dataset thuoc CHINH acc
                dang chay voi; 403/404 cua acc khac chi co nghia 'private')
    - unknown : khong kiem duoc (acc khac / output la) -> bo qua
    """
    out = sh(['kaggle', 'datasets', 'status', slug])
    if re.search(r'ready|active', out) and \
            not re.search(r'processing|in_progress', out):
        return 'ok', 'READY'
    low = out.lower()
    if re.search(r'403|404|not found|forbidden|cannot access', low):
        if '/' in slug and acc and slug.split('/')[0].lower() == acc:
            return 'missing', 'KHONG TON TAI (403/404) tren acc chinh'
        return 'unknown', 'khong kiem duoc (acc khac / private)'
    return 'unknown', 'trang thai khong ro: %s' % out.strip()[-60:].replace('\n', ' ')


def kernel_exists(slug):
    out = sh(['kaggle', 'kernels', 'status', slug])
    return 'has status' in out or 'KernelWorkerStatus' in out


q = json.load(open(os.environ.get(
    'GPU_QUEUE', os.path.join(ROOT, 'scripts', 'gpu_queue.json')),
    encoding='utf-8'))
bad = []
ds_missing = []
acc = kaggle_account()
print("=" * 74)
print("PRE-FLIGHT HANG DOI GPU (%d muc) | acc CLI = %s" % (len(q), acc or "?"))
print("=" * 74)
for i, it in enumerate(q, 1):
    d = it['dir']
    ok = True
    msgs = []
    if not os.path.isdir(os.path.join(ROOT, d)):
        print("%2d. %-42s THIEU THU MUC %s" % (i, it['id'], d))
        bad.append(it['id'])
        continue
    mf = os.path.join(ROOT, d, 'kernel-metadata.json')
    if not os.path.exists(mf):
        print("%2d. %-42s THIEU metadata" % (i, it['id']))
        bad.append(it['id'])
        continue
    md = json.load(open(mf, encoding='utf-8'))
    if md.get('id') != it['id']:
        ok = False
        msgs.append('ID MISMATCH (%s)' % md.get('id'))
    cf = os.path.join(ROOT, d, md.get('code_file', ''))
    if not os.path.exists(cf):
        ok = False
        msgs.append('THIEU code_file %s' % md.get('code_file'))
    else:
        try:
            py_compile.compile(cf, doraise=True)
        except Exception as e:
            ok = False
            msgs.append('COMPILE FAIL %s' % str(e)[:60])
    for ds in md.get('dataset_sources', []):
        # FIX (MiMo 22/10): truoc day CHI kiem dataset 'hhjiji/*' => MUNG voi
        # dataset cua acc A/B - dung loai lỗi vừa xảy ra (kernel chay khong co
        # adapter vi Kaggle bo qua dataset khong ton tai).
        # Quy tac: 403/404 = 'khong ton tai' CHI khi dataset thuoc CHINH acc
        # dang chay voi; acc khac (private) => 'khong kiem duoc' => bo qua.
        st, note = ds_state(ds, acc)
        if st == 'missing':
            if it.get('expect_later') and 'lora' in ds:
                msgs.append('dataset adapter (se tao sau khi train) - OK')
            else:
                # KHONG chan ca hang doi (watchdog co kiem chi tiet tung kernel
                # va se BO QUA dung kernel bi thieu dataset) -> chi bao.
                ds_missing.append('%s: %s' % (it['id'], ds))
                msgs.append('DATASET KHONG TON TAI (watchdog se bo qua kernel '
                            'nay): %s' % ds)
        elif st == 'unknown' and 'lora' in ds.lower():
            # adapter ma KHONG kiem duoc (acc khac / private) -> CHI canh bao,
            # KHONG chan: preflight co the chay voi key bat ky. Khi chay bang
            # key cua acc do, 'missing' moi chan (khai bao that).
            msgs.append('CHUA XAC NHAN dataset adapter %s (%s)' % (ds, note))
    if not kernel_exists(it['id']):
        msgs.append('chua push (se push luc quota)')
    print("%2d. %-42s %s %s" % (i, it['id'], 'OK ' if ok else 'BAD',
                                '| ' + '; '.join(msgs)))
    if not ok:
        bad.append(it['id'])
print("-" * 74)
if ds_missing:
    print("CANH BAO: %d muc thieu dataset (watchdog se bo qua dung kernel, "
          "khong chan ca hang doi):" % len(ds_missing))
    for x in ds_missing:
        print("   -", x)
print("PRE-FLIGHT: %d/%d muc san sang" % (len(q) - len(bad), len(q)))
if bad:
    print("CAN CHUA SAN SANG:", bad)
    sys.exit(1)
print("TAT CA DUOC SAN SANG")
