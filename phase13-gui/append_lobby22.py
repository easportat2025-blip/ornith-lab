entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 20/10 12:15 " + chr(8212) + " **PIPELINE LIVE tren acc A: 2 GPU session chay dong thoi (train v21 + think0)** — pre-flight 17/17" + chr(10) + chr(10)
entry += "- **Ferry xong 9/9** (`ornith-gui-lora` 465MB, `ornith-offline-browsers` 375MB, 3 suite bench, 4 dataset 3D) -> **pre-flight 17/17 muc san sang**." + chr(10)
entry += "- Watchdog **da tu push** `khoadangnguye/ornith-gui-bench-v15-think0` (12:04) — chay **song song** voi `sft-v21` (train) va tu cho khi du 2 session GPU." + chr(10)
entry += "- **Them kernel CPU `khoadangnguye/ornith-policy-replay`** (vua push): sinh **du lieu train kieu THAT** tu chinh task B15/B15.5/B16 bang script success-policy cua bench (chay policy tren trang that, chup anh truoc moi buoc -> row (image, instruction, action) voi action `CLICK x y` chuan data train GUI). **Chi variant 0+1 (variant 2 giu lam held-out)**. Da test local: B15 suite ra **135 row** (T01 18, T08 18, T07 15, T11 14, T02/T05/T06/T09 12, T12 10, T03/T04/T10 4) -> uoc **~400 row** cho 3 suite. Muc dich: day model hoc **task 0/3** (T01,T02,T05,T06,T07,T08,T12 = 58% diem B15) tren **trang that** chu khong phai mock." + chr(10)
entry += "- Luu y khi review: `policy_tNN(spec, peek)` la **FACTORY** (tra policy_fn), va moi suite phai chay o **process rieng** (cung ten module 'checker' -> xung import)." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
