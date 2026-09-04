# 研究步骤审计表

本目录维护研究步骤的状态、依赖、证据、实验命令、随机种子、环境、产物路径以及
`GO/ITERATE/STOP` 决策。文档完成只表示规格已冻结，不表示对应定理、实现或实验已经
通过。

> **Round 5 CLOSED。** 本页记录已完成步骤及历史门禁，不是 Round 6 执行计划；未经
> 用户另行明确授权，不得运行新实验、clean replay 或新机制 probe。Step 009 与当前
> `next_round_gate.json` 是 Round 5 终态依据。

## 当前状态

| Step | 内容 | 状态 | 主要未关闭门禁 |
| --- | --- | --- | --- |
| 001 | 文献与 novelty 初筛 | `CLOSED / REFRAME-SYSTEM` | 高威胁近邻已完成 Round 5 所需闭环；当前算法 novelty 未建立。 |
| 002 | 完整实验协议 | `EXECUTED / ROUND-5-CLOSED` | 冻结 M2 已执行；本协议不授权新的实验 round。 |
| 003 | S-fixed/S-param soundness contract | `SPECIFIED / M0 PASS-CANARY` | 已固定 `C=M^{-1}`；rigorous arithmetic、restricted BE MNA 和负例回归达到 canary 门槛，但 theorem 仍以 TCB 前提为条件。 |
| 004 | 定理级先例闭环 | `REFRAME-SYSTEM / COMPLETE` | 当前 recurrence 是标准 verified block solve；adaptive verified step/slab selection 也有直接高威胁先例。 |
| 005 | baseline defect canary | `PASS-CANARY` | float32/float64 producer、独立测试参考与真实 checker verdict 已分离；diode/ring producer probes 已完成。 |
| 006 | selective recovery contract | `SPECIFIED / REPLAY-UNVERIFIED` | 标量 containment 规则已明确；多维 digest/hash replay 和端到端 fallback 成本后置。 |
| 007 | BlockStamp operator specification | `CLAIM-I IMPLEMENTATION-CANARY-PASS / M1 REFRAME-SYSTEM` | 12-cell dense-action canary 已通过；当前 recurrence 不作为算法 headline。 |
| 008 | M0/M1/M2 evidence gate | `M2 COMPLETE / SUPERSEDED-BY-009` | 注册 M2 的 W 正信号已由 Step 009 的 pointwise contraction baseline 复核。 |
| 009 | M2 结果与 contractive-interface killer gate | `W FAIL-CANARY / D,E STOP` | contractive pointwise 支配或追平六实例 fixed/adaptive slab；algorithm novelty 未建立。 |

## 当前机器证据

- `numerical_defect_cases.csv` + manifest：24 个实际 residual-stopped float32/float64
  负例均由 checker 返回 `UNKNOWN`，0 false accept；严格阈值对照一步到根并 `ACCEPT`。
- `rigorous_backend_summary.json`：400,056 attempted、400,044 supported、12 structured
  unsupported、0 containment violation；八项操作各 50,000 random + 7 edge。
- `mna_canary.json`：RC 与 diode-RC 各 100 步全部 `ACCEPT`；1,800 Jacobian samples
  0 violation；17 negative cases 0 false accept。
- `operator_canary.json`：12 个 grid cells 共 2,400 个 nonsingular cases（含 24 个
  nonzero-width interval RHS）全部包含独立 dense exact coordinate hull；0 violation；
  额外 1 个 singular case 为 `UNSUPPORTED`。最大绝对 inflation 为
  0.1321725812626729，因此 Claim W 仍未成立。
- `b2_fairness.json`：`PASS / B2-STRONG-COMPONENT-MATCHED`；共享 hashes 完整。
- `minimal_probe.csv` + manifest：2250/2250 rows；原注册规则 `W=PASS`、`D/E=STOP`；
  2250 个整轨配置 verdict 全部为 `UNKNOWN`。
- `interface_contraction_canary.json`：pointwise contraction 在 6/6 实例提升旧 B2，且没有
  fixed slab 或 largest-first adaptive policy 得到更长前缀。
- `next_round_gate.json`：`M1 REFRAME-SYSTEM`、`W KILLER-BASELINE-CANARY-FAIL`、
  `Paper Candidate FAIL-UNVERIFIED`。所有当前 JSON 仍记录 `dirty_worktree=true`。

## Round 5 终止规则（不是执行顺序）

1. 保持 M0 全量回归；任何 false accept 或 containment failure 都触发 `STOP-S` 并使后续
   结果失效。M0 canary 成功不能写成无条件 theorem。
2. 当前 recurrence、device path、固定 slab 与 adaptive-largest-first 均不得作为算法
   headline；它们已被先例或 killer baseline 覆盖/解释。
3. 不对当前方法执行 clean replay 或更大实验。
4. 当前算法方向归档，只保留 restricted certificate-system 原型事实。任何新机制、
   canary 或根本转向均属于未授权的后续 round，必须等待用户另行明确指令。

当前整体状态为 `Research Opportunity / Paper Candidate FAIL-UNVERIFIED`。升级为
`Pre-Paper Candidate` 必须满足 Step 008 的联合门禁；协议、proof skeleton 或单次 canary
不能替代 novelty、主方法和 killer-baseline 证据。复现命令见 Step 008 与顶层 README。
