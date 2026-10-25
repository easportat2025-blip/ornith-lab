# TASK-26 — 5 app desktop (bien ngau nhien + nhieu buoc)

> Sinh theo spec `phase14-desktop/TASK26_TASK27.md`. Moi app: HTML+JS chay duoc tu
> `file://` (offline, khong can mang), bien **ngau nhien moi lan load**, **nhieu buoc**,
> va co **phan hoi** khi agent lam dung (de agent biet buoc nao da co hieu qua).
> Checker doc trang thai tu **DOM** (khong tin co-flag) va **tinh lai** trong Python.

## Files

| File | Vai tro |
|---|---|
| `tasks/game_2048.html` | T20_2048 (co san tu truoc) |
| `tasks/t21_form_desktop.html` | T21_form_desktop (moi) |
| `tasks/t22_calc.html` | T22_calc (moi) |
| `tasks/t23_table_sort.html` | T23_table_sort (moi) |
| `tasks/t24_text_edit.html` | T24_text_edit (moi) |
| `tasks/checker_desktop.py` | checker + success-policy + fail-policy + self-test |
| `tasks/self_test_report.json` | ket qua self-test |

## Chay self-test

```powershell
python phase14-desktop/tasks/checker_desktop.py --self-test --reps 3
```
Ket qua: **15/15 success-policy PASS + 15/15 fail-policy bi reject** (5 task x 3 lan,
moi lan la 1 bien ngau nhien moi). Fail-policy gom 2 loai: (a) click goc man hinh,
(b) go sai gia tri.

## Action mapping giua 2 moi truong (QUAN TRONG khi viet instruction)

| Action | Playwright (bench B15/B15.5/B16, local) | Desktop env (`phase14-desktop/env.py`) |
|---|---|---|
| click | `CLICK x y` | `CLICK x y` (xdo qua man hinh that) |
| go chu | `TYPE text` | `TYPE text` |
| phim | `KEY ArrowUp` · `KEY ctrl+a` · `KEY End` · `KEY PageDown` | `KEY up` · `KEY ctrl+a` · **KHONG co `end` / `pagedown`** |
| cuon | `KEY End` / `KEY PageDown` | **`SCROLL 5`** (chuot xe) |

⇒ Task nao **bat buoc cuon** (T23_table_sort) phai instruction theo cach cua env:
desktop dung `SCROLL 5`, trinh duyet dung `KEY End`. Trong app, dong huong chi viet chung
("scroll down to the bottom") de khong phu thuoc moi truong.

## Moi task: mo ta + toa do that

> Toa do normalized 0..1000 (x/1280*1000, y/720*1000), **do bang getBoundingClientRect
> luc app vua load** (dung cho app khong bi cuon). App nao bi cuon -> dung `_live()`
> trong `checker_desktop.py` (doc lai toa do moi luc chay).

### T20_2048 — `game_2048.html`

