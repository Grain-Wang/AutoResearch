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
| 区域/dense defer 是创新 | 直接算法基线 | DeferredSeg 已覆盖 pixel-wise defer 与 spatial coherence |
| 经验误差贡献教师是创新 | 直接算法基线 | MRUF 已使用 leave-one-out error increase 监督路由 |
| 连续 advantage defer 是创新 | 直接算法基线 | Regression with Multi-Expert Deferral 已覆盖连续损失与 two-stage defer |
| 冻结专家 post-hoc router 是创新 | 直接算法基线 | Density-Ratio Post-Hoc L2D 已覆盖冻结 expert scorer 与可调 threshold |
| 完整真实 caption | predicate-clean caption | oracle 只排除启用 predicates，不能证明完整 factuality |

## 两个独立主张

| 主张 | 允许的最强表述 | 唯一支持门禁 | 失败动作 |
| --- | --- | --- | --- |
| Claim-F（科学） | predicate-clean/错误条件下，原始文本—区域语义具有任务有效的增量预测信息 | 同模型/同目标 C-direct−B-direct 与 C-direct−C-permuted 的 AUROC/HV scene-cluster CI 下界均 >0 | 删除语义增量与自然部署外推 |
| Claim-M（方法） | clean-retention/tail-regret 决策过程优于相同 OOF experts、合法特征和预算的直接 defer 方法 | Main 相对 Risk-L2D-C 及四个 published-method adaptations 的 HV scene-cluster CI 下界均 >0 | 删除算法贡献；不得用 Claim-F 代替 |

## 结果出现前允许的主张

只允许写“提出待验证的 Claim-F/Claim-M、OOF 冻结候选协议和预注册门禁”。不得写“证明”“显著提高”“安全”“首次”或“优于”。上述统计组件与四类直接 routing 机制不得单独列为新颖性。

## 结果出现后的更新规则

每个主张必须链接到结果文件、scene/drive 数、图像数、随机种子与 cluster 95% CI。若对应差异 CI 跨 0，组件不得列为贡献；若只在合成干预成立，主张必须限定为可验证干预压力测试，不能外推自然 caption 错误。Claim-F 成立而 Claim-M 失败时，只允许报告语义可预测性发现，不得声称提出了更优 router，也不得进入 AGENTS.md 的算法 Paper Build。
