# -*- coding: utf-8 -*-
"""
build_b17_apps.py - BUILD 8 APP WEB KHÓ cho suite B17 (GĐ-A, @GLM giao).

MỤC TIÊU (theo số liệu đã đo, không đoán):
  * B15.5/B16-A đã "tất định" còn task khó (C3_misread_text, C4_no_submit,
    C1_no_action, C2_stuck_repeat) + 3 verb chưa có trong data (SCROLL/MOVE/
    DRAG) + error-recovery + keyboard-nav.
  * B17 phải KHIẾN model mạnh nhất <= 20% (W1) và phủ >= 10 năng lực (W2).

MỖI APP ĐƯỢC:
  1. tự sinh giá trị ngẫu nhiên lúc load -> window.__spec = {vars:{...}}
     (GLM dung SPEC_JS de render instruction tu day - app TUONG THICH
     voi contract cua checker hien tai)
  2. window.__state = {...}  (checker TIN LAI tu DOM, khong tin co-flag)
  3. window.__targets = {id: [x,y normalized 0..1000]}
  4. KHONG phu thuoc ngoai (offline) - chay duoc tren Colab/Kaggle/CSP

Dung:
    python scripts/build_b17_apps.py
    python scripts/lint_task_static.py phase13-gui/bench_b17
ASCII-only source.
"""
import io
import json
import os
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = r"C:\Users\Admin\Desktop\New folder"
OUT = os.path.join(ROOT, "phase13-gui", "bench_b17", "tasks")

CSS = """
*{box-sizing:border-box}body{margin:0;font:15px system-ui,sans-serif;
background:#eef1f6;color:#1d2330;padding:18px}
.card{background:#fff;border:1px solid #d6dbe6;border-radius:10px;
padding:16px;margin-bottom:12px;max-width:760px}
h2{font-size:18px;margin:0 0 8px}
.note{background:#fff8e1;border:1px solid #e4cf88;border-radius:8px;
padding:10px;margin:8px 0;font-family:ui-monospace,monospace}
.note b{color:#8a6d1f}
label{display:block;margin:8px 0 3px;font-weight:600}
input[type=text]{width:320px;padding:8px;border:1px solid #b9c1d1;
border-radius:6px;font-size:15px}
button{background:#3b6fd4;color:#fff;border:0;border-radius:6px;
padding:9px 18px;font-size:15px;cursor:pointer;margin-top:8px}
button:disabled{background:#aab3c6;cursor:not-allowed}
.panel{max-height:150px;overflow-y:auto;border:1px solid #b9c1d1;
border-radius:6px;width:520px}
table{border-collapse:collapse;width:100%}
td{border-bottom:1px solid #eef0f4;padding:5px 8px;font-size:14px}
#msg{margin-top:8px;min-height:20px;color:#3b6fd4}
#msg.bad{color:#b3261e}
.hidden{display:none}
"""

JS_HELP = """
function R(a){return a[Math.floor(Math.random()*a.length)]}
function norm(el){const r=el.getBoundingClientRect();
return [Math.round((r.left+r.width/2)/innerWidth*1000),
Math.round((r.top+r.height/2)/innerHeight*1000)]}
function targets(){const o={};document.querySelectorAll('[id]').forEach(e=>{
if(['__spec','__state','__targets'].includes(e.id))return;
o[e.id]=norm(e)});return o}
"""


def page(title, body, script):
    return ("<!doctype html>\n<html lang=\"en\">\n<head>\n<meta charset=\"utf-8\">\n"
            "<title>%s</title>\n<style>%s</style>\n</head>\n<body>\n%s\n"
            "<script>%s\n%s</script>\n</body>\n</html>\n"
            % (title, CSS, body, JS_HELP, script))


APPS = []

