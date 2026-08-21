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

## 结果出现前允许的主张

只允许写“提出待验证的语义增量假设、冻结候选协议和预注册门禁”。不得写“证明”“显著提高”“安全”“首次”或“优于”。

## 结果出现后的更新规则

每个主张必须链接到结果文件、统计单位、随机种子与 95% CI。若对应差异 CI 跨 0，组件不得列为贡献；若只在合成干预成立，主张必须限定为合成干预，不能外推自然 caption 错误。
