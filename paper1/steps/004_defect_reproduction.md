# 004 Defect Reproduction

## Status

`004-A STOP_H_SENSITIVITY; 004-B STOPPED_BY_004-A`。该步骤拆成两个不能混写的假设。NYUv2 diagnostic 有 100 图、59 clusters、1200 local rows，machine-check 为 1200/1200；独立规则解析器的分层样本为 100/100 predicate pass。held-out-template text-only macro-F1 为 0.488，自动 surface-form 为 1200/1200，但这不估计人类自然度。锁定 TR2M、Depth Anything、DINOv2 与 CLIP 权重后，004-A 已完成 10,000 次 paired cluster bootstrap。两个冲突族有正向区域 AbsRel 信号，但 semantic-preserving 对照也稳定退化，违反预注册的特异性门槛。因此停止 CoVoL 问题主张，004-B 不再运行。

## 004-A H-sensitivity

问题：同一个语言模型 `D1` 从 predicate-clean caption 切换到 corrupted caption 时是否显著退化？

- 可使用锁定的 TR2M released checkpoint；
- 比较 `R_i(D1_corrupt)-R_i(D1_clean)`；
- 只证明 caption sensitivity，不证明 fallback necessity；
- 结果必须标注 `diagnostic-only`，不得写成 `D1 vs D0` regret。

diagnostic predicate-clean/corrupted captions、predicate precision、held-out-template text artifact control 和自动 surface-form audit 均已就绪；released core checkpoint、Depth Anything ViT-S、DINOv2 ViT-L 和 CLIP ViT-L/14 的 revision、字节数与 SHA256 见 [`tr2m_release_audit.json`](../results/covol/tr2m_release_audit.json) 与 [`sensitivity_diagnostic_summary.json`](../results/covol/sensitivity_diagnostic_summary.json)。runner 每完成一图原子写入 12 行、只接受完整且与 frozen corpus identity 一致的续跑 CSV。结果只能标为 NYUv2 training-only diagnostic。

预注册主指标 `REGION_ABS_REL_DEGRADATION` 的 cluster-balanced 结果如下：

| family | point | paired cluster-bootstrap 95% CI | 门禁解释 |
| --- | ---: | ---: | --- |
| semantic-preserving | 0.001156 | [0.000579, 0.001777] | CI 不含 0，控制条件失败 |
| target deletion | 0.000055 | [-0.001198, 0.001109] | 不支持稳定退化 |
| local entity conflict | 0.001620 | [0.000195, 0.002903] | 支持敏感性信号，但不具冲突特异性 |
| depth relation conflict | 0.000806 | [0.000347, 0.001298] | 支持敏感性信号，但不具冲突特异性 |

固定判据要求“至少一个冲突族 CI 下界大于 0，且 semantic-preserving CI 包含 0”。前半项满足，后半项失败，故 runner 返回 `STOP_H_SENSITIVITY`（科学停止退出码 4）。不能通过删除对照、改阈值、选择单个 variant 或只报告两个正向冲突族来挽救主张。当前最简解释是 released TR2M 对文本表面改写存在一般敏感性；该诊断没有证明局部语义冲突特异效应、D0 fallback 必要性或 router 价值。

可复现信息：100 图、1200 rows、59 clusters、bootstrap seed 按 family/metric 冻结；运行环境为 Python 3.12.13、PyTorch 2.5.0+cu121、CUDA 12.1、NVIDIA A800 80GB PCIe。逐行 CSV SHA256 为 `a2d45fe96581d3234aa41d62c2a63f3e793f705e56c6054e9c8c3818111db721`，summary SHA256 为 `e4a304b1e6c2d8db6b1b95a666fe7f9fb88e73c7200addc400aecb10b2ce4659`。

## 004-B H-fallback-defect

本步骤已由 004-A 的上游问题真实性门禁停止，不再因为取得新 Step003 authorization 而恢复。以下合同仅作为预注册记录保留。

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

## Artifacts

- `paper1/experiments/covol/run_sensitivity_diagnostic.py`
- `paper1/results/covol/sensitivity_diagnostic.csv`
- `paper1/results/covol/sensitivity_diagnostic_summary.json`
- `fallback_defect.csv` 与 `natural_error_prevalence.csv` 有意不存在，因为上游停止门禁禁止 004-B。
