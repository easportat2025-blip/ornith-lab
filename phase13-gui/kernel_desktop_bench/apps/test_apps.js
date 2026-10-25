// test_apps.js - kiem tra logic 3 app co bien ngau nhien (TASK-28 v2, GLM).
// Chay: node phase13-gui/kernel_desktop_bench/apps/test_apps.js
// Dung DOM stub nho: dung de chay JS app offline, khong can trinh duyet.
const fs = require('fs');
const path = require('path');
const vm = require('vm');

const HERE = __dirname;

function mkEl(tag, id) {
  const e = {
    tagName: (tag || 'div').toUpperCase(), id: id || '', value: '',
    textContent: '', innerHTML: '', children: [], attrs: {},
    className: '', _l: {},
    classList: { add() {}, remove() {}, contains() { return false; } },
    addEventListener(t, f) { (this._l[t] = this._l[t] || []).push(f); },
    dispatch(t, ev) { (this._l[t] || []).forEach(f => f.call(this, ev || {})); },
    dispatchEvent(ev) { (this._l[ev && ev.type] || []).forEach(f => f.call(this, ev)); },
    focus() { this.focused = true; },
    appendChild(c) { this.children.push(c); return c; },
    setAttribute(k, v) { this.attrs[k] = String(v); },
    getAttribute(k) { return this.attrs[k]; },
    getBoundingClientRect() { return { left: 10, top: 20, width: 100, height: 30 }; },
    querySelector() { return null; },
    querySelectorAll() { return []; },
  };
  return e;
}

function loadApp(file) {
  const html = fs.readFileSync(path.join(HERE, file), 'utf8');
  const script = html.split('<script>')[1].split('</script>')[0];
  const els = {};
  const ids = html.match(/id="([A-Za-z0-9_]+)"/g) || [];
  ids.forEach(m => {
    const id = m.slice(4, -1);
    els[id] = mkEl('div', id);
  });
  // attrs gan theo HTML (data-plan / data-target / data-label)
  const attrRe = /id="([A-Za-z0-9_]+)"[^>]*data-plan="([^"]+)"/g;
  let m;
  while ((m = attrRe.exec(html)) !== null) {
    els[m[1]].setAttribute('data-plan', m[2]);
    els[m[1]].className = 'plan';
  }
  // list container: scroll props
  if (els['list']) {
    els['list'].scrollTop = 0;
    els['list'].clientHeight = 470;
    els['list'].scrollHeight = 1800;
  }
  const document = {
    body: mkEl('body'),
    _l: {},
    getElementById: (id) => els[id] || null,
    createElement: (t) => mkEl(t),
    dispatch: (t, ev) => ((document._l[t] || []).forEach(f => f.call(document, ev || {}))),
    querySelector: (sel) => {
      if (sel === '[data-target="1"]') {
        const stack = els['list'] ? els['list'].children : [];
        for (const c of stack) if (c.getAttribute('data-target') === '1') return c;
      }
      return null;
    },
    querySelectorAll: (sel) => {
      if (sel === '.plan') {
        return ['p0', 'p1', 'p2'].map(k => els[k]).filter(Boolean);
      }
      return [];
    },
    addEventListener: (t, f) => { (document._l[t] = document._l[t] || []).push(f); },
  };
  const win = { innerWidth: 1280, innerHeight: 720 };
  const ctx = { window: win, document, Math, JSON, console,
                Event: class { constructor(type) { this.type = type; } } };
  ctx.window.window = ctx.window;
  vm.createContext(ctx);
  vm.runInContext(script, ctx);
  return { win, document, els };
}

let fails = 0;
function ok(cond, msg) {
  if (cond) { console.log('  ok   ' + msg); }
  else { console.log('  FAIL ' + msg); fails++; }
}

