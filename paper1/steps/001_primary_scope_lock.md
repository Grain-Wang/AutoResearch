# 001 Primary Scope Lock

## Task

自动图像 caption 含局部、可机器验证的语义错误时，在两个冻结 metric-depth 候选之间逐区域选择，并在语言候选无经验收益的区域回退到纯视觉候选。

## Input

RGB 图像 `I`、自动 caption `c`、冻结纯视觉候选 `D0(I)`、冻结图文候选 `D1(I,c)`；训练期可用 metric-depth GT 构造区域经验优势，推理期不可用 GT。

## Primary Claim

在控制视觉难度、候选差异和残差幅度后，交叉拟合的文本—区域语义增量优势估计结合 clean-gain 约束的尾部 regret 优化，能够比标准 two-expert learning-to-defer 更好地选择 `D0/D1`。

## Falsification

若错误 caption 的正 regret 不能在 NYUv2/KITTI 同时复现；或加入语义特征后 held-out AUROC 增量小于 `0.03` 或其 95% CI 下界不大于 0；或在保留至少 80% clean gain 时不能相对原始 `D1` 降低至少 50% worst-of-3 regret并显著优于最强公平基线，则主张被否定，不升级为 Paper Candidate；Q-GeoRoute 只能在记录该决定后作为新主线启动。
