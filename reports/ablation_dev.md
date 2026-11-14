# Ablation T02 tren gold set dev (tu gan, B = 20)

Gold: 56 anh dev, 33 anh loi. Khong ap review cua nguoi. Nguong RECAPTURE z >= 3.0.

| Cau hinh | Recall@20 | Precision@20 | Ty le RECAPTURE (96 anh) | Loi bat duoc trong top-20 theo loai |
|---|---|---|---|---|
| PoC day du (4 tin hieu) | 20/33 = 0.61 (95% CI 0.44–0.75) | 20/20 = 1.00 (95% CI 0.84–1.00) | 46% | blur 5/13 · dark 6/6 · glare 4/4 · compression 5/10 |
| bo `blur` | 20/33 = 0.61 (95% CI 0.44–0.75) | 20/20 = 1.00 (95% CI 0.84–1.00) | 33% | blur 1/13 · dark 6/6 · glare 4/4 · compression 9/10 |
| bo `dark` | 20/33 = 0.61 (95% CI 0.44–0.75) | 20/20 = 1.00 (95% CI 0.84–1.00) | 40% | blur 8/13 · dark 0/6 · glare 4/4 · compression 8/10 |
| bo `glare` | 20/33 = 0.61 (95% CI 0.44–0.75) | 20/20 = 1.00 (95% CI 0.84–1.00) | 38% | blur 7/13 · dark 6/6 · glare 0/4 · compression 7/10 |
| bo `compression` | 19/33 = 0.58 (95% CI 0.41–0.73) | 19/20 = 0.95 (95% CI 0.76–0.99) | 32% | blur 8/13 · dark 6/6 · glare 4/4 · compression 1/10 |
