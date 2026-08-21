# 011 Claim Language Revision

## 已完成替换

| 旧表述 | 当前表述 | 原因 |
| --- | --- | --- |
| counterfactual value | controlled caption intervention 下冻结候选的 empirical advantage | 未建立结构因果模型 |
| safe depth routing | selective/fallback-aware candidate routing | 尚无风险界或逐样本保证 |
| 错误语言危害是新发现 | 既有研究已知的研究动机 | arXiv:2404.08540 与 Iris 已覆盖 |
| 细粒度文本/语义原子是创新 | 最近邻已有机制 | CapDepth 已覆盖 |
| 冻结视觉+语言校准是创新 | 最近邻已有机制 | arXiv:2601.01457 与 TR2M 已覆盖 |
| 通用 advantage gate 是创新 | 必须与 L2D/SelectiveNet 比较 | 两专家选择本身并不新 |
| cross-fitting/正交残差是创新 | 标准统计学习组件的任务化使用 | DML 与 Orthogonal Statistical Learning 已覆盖 |
| CVaR/coverage control 是创新 | 标准尾部风险与选择预测组件的任务化使用 | CVaR optimization、Learn then Test 与近期 general risk control 已覆盖 |

## 两个独立主张

| 主张 | 允许的最强表述 | 唯一支持门禁 | 失败动作 |
| --- | --- | --- | --- |
| Claim-F（科学） | 文本—区域语义在控制视觉难度和候选差异后具有任务有效的增量预测信息 | `C-B AUROC >= 0.03` 且 paired CI 下界 >0；同时 C 相对 B 的 retention–CVaR Pareto hypervolume 差值 CI 下界 >0 | 删除语义增量与自然部署外推 |
| Claim-M（方法） | orthogonalized、clean-constrained tail-risk router 优于相同输入和风险目标的标准方法 | Main 相对 same-feature、same-objective、same-budget `Risk-L2D-C` 的 hypervolume 差值 CI 下界 >0，并通过两数据集/held-out 条件 | 删除算法贡献；不得用 Claim-F 代替 |

## 结果出现前允许的主张

只允许写“提出待验证的 Claim-F/Claim-M、冻结候选协议和预注册门禁”。不得写“证明”“显著提高”“安全”“首次”或“优于”。cross-fitting、orthogonalization、CVaR 和 coverage control 不得单独列为新颖性。

## 结果出现后的更新规则

每个主张必须链接到结果文件、统计单位、随机种子与 95% CI。若对应差异 CI 跨 0，组件不得列为贡献；若只在合成干预成立，主张必须限定为合成干预，不能外推自然 caption 错误。Claim-F 成立而 Claim-M 失败时，只允许报告语义可预测性发现，不得声称提出了更优 router。
