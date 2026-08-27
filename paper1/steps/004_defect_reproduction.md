# 004 Defect Reproduction

## Status

`004-A AUTOMATED-VALIDITY-PASS / PENDING-MODEL-EXECUTION; 004-B BLOCKED`。该步骤拆成两个不能混写的假设。NYUv2 diagnostic 已有 100 图、59 clusters、1200 local rows且 machine-check 100%；独立规则解析器的分层样本为 100/100 predicate pass。held-out-template text-only macro-F1 为 0.488，自动 surface-form 为 1200/1200，但这不估计人类自然度。TR2M core 与 relative-depth checkpoint 已锁定哈希，可续跑 batch runner 已实现；DINOv2/CLIP 的运行时哈希和实际 004-A 执行仍待完成，因此还没有 H-sensitivity 结果。004-B 额外依赖新的两真实数据集 authorization、公平 D0/D1 与真实实体级 OOF cache。shared CUDA canary 不构成上述任一输入。

## 004-A H-sensitivity

问题：同一个语言模型 `D1` 从 predicate-clean caption 切换到 corrupted caption 时是否显著退化？

- 可使用锁定的 TR2M released checkpoint；
- 比较 `R_i(D1_corrupt)-R_i(D1_clean)`；
- 只证明 caption sensitivity，不证明 fallback necessity；
- 结果必须标注 `diagnostic-only`，不得写成 `D1 vs D0` regret。

当前 diagnostic predicate-clean/corrupted captions、predicate precision、held-out-template text artifact control 和自动 surface-form audit 已就绪；released core checkpoint 和 Depth Anything ViT-S checkpoint 的 revision、字节数与 SHA256 见 [`tr2m_release_audit.json`](../results/covol/tr2m_release_audit.json)。runner 每完成一图原子写入 12 行、只接受完整且与 frozen corpus identity 一致的续跑 CSV，并在结束时锁定 CLIP/DINO 权重哈希。结果只能标为 NYUv2 training-only diagnostic。

## 004-B H-fallback-defect

数据集组合必须读取新的 Step003 authorization：只有 NYUv2 与 `015` 顺序中首个真实候选 full-pilot coverage 都通过时才进入正式双数据集缺陷复现。当前 frozen KITTI source 已停止；VKITTI2 只作 synthetic structured auxiliary analysis，不能替代真实候选。

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

H-fallback-defect 仅当至少一个局部错误族在新 authorization 冻结的两个真实 internal-test 数据集上，其 cluster-mean regret 95% CI 下界均大于 0 才通过。VKITTI2、null_diagnostic 和 global swap 不进入该门禁。

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
