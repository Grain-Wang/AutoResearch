# 016 CoVoL Closure

最终状态：`ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`。本文件是 CoVoL 当前状态的唯一科学解释；机器可读版本为 [`covol_closure.json`](../artifacts/covol/covol_closure.json)。旧 artifact 保留历史原貌，由 closure manifest 显式 supersede，不得单独解释为当前授权。

## 1. 原任务

原任务研究自动图像 caption 中局部实体或深度关系错误是否损害图文 metric-depth 候选，并尝试在冻结的纯视觉候选 `D0` 与图文候选 `D1` 之间做区域选择。该自动-caption问题没有在 004-A 中被直接检验，当前结论不得外推到自然 caption 错误、其他语言深度模型或任意 fallback router。

## 2. 实际 diagnostic 输入

004-A 使用的不是 automatic caption。`build_interventions.py` 从 NYUv2 official-train 的 GT class、instance mask 与 median metric depth 构造确定性短关系模板。100 张图、59 个 scene clusters 各有四个 family、每族三个固定 template variants，共 1200 行。`semantic_preserving-v0` 与 clean 完全相同，v1/v2 是固定规则改写；机器 parser 验证了模板 predicate，但没有验证人类语义等价性、自然度或无歧义性。

Round 9 建议的双人盲审没有执行：根目录 `AGENTS.md` 禁止新增人工标注和开放式人评，除非用户改变授权。仓库不伪造这项证据，最终限制固定为 `human_naturalness=NOT_ASSESSED`。

## 3. 预注册判据

004-A 要求至少一个 conflict family 的 region AbsRel degradation cluster-bootstrap 95% CI 下界大于 0，同时规则定义的 semantic-preserving family CI 包含 0。统计单位为 scene cluster，bootstrap 为 10,000 次。该判据是项目停止门禁，不是等价性检验，也不是直接的 `conflict - control` estimand；它不能证明一个很小的控制效应具有实践意义。

## 4. 观测结果

在 released TR2M 单模型、NYUv2 training-only diagnostic 上，region AbsRel degradation 为：

| Family | Point | 95% cluster-bootstrap CI |
| --- | ---: | ---: |
| semantic-preserving | 0.001156 | [0.000579, 0.001777] |
| target deletion | 0.000055 | [-0.001198, 0.001109] |
| local entity conflict | 0.001620 | [0.000195, 0.002903] |
| depth relation conflict | 0.000806 | [0.000347, 0.001298] |

控制 CI 不含 0，故预注册状态为 `STOP_H_SENSITIVITY`。逐 family text-only 审计进一步发现 target-deletion F1 `1.000`、local-entity F1 `0.662`，均超过 0.60 上限；aggregate macro-F1 0.488 不能再单独判定无模板泄漏。

探索性 matched `family - semantic_preserving` postmortem 不改变 STOP：local-entity point `+0.000464`、95% CI `[-0.000927, 0.001740]`；depth-relation point `-0.000350`、95% CI `[-0.000680, -0.000036]`，family-level Holm-adjusted p 均为约 `0.1215`。这些数字只描述冻结 CSV，未预注册 smallest effect size 或等价区间。

## 5. 可支持结论

唯一支持的核心结论是：

> 在该确定性 GT 关系模板 corpus 上，released TR2M 的误差变化不具备预注册的冲突特异性；因此当前 GT-template probe 与 Main-PR 研究路径停止。

还可支持以下审计事实：004-A 的输入、模型权重、逐行结果与 cluster bootstrap 已由 hash 锁定；目标区域的 median pixel mass 约 8.55%，cluster-balanced mean 约 10.72%；效应的实践尺度、逐 template 异质性与单 cluster 影响已在探索性 practical-effect artifact 中报告。

## 6. 不可支持结论

- 不支持“自动 caption 局部错误问题整体被否定”或“所有语义等价 caption 都会损害深度”。
- 不支持人类看来 semantic-preserving、自然或无歧义；这些性质未评估。
- 不支持 local-entity 正向变化来自语义冲突而非 family-specific 模板线索。
- 不支持 D0 fallback、Claim-F、Claim-M、Main-PR 优于任何 baseline，相关真实结果有意不存在。
- 不支持跨模型、跨数据集、official-test、部署安全或因果主张。
- 探索性 direct difference、Holm p 值、相对效应或 leave-one-cluster-out 诊断不能反向恢复预注册主张。

## 7. 停止动作

[`covol_scientific_gate.json`](../artifacts/covol/covol_scientific_gate.json) 将 `step004_b`、`step005`、`step006`、`step007`、`step008`、`official_test` 与 `second_dataset_recovery` 全部设为 false，绑定原始 sensitivity CSV/summary SHA256，并固定 exit code 4。现有二数据集恢复、KITTI oracle 审计和 Step005 cache 入口必须同时通过历史 Step003 gate 与最终 scientific gate；伪造 Step003 PASS 也不能绕过 STOP。

旧 `diagnostic_intervention_audit.json` 中的 `PENDING_INDEPENDENT_PRECISION_AND_H_SENSITIVITY`、历史 `RECOVER_TWO_REAL_DATASETS` 与 Step005–014 协议由 closure manifest 标记为 superseded/archived，不覆盖历史文件。CoVoL exclusive queue、数据恢复、模型训练、official test 和新 GPU 科学任务均不再授权。

## 8. 可复用资产

- 1200-row GT-template corpus 的生成器、machine predicate audit 与独立 parser；它们只能复用于规则模板研究。
- released TR2M/Depth Anything/DINOv2/CLIP 权重 provenance、可续跑 004-A runner 和逐行 sensitivity CSV。
- cluster-balanced bootstrap、practical-effect、matched postmortem 与逐 family text-artifact 工具。
- full-crop risk、cache lineage、feature firewall 与候选路由协议代码；它们是通用实现资产，不是 CoVoL 算法证据。

在已准备 NYUv2、TR2M repository、checkpoint 与 encoder cache 的同环境中，004-A 的重放入口为：

```bash
python -m paper1.experiments.covol.run_sensitivity_diagnostic \
  --authorization paper1/artifacts/covol/step003_authorization.json \
  --interventions paper1/data/covol/diagnostic_interventions.jsonl \
  --eval-protocol paper1/configs/covol/depth_eval_protocol_v1.json \
  --release-audit paper1/results/covol/tr2m_release_audit.json \
  --nyuv2-labeled <repo-local-nyuv2-labeled-mat> \
  --tr2m-root <repo-local-tr2m-source> \
  --tr2m-checkpoint <repo-local-tr2m-checkpoint> \
  --depth-checkpoint <repo-local-depth-anything-checkpoint> \
  --cache-root <repo-local-encoder-cache> \
  --output <repo-local-replay-csv> \
  --summary-output <repo-local-replay-summary> \
  --device cuda:2 --restart
```

重放前后必须分别核对 corpus、checkpoint、runner、CSV 与 summary 的 closure SHA；环境目标为 Python 3.12.13、PyTorch 2.5.0+cu121、CUDA 12.1 和 A800 80GB。设备编号或运行时字符串变化会改变 summary 字节，不得伪称逐字节复现。
