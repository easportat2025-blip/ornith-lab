"""check_name_collisions.py - so sanh ten top-level giua script train v22 va
module synth inline (de chan define bi ghi de)."""
import ast

train = ast.parse(open('phase13-gui/kernel_v22/gui_sft_v22.py',
                       encoding='utf-8').read())
synth = ast.parse(open('phase13-gui/gen_synth_targeted.py',
                       encoding='utf-8').read())


def names(tree):
    out = {}
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
            out[n.name] = n
        elif isinstance(n, ast.Assign):
            for t in n.targets:
                if isinstance(t, ast.Name):
                    out[t.id] = n
    return out


tn = names(train)
sn = names(synth)
common = sorted(set(tn) & set(sn))
print("ten trung:", common)
for k in common:
    a = ast.dump(tn[k])
    b = ast.dump(sn[k])
    print("  %-14s %s" % (k, "GIONG" if a == b else "KHAC GIA TRI !!"))
