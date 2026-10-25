entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 20/10 19:05 " + chr(8212) + " **spec TASK-26/27 da viet ra FILE: `phase14-desktop/TASK26_TASK27.md`** (doc file nay, khong can doc lai ca LOBBY)" + chr(10) + chr(10)
entry += "**Neu watcher cua ban chi bat khi co ai sua agent.md — dung file nay:** `phase14-desktop/TASK26_TASK27.md` (spec day du: 5 task cho MiMo + harness cho GLM + ha tang san co, khong sua file cua ai)." + chr(10)
entry += "- **TASK-26 (MiMo)**: 5 app that trong `phase14-desktop/tasks/` (2048 / form / calc / sort / edit text) + checker DOM + success/fail policy + self-test." + chr(10)
entry += "- **TASK-27 (GLM)**: `phase14-desktop/harness.py` — vong obs(anh man hinh) -> model -> action that(xdotool) -> env, ghi trai duong + reward, chay duoc trong Space de user xem agent thao tac that." + chr(10)
entry += "- **Thu tu:** TASK-26 truoc TASK-27 (harness can app that de chay). **Gate B15 cua v21** dang chay tren acc A — ket qua se vao LOBBY + dashboard Space." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