# ---------------------------------------------------------------- B17-1
APPS.append(("t30_note_order", page(
    "Account Setup",
    """<div class="card">
<h2>Account Setup</h2>
<div class="note">Values (listed in the opposite order to the fields):<br>
<b>B = <span id="vCODE_B"></span></b><br><b>A = <span id="vNAME_A"></span></b></div>
<label>Field A</label><input type="text" id="fa">
<label>Field B</label><input type="text" id="fb">
<label>Field C (leave empty)</label><input type="text" id="fc">
<button id="sub">Submit</button>
<div id="msg"></div>
</div>""",
    """const NAME_A=R(["Alex","Robin","Casey","Morgan","Quinn","Riley","Avery"]);
const CODE_B=R(["K7-221","R9-305","T4-118","M2-774","P8-063"]);
window.__spec={vars:{NAME_A:NAME_A,CODE_B:CODE_B},order:["CODE_B","NAME_A"]};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
function snap(){window.__state={fa:fa.value,fb:fb.value,fc:fc.value,
submitted:false};}
fa.addEventListener('input',snap);fb.addEventListener('input',snap);
fc.addEventListener('input',snap);
sub.addEventListener('click',()=>{snap();window.__state.submitted=true;
const ok=fa.value.trim()===NAME_A&&fb.value.trim()===CODE_B&&fc.value.trim()==="";
msg.textContent=ok?"Account created":"Some fields are wrong";
msg.className=ok?"":"bad";window.__state.ok=ok;});
snap();window.__targets=targets();"""),
    {"task_id": "T30_note_order", "app": "t30_note_order.html",
     "instruction": ("Fill Field A and Field B with the values listed in the "
                     "note box (the note lists them in the opposite order to "
                     "the fields). Leave Field C empty, then press Submit."),
     "capabilities": ["read_note", "type_text", "click_button", "no_decoy_fill",
                      "reordered_values"],
     "spec_vars": ["NAME_A", "CODE_B"]}))

# ---------------------------------------------------------------- B17-2
APPS.append(("t31_scroll_code", page(
    "Archive",
    """<div class="card">
<h2>Archive list</h2>
<div class="note">The code you need: <b><span id="vCODE"></span></b></div>
<div class="panel" id="panel"><table id="tb"></table></div>
<button id="sub" style="position:fixed;right:20px;bottom:20px">Confirm</button>
<div id="msg"></div>
</div>""",
    """const ROWS=14;
const idx=8+Math.floor(Math.random()*(ROWS-7));   // hang 8..14 (duoi khung)
const codes=[];for(let i=1;i<=ROWS;i++)codes.push(R(['Z','Q','H','M','B','K'])+
'-'+(1000+i*7+Math.floor(Math.random()*5)));
const CODE=codes[idx-1];
window.__spec={vars:{CODE:CODE},target_row:idx};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
const tb=document.getElementById('tb');
for(let i=1;i<=ROWS;i++){const tr=document.createElement('tr');
const code=codes[i-1];
tr.innerHTML='<td>Row '+i+'</td><td>'+code+'</td><td>'+(10+i)+'</td>';
if(i===idx)tr.dataset.target='1';
tr.addEventListener('click',()=>{window.__state={clicked:tr.cells[1].textContent,
submitted:false};});
tb.appendChild(tr);}
window.__state={clicked:'',submitted:false};
sub.addEventListener('click',()=>{window.__state.submitted=true;
const ok=window.__state.clicked===CODE;msg.textContent=ok?"Confirmed":"Wrong row";
msg.className=ok?"":"bad";window.__state.ok=ok;});
window.__targets=targets();"""),
    {"task_id": "T31_scroll_code", "app": "t31_scroll_code.html",
     "instruction": ("The archive list sits inside a scrollable panel. Scroll "
                     "down to the bottom of the list, then click the row whose "
                     "code matches the note, then press Confirm."),
     "capabilities": ["scroll", "read_note", "click_row", "click_button",
                      "target_below_fold"],
     "spec_vars": ["CODE"]}))

