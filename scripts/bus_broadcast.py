"""bus_broadcast.py - gui huong dan BUS truc tiep VAO SESSION cua tung agent
(theo danh sach session id) + lenh ra bus.

Dung:
    python scripts/bus_broadcast.py
"""
import io
import json
import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import watch_bus as wb  # noqa: E402

# session id -> ten agent (lay tu /api/session theo tieu de)
TARGETS = {
    "ses_ead8c9fcdffe5oLN2Bs6ywVrw3": "helper-1 (DOC agent.md / nhien vu lobby)",
    "ses_ead9ad3bbffelGBjC7wcKDiEZH": "helper-2 (Agent phu Ornith: LOBBY & TASK BOARD)",
    "ses_ea35f710fffe9ddA1QKzyggmcG": "agent phu (deploy OpenCode len HF Space)",
}

MSG = """[HUONG DAN BUS - doc file: AGENT_BUS_GUIDE.md]

Moi truong trao doi da co BUS tuc thien (tin den trong ~1 giay, day thang vao session cua ban).
1) GUI TIN: python scripts/bus_post.py TEN_BAN "NOI DUNG" --tag bench|app|harness|question|done
2) agent.md = SO CAI (append-only): ghi quyet dinh / so lieu / CLAIM / RELEASE. KHONG dung agent.md de goi goi.
3) KHONG ghi "cho phan hoi roi ngu" -> post bus roi lam viec khac tiep.
4) Watchdog poll 60s + post bus moi khi kernel COMPLETE/ERROR + khi push xong -> ket qua GPU den ban ngay.

VIEC CUA BAN (21/10):
- MiMo: UU TIEN doc trace T14-T18 (phase13-gui/out_bench_v155_v21/b15_result.json + out_bench_v155_B/) de lam sach suite B15.5 (T13 da sua xong - xem file nay lam mau). Sau do TASK-26: 5 app that co BIEN NGAU NHIEN + NHIEU BUOC.
- GLM: harness.py da chuyen sang Playwright headful (khong can sua lai). Con loi OFFSET 86px -> cat anh theo viewport. Tiep: viet kernel desktop-bench (TASK-28) trong phase13-gui/kernel_desktop_bench/ (KHONG push kernel - minh push; bao bus khi xong).
Chi tiet: AGENT_BUS_GUIDE.md + agent.md tin 11:30/11:45.
"""


def main():
    ok = 0
    for sid, name in TARGETS.items():
        good = wb.oc_send(sid, MSG)
        print("%-52s -> %s" % (name, "OK" if good else "FAIL"))
        ok += 1 if good else 0
    # luu vao bus de agent moi/agent dang doc cung thay
    try:
        body = json.dumps({"from": "DeepSeek", "text": MSG,
                           "tag": "guide"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8777/post", data=body,
                                     headers={"Content-Type": "application/json"},
                                     method="POST")
        urllib.request.urlopen(req, timeout=8).read()
        print("bus: da luu huong dan")
    except Exception as e:
        print("bus loi:", e)
    print("ket qua: %d/%d session nhan duoc" % (ok, len(TARGETS)))


if __name__ == "__main__":
    main()
