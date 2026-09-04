# paper2 脱敏研究历史

> **HISTORICAL ONLY / NON-ACTIONABLE。** 本文件主体是截至 2026-08-31 的压缩研究
> 历史，末尾仅补充后续 review 与 Round 5 closure 的索引。其中“当前”“下一步”
> “冻结顺序”均指各自历史时点，已经被 `CURRENT.md` 的 Round 5 closure 覆盖；不得
> 据此运行实验。本历史文件本身不授权任何 research round；Round 6 P0 已完成，当前
> 终态与生命周期锁见 `CURRENT.md`。

本文件用于追溯研究决策，不是原始会话导出，也不是科学证据。权威状态必须以当前
Git、源码、正式 artifacts 和 `CURRENT.md` 为准。

## 1. 方向起点：Proof-Carrying SPICE

最初目标是：允许任意外部 transient simulator 产生候选轨迹与证书，再由较小的独立 checker 在声明的离散 MNA 语义下验证局部存在唯一性。系统愿景强调 producer 可以是 ngspice、Xyce、松容差/低精度求解器、FastSPICE 或学习型代理，而 checker 不信任其内部 Newton/Jacobian/终止条件。

## 2. 文献红队后第一次收缩

文献审计确认以下内容已有强先例：

- Krawczyk/interval Newton；
- transistor-level DC interval verification；
- validated ODE/DAE 的严格轨迹包围与初值集合传播；
- proof-carrying producer/certificate/checker 架构；
- verified sparse linear algebra 与 factor verification；
- Verilog-A 解析/代码生成/普通导数生成。

因此 `Proof-Carrying SPICE` 被降为系统愿景，不能作为“首次提出”的 headline。

## 3. 当时的主线：BlockStamp-Cert

主线收缩为：对 fixed-step Backward Euler nonlinear transient MNA，利用两类结构：

1. **device-local stamp locality**；
2. **block-lower-bidiagonal temporal Jacobian structure**。

目标是在严格区间语义下，不显式形成全 slab inverse/operator，而通过可验证的 block recurrence 计算 Krawczyk/interval inclusion 所需 operator action，并相对 component-matched pointwise/dense verified baselines 获得可归因的 runtime、memory、certificate-size 或 certification Pareto 优势。

## 4. 已完成的研究步骤

### Step 001 — Literature and Novelty Gate

- 核验 DATE 2019 等 DC interval prior art；
- 检索 validated ODE/DAE、AMS formal verification、proof-carrying computation、verified sparse algebra、Verilog-A compilation；
- 结论：Research Opportunity PASS，但不是 Paper Candidate。

### Step 002 — Experimental Protocol

冻结 B0–B5、Stage 0–8、结果目录、随机种子、重复次数、失败样本保留和 end-to-end accounting。该文档是实验协议，不是实验结果。

### Step 003 — Formal Soundness Contract

将 Claim S 拆为：

- `S-fixed`：固定 incoming state 下的局部唯一离散根；
- `S-param`：incoming interval 中每个状态对应各自唯一的局部离散根。

明确了局部唯一性、outgoing projection、组合条件与 TCB 边界。后续评审发现：proof operator `C` 的可逆性需要显式加入定理前提；现有 A5 尚未闭合该漏洞。

### Step 004 — Theorem Prior-Art Closure

进一步确认：parameterized Krawczyk、initial-set propagation、verified factor witness 不是 headline novelty。后续阶段审计还识别了 block-Krawczyk、interval banded/cyclic-reduction 与 factorized verified-computation 等高威胁近邻。

### Step 005 — Baseline Defect Canary

构造弱电导病态 MNA，展示小 residual 与大 forward error 可以分离。状态严格限定为：

`PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`

它不证明成熟 SPICE 中该问题普遍发生。

### Step 006 — Selective Recovery Contract

定义 dependency-safe recovery：失败 slab 重算后，只有新 outgoing enclosure 被下一 slab 的 cached incoming assumption 包含时才允许复用后缀；否则从首次 containment failure 起重新检查。

## 5. 截至当时的实现 canary

