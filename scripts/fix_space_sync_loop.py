# -*- coding: utf-8 -*-
"""fix_space_sync_loop.py - sua 2 loi trong space_sync_loop.py sau khi patch:
1) thieu bien HERE
2) loi goi update_result_daily() nam sai cho (trong try/except)
"""
import io

P = "scripts/space_sync_loop.py"
s = io.open(P, encoding="utf-8").read()

if "HERE = os.path.dirname(os.path.abspath(__file__))" not in s:
    s = s.replace("INTERVAL = int(os.environ.get(\"SPACE_SYNC_INTERVAL\", \"180\"))",
                  "HERE = os.path.dirname(os.path.abspath(__file__))\n"
                  "INTERVAL = int(os.environ.get(\"SPACE_SYNC_INTERVAL\", \"180\"))")

# goi sai cho -> goi sai trong vong lap
bad = """        space_sync.push_to_space(st, "", os.environ["HF_TOKEN"])
        update_result_daily()
    except Exception as e:"""
good = """        space_sync.push_to_space(st, "", os.environ["HF_TOKEN"])
    except Exception as e:"""
if bad in s:
    s = s.replace(bad, good)
    print("da bo loi goi sai cho")

# them loi goi dung cho (sau khi vong lap)
if "update_result_daily()\n" in s and "        update_result_daily()" not in s:
    s = s.replace("        space_sync.push_to_space(st, \"\", os.environ[\"HF_TOKEN\"])\n"
                  "    except Exception as e:",
                  "        space_sync.push_to_space(st, \"\", os.environ[\"HF_TOKEN\"])\n"
                  "    except Exception as e:")
    s = s.replace("        time.sleep(INTERVAL)",
                  "        update_result_daily()\n        time.sleep(INTERVAL)")
    print("da them loi goi trong vong lap")

io.open(P, "w", encoding="utf-8", newline="\n").write(s)
print("OK")
