# 001 Primary Scope Lock

## Current branch state

`STOPPED_BY_H_SENSITIVITY_CONTROL`。004-A 在 100 张 NYUv2 official-train diagnostic 图像上发现两个冲突族有正向 region AbsRel sensitivity，但 semantic-preserving 对照同样稳定退化（95% CI `[0.000579, 0.001777]`），违反预注册的冲突特异性条件。该上游否证结果停止整个 CoVoL 主张；第二真实数据集、Step003 authorization 或更多模型实验不能自动恢复本方向。

## Task

自动图像 caption 含局部、可机器验证的语义错误时，在两个冻结 metric-depth 候选之间逐区域选择，并在语言候选无经验收益的区域回退到纯视觉候选。

## Input

RGB 图像 `I`、自动 caption `c`、冻结纯视觉候选 `D0(I)`、冻结图文候选 `D1(I,c)`；训练期可用 metric-depth GT 构造区域经验优势，推理期不可用 GT。

## Primary Claim

| Claim | 状态 | 唯一证据 | 支持条件 |
| --- | --- | --- | --- |
| Claim-F：控制视觉难度与候选差异后，原始文本—区域语义仍有增量 advantage 预测力 | STOPPED_BY_H_SENSITIVITY_CONTROL | Step 006 结果有意不存在；上游 004-A 对照已否定继续执行的前提 | 不在 CoVoL 范围内恢复；新问题需另做范围与机会门禁 |
| Claim-M：固定 clean utility 下的局部尾部 regret router 优于获得相同 OOF experts 与合法 zC 特征的直接 defer 方法 | STOPPED_BY_H_SENSITIVITY_CONTROL | Step 007/008 结果有意不存在；上游 004-A 对照已否定继续执行的前提 | 不在 CoVoL 范围内恢复；不得用协议或代码结果替代算法证据 |

cross-fitting、partial residualization、CVaR、clean constraint、dense defer、language-guided frozen-expert routing、leave-one-out contribution teacher、continuous regression defer 和 frozen-expert post-hoc scoring 均已被先行工作覆盖，不能单独列为创新。唯一待否证差异由 [014 objective spec](014_objective_and_algorithm_spec.md) 定义。

## Falsification

004-A 的 semantic-preserving 对照已触发预注册停止规则，因此后续 H-fallback-defect、Claim-F 和 Claim-M 不再执行。该负结果不得通过事后修改对照、阈值或 family 选择来改写。Q-GeoRoute 或任何新方向只能在记录正式范围变更、更新最近邻并重新通过 Research Opportunity Gate 后启动。
