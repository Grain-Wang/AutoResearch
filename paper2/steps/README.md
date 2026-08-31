# 研究步骤审计表

本目录维护研究步骤的状态、依赖、证据、实验命令、随机种子、环境、产物路径以及
`GO/ITERATE/STOP` 决策。文档完成只表示规格已冻结，不表示对应定理、实现或实验已经
通过。

## 当前状态

| Step | 内容 | 状态 | 主要未关闭门禁 |
| --- | --- | --- | --- |
| 001 | 文献与 novelty 初筛 | `GO / BOUNDED` | 递推公式冻结后仍需补 block-Krawczyk、interval cyclic reduction 与 factorized verified-computation 高威胁近邻。 |
| 002 | 完整实验协议 | `SPECIFIED` | B2-strong/B3/B5、完整公平性 manifest、component ladder 和 nonlinear transient 主结果尚未完成。 |
| 003 | S-fixed/S-param soundness contract | `SPECIFIED / M0 PASS-CANARY` | 已固定 `C=M^{-1}`；rigorous arithmetic、restricted BE MNA 和负例回归达到 canary 门槛，但 theorem 仍以 TCB 前提为条件。 |
| 004 | 定理级先例闭环 | `ITERATE` | 通用 Krawczyk/S-param/factor novelty 已关闭；需围绕 Step 007 的精确 recurrence 继续审计。 |
| 005 | baseline defect canary | `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED` | float32/float64 producer、exact oracle 与真实 checker verdict 已分离；仍需 nonlinear transient tolerance/precision probe。 |
| 006 | selective recovery contract | `SPECIFIED / REPLAY-UNVERIFIED` | 标量 containment 规则已明确；多维 digest/hash replay 和端到端 fallback 成本后置。 |
| 007 | BlockStamp operator specification | `CLAIM-I IMPLEMENTATION-CANARY-PASS / M1 ITERATE` | 12-cell dense-action canary 已通过；recurrence-specific novelty、device-aware mechanism 和效率仍未解决。 |
| 008 | `008_next_round_gate.md`：M0/M1/M2 evidence gate | `M0 PASS-CANARY / M1 ITERATE / M2 NOT-STARTED` | B2-strong、完整 fairness hashes、component ladder 和 matched nonlinear probe 阻断升级。 |

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
- `b2_fairness.json`：`B2-CANARY-ONLY / ITERATE`；verified-sparse B2-strong 未实现，
  `all_required_hashes_present=false`。
- `next_round_gate.json`：`Research Opportunity PASS`，`Paper Candidate
  FAIL-UNVERIFIED`。所有当前 JSON 均记录 `dirty_worktree=true`，尚非 clean replay。

## 当前执行顺序

1. 保持 M0 全量回归；任何 false accept 或 containment failure 都触发 `STOP-S` 并使后续
   结果失效。M0 canary 成功不能写成无条件 theorem。
2. 关闭 M1 的 recurrence-specific prior art 与 device/time-specific mechanism；当前
   Claim I 只说明测试实现包含 exact dense action，不说明 novelty 或 efficiency。
3. 实现 verified-sparse B2-strong，并补齐 candidate、tube、backend、semantics、scaling、
   ordering、factor、线程和硬件的完整共享 hashes。
4. 执行 `dense-slab generic -> device-local pointwise -> temporal-only ->
   temporal+device` component ladder，分别判断 Claim I/W/D/E。
5. 仅在 B2 fairness 可判定后运行 diode-RC 与 3-stage ring 的未筛选 M2 网格；
   composition、recovery、第二 producer、SRAM/BSIM/Verilog-A 均后置。

当前整体状态为 `Research Opportunity / Paper Candidate FAIL-UNVERIFIED`。升级为
`Pre-Paper Candidate` 必须满足 Step 008 的联合门禁；协议、proof skeleton 或单次 canary
不能替代 novelty、主方法和 killer-baseline 证据。复现命令见 Step 008 与顶层 README。
