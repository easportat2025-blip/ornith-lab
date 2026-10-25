import re
files = ['phase13-gui/kernel_bench_v15/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v155/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v16/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v155_v21/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v16_v21/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v21/bench_v15_kernel.py',
         'phase13-gui/kernel_bench_v18_think0/bench_v15_kernel.py']
for f in files:
    s = open(f, encoding='utf-8').read()
    m = re.findall(r'for name in \("bench[^)]*\)', s)
    think = [l for l in s.splitlines() if l.startswith('ENABLE_THINKING')]
    print(f.split('/')[1], '|', m, '|', think[0][:60] if think else 'NO-THINK-CONST')
