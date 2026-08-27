# 研究步骤审计表

## 唯一当前状态

- CoVoL：`ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`。自然 automatic-caption 问题未被 004-A 直接检验。
- SR-VEP：`PARKED_BEFORE_CANARY / NO_REPOSITORY_SCIENTIFIC_RESULT`。
- BAR-Depth：`SELECTED_RESEARCH_OPPORTUNITY / V1_INVALID_METRIC_ALIGNMENT / V2_REPAIR_REQUIRED / NOT_PAPER_CANDIDATE`。
- 当前唯一允许的科学动作：保持其余合同不变，运行 positive median scale-only v2 repair canary。

| 步骤 | 状态 | 当前证据 | 允许的下一出口 |
| --- | --- | --- | --- |
| 001 主线范围 | BAR-DEPTH-ORACLE-CANARY | 用户显式换题；只授权 200 图 oracle canary | DIODE/model provenance |
| 002 CoVoL 最近邻 | ARCHIVED-HISTORICAL-AUDIT | 原 depth/routing 最近邻保留 | 无 CoVoL 出口 |
| 003 GT-template 干预数据 | ARCHIVED / HUMAN-NATURALNESS-NOT-ASSESSED | 100 图、59 clusters、1200 rows；machine/parser pass；逐 family artifact 检出 | 无；旧 pending 状态由 closure supersede |
| 004 GT-template 缺陷 probe | STOP-H-SENSITIVITY | released TR2M；semantic-preserving CI 不含 0 | 无 004-B；只允许重放/审计 |
| 005 冻结专家 | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | validator helper 仅有合成 QA | 无，不训练 D0/D1 |
| 006 语义增量 | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | Claim-F 真实结果有意不存在 | 无 |
| 007 公平基线 | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | 历史 baseline 合同 | 无 |
| 008 Main-PR canary | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | Claim-M 真实结果有意不存在 | 无 |
| 009 组件消融 | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | 未执行 | 无 |
| 011 CoVoL claim language | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | 最终科学解释由 Step016 唯一给出 | 无 |
| 012 Q-GeoRoute | PARKED | 与四个情感候选共同进入 Gate017，未获选择 | 无 |
| 014 Main-PR objective | ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED | 只有 scalar/helper QA | 无 |
| 015 二数据集恢复 | SUPERSEDED_BY_H_STOP | 三候选为历史 `PENDING_SOURCE_ACCESS`，不是 coverage FAIL | 无，不再获取 CoVoL 数据 |
| 016 CoVoL closure | DONE | 全局 scientific gate、探索性 postmortem、practical effects、逐 family artifact control | 只允许 hash validation/replay |
| 017 历史机会门禁 | SUPERSEDED-SELECTION | 当时选择 SR-VEP；未运行即被显式换题取代 | 无并行出口 |
| 018 BAR-Depth oracle v1 | INVALID-METRIC-ALIGNMENT | 2400 rows；raw gate STOP 被 metric-domain clipping 作废 | 不得解释 GO/STOP |
| 019 v1 metric audit | DONE / INVALID-V1 | outdoor 157,380 clipped valid pixels；mean AbsRel 766.05 | 只允许 scale-only v2 repair |

## CoVoL 执行安全

[`covol_scientific_gate.json`](../artifacts/covol/covol_scientific_gate.json) 绑定原始 sensitivity CSV/summary SHA，并将 `step004_b`、`step005`、`step006`、`step007`、`step008`、`official_test` 与 `second_dataset_recovery` 全部设为 false。任何现有 CoVoL 下游入口必须先通过该 gate，再检查历史 Step003 authorization；当前固定以 exit code 4 停止。

`diagnostic_intervention_audit.json` 的 pending 字段不覆盖。唯一当前状态由 [`covol_closure.json`](../artifacts/covol/covol_closure.json) 解释。human equivalence/naturalness 因仓库禁止新增人工标注而没有评估，不能用规则 parser 代替。

## 当前不能声称

- 不能把 GT-template 单模型 probe 外推成 automatic-caption 普遍结论。
- 不能把探索性 difference-in-difference、显著性或 template slice 用来恢复 CoVoL。
- 不能声称 BAR-Depth oracle headroom、router 可学习性或 latency 增益已成立。
- 不能称任何当前方向为 Paper Candidate、强 CCF-C 论文或完成的算法贡献。

## 记录要求

新方向每个 gate 必须记录 source revision/许可、文件 hash、fold/seed、数据泄漏检查、命令、运行时、完整切片、失败结果和 `GO/ITERATE/STOP`。结果不足以支持或否定 claim 时只保留 Research Opportunity，不提前进入 Paper Build。
