"""dump_log.py - in noi dung log kernel (JSON array / JSONL) ra text."""
import io, json, re, sys

path = sys.argv[1]
raw = io.open(path, encoding='utf-8', errors='replace').read()

out = []
# thu 1: JSONL moi dong 1 object
ok = True
for ln in raw.splitlines():
    ln = ln.strip().rstrip(',')
    if not ln or ln in ('[', ']'):
        continue
    if not ln.startswith('{'):
        ok = False
        break
    try:
        o = json.loads(ln)
    except Exception:
        ok = False
        break
    if isinstance(o, dict) and 'data' in o:
        out.append(str(o['data']))
    else:
        out.append(str(o))
if not ok:
    # thu 2: quet moi "data":"..." trong ca file
    out = re.findall(r'"data":"(.*?)"', raw, re.S)

for t in out:
    t = t.replace('\\n', '\n').replace('\\u003e', '>').replace('\\u003c', '<')
    t = t.replace('\\u0026', '&').replace('\\u0027', "'").replace('\\"', '"')
    sys.stdout.write(t + '\n')