# ---------------------------------------------------------------- B17-3
APPS.append(("t32_drag_slider", page(
    "Sensitivity",
    """<div class="card">
<h2>Sensitivity</h2>
<div class="note">Set the slider to <b><span id="vVALUE"></span></b></div>
<div id="wrap" style="width:420px;height:34px;background:#dde2ec;
border-radius:17px;position:relative;margin:14px 0">
<div id="fill" style="position:absolute;left:0;top:0;height:34px;width:10%;
background:#3b6fd4;border-radius:17px"></div>
<div id="knob" style="position:absolute;left:calc(10% - 11px);top:0;
width:22px;height:34px;background:#1f4fa8;border-radius:11px"></div></div>
<button id="sub">Apply</button><div id="msg"></div>
</div>""",
    """const VALUE=R([30,45,60,75,90]);
window.__spec={vars:{VALUE:VALUE}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
let val=10;
const wrap=document.getElementById('wrap'),knob=document.getElementById('knob'),
fill=document.getElementById('fill');
function setv(v){val=v;knob.style.left='calc('+v+'% - 11px)';
fill.style.width=v+'%';}
function fromX(cx){const r=wrap.getBoundingClientRect();
setv(Math.max(0,Math.min(100,Math.round((cx-r.left)/r.width*100))));}
wrap.addEventListener('mousedown',e=>{fromX(e.clientX);
const mv=ev=>fromX(ev.clientX);const up=()=>{document.removeEventListener(
'mousemove',mv);document.removeEventListener('mouseup',up);};
document.addEventListener('mousemove',mv);document.addEventListener('mouseup',up);});
window.__state={value:val,submitted:false};
sub.addEventListener('click',()=>{window.__state.value=val;
window.__state.submitted=true;const ok=Math.abs(val-VALUE)<=2;
msg.textContent=ok?"Applied":"Wrong level";msg.className=ok?"":"bad";
window.__state.ok=ok;});
window.__targets=targets();"""),
    {"task_id": "T32_drag_slider", "app": "t32_drag_slider.html",
     "instruction": ("Set the sensitivity slider to the value shown in the note "
                     "by dragging its handle, then press Apply."),
     "capabilities": ["drag", "read_note", "click_button", "continuous_value"],
     "spec_vars": ["VALUE"]}))

# ---------------------------------------------------------------- B17-4
APPS.append(("t33_error_retry", page(
    "Device Setup",
    """<div class="card">
<h2>Device Setup</h2>
<div class="note">Setup code: <b><span id="vCODE"></span></b></div>
<label>Setup code</label><input type="text" id="code">
<button id="sub">Submit</button><div id="msg"></div>
</div>""",
    """const CODE=R(["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"]);
window.__spec={vars:{CODE:CODE}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
let submits=0;
function snap(){window.__state={code:code.value,submits:submits,
submitted:false,message:msg.textContent};}
code.addEventListener('input',snap);
sub.addEventListener('click',()=>{submits++;snap();
if(submits===1){msg.textContent='Error: invalid code';
msg.className='bad';}
else{const ok=code.value.trim()===CODE;
msg.textContent=ok?'Device activated':'Error: invalid code';
msg.className=ok?'':'bad';window.__state.ok=ok;}
window.__state.submitted=true;window.__state.message=msg.textContent;});
snap();window.__targets=targets();"""),
    {"task_id": "T33_error_retry", "app": "t33_error_retry.html",
     "instruction": ("Type the setup code from the note into the code box and "
                     "press Submit. If the app reports an error, press Submit "
                     "once more without changing the value."),
     "capabilities": ["read_note", "type_text", "error_recovery",
                      "no_value_change", "click_button"],
     "spec_vars": ["CODE"]}))

