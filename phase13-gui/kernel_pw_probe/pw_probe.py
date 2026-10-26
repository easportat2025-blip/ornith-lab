"""CPU probe: verify offline Playwright bundle mounts and passes V1-V6."""
import json
import os
import sys

helper = None
for root, _dirs, files in os.walk("/kaggle/input"):
    if "setup_playwright_offline.py" in files:
        helper = root
        break
assert helper, "setup_playwright_offline.py not found"
print("helper:", helper, flush=True)
sys.path.insert(0, helper)
from setup_playwright_offline import setup_playwright_offline  # noqa: E402

info = setup_playwright_offline()
print("PW_PROBE_OK", json.dumps(info, sort_keys=True), flush=True)
