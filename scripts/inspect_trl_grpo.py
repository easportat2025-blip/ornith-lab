# -*- coding: utf-8 -*-
"""inspect_trl_grpo.py - doc API THAT cua trl 1.14.1 tu wheel (khong doan)."""
import io
import re
import sys
import zipfile

W = r"C:\Users\Admin\AppData\Local\Temp\opencode\wheels\trl-1.14.1-py3-none-any.whl"


def show(title, lines, n=14):
    print("\n=== %s ===" % title)
    for l in lines[:n]:
        print("   " + l.strip()[:150])


def main():
    z = zipfile.ZipFile(W)
    src = z.read("trl/trainer/grpo_trainer.py").decode("utf-8", "replace")

    # 1) cach goi reward function
    lines = src.split("\n")
    show("goi reward function",
         [l for l in lines if "reward_funcs[" in l or "reward_funcs(" in l
          or "for reward_func in" in l])

    # 2) protocol: dong doc reward_func
    idx = [i for i, l in enumerate(lines) if "def _calculate_rewards" in l
           or "def calculate_rewards" in l]
    if idx:
        show("ham tinh reward (trich)", lines[idx[0]:idx[0] + 45])

    # 3) cot du lieu (prompt/image)
    show("cot du lieu",
         [l for l in lines if re.search(r"image", l)
          and re.search(r"columns|key|\"images?\"|'images?'", l)])

    # 4) GRPOConfig: cac field quan trong
    cfg = z.read("trl/trainer/grpo_config.py").decode("utf-8", "replace")
    cl = cfg.split("\n")
    show("GRPOConfig fields",
         [l for l in cl if re.match(r"\s+(num_generations|max_completion_length|"
                                    r"max_prompt_length|beta|loss_type|"
                                    r"scale_rewards|num_iterations|steps_per_generation|"
                                    r"epsilon|epsilon_high|mask_truncated_completions|"
                                    r"vllm_mode|use_vllm|log_completions|"
                                    r"generation_batch_size)\s*[:=]", l)], 26)

    # 5) co ho tro anh trong data_utils khong?
    try:
        du = z.read("trl/data_utils.py").decode("utf-8", "replace")
        show("data_utils (multimodal)",
             [l for l in du.split("\n")
              if "image" in l and ("def " in l or "return" in l or "content" in l)], 12)
    except KeyError:
        print("\n  (khong co trl/data_utils.py)")

    # 6) vi du reward func trong tai lieu
    for n in z.namelist():
        if n.startswith("trl/trainer/grpo") and n.endswith(".py"):
            pass
    print("\n  (xong)")


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    main()
