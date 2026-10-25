# ornith-gui-rollout-v20 (TASK-12)

Self-play rollout kernel cho self-improving loop (MAIN_QUEST §3):

- Adapter DUY NHAT: hhjiji/ornith-gui-lora-v20 (thay bang version sau thi
  sua dataset_sources + id).
- Sampling: temperature 0.7, top_p 0.95 (PolicyV3), max_new_tokens=256.
- Suite B15 (12 task x 3 variant), N=4 rep moi episode (SMOKE_TASKS de test).
- Verify bang checker.check_task cua suite (ngoai model, doc DOM that).
- Chi giu cac buoc thuoc episode THANH CONG (self-distillation thanh cong);
  cap MAX_ROWS (480) dong.
- Output: rollout_rows.jsonl (image/task/instruction/target/action/mode...),
  rollout_summary.json (win rate, parse, prose_leak, per task),
  rollout_bundle.zip (jsonl + summary + shots/ chi anh duoc dung),
  rollout_result.json (episode stats).
