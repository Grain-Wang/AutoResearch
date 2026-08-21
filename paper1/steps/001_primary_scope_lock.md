# 001 Primary Scope Lock

## Task

自动图像 caption 含局部、可机器验证的语义错误时，在两个冻结 metric-depth 候选之间逐区域选择，并在语言候选无经验收益的区域回退到纯视觉候选。

## Input

RGB 图像 `I`、自动 caption `c`、冻结纯视觉候选 `D0(I)`、冻结图文候选 `D1(I,c)`；训练期可用 metric-depth GT 构造区域经验优势，推理期不可用 GT。

## Primary Claim

| Claim | 状态 | 唯一证据 | 支持条件 |
| --- | --- | --- | --- |
| Claim-F：控制视觉难度与候选差异后，原始文本—区域语义仍有增量 advantage 预测力 | UNVERIFIED SCIENTIFIC HYPOTHESIS | Step 006 的 B-direct/C-direct/C-permuted scene-group OOF controls | C-direct−B-direct 与 C-direct−C-permuted 的 AUROC/HV scene-cluster CI 下界均 >0；Main-orth 不参与 |
| Claim-M：clean-retention/tail-regret router 优于获得相同 OOF experts 与合法 zC 特征的直接 defer 方法 | UNVERIFIED METHOD HYPOTHESIS | Step 007/008 与 Risk-L2D-C、regression、density-ratio、dense-coherence、LOO-uncertainty baselines 比较 | Main 相对每个 direct baseline 的两数据集 HV scene-cluster CI 下界均 >0 |

cross-fitting、orthogonal residualization、CVaR、clean constraint、dense defer、leave-one-out contribution teacher、continuous regression defer 和 frozen-expert post-hoc scoring 均已被先行工作覆盖，不能单独列为创新。

## Falsification

若 OOF 公平冻结 `D0/D1` 下的 fallback defect 不能稳定复现，则整个主线停止。若 Claim-F 任一 direct/permuted 门禁失败，撤回语义增量发现。若 Claim-M 不能显著优于任一 direct killer baseline，则撤回算法贡献，即使 Claim-F 成立也不得按 AGENTS.md 升级为算法 Paper Candidate；最多另行评估分析型普通 CCF-C 路径。Q-GeoRoute 只能在记录正式范围变更后作为新主线启动。