// ---------------- t21_form ----------------
console.log('== t21_form (random user/email/pass, checker so sanh chinh xac) ==');
{
  const a = loadApp('t21_form.html');
  const s1 = a.win.__spec;
  ok(!!s1.user && !!s1.email && !!s1.pass, 'spec co user/email/pass');
  ok(s1.pass.length >= 8, 'password >= 8 ky tu (' + s1.pass.length + ')');
  ok(!!a.win.__targets.user && !!a.win.__targets.register, '__targets co toa do');
  // dung gia tri -> ok=1
  a.els['u'].value = s1.user; a.els['u'].dispatch('input');
  a.els['e'].value = s1.email; a.els['e'].dispatch('input');
  a.els['p'].value = s1.pass; a.els['p'].dispatch('input');
  a.els['c'].value = s1.pass; a.els['c'].dispatch('input');
  a.els['go'].dispatch('click');
  ok(a.win.__form_state.ok === 1, 'dien dung gia tri -> ok=1');
  // sai gia tri -> ok=0
  const b = loadApp('t21_form.html');
  const s2 = b.win.__spec;
  b.els['u'].value = 'wrong'; b.els['u'].dispatch('input');
  b.els['e'].value = s2.email; b.els['e'].dispatch('input');
  b.els['p'].value = 'Password123'; b.els['p'].dispatch('input');
  b.els['c'].value = 'Password123'; b.els['c'].dispatch('input');
  b.els['go'].dispatch('click');
  ok(b.win.__form_state.ok === 0, 'gia tri sai (mat khau 11 ky tu) -> ok=0');
  // confirm khong khop -> ok=0
  const c = loadApp('t21_form.html');
  const s3 = c.win.__spec;
  c.els['u'].value = s3.user; c.els['u'].dispatch('input');
  c.els['e'].value = s3.email; c.els['e'].dispatch('input');
  c.els['p'].value = s3.pass; c.els['p'].dispatch('input');
  c.els['c'].value = s3.pass + 'x'; c.els['c'].dispatch('input');
  c.els['go'].dispatch('click');
  ok(c.win.__form_state.ok === 0, 'confirm khong khop mat khau -> ok=0');
  // bien ngau nhien: 2 lan tai -> gia tri khac nhau
  ok(s1.pass !== b.win.__spec.pass || s1.user !== b.win.__spec.user,
     '2 lan tai -> gia tri NGAY NHIEN khac nhau');
}

// ---------------- t22_order ----------------
console.log('== t22_order (nhac thu tu + gia tri) ==');
{
  const a = loadApp('t22_order.html');
  const s = a.win.__spec;
  ok(!!s.name && !!s.code && !!s.plan, 'spec co name/code/plan');
  // thu tu SAI: code truoc, plan sau
  a.els['nm'].value = s.name; a.els['nm'].dispatch('input');
  a.els['cd'].value = s.code; a.els['cd'].dispatch('input');
  const pid = 'p' + ['Basic', 'Pro', 'Plus'].indexOf(s.plan);
  a.els[pid].dispatch('click');
  a.els['go'].dispatch('click');
  ok(a.win.__state.ok === 0, 'thu tu SAI -> ok=0 (order khong dung)');
  // thu tu DUNG
  const b = loadApp('t22_order.html');
  const t = b.win.__spec;
  b.els['nm'].value = t.name; b.els['nm'].dispatch('input');
  const pid2 = 'p' + ['Basic', 'Pro', 'Plus'].indexOf(t.plan);
  b.els[pid2].dispatch('click');
  b.els['cd'].value = t.code; b.els['cd'].dispatch('input');
  b.els['go'].dispatch('click');
  ok(b.win.__state.ok === 1, 'thu tu DUNG + gia tri dung -> ok=1');
  ok(!!b.win.__targets.name && !!b.win.__targets.submit, '__targets du');
  // REGESSION (22/10): trinh duyet that bam 1 input event cho MOI KY TU.
  // App cu ghi ORDER moi lan => ORDER dai > 4 => ok LUON = 0 => task BAT KHA THI
  // (local integration test da bat dung loi nay).
  const c = loadApp('t22_order.html');
  const u = c.win.__spec;
  u.name.split('').forEach((ch, i) => {
    c.els['nm'].value = u.name.slice(0, i + 1); c.els['nm'].dispatch('input');
  });
  const pid3 = 'p' + ['Basic', 'Pro', 'Plus'].indexOf(u.plan);
  c.els[pid3].dispatch('click');
  u.code.split('').forEach((ch, i) => {
    c.els['cd'].value = u.code.slice(0, i + 1); c.els['cd'].dispatch('input');
  });
  c.els['go'].dispatch('click');
  ok(c.win.__state.ok === 1,
     'nhap NHIEU ky tu (nhieu input event) -> ok=1 (khong ghi ORDER lap)');
}

