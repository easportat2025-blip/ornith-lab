# -*- coding: utf-8 -*-
"""fix_lobby38_line4.py - sua dong 4 (co dau nhay long) cua append_lobby38.py."""
import io

P = "phase13-gui/append_lobby38.py"
lines = io.open(P, encoding="utf-8").read().splitlines(True)
good = ('entry += "**| task | win | nhan xet |" + chr(10) + "|---|---|---|" + chr(10)\n'
        'entry += "| **T26_clipboard** | **19/20 (95%)** | ✅ **agent doc man hinh '
        '+ bam Ctrl+C/V that — computer-use THAT da chay!** |" + chr(10)\n')
if len(lines) > 3:
    lines[3] = good
    io.open(P, "w", encoding="utf-8", newline="\n").write("".join(lines))
    print("da sua dong 4")
src = "".join(lines)
try:
    compile(src, "x", "exec")
    print("compile OK")
except SyntaxError as e:
    print("van loi dong", e.lineno, e.msg)
