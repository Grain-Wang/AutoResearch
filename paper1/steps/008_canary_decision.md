# 008 Canary Decision

## Status

`PENDING`。本步骤只汇总冻结结果，不允许新增 trial、改阈值或换聚合口径。

## Claim-F

证据只来自 Step 006 的固定宽度 `B-direct/C-direct/C-permuted-global/C-permuted-local` controls；Main-PR 不参与。`C-direct−B-direct` 与两类 `C-direct−C-permuted` 的 AUROC 和 policy hypervolume cluster-CI 双门都通过才标为 `SUPPORTED-INTERNAL`；任一失败即 `UNSUPPORTED`。仅 structured errors 通过时必须写成 `SUPPORTED-STRUCTURED-ONLY`。

## Claim-M

正式 local datasets 由 Step 003 的 `dataset_fallback_decision.yaml` 唯一冻结；不得在结果出现后于 KITTI 与 VKITTI2 之间择优报告。

证据来自 Main 与全部 direct killer baselines：

- dev 上只在 clean gain retention ≥80% 的 thresholds 中选择 CVaR 最低者，并冻结该 threshold；
- 相对 always-D1 worst-of-3 regret 降低 ≥50%；
- internal-test 上，Main-PR 相对 Risk-L2D-C、TIGER-style LOO、Regression-L2D、DR-PostHoc-L2D、Dense-Coherence-L2D 和 LOO-Uncertainty-Router 的 `CVaR@Ret≥0.80` 与 `WorstOf3@Ret≥0.80` 风险差 scene/drive-cluster CI 上界均 <0；
- Pareto hypervolume 只作为 secondary sensitivity，不再单独支持 Claim-M；
- held-out captioner 与 held-out error family 方向一致；
- region boundary artifact 未否定最终 gate 实现。
- 正式 D0/D1 的信号显著超过 image-only twins 与 shuffled-caption expert controls；
- caption dropout、corruption augmentation、multi-caption ensemble 和 consistency filtering 均未支配 Main Pareto。

任一 direct 或 robust expert baseline 缺失/不败时，Claim-M 标为 `UNSUPPORTED`，不得把 cross-fitting/CVaR/region routing 的组合命名成新算法贡献。

## Natural-error relevance

每个 dataset×captioner×error predicate 的独立 scene 数与 error 数必须达到 power-analysis 冻结值；“30 个错误”不再作为无功效依据的通用阈值。power <0.80、annotation coverage 失败或 predicate precision <0.95 时只能报告描述统计，不能声称真实部署鲁棒性。

## Paper Candidate Gate

只有 OOF H-fallback-defect、Claim-F、Claim-M、全部 direct/robust controls、第二 backbone 重复和最新近邻审计全部通过，才能升级。若只在合成错误上成立，最多保留为受控鲁棒性 Research Opportunity。

若 Claim-F 成立而 Claim-M 失败，预注册降级为“语义条件增量可预测性”分析方向：它可以另行评估普通 CCF-C 价值，但不满足 AGENTS.md 的算法型 Paper Candidate Gate，不进入当前 Paper Build。