# ---------------------------------------------------------------- B17-5
APPS.append(("t34_tab_nav", page(
    "Directory",
    """<div class="card">
<h2>Directory</h2>
<div class="note">Family: <b><span id="vFAM"></span></b> &middot; Given: <b><span id="vGIV"></span></b> &middot;
City: <b><span id="vCITY"></span></b></div>
<label>Family name</label><input type="text" id="f1">
<label>Given name</label><input type="text" id="f2">
<label>City</label><input type="text" id="f3">
<button id="sub">Submit</button><div id="msg"></div>
</div>""",
    """const FAM=R(["Novak","Okafor","Ibarra","Lindqvist","Takahashi"]);
const GIV=R(["Mila","Idris","Anouk","Sven","Rei"]);
const CITY=R(["Bergen","Kyoto","Lima","Riga","Accra"]);
window.__spec={vars:{FAM:FAM,GIV:GIV,CITY:CITY}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
function snap(){window.__state={f1:f1.value,f2:f2.value,f3:f3.value,
submitted:false};}
[f1,f2,f3].forEach(e=>e.addEventListener('input',snap));
sub.addEventListener('click',()=>{snap();window.__state.submitted=true;
const ok=f1.value.trim()===FAM&&f2.value.trim()===GIV&&f3.value.trim()===CITY;
msg.textContent=ok?'Saved':'Mismatch';msg.className=ok?'':'bad';
window.__state.ok=ok;});
document.addEventListener('keydown',e=>{if(e.key==='Enter'){e.preventDefault();
sub.click();}});
snap();window.__targets=targets();"""),
    {"task_id": "T34_tab_nav", "app": "t34_tab_nav.html",
     "instruction": ("Fill the three fields with the values from the note "
                     "using the Tab key to move between them, then press Enter "
                     "to submit. Do not click the fields with the mouse."),
     "capabilities": ["keyboard_nav", "read_note", "type_text",
                      "key_enter_submit", "no_mouse_click"],
     "spec_vars": ["FAM", "GIV", "CITY"]}))

# ---------------------------------------------------------------- B17-6
APPS.append(("t35_hover_code", page(
    "Serial card",
    """<div class="card">
<h2>Serial card</h2>
<div class="note">Serial of the card named <b>Serial</b></div>
<div id="card" style="width:300px;padding:14px;border:1px dashed #b9c1d1;
border-radius:8px;background:#fbfcfe">Card name: Serial<br>
Code: <span id="code" class="hidden">hidden</span></div>
<label>Code</label><input type="text" id="inp">
<button id="sub">Verify</button><div id="msg"></div>
</div>""",
    """const CODE=R(["S-4471","P-9026","D-1183","L-6650","H-3307"]);
window.__spec={vars:{CODE:CODE}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
let moved=false;
card.addEventListener('mouseenter',()=>{moved=true;code.classList.remove('hidden');
code.textContent=CODE;window.__state={moved:true,code:inp.value,submitted:false};});
function snap(){window.__state={moved:moved,code:inp.value,submitted:false};}
inp.addEventListener('input',snap);
sub.addEventListener('click',()=>{snap();window.__state.submitted=true;
const ok=inp.value.trim()===CODE&&moved;msg.textContent=ok?'Verified':'Wrong code';
msg.className=ok?'':'bad';window.__state.ok=ok;});
snap();window.__targets=targets();"""),
    {"task_id": "T35_hover_code", "app": "t35_hover_code.html",
     "instruction": ("Move the pointer over the card named Serial to reveal "
                     "its code, type the code into the box, then press "
                     "Verify."),
     "capabilities": ["hover_move", "read_note", "type_text", "click_button"],
     "spec_vars": ["CODE"]}))