// ---------------- t23_keys ----------------
console.log('== t23_keys (ESC + phim cuon panel + click muc target) ==');
{
  const a = loadApp('t23_keys.html');
  ok(!!a.win.__spec.code, 'spec co code');
  ok(a.els['list'].children.length === 60, 'list co 60 muc (' + a.els['list'].children.length + ')');
  const target = a.els['list'].children[59];
  ok(!!target.getAttribute('data-target'), 'muc cuoi la target');
  ok(/tabindex="0"/.test(require('fs').readFileSync(path.join(HERE, 't23_keys.html'), 'utf8')),
     'panel co tabindex=0 (focus de phim cuon duoc)');
  ok(a.els['list'].focused === true, 'panel TU FOCUS() khi tai trang (L4 cua lint)');
  // ESC -> dong banner
  a.document.dispatch('keydown', { key: 'Escape' });
  ok((a.win.__keys || []).indexOf('Escape') >= 0, 'ghi nhan phim Escape');
  // PageDown x5 -> panel cuon toi day
  for (let i = 0; i < 5; i++) a.document.dispatch('keydown', { key: 'PageDown' });
  ok(a.win.__scrolled === true, 'PageDown cuon panel toi day (__scrolled=true)');
  // click muc target -> ok=1  (handler nam tren #list, event bubble tu muc len list)
  a.els['list'].dispatch('click', { target: target });
  ok(a.win.__state.ok === 1, 'click muc target sau khi cuon + ESC -> ok=1');
  // thieu ESC -> ok=0
  const b = loadApp('t23_keys.html');
  b.els['list'].scrollTop = 1330; b.els['list'].dispatch('scroll');
  b.els['list'].dispatch('click', { target: b.els['list'].children[59] });
  ok(b.win.__state.ok === 0, 'thieu ESC -> ok=0');
}

// ---------------- t25_recovery ----------------
console.log('== t25_recovery (decoy no-op + read-before-act + loop recovery) ==');
{
  const a = loadApp('t25_recovery.html');
  const r0 = a.win.__recovery;
  const tg = a.win.__targets;
  const btns = a.win.__btns;
  ok(!!r0 && r0.done === false, 'mac dinh chua bat gi (done=false)');
  ok(tg && !!tg.target && tg.decoys && tg.decoys.length === 2,
     '__targets co 1 target + 2 decoy');
  ok(!!btns && btns.length === 3, 'co 3 nut Enable');
  const tId = r0.target_id;
  const dec = [0, 1, 2].filter(i => i !== tId);
  // 1) click DECOY 1 lan: khong an (done=false), repeated=false
  btns[dec[0]].dispatch('click');
  ok(a.win.__recovery.done === false, 'click decoy -> khong bat duoc (done=false)');
  ok(a.win.__recovery.decoy_clicks === 1, 'decoy_clicks=1');
  ok(a.win.__recovery.repeated === false, 'click decoy 1 lan -> repeated=false');
  // 2) click LAI cung decoy: repeated=true  => reward 0 (LOOP)
  btns[dec[0]].dispatch('click');
  ok(a.win.__recovery.repeated === true, 'click lai cung decoy -> repeated=true (LOOP)');
  // 3) click dong DUNG: done=true (nhung repeated=true => van reward 0)
  btns[tId].dispatch('click');
  ok(a.win.__recovery.done === true, 'click row dung -> done=true');
  const rewardLoop = (a.win.__recovery.done && !a.win.__recovery.repeated) ? 1 : 0;
  ok(rewardLoop === 0, 'LOOP (lap lai decoy) => reward=0');
  // 4) kich ban DUNG: click 1 decoy roi click row dung => reward=1 (recovery)
  const b = loadApp('t25_recovery.html');
  const tId2 = b.win.__recovery.target_id;
  const dec2 = [0, 1, 2].filter(i => i !== tId2);
  b.win.__btns[dec2[0]].dispatch('click');
  b.win.__btns[tId2].dispatch('click');
  const rewardOk = (b.win.__recovery.done && !b.win.__recovery.repeated) ? 1 : 0;
  ok(b.win.__recovery.done === true, 'recovery: click decoy 1 lan + dong dung -> done=true');
  ok(b.win.__recovery.repeated === false, 'recovery: khong lap decoy -> repeated=false');
  ok(rewardOk === 1, 'recovery => reward=1');
  // 5) bien ngau nhien: 2 lan tai khac nhau -> khac target hoac khac code
  const c = loadApp('t25_recovery.html');
  ok(c.win.__targets.codes.length === 3, 'app tao 3 dong');
}

