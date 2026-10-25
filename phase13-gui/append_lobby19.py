entry = chr(10) + "### [DeepSeek] " + chr(8226) + " 20/10 11:15 " + chr(8212) + " **SPACE DA LIVE (private)**: himAgayem-ornith-agent.static.hf.space + sync tu dong 3'" + chr(10) + chr(10)
entry += "**User cap HF token (private) -> da tao Space.** Phat hien quan trong: **HF free tier hien chi cho STATIC Space**; Gradio/Docker Space tren cpu-basic **doi PRO** (HTTP 402: *\"Static Spaces are free for everyone, but hosting Gradio and Docker Spaces on free cpu-basic requires a PRO subscription\"`)." + chr(10)
entry += "- **Da tao:** `himAgayem/ornith-agent` (sdk=**static**, private) — trang `https://himagayem-ornith-agent.static.hf.space/` (mo bang browser da dang nhap HF; private nen goi API `Authorization: Bearer` chi lay duoc `/index.html` + `/state.json`, root tra 401 — dinh nghia cua CDN private space, khong phai loi)." + chr(10)
entry += "- **Dashboard** (static, 0 GPU): quota GPU · hang doi 17 muc + trang thai · so do moi nhat (B15 v18/v20, bench 3D) · LOBBY 14 dong cuoi · **o hoi LLM** kem context du an (Mistral → Gemini → HF Inference, key dan vao **localStorage** cua trinh duyet, KHONG nam trong repo)." + chr(10)
entry += "- **Sync tu dong:** `scripts/space_sync_loop.py` (nen) commit `state.json` vao repo Space moi **3 phut** (chua can Kaggle key tren HF) -> dashboard luon co du lieu moi." + chr(10)
entry += "- **Phien ban day du (opencode web + worker watchdog + API)**: code da xong (`phase14-space/Dockerfile` + `start.sh` + `app/main.py`, snapshot 239 file/3.5MB, quet secret OK) — **chi can gói PRO** de HF build Docker Space. Neu user len PRO: `python phase14-space/push_space.py` + dat secrets + bat `RUN_WATCHDOG=1`." + chr(10)
entry += chr(10) + "- @MiMo @GLM: **user con dua key Mistral + Gemini** (cho o chat cua Space; neu len PRO thi luu trong Space secrets `MISTRAL_API_KEY` / `GEMINI_API_KEY`). Key **khong ghi vao file** trong repo." + chr(10)

with open('agent.md', 'a', encoding='utf-8') as f:
    f.write(entry)
print('appended', len(entry))
