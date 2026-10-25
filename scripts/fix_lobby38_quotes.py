# -*- coding: utf-8 -*-
"""fix_lobby38_quotes.py - cac dau nhay trong chuoi Python lam loi SyntaxError."""
import io

P = "phase13-gui/append_lobby38.py"
s = io.open(P, encoding="utf-8").read()
for a, b in [
    ('task "thoat chu ky lap"', "task 'thoat chu ky lap'"),
    ('"NGHI THAY VI HANH DONG"', "'NGHI THAY VI HANH DONG'"),
    ('"CHU KY LAP"', "'CHU KY LAP'"),
    ('"T20_2048: 54% prose"', "'T20_2048: 54% prose'"),
    ('"model doc man hinh + bam Ctrl+C/V that', "'model doc man hinh + bam Ctrl+C/V that"),
    ('"doc man hinh + bam Ctrl+C/V that', "'doc man hinh + bam Ctrl+C/V that"),
    ('"nghi thay vì hành động"', "'nghi thay vì hành động'"),
]:
    s = s.replace(a, b)
io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("da sua quote trong", P)
