# 008 Canary Decision

## Status

`STOPPED-BY-004-A-H-SENSITIVITY-CONTROL`。本步骤只保留冻结协议，不允许新增 trial、改阈值或换聚合口径。004-A 的 semantic-preserving region AbsRel degradation CI 不包含 0，已停止 CoVoL；新的第二真实数据集或 Step003 authorization 不能恢复 Claim-F/Claim-M。

## Claim-F

证据只来自 Step 006 的固定宽度 `B-direct/C-direct/C-permuted-global/C-permuted-local` controls；Main-PR 不参与。`C-direct−B-direct` 与两类 `C-direct−C-permuted` 的 AUROC 门和 dev-frozen constrained `CVaR/WorstOf3@Dev-LCB-Ret>=0.80` 门都通过才标为 `SUPPORTED-INTERNAL`；hypervolume 仅为 secondary。任一主门失败即 `UNSUPPORTED`。仅 structured errors 通过时必须写成 `SUPPORTED-STRUCTURED-ONLY`。

## Claim-M

正式 local datasets 由新的 Step003 authorization 和其 hash-linked coverage JSON 唯一冻结，必须包含 NYUv2 与 `015` 预注册顺序中首个通过的真实候选；当前 frozen KITTI source 不在授权数据集中。power 与结果表都必须保存 SHA256 和 dataset role。VKITTI2 固定为 synthetic structured auxiliary set，不得在结果出现后择优替代。

证据来自 Main 与全部 direct killer baselines：

- seeds `17/29/43` 各自产生 expert cache、router、dev threshold 与 internal-test outcome，不共享训练结果或 threshold；
- 每个 seed 在 dev 上对 21 个 thresholds 运行 10,000 次 cluster bootstrap；只在 one-sided 95% clean-gain retention LCB ≥80% 的 thresholds 中选择 cluster-balanced CVaR 最低者，并冻结该 threshold；
- 相对 always-D1 worst-of-3 regret 降低 ≥50%；
- internal-test 上先报告冻结 threshold 的 retention 点估计与 two-sided 95% cluster CI；Main-PR 点估计 `<0.80` 时返回 `STOP_TEST_RETENTION_VIOLATION`，不继续判 Claim-M PASS；
- internal-test 上，Main-PR 相对 Risk-L2D-C、TIGER-style LOO、Regression-L2D、DR-PostHoc-L2D、Dense-Coherence-L2D 和 LOO-Uncertainty-Router 的 `CVaR@Dev-LCB-Ret≥0.80` 与 `WorstOf3@Dev-LCB-Ret≥0.80` 风险差在三个固定 seed 各自的 paired cluster CI 上界均 <0，且三个 seed 的 point direction 一致；
- 主表使用 cluster-balanced estimand；image-weighted risk 只能作为 sensitivity；
- Pareto hypervolume 只作为 secondary sensitivity，不再单独支持 Claim-M；
- held-out captioner 与 held-out error family 方向一致；
- region boundary artifact 未否定最终 gate 实现。
- 正式 D0/D1 的信号显著超过 image-only twins 与 shuffled-caption expert controls；
- caption dropout、corruption augmentation、multi-caption ensemble 和 consistency filtering 均未支配 Main Pareto。

任一 direct 或 robust expert baseline 缺失/不败时，Claim-M 标为 `UNSUPPORTED`，不得把 cross-fitting/CVaR/region routing 的组合命名成新算法贡献。

## Frozen artifact lineage

每个 method×seed 的 operating point 必须由 dev artifact 唯一解析。artifact 至少绑定 raw outcome table、coverage grid、expert cache、metric-spec version、minimum-clean-gain artifact、method config 与 code commit 的实际 SHA256。internal-test evaluator 必须打开并重算这些 hash，拒绝裸 `threshold_index`、跨 seed threshold 或任何不匹配的 outcome table。

主 inference 的独立单位仍是 dataset-specific frozen cluster。三个训练 seed 是固定重复，各自对完整 clusters 做 paired bootstrap，左右方法复用相同 cluster 索引；逐 seed 报告 CI，跨 seed 仅报告 mean±sample SD，不生成 seed-population CI。训练 seed 与 bootstrap seed 必须分字段记录。

## Natural-error relevance

每个 dataset×captioner×error predicate 的独立 scene 数与 error 数必须达到 power-analysis 冻结值；“30 个错误”不再作为无功效依据的通用阈值。power <0.80、annotation coverage 失败或 predicate precision <0.95 时只能报告描述统计，不能声称真实部署鲁棒性。

## Paper Candidate Gate

只有 OOF H-fallback-defect、Claim-F、Claim-M、全部 direct/robust controls、第二 backbone 重复和最新近邻审计全部通过，才能升级。若只在合成错误上成立，最多保留为受控鲁棒性 Research Opportunity。

若 Claim-F 成立而 Claim-M 失败，预注册降级为“语义条件增量可预测性”分析方向：它可以另行评估普通 CCF-C 价值，但不满足 AGENTS.md 的算法型 Paper Candidate Gate，不进入当前 Paper Build。
