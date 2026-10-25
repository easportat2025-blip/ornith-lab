"""build_gen3d.py - inline blender_scenes.py vao generate_3d.py (Kaggle chi
upload code_file) + tao file kernel san dung."""
import os
import re

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "blender_scenes.py")
GEN = os.path.join(HERE, "generate_3d.py")
START = "# --- BEGIN BLENDER_SCRIPT (embed) ---"
END = "# --- END BLENDER_SCRIPT (embed) ---"

blender = open(SRC, encoding="utf-8").read()
# bo module docstring (de embed khong xung bao triple-quote)
blender = re.sub(r'^"""[\s\S]*?"""\n', '', blender, count=1)
assert '"""' not in blender, "blender script con triple-quote"
assert START not in blender

gen = open(GEN, encoding="utf-8").read()
block = START + "\nBLENDER_SCRIPT = r'''%s'''\n%s\n" % (blender, END)
if START in gen:
    gen = re.sub(re.escape(START) + r'[\s\S]*?' + re.escape(END), block, gen,
                 count=1)
    print("thay the block embed cu")
else:
    gen = gen.replace('HERE = os.path.dirname(os.path.abspath(__file__))',
                      'HERE = os.path.dirname(os.path.abspath(__file__))\n' + block,
                      1)
    print("them block embed moi")
# doi dung file rieng (chi co code_file duoc upload)
gen = gen.replace('os.path.join(HERE, "blender_scenes.py")',
                  'os.path.join(TMP, "blender_scenes.py")')
open(GEN, 'w', encoding="utf-8").write(gen)
print("OK %s (%d bytes)" % (GEN, len(gen)))
