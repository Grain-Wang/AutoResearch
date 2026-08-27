# paper1：情感 MLLM 研究主线与 CoVoL 归档

## 当前状态

CoVoL-Depth 已归档为 **`ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`**。004-A 使用的是 NYUv2 GT entity/instance/median-depth 构造的确定性短模板，不是 automatic captions。semantic-preserving 控制也稳定变化，因此证据只支持“当前 GT-template probe 与 Main-PR 路径停止”，不支持“自动 caption 局部错误问题整体被否定”。004-B、公平 D0/D1、Claim-F、Claim-M、Main-PR、第二数据集恢复与 official test 均不得继续。

重新选题后，唯一选择的 Research Opportunity 是 **SR-VEP：Source-Residualized Video-Grounded Emotion Preference**，状态为 `DEFECT_CANARY_PENDING / NOT_PAPER_CANDIDATE`。它先检验 EmoPrefer/MER-Prefer judge 是否可通过 generator identity/length shortcut 接近 audio-visual judge，再尝试用 same-generator video matching、cross-fitted source residualization 与 worst-group pairwise optimization 恢复可验证的视频 grounding。当前只授权 CPU defect canary，尚无仓库自有科学结果或算法 claim。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [新 Research Opportunity Gate](steps/017_research_opportunity_gate.md)
3. [SR-VEP 候选定义](ideas/candidates/01_source_residualized_emotion_preference.md)
4. [CoVoL 最终 closure](steps/016_covol_closure.md)
5. [执行状态表](steps/README.md)
6. [最新 Round-9 审稿意见](responce_from_reviewer/review_round9.md)
7. [Round-9 回应](responce_from_reviewer/response_round9.md)

## 执行边界

CoVoL 原依赖链已被全局 scientific gate 停止。旧 Step003 authorization 即使被替换为 PASS，也不能绕过该门禁；Step004-B、005–008、official test 和数据恢复固定返回 exit code 4。SR-VEP 的执行顺序仅为“官方 annotation/许可审计 → CPU shortcut canary → grounded-signal canary → 最小 LoRA prototype”，任一量化门失败立即停止，不在 canary 前建设通用训练框架。

## CoVoL 科学事实与解释限制

training-only diagnostic 从 Step003 的 hash-linked 1000-row manifest 中稳定选择 100 图/59 clusters，生成四个 local families 各 300 行，共 1200 行。machine-check 为 1200/1200，独立规则 parser 分层抽取的 100/100 通过；这只验证规则模板合同。aggregate text-only macro-F1 为 0.488，但逐 family 审计检出 target deletion F1 1.000、local entity F1 0.662，状态为 `FAMILY_ARTIFACT_DETECTED`。自动 surface-form 1200/1200 通过，人类等价性/自然度仍为 `NOT_ASSESSED`。

004-A 的区域 AbsRel degradation 为：semantic-preserving `0.001156 [0.000579, 0.001777]`、target deletion `0.000055 [-0.001198, 0.001109]`、local entity conflict `0.001620 [0.000195, 0.002903]`、depth relation conflict `0.000806 [0.000347, 0.001298]`。预注册要求 semantic-preserving CI 包含 0，故状态为 `STOP_H_SENSITIVITY`。探索性 conflict-minus-control、Holm correction、practical effects 与 leave-one-cluster-out 诊断不能反向恢复 STOP，见 [closure](steps/016_covol_closure.md)。

真实 Step003 CPU gate 的历史状态为 `STOP_TWO_DATASET_CLAIM`：NYUv2 local-oracle feasibility 通过，当前冻结 KITTI source 未提供满足合同的 local depth/mask oracle。Cityscapes、ScanNet v2、Matterport3D 候选均为 `PENDING_SOURCE_ACCESS`，现在统一由 closure 标为 `SUPERSEDED_BY_H_STOP`，不再是活跃出口。

所有 CoVoL downstream 入口必须先验证 [global scientific gate](artifacts/covol/covol_scientific_gate.json)，再验证历史 [Step003 authorization](artifacts/covol/step003_authorization.json)。最终 scientific gate 优先，当前所有下游 action 固定 exit code 4。唯一 hash-linked 当前状态由 [closure manifest](artifacts/covol/covol_closure.json) 给出；旧 `diagnostic_intervention_audit.json` 的 pending 字段保留历史原貌，不再解释当前状态。

## 可复现检查

本机允许执行 Ruff、Black、Pytest、closure validator 与微型合成测试。受许可约束的 NYUv2/MER media、模型权重、环境与 cache 均保存在 Git 忽略的仓库子目录，不提交或重分发。

```bash
python -m paper1.experiments.covol.validate_covol_closure \
  --manifest paper1/artifacts/covol/covol_closure.json

python -m paper1.experiments.covol.scientific_gate \
  --action step005

python -m ruff check paper1
python -m black --check paper1
python -m pytest paper1/tests -q \
  --basetemp .local-deps/pytest-paper1
```

scientific-gate 的第二条命令必须返回 `STOPPED_BY_H_SENSITIVITY` 和 exit code 4；这表示安全停止，不是 QA 失败。004-A 的完整重放命令、锁定运行时和字节级限制见 [016 closure](steps/016_covol_closure.md)。

## 当前不能声称

- 不能声称 automatic-caption 问题已被 CoVoL diagnostic 普遍否定，也不能声称固定 paraphrases 有人类等价性或自然度。
- 不能声称已训练 CoVoL D0/D1、router，或已验证 Claim-F/Claim-M。
- 不能声称 SR-VEP 的外部 shortcut 数字已在本仓库复现、候选算法有效，或已经达到 Paper Candidate/强 CCF-C。
- 不能把 QA、协议、hash、GPU availability 或代码量写成科学贡献。