- **Muc tieu:** Choi 2048 bang phim mui (Arrow hoac WASD) cho diem >= 40.
- **Reward (checker doc):** Diem >= 40 (doc tu #s).
- **Bien ngau nhien:** doi moi lan load (user/email/password, 2 bieu thuc, 12 hang + score, cau text).
- **Toa do element (normalized 0..1000):**

| element | x | y | doc bang |
|---|---|---|---|
| `#c0` | 416 | 374 | `window.__targets` (luc load) |
| `#c1` | 472 | 374 | `window.__targets` (luc load) |
| `#c10` | 528 | 574 | `window.__targets` (luc load) |
| `#c11` | 584 | 574 | `window.__targets` (luc load) |
| `#c12` | 416 | 674 | `window.__targets` (luc load) |
| `#c13` | 472 | 674 | `window.__targets` (luc load) |
| `#c14` | 528 | 674 | `window.__targets` (luc load) |
| `#c15` | 584 | 674 | `window.__targets` (luc load) |
| `#c2` | 528 | 374 | `window.__targets` (luc load) |
| `#c3` | 584 | 374 | `window.__targets` (luc load) |
| `#c4` | 416 | 474 | `window.__targets` (luc load) |
| `#c5` | 472 | 474 | `window.__targets` (luc load) |
| `#c6` | 528 | 474 | `window.__targets` (luc load) |
| `#c7` | 584 | 474 | `window.__targets` (luc load) |
| `#c8` | 416 | 574 | `window.__targets` (luc load) |
| `#c9` | 472 | 574 | `window.__targets` (luc load) |
| `#score` | 517 | 291 | `window.__targets` (luc load) |

- **Chieu cao trang:** 720 px (viewport 720) → khong can cuon

### T21_form_desktop — `t21_form_desktop.html`

- **Muc tieu:** Dien user / email / password / confirm theo gia tri trong o vang, tick I accept the terms, roi bam Create account.
- **Reward (checker doc):** u==nu, e==ne, p==np, p2==np, terms tick, status='Account created'.
- **Bien ngau nhien:** doi moi lan load (user/email/password, 2 bieu thuc, 12 hang + score, cau text).
- **Toa do element (normalized 0..1000):**

| element | x | y | doc bang |
|---|---|---|---|
| `#e` | 430 | 406 | `window.__targets` (luc load) |
| `#ne` | 277 | 231 | `window.__targets` (luc load) |
| `#np` | 267 | 258 | `window.__targets` (luc load) |
| `#nu` | 268 | 203 | `window.__targets` (luc load) |
| `#p` | 430 | 474 | `window.__targets` (luc load) |
| `#p2` | 430 | 542 | `window.__targets` (luc load) |
| `#submit` | 236 | 656 | `window.__targets` (luc load) |
| `#terms` | 304 | 598 | `window.__targets` (luc load) |
| `#u` | 430 | 338 | `window.__targets` (luc load) |

- **Chieu cao trang:** 574 px (viewport 720) → khong can cuon

### T22_calc — `t22_calc.html`

- **Muc tieu:** Tra loi 2 bieu thuc: click o dap an, go ket qua, bam Check answer 1 / Check answer 2, roi bam Submit answers.
- **Reward (checker doc):** a1 == e1 tinh lai, a2 == e2 tinh lai, status chua 'accepted'.
- **Bien ngau nhien:** doi moi lan load (user/email/password, 2 bieu thuc, 12 hang + score, cau text).
- **Toa do element (normalized 0..1000):**

| element | x | y | doc bang |
|---|---|---|---|
| `#a1` | 273 | 240 | `window.__targets` (luc load) |
| `#a2` | 273 | 461 | `window.__targets` (luc load) |
| `#c1` | 264 | 298 | `window.__targets` (luc load) |
| `#c2` | 264 | 519 | `window.__targets` (luc load) |
| `#submit` | 252 | 616 | `window.__targets` (luc load) |

- **Chieu cao trang:** 547 px (viewport 720) → khong can cuon

### T23_table_sort — `t23_table_sort.html`

- **Muc tieu:** Bang dai hon cua so -> phai CUON XUONG (trong desktop env dung action 'SCROLL 5'; trong trinh duyet dung 'KEY End' hoac 'KEY PageDown' - env desktop KHONG co key end/pageDown). Click header Score (1 lan = asc, lan nua = desc) de sap xep giam dan theo Score, click dong co Score cao nhat, roi bam Confirm selection.
- **Reward (checker doc):** Thu tu tbody == tinh lai tu #data, dong da chon == dong cao nhat, status chua 'Confirmed'.
- **Bien ngau nhien:** doi moi lan load (user/email/password, 2 bieu thuc, 12 hang + score, cau text).
- **Toa do element (normalized 0..1000):**

| element | x | y | doc bang |
|---|---|---|---|
| `#confirm` | 223 | 1066 | `window.__targets` (luc load) |
| `#hscore` | 735 | 311 | `window.__targets` (luc load) |

- **Chieu cao trang:** 853 px (viewport 720) → PHAI CUON

### T24_text_edit — `t24_text_edit.html`

- **Muc tieu:** Thay TOAN BO noi dung textarea bang cau moi trong o 'New text' (click textarea, Ctrl+A, TYPE cau moi), roi bam Save file.
- **Reward (checker doc):** gia tri textarea == #want, status chua 'Saved'.
- **Bien ngau nhien:** doi moi lan load (user/email/password, 2 bieu thuc, 12 hang + score, cau text).
- **Toa do element (normalized 0..1000):**

| element | x | y | doc bang |
|---|---|---|---|
| `#save` | 200 | 516 | `window.__targets` (luc load) |
| `#ta` | 510 | 346 | `window.__targets` (luc load) |

- **Chieu cao trang:** 429 px (viewport 720) → khong can cuon

