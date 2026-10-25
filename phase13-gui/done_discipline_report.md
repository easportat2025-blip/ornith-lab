# Do "ky luat DONE" trong data train + hanh vi model

_Sinh tu dong boi `phase13-gui/done_discipline.py` (GLM) - khong go tay so lieu._

## 1) Data train: tung nguon co day "chuoi roi moi DONE" khong?

> **LUU Y SEMANTIC** (theo @MiMo 22/10): 2 chi so khac nghia - **%row la DONE** (cai model THAT su thay khi train) va **%episode ket thuc bang DONE** (chi co y nghia o nguon co field episode/step; voi gui-traj goc - data 1-action - episode chi duoc SUY RA tu ten file `..._sMM.png`, nen dung %row la DONE cho nguon do; %episode co y nghia sau khi R2 them row DONE).

| nguon | rows | episodes | buoc/ep (min/med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE | verbs |
|---|---|---|---|---|---|---|---|
| gui-traj (R2 aug) | 972 | 216 | 2/5.0/9 | 5.6% | 100.0% | 22.22% | CLICK=577, DONE=216, TYPE=144, KEY=35 |
| gui-traj (base 816) | 816 | 216 | 1/4.5/9 | 3.2% | 27.8% | 7.35% | CLICK=577, TYPE=144, DONE=60, KEY=35 |
| policy-replay (332) | 332 | 52 | 2/6.0/14 | 34.6% | 100.0% | 15.66% | CLICK=198, DONE=52, TYPE=44, KEY=38 |
| selfplay d2 (123) | 123 | 18 | 2/6.5/12 | 38.9% | 50.0% | 8.94% | CLICK=89, TYPE=17, DONE=11, KEY=6 |
| train3d (300) | 300 | 300 | 1/1.0/1 | 0.0% | 0.0% | 0.00% | CLICK=300 |
| train3d-hard (300) | 300 | 300 | 1/1.0/1 | 0.0% | 0.0% | 0.00% | CLICK=300 |
| real-ui (792) | 792 | 792 | 1/1.0/1 | 0.0% | 0.0% | 0.00% | =792 |
| rollout-raw (511) | 511 | 72 | 2/8.0/10 | 61.1% | 37.5% | 5.28% | CLICK=356, TYPE=50, =46, KEY=32, DONE=27 |

## 2) Synth targeted (dung dung ham kernel v22: build_targeted(250, 303))

| nguon | rows | episodes | buoc/ep (min/med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE |
|---|---|---|---|---|---|---|
| synth targeted S1-S8 (n=250, dr=0.0 = v22) | 2032 | 500 | 2/3.0/10 | 4.8% | 0.0% | 0.00% |
| **synth targeted S1-S8 (n=250, dr=0.75 = MOI)** | 2420 | 500 | 2/4.0/11 | 5.2% | 77.6% | 16.03% |

## 3) Hanh vi thuc cua model trong rollout (511 row, policy v20 t=0.7)

| nhom | episodes | %ep ket thuc bang DONE | %ep co DONE bat ky luc | avg buoc/ep |
|---|---|---|---|---|
| nhom | episodes | %ep ket thuc bang DONE | %ep co DONE bat ky luc | avg buoc/ep |
|---|---|---|---|---|
| WIN | 24 | 95.8% | 95.8% | 5.0 |
| nhom | episodes | %ep ket thuc bang DONE | %ep co DONE bat ky luc | avg buoc/ep |
|---|---|---|---|---|
| FAIL | 48 | 8.3% | 8.3% | 8.1 |

## 4) B15 v21 (model tren bench that): episode co DONE khong?

| nhom | episodes | %ep co DONE | %ep ket thuc bang DONE | avg buoc/ep |
|---|---|---|---|---|
| WIN | 11 | 90.9% | 90.9% | 4.6 |
| FAIL | 25 | 0.0% | 0.0% | 8.4 |

## 5) Pha loang trong mix v22 (theo so ROW thuc te)

| nguon trong mix v22 | rows | %DONE cua nguon | dong gop DONE | ghi chu |
|---|---|---|---|---|
| synth (grounding don le) | 1200 | 0.00% | 0.0 row | row khong co 'action' (grounding 1 CLICK) |
| real-ui | 792 | 0.00% | 0.0 row |  |
| gui-traj | 816 | (khong do duoc) | - |  |
| synth targeted S1-S8 | 2032 | 0.00% | 0.0 row | 250 episode |
| train3d | 300 | 0.00% | 0.0 row |  |
| train3d-hard | 300 | 0.00% | 0.0 row |  |
| policy-replay | 332 | 15.66% | 52.0 row |  |
| selfplay (cap 30%) | 123 | 8.94% | 11.0 row |  |
| **TONG mix v22** | **5079** | - | **63.0 row DONE (1.24%)** | |

**Chi nguon day "chuoi -> DONE" la policy-replay + selfplay**: 90.0/966.0 row DONE cua 2 nguon do = **1.8% cua toan mix** (90 row) - phan con lai cua mix khong co DONE sau chuoi.

## 6) gen_synth_long (file moi cua @MiMo) + sweep `done_rate`

| done_rate | rows | episodes | buoc/ep (med/max) | %ep >=8 buoc | %ep ket thuc bang DONE | %row la DONE | verbs |
|---|---|---|---|---|---|---|---|
| 0.00 | 1050 | 120 | 8.0/11 | 100.0% | 0.0% | 0.00% | CLICK=720, TYPE=240, KEY=90 |
| 0.25 | 1082 | 120 | 8.0/12 | 100.0% | 26.7% | 2.96% | CLICK=720, TYPE=240, KEY=90, DONE=32 |
| 0.35 | 1093 | 120 | 9.0/12 | 100.0% | 35.8% | 3.93% | CLICK=720, TYPE=240, KEY=90, DONE=43 |
| 0.50 | 1107 | 120 | 9.0/12 | 100.0% | 47.5% | 5.15% | CLICK=720, TYPE=240, KEY=90, DONE=57 |
| 0.75 | 1138 | 120 | 9.0/12 | 100.0% | 73.3% | 7.73% | CLICK=720, TYPE=240, KEY=90, DONE=88 |
| 1.00 | 1170 | 120 | 9.0/12 | 100.0% | 100.0% | 10.26% | CLICK=720, TYPE=240, DONE=120, KEY=90 |
| **0.75 (n=250, production)** | 2365 | 250 | 9.0/12 | 100.0% | 71.6% | 7.57% |

## 7) Co che: action CUOI cua episode la gi? (nguon dang loai DONE)

| nguon | episode nhieu buoc | %ep cuoi = DONE | %ep cuoi = CLICK (khong DONE) |
|---|---|---|---|
| gui-traj (R2 aug) | 216 | 100.0% | 0.0% |
| gui-traj (base 816) | 169 | 35.5% | 64.5% |
| policy-replay (332) | 52 | 100.0% | 0.0% |
| selfplay d2 (123) | 18 | 50.0% | 50.0% |
| rollout-raw (511) | 72 | 37.5% | 62.5% |
| synth targeted S1-S8 | 500 | 0.0% | 100.0% |
> Doc dong nay: mot episode nhieu buoc cuoi bang **CLICK** (khong DONE) => model hoc 'chuoi ket thuc bang 1 click' => khong bao gio DONE. Day la ly do C4 / 0% episode fail co DONE.

## 8) Kich ban mix: P(DONE | buoc cuoi cua episode nhieu buoc) + %DONE toan mix

| kich ban | them vao mix | episode nhieu buoc | ep cuoi=DONE | **P(DONE \| cuoi multi-step)** | rows DONE / tong rows |
|---|---|---|---|---|---|
| S0 = v22 hien tai | - | 786 | 277 | **35.2%** | 279 / 5079 = 5.49% |
| S1 = + long 250 ep (dr 0.35) | gen_synth_long n=250 | 1036 | 365 | **35.2%** | 367 / 7364 = 4.98% |
| S1b = + long 250 ep (dr 0.75) | gen_synth_long n=250 | 1036 | 465 | **44.9%** | 467 / 7364 = 6.34% |
| S2 = + long 250 ep (dr 0.60) | gen_synth_long n=250 | 1036 | 427 | **41.2%** | 429 / 7364 = 5.83% |
| S3 = + long 250 (dr .75) + targeted co DONE cuoi | gen_synth_long + sua targeted | 1036 | 715 | **69.0%** | 717 / 7614 = 9.42% |
| S4 = + long 600 (dr .75) + targeted co DONE cuoi | gen_synth_long n=600 + sua targeted | 1386 | 977 | **70.5%** | 979 / 10813 = 9.05% |

> Doc: **P(DONE | cuoi episode nhieu buoc)** la xac suat model 'sau khi chuoi xong thi emit DONE'. Hien tai **35.2%** (61/320 episode nhieu buoc ket thuc bang DONE). Chi lenh `done_rate` cua gen_synth_long: dr 0.75 + 250 ep => **44.9%** (da > 40%) ma VAN giu 25% chuoi dai khong DONE (model van biet phai tiep) + L4 giu 'khong DONE som'. Muon >50% thi PHAI sua them 250 episode targeted (hoac cat targeted khoi mix) - vi targeted 100% ket thuc bang CLICK.
| **S6 = v23a: CHI targeted dr0.75 (RHE + 388 row)** | re-inline targeted | 786 | 665 | **84.6%** | 667 / 5467 = 12.20% |
> **S6 vs S5: them long 250 ep KHONG tang P(DONE) ma lam GIAM nho** (84.6% -> 81.5%) vi long co 25% episode khong DONE; long day them kha nang CHAIN DAU (%ep >=8 buoc), khac co che DONE. => **chay v23a truoc** (RHE +388 row / +69 steps ~ +5% GPU), neu v23a van fail o task nhieu buoc thi moi xet v23b.
| **S7 = v22 + R2 (GPT: +0 row DONE vao tap tra)** | traj_done_aug | 786 | 277 | **35.2%** | 279 / 5079 = 5.49% |
| **S8 = v23a + R2 (khuyến nghị)** | targeted dr0.75 + traj_done_aug | 786 | 665 | **84.6%** | 667 / 5467 = 12.20% |
> **Chi phi R2: +0 row ( dung anh buoc cuoi ) ~ +0 steps** => re dat hon nhieu so voi +1977 row cua long 250 ep.
| **S5 = v23: targeted dr0.75 + long 250 dr0.75 (DO DUOC)** | gen_synth_long + re-inline targeted | 1036 | 844 | **81.5%** | 846 / 7832 = 10.80% |

> **Chi phi (do duoc):** mix v23 = 7832 row -> `STEPS = 500 x 7832/2808` = **1394 steps** (~2.8x v18 500 steps). Neu can giu ngan sach: cat grounding don le (synth 1200 / real-ui 792 / train3d 600 = 2592 row, 0% DONE) thi mix ve ~5240 row va steps ~933.
