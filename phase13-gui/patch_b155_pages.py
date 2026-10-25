"""patch_b155_pages.py - sua T14_alerts + T15_dialog de SUCCESS-POLICY (va agent
that) co the scroll container bang KEY End/PageDown MA KHONG CAN focus.

TASK-24 (DeepSeek): self-test tren Kaggle THAT -> B15.5 14/18.
  - T15_dialog 3/3 fail check 'scrolled before accepting': KEY End khong scroll
    div chua focus -> scrolledat set MUON (sau khi ack) -> sai thu tu.
  - T14_alerts v0 fail 'feed scrolled to bottom' -> cung ly do (race).
Fix: (1) them keydown handler page-level: End/PageDown -> scroll container
(2) T15: ack chi hop le SAU khi da scroll (page cam chon sai thu tu) -> checker
    giu nguyen nghia 'phai scroll truoc khi accept'.
"""
import re

T14 = 'phase13-gui/bench_v15/tasks_v15_5/tasks/t14_alerts.html'
T15 = 'phase13-gui/bench_v15/tasks_v15_5/tasks/t15_dialog.html'

KEY_JS = """
// TASK-24: End/PageDown luon scroll container (khong can focus) -> agent
// khong the "ket" neu khong click dung container truoc.
document.addEventListener("keydown", function(e){
  if (e.key === "End" || e.key === "PageDown") {
    var c = document.getElementById("%s");
    if (c && c.scrollHeight > c.clientHeight + 4) {
      c.scrollTop = c.scrollHeight;
      c.dispatchEvent(new Event("scroll"));
      e.preventDefault();
    }
  }
});
"""

ACK_JS_OLD = """ack.addEventListener("change",function(){
  document.body.dataset.ackedat=String(performance.now());
  document.body.dataset.ack=ack.checked?"1":"0";
  contbtn.disabled=!ack.checked;
});"""

ACK_JS_NEW = """ack.addEventListener("change",function(){
  // TASK-24: chi accept duoc SAU khi da scroll xuong cuoi terms
  // (thu tu sai -> checkbox bi bo chon, agent phai scroll truoc).
  if (document.body.dataset.scrolled !== "1") {
    ack.checked = false;
    document.body.dataset.ack = "0";
    document.body.dataset.ackedat = "";
    contbtn.disabled = true;
    return;
  }
  document.body.dataset.ackedat=String(performance.now());
  document.body.dataset.ack=ack.checked?"1":"0";
  contbtn.disabled=!ack.checked;
});"""


def patch(path, container, ack_old=None, ack_new=None):
    s = open(path, encoding='utf-8').read()
    if 'TASK-24' in s:
        print('skip (da patch)', path)
        return
    js = KEY_JS % container
    # chen handler truoc </script> cuoi cung
    idx = s.rfind('</script>')
    assert idx > 0, path
    s = s[:idx] + js + s[idx:]
    if ack_old and ack_old in s:
        s = s.replace(ack_old, ack_new)
        print('  + ack enforce order')
    open(path, 'w', encoding='utf-8').write(s)
    print('patched', path, '| container', container)


patch(T14, 'feed')
patch(T15, 'terms', ACK_JS_OLD, ACK_JS_NEW)
print('done')
