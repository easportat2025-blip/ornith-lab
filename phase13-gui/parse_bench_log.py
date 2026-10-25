"""parse_bench_log.py - trich ket qua B15 tu log kernel."""
import io, re, sys

path = sys.argv[1]
raw = io.open(path, encoding='utf-8', errors='replace').read()

print("=== MARKERS ===")
for m in ['V4b', 'V5 ', 'V6 ', 'deps_out', 'chromium', 'launch', 'pw_',
          'offline', 'playwright', 'browser']:
    hits = list(re.finditer(re.escape(m), raw, re.I))
    if hits:
        i = hits[0].start()
        ctx = raw[max(0, i-70):i+90].replace('\n', ' ')
        print(m, "n=" + str(len(hits)), "first=" + ctx)

print("")
print("=== B15 LINES ===")
bs = re.findall(r'\[b15\][^"\r\n]*', raw)
print("count:", len(bs))
for b in bs:
    print(b.strip())

print("")
print("=== RUNNER SUMMARY ===")
for m in re.findall(r'runner MiMo xong[^"\r\n]*', raw):
    print(m)
for m in re.findall(r'\d+ episode[^"\r\n]*', raw):
    print(m)

print("")
print("=== TRACEBACK/ERROR ===")
for m in re.findall(r'Traceback.*?KeyError[^"\r\n]*', raw, re.S):
    print(m[:400])