# 008 Canary Decision

## Status

`PENDING`。本步骤只汇总冻结结果，不允许新增 trial、改阈值或换聚合口径。

## Claim-F

证据只来自 Step 006。AUROC 与 policy hypervolume 双门通过才标为 `SUPPORTED-INTERNAL`；任一失败即 `UNSUPPORTED`。仅 structured errors 通过时必须写成 `SUPPORTED-STRUCTURED-ONLY`。

## Claim-M

证据只来自 Main vs same-feature Risk-L2D-C：

- clean gain retention ≥80%；
- 相对 always-D1 worst-of-3 regret 降低 ≥50%；
- NYUv2/KITTI internal-test 的 Pareto hypervolume 增量 95% CI 下界均 >0；
- held-out captioner 与 held-out error family 方向一致；
- region boundary artifact 未否定最终 gate 实现。

未显著优于 Risk-L2D-C 时，Claim-M 标为 `UNSUPPORTED`，不得把 cross-fitting/CVaR 的组合命名成新算法贡献。

## Natural-error relevance

每个 dataset×captioner×error predicate 至少 30 个 verified natural errors 才做显著性结论。样本不足或 predicate precision <0.95 时只能报告描述统计，不能声称真实部署鲁棒性。

## Paper Candidate Gate

只有 H-fallback-defect、Claim-F、Claim-M、第二 backbone 重复和最新近邻审计全部通过，才能升级。若只在合成错误上成立，最多保留为受控鲁棒性 Research Opportunity。
