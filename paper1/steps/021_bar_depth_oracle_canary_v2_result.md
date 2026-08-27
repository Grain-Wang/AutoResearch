# 021 BAR-Depth Oracle Canary v2 Result

## Decision

`GO_ORACLE_ROUTABILITY_UNVERIFIED / NOT_PAPER_CANDIDATE`。

v2 在与 v1 完全相同的 200 张 DIODE validation 图像、20 scans、Depth Anything
V2-S、3×4 actions 和 25% budget 上完成 2400 个逐区域评测。positive median
scale-only alignment 与 `[0.1, 350]m` prediction range 消除了 v1 的伪 `1e6m`
误差；原门禁的四项检查全部通过。

## Frozen gate result

| 检查 | Point estimate | Scan-cluster 95% CI | 阈值 | 结果 |
| --- | ---: | ---: | ---: | --- |
| positive headroom / base primary error | 10.42% | [7.03%, 13.15%] | lower ≥ 3% | PASS |
| oracle capture at 3/12 regions | 92.72% | [88.25%, 97.54%] | lower ≥ 70% | PASS |
| oracle primary-error reduction | 9.66% | [6.59%, 12.36%] | lower ≥ 2% | PASS |
| ordinary AbsRel relative degradation | −9.72% | [−13.33%, −5.51%] | point ≤ 1% | PASS |

负 degradation 表示普通 AbsRel 同时改善，不是 safety trade-off。全量执行 12 个
regions 的 primary reduction 为 8.84% [4.94%, 11.93%]；3-region oracle 更高，说明
部分区域动作有害，计算分配问题不是简单地“所有 patch 都做”。

## Domain stability

- indoor：headroom 10.36%，3-region capture 99.60%，primary reduction 10.32%；
- outdoor：headroom 10.45%，capture 88.62%，primary reduction 9.26%；
- 两域 point estimates 同方向，v1 中 outdoor 独占全局误差的病态已消失。

v2 有 613,463 / 138,659,335 valid pixels（0.4424%）触发预定义 prediction-depth
range clipping。该比例被显式报告；它产生有限的 350m prediction，不再制造 v1 的
无限/百万米伪误差。

## Router and novelty boundary

本结果只验证“可改善收益存在且集中”。它没有验证不读取 GT/patch output 时能否预测
utility。描述性 positive-utility capture 为：RGB gradient 56.69%、base-depth
gradient 72.90%、两者 rank-combination 72.30%。未 bootstrap 的净 primary reduction
诊断分别为 4.97%、6.54%、6.62%，低于 oracle 9.66%，但 base-gradient 已很强。

因此最强反方意见是：2021 content-adaptive patch selection 或简单 base-gradient
Top-K 可能已经恢复大部分收益，新 learned router 的空间不足以构成算法论文。下一门禁
必须用 scan-held-out cross-fitting 比较 random、RGB edge、base-depth edge、2021
content-adaptive selection、uncertainty 和 learned marginal-utility router，并报告真实
accuracy–latency Pareto。未超过这些 killer 前，不能升级 Paper Candidate。

## Bound artifacts

- [`oracle_canary_summary_v2.json`](../results/bar_depth/oracle_canary_summary_v2.json)
- [`oracle_patch_utility_v2.csv`](../results/bar_depth/oracle_patch_utility_v2.csv)
- [`oracle_raw_provenance_v2.json`](../results/bar_depth/oracle_raw_provenance_v2.json)
- [`oracle_cluster_bootstrap_v2.csv`](../results/bar_depth/oracle_cluster_bootstrap_v2.csv)
- [`diode_val_200_audit_v2.json`](../artifacts/bar_depth/diode_val_200_audit_v2.json)

summary 将 config、manifest、raw CSV、bootstrap、模型源码 commit、权重 SHA256 和
完整 BAR-Depth implementation SHA 绑定；共享 GPU timing 只作 diagnostic。
