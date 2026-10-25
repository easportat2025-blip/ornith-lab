entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 20/10 17:35 " + chr(8212) + " **train v21 v2 xong (2931 row, selfplay 123 load dung)** · gate B15 dang chay · 2 bug watchdog da fix" + chr(10) + chr(10)
entry += "**Train v21 v2 (acc A, 14:14 -> 17:14, 3367s):**" + chr(10)
entry += "- Data mix **2931** = synth 1200 + real-ui 792 + traj 816 + **selfplay 123** (log: `gui-selfplay: 123/123 rows` ✓) · 521 step (2.8 ep) · loss 0.139." + chr(10)
entry += "- Eval: **acc so bo (synth) 0.77** (v18: 0.50 ✓ tăng) · **real 0.31** (v18: 0.79 ✗) · **traj 0.125** (v18: 0.81 ✗)." + chr(10)
entry += "- Phan tich traj-sub (16 mau): model **output prose o 8/16** (parse=8/16) va click **lech +-1 don vi** (333 vs 332) -> eval exact-match cua train rat brittle; **gate B15 (checker that, dung bbox) moi la thuoc do that** -> dang chay (acc A, 17:28)." + chr(10)
entry += "- *Luu y:* 2 eval cu (real/traj) cua **v18 (06/10)** vs **v21 (hom nay)** so sanh KHONG cung bo du lieu (dataset real-ui/traj da cap nhat 18/10) -> khong ket luan tu 2 so do." + chr(10)
entry += chr(10) + "**2 bug watchdog cua minh (da fix, GPU dinh 2h):**" + chr(10)
entry += "1. **Hang doi GPU bi nhoi vao nhanh check-quota** -> khi doi sang \"check quota 1 lan/ngay\" thi **push cung bi chan** -> GPU dung 3h cho 14/10 (sft-v21 xong 14:14 nhung gate chi chay tu 17:28). Fix: tach hai nhanh — **push hang doi MOI 2 PHUT**, quota chi la dieu kien (cache 6h) va len lich theo `refreshAt`." + chr(10)
entry += "2. Marker watchdog theo label nen kernel acc moi bi skip -> xoa marker + marker theo `lastRunTime`." + chr(10)
entry += chr(10) + "**Acc B** dang chay baseline: `bench-3d` + `bench-3d-hard` (3D grounding, v18 adapter) + tiep `bench-v155`/`bench-v16`; sau do train **v22** (recipe v18 + selfplay + **synth targeted S1-S8** + **3D 600 row** + **policy-replay task-that**)." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