// ---------------- t26_clipboard ----------------
console.log('== t26_clipboard (chuoi 5 buoc: click -> ctrl+a -> ctrl+c -> click -> ctrl+v) ==');
{
  const a = loadApp('t26_clipboard.html');
  ok(!!a.els['src'].value, 'Source co noi dung ngau nhien: ' + a.els['src'].value);
  ok(a.els['dst'].value === '', 'Target rong');
  ok(!!a.win.__targets.source && !!a.win.__targets.target, '__targets co source+target');
  ok(a.win.__clip && a.win.__clip.ok === false, 'mac dinh chua paste (ok=false)');
  // ctrl+c tren Source -> luu vao clipboard app
  a.els['src'].dispatch('keydown', { key: 'c', ctrlKey: true, target: a.els['src'] });
  ok(a.win.__clip.copied === true, 'ctrl+c tren Source -> copied=true');
  // ctrl+v tren Target -> dan
  a.els['dst'].dispatch('keydown', { key: 'v', ctrlKey: true, target: a.els['dst'] });
  ok(a.els['dst'].value === a.els['src'].value, 'ctrl+v tren Target -> noi dung khop');
  ok(a.win.__clip.ok === true, 'clipboard ok=true (reward=1)');
}

// ---------------- t27_errorecover ----------------
console.log('== t27_errorecover (app bao LOI nhung ket qua DUNG) ==');
{
  const a = loadApp('t27_errorecover.html');
  const code = a.els['code'].textContent;
  ok(!!code, 'note co activation code: ' + code);
  ok(a.win.__state && a.win.__state.activated === false, 'mac dinh chua active');
  a.els['codein'].value = code; a.els['codein'].dispatch('input');
  a.els['go'].dispatch('click');
  ok(a.win.__state.first_error === true, 'lan 1: app bao loi (first_error=true)');
  ok(a.win.__state.activated === false, 'lan 1: chua active');
  // lan 2: giu nguyen gia tri (dung) -> app bat dau chay
  a.els['go'].dispatch('click');
  ok(a.win.__state.activated === true,
     'lan 2: giu nguyen gia tri dung => active=true (error-recovery)');
  ok(a.win.__state.typed === a.win.__state.code, 'gia tri khong bi doi');
}

// ---------------- t28_distractor ----------------
console.log('== t28_distractor (nhieu dong giong nhau, chi 1 dong khop ma) ==');
{
  const a = loadApp('t28_distractor.html');
  const st = a.win.__state;
  ok(!!st && st.rows === 8, '8 dong (nhieu dong giong nhau)');
  ok(!!st.badge, 'note co badge: ' + (st && st.badge));
  ok(!!a.win.__targets, '__targets co (nut tao dong -> DOM stub co the thieu)');
  // click DONG SAI -> ok=0 (dung __btns: nut duoc tao dong trong JS)
  const btns = a.win.__btns || [];
  ok(btns.length === 8, 'app expose 8 nut (__btns)');
  // tim dong khac dong dich: __targets.ok la toa do -> dung index bang picked
  let okIdx = -1;
  for (let i = 0; i < btns.length; i++) {
    btns[i].dispatch('click');
    if (a.win.__state.ok === 1) { okIdx = i; break; }
  }
  ok(okIdx >= 0, 'co 1 dong khop ma (ok=1)');
  ok(a.win.__state.picked === okIdx, 'click dung dong -> picked=dong do');
  // click 1 dong khac -> ok=0 (khu that lai dong vua chon)
  for (let i = 0; i < btns.length; i++) {
    if (i === okIdx) continue;
    btns[i].dispatch('click');
    ok(a.win.__state.ok === 0, 'click dong sai (index ' + i + ') -> ok=0');
    break;
  }
}

console.log('\n' + (fails === 0 ? 'ALL APP CHECKS PASSED' : (fails + ' CHECK(S) FAILED')));
process.exit(fails === 0 ? 0 : 1);