# ---------------------------------------------------------------- B17-7
APPS.append(("t36_wizard_steps", page(
    "Upgrade wizard",
    """<div class="card">
<h2>Upgrade wizard</h2>
<div class="note">Plan: <b><span id="vPLAN"></span></b> &middot; Add-on: <b><span id="vADDON"></span></b></div>
<div id="s1"><label>Plan</label><select id="plan">
<option value="">(pick one)</option><option>Basic</option><option>Pro</option>
<option>Ultra</option></select>
<button id="b1">Next</button></div>
<div id="s2" class="hidden"><label>Add-on</label><select id="addon">
<option value="">(pick one)</option><option>Backup</option>
<option>Support</option><option>Storage</option></select>
<button id="b2">Next</button></div>
<div id="s3" class="hidden"><div id="sum"></div>
<button id="b3">Finish</button></div>
<div id="msg"></div>
</div>""",
    """const PLAN=R(["Basic","Pro","Ultra"]);
const ADDON=R(["Backup","Support","Storage"]);
window.__spec={vars:{PLAN:PLAN,ADDON:ADDON}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
let step=1;
function snap(){window.__state={step:step,plan:plan.value,addon:addon.value,
submitted:false};}
b1.addEventListener('click',()=>{snap();if(plan.value!==PLAN){
msg.textContent='Wrong plan';msg.className='bad';return;}
msg.textContent='';msg.className='';step=2;s1.classList.add('hidden');
s2.classList.remove('hidden');snap();});
b2.addEventListener('click',()=>{snap();if(addon.value!==ADDON){
msg.textContent='Wrong add-on';msg.className='bad';return;}
msg.textContent='';msg.className='';step=3;s2.classList.add('hidden');
s3.classList.remove('hidden');sum.textContent='Plan: '+plan.value+' + '+
addon.value;snap();});
b3.addEventListener('click',()=>{snap();window.__state.submitted=true;
const ok=plan.value===PLAN&&addon.value===ADDON;msg.textContent=ok?'Done':'Failed';
msg.className=ok?'':'bad';window.__state.ok=ok;});
snap();window.__targets=targets();"""),
    {"task_id": "T36_wizard_steps", "app": "t36_wizard_steps.html",
     "instruction": ("Complete the wizard in order: on step 1 pick the plan "
                     "named in the note and press Next, on step 2 pick the "
                     "add-on named in the note and press Next, then on step 3 "
                     "press Finish."),
     "capabilities": ["multi_step", "read_note", "select_option",
                      "click_button", "no_premature_submit"],
     "spec_vars": ["PLAN", "ADDON"]}))

# ---------------------------------------------------------------- B17-8a (loop_recovery - port tu T25 desktop)
APPS.append(("t38_recovery", page(
    "Device Setup",
    """<div class="card">
<h2>Device Setup</h2>
<div class="note">Enable the feature whose code is <b><span id="vCODE"></span></b>.
If a control does not respond, try a different control.</div>
<table id="tb"><tr><th>Feature</th><th>Code</th><th>Controls</th><th>Status</th></tr>
<tr><td>Audio</td><td id="c0"><span id="vC0"></span></td><td><button class="p" data-i="0">Enable</button>
<button class="b" data-i="0">Enable (backup)</button></td><td id="s0">disabled</td></tr>
<tr><td>Display</td><td id="c1"><span id="vC1"></span></td><td><button class="p" data-i="1">Enable</button>
<button class="b" data-i="1">Enable (backup)</button></td><td id="s1">disabled</td></tr>
<tr><td>Network</td><td id="c2"><span id="vC2"></span></td><td><button class="p" data-i="2">Enable</button>
<button class="b" data-i="2">Enable (backup)</button></td><td id="s2">disabled</td></tr>
<tr><td>Storage</td><td id="c3"><span id="vC3"></span></td><td><button class="p" data-i="3">Enable</button>
<button class="b" data-i="3">Enable (backup)</button></td><td id="s3">disabled</td></tr>
</table><div id="msg"></div>
</div>""",
    """const POOL=["AX-7719","QR-2048","LM-6633","ZT-9105","BK-3384"];
const CODES=POOL.slice().sort(()=>Math.random()-0.5).slice(0,4);
const IDX=Math.floor(Math.random()*4);
const CODE=CODES[IDX];
window.__spec={vars:{CODE:CODE,C0:CODES[0],C1:CODES[1],C2:CODES[2],C3:CODES[3]},target_row:IDX};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
let tries=0;
function snap(){window.__state={code:CODE,tries:tries,enabled:document.getElementById('s'+IDX).textContent==='enabled',submitted:false};}
document.querySelectorAll('.p').forEach(b=>b.addEventListener('click',()=>{tries++;
snap();if(parseInt(b.dataset.i,10)===IDX){document.getElementById('msg').textContent='No response';
document.getElementById('msg').className='bad';}
else{}}));
document.querySelectorAll('.b').forEach(b=>b.addEventListener('click',()=>{tries++;
snap();if(parseInt(b.dataset.i,10)===IDX){document.getElementById('s'+IDX).textContent='enabled';
document.getElementById('msg').textContent='Enabled';document.getElementById('msg').className='';}
else{document.getElementById('msg').textContent='Wrong feature';document.getElementById('msg').className='bad';}
window.__state.enabled=document.getElementById('s'+IDX).textContent==='enabled';
window.__state.submitted=true;window.__state.ok=window.__state.enabled;}));
snap();window.__targets=targets();"""),
    {"task_id": "T38_recovery", "app": "t38_recovery.html",
     "instruction": ("Open the Device Setup page. The support note shows a "
                     "feature code. Click the Enable button on the row whose "
                     "feature code matches the note. If a control does not "
                     "respond, try a different control instead of clicking the "
                     "same one again."),
     "capabilities": ["read_note", "click_button", "error_recovery",
                      "no_repeat_click", "loop_recovery"],
     "spec_vars": ["CODE", "C0", "C1", "C2", "C3"]}))

