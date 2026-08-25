# 004 Defect Reproduction

## Status

`BLOCKED-BY-003-CORPUS-AND-005`。该步骤拆成两个不能混写的假设。NYUv2 coverage PASS 只说明局部 oracle 可用；intervention corpus 尚未构建，因此 004-A 也没有可运行输入。004-B 还额外依赖公平 D0/D1 与实体级 OOF cache。shared CUDA canary 不构成上述任一输入。

## 004-A H-sensitivity

问题：同一个语言模型 `D1` 从 predicate-clean caption 切换到 corrupted caption 时是否显著退化？

- 可使用锁定的 TR2M released checkpoint；
- 比较 `R_i(D1_corrupt)-R_i(D1_clean)`；
- 只证明 caption sensitivity，不证明 fallback necessity；
- 结果必须标注 `diagnostic-only`，不得写成 `D1 vs D0` regret。

003 的 NYUv2 intervention corpus 与 predicate-clean/corrupted captions 就绪后才可运行本项；若正式范围仍未缩窄，结果只能标为单数据集 diagnostic。

## 004-B H-fallback-defect

数据集组合先读取 `dataset_fallback_decision.yaml`：只有 NYUv2 与 KITTI coverage 都通过时才进入正式双数据集缺陷复现。KITTI local coverage 失败时返回 `STOP_TWO_DATASET_CLAIM`；VKITTI2 只作 synthetic structured auxiliary analysis，不能替代 KITTI。

问题：corrupted `D1` 是否比独立训练、冻结且公平的 `D0` 更差？

$$
r_{i,v}=R_i(D1_{corrupt,v})-R_i(D0).
$$

运行前必须同时存在：

1. `expert_manifest.json` 中 D0/D1 checkpoint SHA256；
2. 两 expert 使用 Step 005 同构输入合同、相同 optimizer/updates/seeds；
3. `expert_stacking_plan.json` 与 `expert_cache_manifest.json` 通过 sequence/drive-cluster OOF 及实体文件 hash 审计；router-train 不含训练内 expert prediction；
4. `D1` 未见 corruption/router 数据。

缺任一项时脚本必须输出 `BLOCKED_MISSING_FAIR_EXPERT` 并退出非零。

H-fallback-defect 仅当至少一个局部错误族在冻结的 NYUv2+KITTI 两个 internal-test 数据集上，其 cluster-mean regret 95% CI 下界均大于 0 才通过。VKITTI2、null_diagnostic 和 global swap 不进入该门禁。

## Natural error motivation audit

对每个 dataset×captioner×predicate 分别报告：

- verified natural-error 的 scene/image 发生率与区间；
- `unverified_mention` 发生率；
- verified error 相对公平 D0 的 mean/worst/CVaR regret；
- 独立 scene 数或 error 数未达到 Step 003 power gate 时只作描述统计，不给显著性结论。

发生率与严重度必须分开。低发生率、高尾部风险可支持风险动机；高发生率但无 D0-relative regret 不支持候选路由。

## Expected artifacts

- `paper1/experiments/covol/run_defect_reproduction.py`
- `paper1/results/covol/sensitivity.csv`
- `paper1/results/covol/fallback_defect.csv`
- `paper1/results/covol/natural_error_prevalence.csv`
- 每行记录 dataset、image/scene ID、captioner revision、error family、expert SHA、seed 和 metric-spec version。
