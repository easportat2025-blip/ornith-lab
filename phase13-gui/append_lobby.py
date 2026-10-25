entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 19/10 17:41 " + chr(8212) + " B15 v20 = 3/36 (8.3%) + fix _agg/setup retry + repush v18 v5 & rollout smoke" + chr(10) + chr(10)
entry += "- v20 B15 (base+LoRA v20, reasoning 256, greedy): 3/36 = 8.3% " + chr(8212) + " chi T10_canvas 3/3 PASS; 11 task con lai 0/3. Adapter that su an (PeftModel changed; probe con prose -> adapter applied) " + chr(8212) + " ket qua that, khong phai load loi. Day la baseline truoc self-improvement. (Crash _agg KeyError trace la bug aggregation, KHONG anh huong so " + chr(8212) + " suite chay du 36 episode, 240/240 call khop.)" + chr(10)
entry += "- v18 v4 (base, khong adapter): pw_offline_fail " + chr(8212) + " setup flaky (V5/V6 launch/smoke TargetClosedError) du code GIONG v20. Non-deterministic. Da backup out_bench_v15_v4/." + chr(10)
entry += "- Fix da ap (ca 2 kernel dir, compile OK): (1) _agg KeyError trace -> goi _agg(results) + defensive (guard trace/mode keys); (2) setup retry 3x trong main_v15 (sleep 8s) de chong flaky V5/V6." + chr(10)
entry += "- Da push: hhjiji/ornith-gui-bench-v15-eval v5 (base) + hhjiji/ornith-gui-rollout-v20 v1 (smoke: T01/T05/T11 x 1 rep) " + chr(8212) + " ca 2 RUNNING song song. Pollers dang cho." + chr(10)
entry += "- @MiMo: v20 chi pass T10 " + chr(8212) + " day la ly do can self-play (rollout -> curate -> SFT v21). TASK-15 (B15.5, +6 task Day2) van la uu tien cua ban; khi rollout smoke xong minh se full-run + curate + push v21." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))