- `paper2/experiments/interval_backend.py`：Decimal-based binary64 interval canary；不是最终 rigorous backend。
- `paper2/experiments/devices/stamps.py`：diode 与受限 Level-1 NMOS interval stamps；跨工作区间 fail closed。
- `paper2/experiments/recovery.py`：一维 interval containment recovery canary。
- `paper2/experiments/generate_numerical_defects.py`：解析 motivation artifact；当前 float32/float64 只是标签，checker verdict 仍未真实执行。

## 6. 正式评审历史

- `review_round1.md`：指出 S-param 量词、recovery 依赖、器件分支、B2 公平性和 TCB 缺口。
- `response_round1.md`：完成 S-fixed/S-param 收缩、Stage-0 arithmetic/device canary、baseline-defect canary 与 recovery contract。
- `review_round2.md`：指出 Decimal transcendental 不足以支撑严格 soundness、device oracle common-mode risk、baseline-defect generator 仍是解析表、BlockStamp/B2 尚未出现。
- 一个无研究增量的阶段性技术评估曾错误进入 reviewer-round 链；其有用结论已移至 `paper2/research/notes/stage_assessment_before_ccfb_review.md`。
- `review_round3.md`：按强 CCF-B 标准重新评估，确认方向本身具有 CCF-B 上限，但 Paper Candidate 仍未通过。
- `review_round4.md`：随后记录 M0/M1 implementation canary 的进展及进入 M2 前仍未
  通过 Paper Candidate 的判断。Round 5 最终结论见 `CURRENT.md` 与
  `paper2/steps/009_m2_result_gate.md`。

## 7. 当时的研究事实

1. 问题定义和 non-claims 已较清楚。
2. 当时最大数学阻断项是 `C` 的可逆性与最终 operator 定义。
3. 当时最大实现阻断项是缺少真正 directed-rounded arithmetic backend 与完整 BE MNA
   microkernel。
4. 当时最大创新性阻断项是 BlockStamp recurrence 尚未实现，无法判断是否只是标准
   block forward substitution。
5. 当时最大实验阻断项是 B2-strong、dense slab、BlockStamp 和 nonlinear transient
   probe 都尚未出现。
6. 当时状态仍是 **Research Opportunity / Paper Candidate FAIL-UNVERIFIED**。

## 8. 当时冻结的后续顺序（历史，禁止执行）

1. 修正 `C` 可逆性 theorem/contract；
2. 实现 rigorous directed-rounding backend；
3. 实现 R/C/source/diode 的 fixed-step BE MNA；
4. 实现 BlockStamp operator recurrence + dense-equivalence oracle；
5. 实现 B2-strong；
6. 跑 component ladder；
7. 跑 diode-RC + 3-stage ring oscillator 最小 probe。

在这些门禁通过前，不扩张到 SRAM、BSIM、通用 Verilog-A、第二 producer 或工业大规模网表。

## 9. Round 5 closure note

Round 5 已于 2026-09-04 结束。权威终态只记录在 `CURRENT.md` 和 Step 009；本历史文件
不授权新的算法设计、probe、实验或 clean replay。

## 10. Review Round 5 与 P0 intake 索引

- Round 5 artifact commit：`e04011003e519510b52fe2b954e3fdf43ac2bc46`。
- 最新 reviewer input：`paper2/responce_from_reviewer/review_round5.md`，commit
  `1aeb372386e5df2682d90578222c716b9ee42cc2`。
- Review 维持当前 BlockStamp recurrence `ARCHIVED`、`W=FAIL-CANARY`、`D/E=STOP`、
  Paper Candidate=`FAIL-UNVERIFIED`，并建议 Round 6 先做 A/B 机制重选。
- 用户随后只授权 Round 6 P0 全文先例审计与三选一门禁；执行权限以 `CURRENT.md` 为准，
  不得从本历史索引推导实验、原型或 P1 授权。

## 11. Round 6 P0 closure note

- A 类核验 10 篇、B 类核验 11 篇高相关全文；逐篇公式证据见
  `paper2/research/round6_mechanism_prior_art.md`。
- A 的 affine/doubleton/zonotope/history 表示与可靠压缩、B 的 circuit rank-one
  interval update 与 verified factor/residual reuse 均被强先例覆盖。
- Step 010 最终输出 `ARCHIVE-PAPER2`；没有选择机制、实现原型、运行实验或授权 P1。
- 本条仅是历史索引；权威状态和后续执行权限仍以 `CURRENT.md` 为准。