# ---------------------------------------------------------------- B17-8
APPS.append(("t37_terms_guard", page(
    "Save document",
    """<div class="card">
<h2>Save document</h2>
<div class="note">Title: <b><span id="vTITLE"></span></b></div>
<label>Title</label><input type="text" id="t">
<label><input type="checkbox" id="terms"> I have read the terms</label>
<button id="sub" disabled>Save</button><div id="msg"></div>
</div>""",
    """const TITLE=R(["Q3 report","Budget 2026","Field notes","Plan v2"]);
window.__spec={vars:{TITLE:TITLE}};
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
Object.keys(window.__spec.vars).forEach(function(k){var e=document.getElementById('v'+k); if(e) e.textContent=window.__spec.vars[k];});
function upd(){sub.disabled=!terms.checked;
window.__state={title:t.value,terms:terms.checked,submitted:false};}
t.addEventListener('input',upd);terms.addEventListener('change',upd);
sub.addEventListener('click',()=>{upd();window.__state.submitted=true;
const ok=t.value.trim()===TITLE&&terms.checked;msg.textContent=ok?'Saved':'Check the form';
msg.className=ok?'':'bad';window.__state.ok=ok;});
upd();window.__targets=targets();"""),
    {"task_id": "T37_terms_guard", "app": "t37_terms_guard.html",
     "instruction": ("Type the document title from the note into the Title "
                     "box, tick the 'I have read the terms' checkbox, then "
                     "press Save. The Save button stays disabled until the "
                     "box is ticked."),
     "capabilities": ["read_note", "type_text", "checkbox", "click_button",
                      "stuck_repeat_guard"],
     "spec_vars": ["TITLE"]}))


def main():
    os.makedirs(OUT, exist_ok=True)
    tasks = []
    for name, html, meta in APPS:
        p = os.path.join(OUT, name + ".html")
        with io.open(p, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(html)
        tasks.append(meta)
        print("   viet %-26s (%d byte)" % (name + ".html", len(html)))
    tj = {"suite": "B17", "version": 1,
          "viewport": {"width": 1280, "height": 720},
          "action_space": ("CLICK x y (0..1000 normalized) | TYPE text | "
                           "KEY name | DONE | SCROLL n | MOVE x y | "
                           "DRAG x1 y1 x2 y2"),
          "tasks": tasks}
    with io.open(os.path.join(OUT, "tasks.json"), "w", encoding="utf-8",
                 newline="\n") as fh:
        json.dump(tj, fh, ensure_ascii=False, indent=1)
    caps = sorted(set(c for t in tasks for c in t["capabilities"]))
    print("=> %d app | %d nang luc (W2): %s" % (len(tasks), len(caps), caps))
    print("=> lenh tiep: python scripts/lint_task_static.py phase13-gui/bench_b17")
    return 0


if __name__ == "__main__":
    sys.exit(main())
