# paper1：BAR-Depth 研究主线与历史方向归档

## 当前状态

CoVoL-Depth 已归档为 **`ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`**。004-A 使用的是 NYUv2 GT entity/instance/median-depth 构造的确定性短模板，不是 automatic captions。semantic-preserving 控制也稳定变化，因此证据只支持“当前 GT-template probe 与 Main-PR 路径停止”，不支持“自动 caption 局部错误问题整体被否定”。004-B、公平 D0/D1、Claim-F、Claim-M、Main-PR、第二数据集恢复与 official test 均不得继续。

用户于 2026-08-27 明确重新选择 **BAR-Depth：预算自适应区域深度细化**，状态为
`GO_ORACLE_ROUTABILITY_UNVERIFIED / ROUTER_KILLER_GATE_PENDING /
NOT_PAPER_CANDIDATE`。DIODE validation 200 图 v2 canary 的 headroom、25% budget
capture 和 primary reduction 均以 scan-cluster CI 通过；这只证明区域收益存在且集中，
尚未训练 router，也不主张加速。此前选中的 SR-VEP 在任何 canary 或数据获取前被
停放，没有仓库自有科学结果。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [BAR-Depth 候选定义](ideas/candidates/02_budget_adaptive_regional_depth.md)
3. [Oracle canary 协议](steps/018_bar_depth_oracle_canary.md)
4. [v1 metric-domain 审计](steps/019_bar_depth_v1_metric_audit.md)
5. [v2 repair 协议](steps/020_bar_depth_oracle_canary_v2.md)
6. [v2 oracle 结果](steps/021_bar_depth_oracle_canary_v2_result.md)
7. [历史 Research Opportunity Gate](steps/017_research_opportunity_gate.md)
8. [CoVoL 最终 closure](steps/016_covol_closure.md)
9. [执行状态表](steps/README.md)
10. [最新 Round-9 审稿意见](responce_from_reviewer/review_round9.md)

## 执行边界

CoVoL 原依赖链继续由全局 scientific gate 停止。BAR-Depth 当前唯一允许的科学动作
是“官方 DIODE validation/模型锁定 → 200 图 oracle utility 枚举 → 冻结 GO/STOP”。
v1 因非法 metric-domain clipping 不产生科学 GO/STOP；fixed-range v2 已通过 oracle
gate。当前下一步只允许同预算 killer heuristics 与 scan-held-out router probe，不建设
多尺度通用框架，也不进入完整 Paper Build。SR-VEP 不并行执行。

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
- 只能在冻结 DIODE-200 / DAv2-S / fixed-range v2 合同内声称 oracle headroom 集中；
  不能声称 router 可学习、实际加速、跨数据集增益或达到 Paper Candidate/强 CCF-C。
- 不能把 QA、协议、hash、GPU availability 或代码量写成科学贡献。
