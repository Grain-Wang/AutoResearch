# Response to Review Round 9

感谢 Round 9 指出 004-A 构造有效性与结论范围不一致。我们接受核心判断：当前材料不是 Paper Candidate；004-A 只能停止确定性 GT-template probe 与 Main-PR 贡献路径，不能外推为 automatic-caption 问题整体被否定。

## 已完成的归档与科学解释收缩

新建 [`016_covol_closure.md`](../steps/016_covol_closure.md)，按“原任务、实际输入、预注册判据、观测结果、可支持结论、不可支持结论、停止动作、可复用资产”八节固定最终表述。README、范围锁、旧 Idea 和 Step004 已同步声明：实际输入由 NYUv2 GT class/instance/median-depth 生成，不是 automatic captions；semantic-preserving v0 与 clean 完全相同，v1/v2 是固定规则改写；human equivalence/naturalness 未评估。

Round 9 建议的 100 条双人盲审没有执行。根目录 `AGENTS.md` 默认禁止新增人工标注、众包和开放式人评，而用户没有改变该授权。我们没有用 AI 或 parser 冒充人类评分；closure 永久保留 `human_naturalness=NOT_ASSESSED`，也不把控制失败解释为模型语义不变性失败。

Step005–009、011、014 已统一标为 `ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED`；Step015 的历史 `RECOVER_TWO_REAL_DATASETS` 标为 `SUPERSEDED_BY_H_STOP`。旧 `diagnostic_intervention_audit.json` 不被覆盖，其 pending 状态由唯一 closure manifest 显式 supersede。

## 全局停止门禁与 closure lineage

新增 [`covol_scientific_gate.json`](../artifacts/covol/covol_scientific_gate.json)，绑定原始 004-A CSV 与 summary SHA256，将 `step004_b/step005/step006/step007/step008/official_test/second_dataset_recovery` 全部设为 false，固定 `STOPPED_BY_H_SENSITIVITY` 与 exit code 4。二数据集候选审计、KITTI oracle 审计和 Step005 cache CLI 现在先通过该最终 gate，再检查历史 Step003 authorization；测试证明伪造 Step003 PASS 也不能绕过 STOP。

新增 closure validator 与测试。机器可读 [`covol_closure.json`](../artifacts/covol/covol_closure.json) 统一绑定 scientific gate、干预 validity、TR2M release audit、004-A rows/summary、逐 family artifact、探索性差值、实践效应与 closure note 的 hash，并将 raw/licensed corpus 作为 repo-local、可重建、可选存在的外部输入验证。删除或篡改 tracked artifact 会使 validator 非零退出。

## 实验解释补充

逐 family one-vs-rest held-template-out 审计已替代 aggregate-only PASS。结果为：semantic-preserving F1 0.285/AUROC 0.517、target deletion 1.000/1.000、local entity 0.662/0.704、depth relation 0.002/0.185；target deletion 与 local entity 超过 0.60，状态为 `FAMILY_ARTIFACT_DETECTED`。CSV 同时报告 caption character length、token count 与相对 clean 的 token edit distance。

已在冻结 1200-row CSV 上完成明确标记为 `EXPLORATORY_POSTMORTEM` 的 matched family-minus-semantic-control 分析：10,000 次 cluster bootstrap、cluster sign-flip p、Holm correction、standardized cluster effect 与 per-template rows 均已输出，且 artifact 固定 `cannot_reverse_preregistered_stop=true`。family-level local-entity 差值约 +0.000464，CI 跨 0；depth-relation 约 -0.000350，family-level Holm-adjusted p 约 0.1215。该分析没有预注册 equivalence margin，不能恢复 confirmatory claim。

practical-effect artifact 报告 target pixel mass、clean region AbsRel、absolute/relative region degradation、full-image degradation、median/IQR/p95 与最大 leave-one-cluster-out influence。target region median 约占 full valid pixels 的 8.55%，cluster-balanced mean 约 10.72%。这些数字只用于尺度与异质性解释。

## 重新选题

[`017_research_opportunity_gate.md`](../steps/017_research_opportunity_gate.md) 以 2024–2026 最近邻、公开数据、单张 A800 probe 和量化 STOP 同时审计五个非等价候选。Q-GeoRoute 只作为其中一项，并因偏离情感主线与复现成本保持 PARKED。只有 **SR-VEP：Source-Residualized Video-Grounded Emotion Preference** 被标记为 `SELECTED_RESEARCH_OPPORTUNITY`。

SR-VEP 针对 EmoPrefer/MER-Prefer 中近期报告的 generator-style confound：content-blind source/length probe 可接近 audio-visual judge，而普通 ODIN content head 接近 chance。候选算法用 same-generator、coarse-emotion-matched cross-video negatives 识别 AV evidence margin，再对 generator-pair/length/style nuisance 做严格折外 residualization，并优化 worst-generator-pair risk。它与 EAPO 的 error augmentation/ensemble、MJ1 的 grounded verification 和普通 ODIN 均有可验证的决策差异。

但这只是 Research Opportunity，仓库尚未独立复现外部缺陷。当前唯一允许的下一动作是获取/hash-lock 官方 annotation tables 与许可文本并运行 CPU 五折 shortcut canary；source recovery <95%、content-blind 与对称 Omni LoRA 差 >5 pp、或后续 correct-match AUROC ≤0.65 均会停止方向。没有算法 claim 成立，也未达到 Paper Candidate。

## 验证

- 新增全局 scientific gate、closure validator、逐 family artifact、postmortem 与对应 pytest。
- CoVoL 下游 action 在当前 gate 上均固定退出 4；旧 Step003 PASS 不能绕过。
- Ruff、Black 和完整 `paper1/tests` 的最终结果在本轮提交前统一复核并记录。
