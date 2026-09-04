# AutoResearch 当前接续状态

## 2026-09-04 Round 5 CLOSED（权威状态）

> Round 5 已结束。本文件不授权 Round 6，也不授权任何新实验、clean replay、扩矩阵
> 或新机制 probe。只有用户另行明确授权后才能开始新的 research round。下方所有旧
> 快照均为历史，不得覆盖本节或作为执行指令。

- 正式 Round 5 artifacts 记录生成时基线 commit
  `51351daa95f6f48cd97f27e639ed6b2d73260761` 和 `dirty_worktree=true`。这是不可回写
  的生成 provenance，不代表提交后 checkout 的 Git 状态；可移植 handoff 的 Git 身份
  由最终包含本文件的 commit 决定。
- 冻结 M2 已完成：450 warm-ups、2,250/2,250 measured rows；六个实例、
  `steps={100,300,1000}`、`slab={1,2,4,8,16}`、五 replicates、五 methods 均完整。
- 2,250 个配置级 checker verdict 全部为 `UNKNOWN`，0 `UNSUPPORTED`、0 confirmed
  false accept。1,800 个 primary rows 触发 whole-run strict fallback，0 个恢复为
  `ACCEPT`。
- 冻结规则相对旧 `device_local_pointwise_b2` 给出 `W=PASS`、`D=STOP`、`E=STOP`；
  但旧 B2 在接受一步后仍传播完整 producer tube，遗漏了“传播已接受 Krawczyk image”
  这一强简单 baseline。
- 新 `interface_contraction_canary.json` 覆盖全部六个 100-step 实例。contractive
  pointwise 的 prefix 相对旧 B2 为 `10->25, 1->13, 1->6, 1->8, 4->5, 1->6`；
  没有固定 slab 或 largest-first `{16,8,4,2,1}` policy 在任何实例击败它。
- Kearfott--Xing 1994、Immler 2018、Duff--Lee 2024 和 Lee 2025 已覆盖 verified
  adaptive step selection / splitting / Krawczyk path tracking 的一般算法形态。因此
  adaptive slab splitting 既无独立 novelty，也无当前 canary 增益。
- 当前机器门禁：`M0 PASS-CANARY`；`M1 REFRAME-SYSTEM`；`M2 ITERATE`；
  `W FAIL-CANARY`；`D/E STOP`；Paper Candidate `FAIL-UNVERIFIED`。仅有 blockers 为
  `ALGORITHMIC_NOVELTY_NOT_ESTABLISHED` 与
  `CLAIM_W_CONTRACTIVE_KILLER_CANARY_FAIL`。
- 新增/更新的核心实现是 contractive pointwise/fixed-slab/greedy prefix 测量、六实例
  canary runner、公共 workload 构造器、gate 逻辑及回归测试。科学解释见
  `paper2/steps/009_m2_result_gate.md`。
- 2026-09-04 回归：仓库级 Ruff 通过；95 个 Python 文件逐文件 Black check 通过；
  `paper2/tests` 94 项全部通过；gate 重生成且所有引用 artifact/source hashes 齐全。

当前算法 claim **不成立**。最强反方意见是：原 W 增益来自遗漏的 pointwise
contraction，而数值核心仍是标准 Krawczyk 与 verified block forward substitution；
adaptive partition 也已有直接先例。该结论保持不变，当前算法路线归档，只保留
restricted certificate-system 原型事实。任何新机制、算法设计、probe 或实验都属于
尚未授权的后续 round；本 handoff 的终点是等待用户指令。

---

## 历史快照：2026-09-02 component-ladder-v1

> **HISTORICAL / NON-ACTIONABLE。** 本节保留当时的状态语言；其中“当前”“下一阶段”
> 和 `M2=NOT-STARTED` 已被上方 Round 5 closure 覆盖，不得据此运行命令或继续研究。

- 分支 `paper2`，checkpoint 记录 commit `51351daa95f6f48cd97f27e639ed6b2d73260761`，
  `dirty_worktree=true`；九个相关源码 hash、config 与 backend 均与当前文件一致。
- 当时完成 round：`component-ladder-v1 / COMPLETE-CANARY / HOLD`。
- 冻结矩阵：6 workloads × `steps={100}` × `slab={1,2,4,8,16}` ×
  `replicate={0}` × 4 methods，共 120 项。
- `0000–0119` 全部存在且可解析；120/120 producer 为 100/100 steps；0 missing、
  0 duplicate、0 failed process、0 unsupported；120 个配置级 verdict 均为合法
  `UNKNOWN`。
- 30/30 matched groups 的 input、producer trace、candidate、tube、backend、semantics、
  scaling、ordering、factor 和 hardware hashes 全部一致。
- Pooled accepted step-slots：dense 457/3000 (15.23%)；B2 545/3000
  (18.17%)；temporal-only 457/3000；temporal+streamed 457/3000。
- Checker runtime 总和：dense 33.1439 s；B2 30.7220 s；temporal-only
  32.5126 s；temporal+streamed 32.6835 s。相对 dense 分别为 1.000×、1.079×、
  1.019×、1.014×；temporal+streamed 比 B2 慢 6.38%。只有一个 replicate，均为
  描述性数字。
