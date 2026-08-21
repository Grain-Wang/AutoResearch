# 001 Primary Scope Lock

## Task

自动图像 caption 含局部、可机器验证的语义错误时，在两个冻结 metric-depth 候选之间逐区域选择，并在语言候选无经验收益的区域回退到纯视觉候选。

## Input

RGB 图像 `I`、自动 caption `c`、冻结纯视觉候选 `D0(I)`、冻结图文候选 `D1(I,c)`；训练期可用 metric-depth GT 构造区域经验优势，推理期不可用 GT。

## Primary Claim

| Claim | 状态 | 唯一证据 | 支持条件 |
| --- | --- | --- | --- |
| Claim-F：控制视觉难度、候选差异和残差幅度后，文本—区域语义仍有增量 advantage 预测力 | UNVERIFIED SCIENTIFIC HYPOTHESIS | Step 006 A/B/C out-of-fold probe | C-B AUROC 增量 ≥0.03 且 95% CI 下界 >0；同时 retention–CVaR Pareto hypervolume 增量 CI 下界 >0 |
| Claim-M：orthogonalized、clean-constrained tail-risk router 优于获得相同语义特征和风险目标的标准 defer | UNVERIFIED METHOD HYPOTHESIS | Step 007/008 与 Risk-L2D-C 的同特征、同容量、同搜索预算比较 | 两数据集 Pareto hypervolume 增量 95% CI 下界 >0 |

cross-fitting、orthogonal residualization、CVaR 和 clean constraint 均是直接复用或任务化改写的标准组件，不能单独列为创新。

## Falsification

若公平冻结 `D0/D1` 下的 fallback defect 不能在 NYUv2/KITTI 同时复现，则整个主线停止。若 Claim-F 任一分类或策略效用条件失败，只撤回语义增量发现。若 Claim-M 不能显著优于 same-feature Risk-L2D-C，则撤回算法贡献，即使 Claim-F 成立也不得升级为 Paper Candidate。Q-GeoRoute 只能在记录正式范围变更后作为新主线启动。