- `temporal_only` 与 `temporal_device_blockstamp` 的 verdict、rate、prefix、margin 在
  30/30 组完全相同；后者仍遍历全局 assembled Jacobian，不是 direct device-stamp
  locality。certificate bytes 也未包含方法特有 witness，不能支持 size claim。
- 正式 artifacts：`results/blockstamp/component_ladder.csv`、
  `component_ladder.manifest.json`、`component_ladder.summary.json`、更新后的
  `b2_fairness.json`，以及 `next_round_gate.json`。
- 机器门禁：B2 strong ready=true、component ladder=PASS，但总状态 `ITERATE`；
  blockers 为 `PRIOR_ART_REFRAME_SYSTEM` 与 `MATCHED_NONLINEAR_M2_NOT_RUN`；
  `M2=NOT-STARTED`，Paper Candidate=`FAIL-UNVERIFIED`。
- Step 008 的后续 M2 是独立下一阶段：6 workloads × steps `{100,300,1000}` ×
  slabs `{1,2,4,8,16}` × 5 replicates × 5 methods = 2250 measured rows，另有 warmups。
  本轮没有启动它。

下方内容保留为历史接续记录；其中关于 B2/component artifacts 尚不存在的描述已经过期。

---

## 历史快照：2026-08-31

> **HISTORICAL / NON-ACTIONABLE。** 以下内容是 2026-08-31 的接续快照，其中所有
> “当前”“启动”“下一步”“复现”措辞只描述当时语境，不能覆盖文件顶部的 Round 5
> closure，也不授权执行任何命令。
>
> 当时有效项目：`paper2 / BlockStamp-Cert`。

### 当时的启动优先级（历史）

1. 完整读取根目录 `AGENTS.md`。
2. 用 `git status --short --branch`、当前源码、测试和 artifacts 核对本文件。
3. 本文件只是接续导航，不得替代机器证据。

### 当时的研究方向（历史）

- 分支与项目：`paper2`。
- 工作题目：**BlockStamp-Cert: Independently Checkable, Circuit-Structured Certificates for Discrete Nonlinear Transient Simulation**。
- 系统愿景：Proof-Carrying SPICE。
- 当时阶段：**Research Opportunity**；Opportunity Gate 为 PASS，Paper Candidate Gate 为 `FAIL-UNVERIFIED`。
- 核心问题：对固定步长 Backward Euler 离散的 nonlinear MNA 瞬态轨迹，能否利用 **device-local stamps + block-lower-bidiagonal temporal structure** 构造严格、独立且比 component-matched 通用逐点验证更高效的 certificate checker。

当时唯一可证伪的算法机会是：联合利用器件局部 stamp 与瞬态 MNA 时间带状结构，对 slab Krawczyk operator 做严格隐式递推，并在 component-matched baselines 下获得可归因的 runtime、memory、certificate-size 或 certification Pareto 优势。

以下内容不得作为 headline novelty：Krawczyk/interval Newton 本身、transistor-level DC interval verification、parameterized root enclosure、generic time-slab/initial-set propagation、verified LU/factor witness、通用 producer/certificate/checker 架构，以及 Verilog-A 解析、代码生成或普通自动微分。

### 当时的远程与评审状态（历史）

- 本轮上传已纳入远端基线 `7f5ee85`（`chore(paper2): remove paper1-specific ignore rules`），未覆盖远端提交。
- 正式评审链现保留 `review_round1.md` 至 `review_round4.md`；最后一份回应仍为
  `response_round3.md`。
- 历史阶段评估位于 `paper2/research/notes/`，不计入 reviewer round。
- 当时计划要求 clean independent replay；该计划已被 Round 5 closure 撤销，当前不授权
  replay。

### 当时已完成的工作（历史）

- 修正 soundness contract：`C` 固定为 checker 重建 midpoint operator `M` 的 exact-real inverse action；加入 `C=0, F(x)=x+2, X=[-1,1]` 反例与奇异算子 fail-closed 回归。
- 新增 MPFR 4.2.1、256-bit、显式 `RNDD/RNDU` 算术路径，覆盖 `add/sub/mul/div/exp/expm1/log/sqrt`。
- 冻结并实现 BlockStamp 递推 `U_0=VSolve(D_0,R_0)`、`U_k=VSolve(D_k,R_k-L_kU_{k-1})`，以 exact `Fraction` 稠密解作独立 action oracle。
- 新增固定拓扑 R/C/current-source/voltage-source/diode Backward Euler MNA、状态布局、history、point/interval residual 与 Jacobian，以及 dense B2 pointwise canary。
- numerical-defect generator 不再硬编码精度标签或 verdict：producer 实际执行 float32/float64 residual-stopped Newton，oracle 使用 exact `Fraction`，verdict 只来自 executable checker；CSV 配有 hash/provenance manifest。
- 文献威胁补入 Chen--Hashimoto block Krawczyk、Schwandt interval cyclic/block cyclic reduction 与 Frommer--Hashemi factorized Krawczyk。只有摘要或机构元数据级证据的条目均已标明，未虚构 theorem-level non-overlap。
- 新增 claim-separated gate runner；文档同步到 Steps 003/004/007/008、research direction、README 和 Round-3 response。

### 当时的机器证据（历史）

- `numerical_defect_cases.csv`：24 个未筛选松阈值配置全部零步 early-stop，exact root 不在 tube、forward error 为 1 V；checker 全部 `UNKNOWN`，0 false accept。manifest 中两项严格阈值控制均一步到根并 `ACCEPT`。
- `rigorous_backend_summary.json`：400,056 attempted，400,044 supported，12 structured unsupported；八项操作各 50,000 random + 7 fixed edge；0 containment violation。
- `mna_canary.json`：RC 与 diode-RC 各 100 步全部 `ACCEPT`；1,800 Jacobian samples 0 violation；17 negative cases 0 false accept。
- `operator_canary.json`：12 个 dimension/slab cells 共 2,400 nonsingular cases，含 24 个 nonzero-width interval RHS；recursive/dense exact-coordinate-hull containment 0 violation；额外 singular case 为 `UNSUPPORTED`。最大绝对 enclosure inflation 为 0.1321725812626729，不能支持 Claim W。
- `b2_fairness.json`：`ITERATE / B2-CANARY-ONLY`；verified-sparse B2-strong、完整共享 hashes 和 matched BlockStamp circuit path 尚未实现。
- `next_round_gate.json`：`M0 PASS-CANARY`；`Claim I IMPLEMENTATION-CANARY-PASS / M1 ITERATE`；`M2 NOT-STARTED`；`Paper Candidate FAIL-UNVERIFIED`。

### 当时的科学裁决（历史）

- 当时仍为 **Research Opportunity**，不是 Paper Candidate。
- Claim S 只有受限实现 canary 与条件式数学合同；不是完整 TCB 形式证明或 general-SPICE soundness。
- Claim I 的 exact-action containment canary 成立，但普通 block forward solve、block Krawczyk、interval cyclic reduction 和 factorization 都已有强先例；算法 novelty 尚未关闭。
- Claim W/D/E 当时均无证据；当时没有 less-wrapping、速度、内存、证书大小或端到端收益主张。
- numerical-defect 只支持静态线性动机；不能外推为成熟 SPICE 常见错误或 nonlinear transient 缺陷。

### 当时计划的后续动作（历史，禁止自动执行）

1. 获取并逐式核验三组高威胁先例全文，完成冻结 recurrence 的 theorem/operator matrix；若不存在非等价 device/time remainder mechanism，停止算法首创表述。
2. 实现真正 verified-sparse B2-strong，并让 B2 与 BlockStamp 共享 candidate、tube、backend、device/MNA semantics、scaling、ordering、factor、线程和硬件 hashes。
3. 只有 B2 fairness 可判定后，进入 diode-RC 与 3-stage ring 的 component ladder/M2；完整记录 generation、check、fallback、RSS 与 certificate bytes。不得先扩 SRAM、BSIM、Verilog-A 或大规模网表。

### 当时的停止与转向条件（历史）

- 若 BlockStamp 对 B2-strong/dense baseline 无稳定可归因优势，停止 Claim E 或降级为 restricted checker/system work。
- 若 pointwise verified checker 已足够便宜且 interface propagation 不构成问题，停止 slab headline。
- 任一 confirmed false accept、严格算术 containment 失败或 theorem counterexample 被 `ACCEPT`，立即停止 Claim S，修复后全量回归。
- 若成熟 SPICE 的自然错误很少，动机改为 `untrusted / approximate / accelerated producer`，不得声称“成熟 SPICE 经常错误”。

### 当时的复现与回归记录（历史，禁止自动执行）

当时从 `paper2/` 运行：

```bash
python3 -m experiments.generate_numerical_defects --output results/blockstamp/numerical_defect_cases.csv --seed 17
python3 -m experiments.run_rigorous_backend --samples 50000 --seed 20260831
python3 -m experiments.run_mna_canary --steps 100 --step-size 1e-05
python3 -m experiments.run_operator_canary --cases-per-grid 200 --dense-canary-cases 2 --seed 20260831
python3 -m experiments.run_next_round_gate
ruff check .
black --check .
pytest tests/
```

当时验证环境为 Python 3.12.3、MPFR 4.2.1。当时完整回归：仓库级 Ruff 通过、54 tests passed、70 个仓库 Python 文件逐文件 Black check 通过、artifact/source hash audit 通过、`git diff --check` 通过。当时机器上的 Black 多文件 worker 在完成并报告全部文件 unchanged 后未正常退出，因此格式判定使用逐文件 `--check`。

### 当时的文件读取规则（历史）

- 当时建议继续研究时读取本文件、源码/测试/结果、
  `paper2/research/research_direction.md` 和最新正式 review；该建议不授权当前继续研究。
- 只有需要追溯 paper2 决策时才读取 `.codex/handoff/TRANSCRIPT.md`。
- `paper2/research/notes/stage_assessment_before_ccfb_review.md` 是历史阶段技术笔记，不是正式 reviewer round，也不能覆盖当前事实。
