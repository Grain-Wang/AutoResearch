# AutoResearch 当前接续状态

更新时间：2026-08-31（Asia/Shanghai）

> **当前有效项目：paper2 / BlockStamp-Cert**
>
> 本文件只保存 `paper2` 分支的当前研究状态。不得从其他 paper 分支、旧项目或历史门禁推断本项目状态。事实优先级固定为：`AGENTS.md` > 当前 Git、源码、测试与实验产物 > 本文件 > `TRANSCRIPT.md`。

## 启动优先级

1. 完整读取根目录 `AGENTS.md`。
2. 用 `git status --short --branch`、当前源码、测试和 artifacts 核对本文件。
3. 本文件只是接续导航，不得替代机器证据。

## 当前研究方向

- 分支与项目：`paper2`。
- 工作题目：**BlockStamp-Cert: Independently Checkable, Circuit-Structured Certificates for Discrete Nonlinear Transient Simulation**。
- 系统愿景：Proof-Carrying SPICE。
- 当前阶段：**Research Opportunity**；Opportunity Gate 为 PASS，Paper Candidate Gate 为 `FAIL / UNVERIFIED`。
- 核心问题：对固定步长 Backward Euler 离散的 nonlinear MNA 瞬态轨迹，能否利用 **device-local stamps + block-lower-bidiagonal temporal structure** 构造严格、独立且比 component-matched 通用逐点验证更高效的 certificate checker。

当前唯一可证伪的算法机会是：联合利用器件局部 stamp 与瞬态 MNA 时间带状结构，对 slab Krawczyk operator 做严格隐式递推，并在 component-matched baselines 下获得可归因的 runtime、memory、certificate-size 或 certification Pareto 优势。

以下内容不得作为 headline novelty：Krawczyk/interval Newton 本身、transistor-level DC interval verification、parameterized root enclosure、generic time-slab/initial-set propagation、verified LU/factor witness、通用 producer/certificate/checker 架构，以及 Verilog-A 解析、代码生成或普通自动微分。

## 远程与评审状态

- 本轮上传已纳入远端基线 `7f5ee85`（`chore(paper2): remove paper1-specific ignore rules`），未覆盖远端提交。
- 正式评审链为 `paper2/responce_from_reviewer/review_round1.md` 至 `review_round3.md`；本轮综合回应为 `response_round3.md`。
- 历史阶段评估位于 `paper2/research/notes/`，不计入 reviewer round。
- 本轮生成的 JSON 保留生成时的 `dirty_worktree=true`，因此仍不能写成 clean independent replay；提交后的干净树独立重放尚待完成。

## 本轮已完成

- 修正 soundness contract：`C` 固定为 checker 重建 midpoint operator `M` 的 exact-real inverse action；加入 `C=0, F(x)=x+2, X=[-1,1]` 反例与奇异算子 fail-closed 回归。
- 新增 MPFR 4.2.1、256-bit、显式 `RNDD/RNDU` 算术路径，覆盖 `add/sub/mul/div/exp/expm1/log/sqrt`。
- 冻结并实现 BlockStamp 递推 `U_0=VSolve(D_0,R_0)`、`U_k=VSolve(D_k,R_k-L_kU_{k-1})`，以 exact `Fraction` 稠密解作独立 action oracle。
- 新增固定拓扑 R/C/current-source/voltage-source/diode Backward Euler MNA、状态布局、history、point/interval residual 与 Jacobian，以及 dense B2 pointwise canary。
- numerical-defect generator 不再硬编码精度标签或 verdict：producer 实际执行 float32/float64 residual-stopped Newton，oracle 使用 exact `Fraction`，verdict 只来自 executable checker；CSV 配有 hash/provenance manifest。
- 文献威胁补入 Chen--Hashimoto block Krawczyk、Schwandt interval cyclic/block cyclic reduction 与 Frommer--Hashemi factorized Krawczyk。只有摘要或机构元数据级证据的条目均已标明，未虚构 theorem-level non-overlap。
- 新增 claim-separated gate runner；文档同步到 Steps 003/004/007/008、research direction、README 和 Round-3 response。

## 当前机器证据

- `numerical_defect_cases.csv`：24 个未筛选松阈值配置全部零步 early-stop，exact root 不在 tube、forward error 为 1 V；checker 全部 `UNKNOWN`，0 false accept。manifest 中两项严格阈值控制均一步到根并 `ACCEPT`。
- `rigorous_backend_summary.json`：400,056 attempted，400,044 supported，12 structured unsupported；八项操作各 50,000 random + 7 fixed edge；0 containment violation。
- `mna_canary.json`：RC 与 diode-RC 各 100 步全部 `ACCEPT`；1,800 Jacobian samples 0 violation；17 negative cases 0 false accept。
- `operator_canary.json`：12 个 dimension/slab cells 共 2,400 nonsingular cases，含 24 个 nonzero-width interval RHS；recursive/dense exact-coordinate-hull containment 0 violation；额外 singular case 为 `UNSUPPORTED`。最大绝对 enclosure inflation 为 0.1321725812626729，不能支持 Claim W。
- `b2_fairness.json`：`ITERATE / B2-CANARY-ONLY`；verified-sparse B2-strong、完整共享 hashes 和 matched BlockStamp circuit path 尚未实现。
- `next_round_gate.json`：`M0 PASS-CANARY`；`Claim I IMPLEMENTATION-CANARY-PASS / M1 ITERATE`；`M2 NOT-STARTED`；`Paper Candidate FAIL-UNVERIFIED`。

## 科学裁决

- 当前仍为 **Research Opportunity**，不是 Paper Candidate。
- Claim S 只有受限实现 canary 与条件式数学合同；不是完整 TCB 形式证明或 general-SPICE soundness。
- Claim I 的 exact-action containment canary 成立，但普通 block forward solve、block Krawczyk、interval cyclic reduction 和 factorization 都已有强先例；算法 novelty 尚未关闭。
- Claim W/D/E 均无证据。当前没有 less-wrapping、速度、内存、证书大小或端到端收益主张。
- numerical-defect 只支持静态线性动机；不能外推为成熟 SPICE 常见错误或 nonlinear transient 缺陷。

## 下一原子动作

1. 获取并逐式核验三组高威胁先例全文，完成冻结 recurrence 的 theorem/operator matrix；若不存在非等价 device/time remainder mechanism，停止算法首创表述。
2. 实现真正 verified-sparse B2-strong，并让 B2 与 BlockStamp 共享 candidate、tube、backend、device/MNA semantics、scaling、ordering、factor、线程和硬件 hashes。
3. 只有 B2 fairness 可判定后，进入 diode-RC 与 3-stage ring 的 component ladder/M2；完整记录 generation、check、fallback、RSS 与 certificate bytes。不得先扩 SRAM、BSIM、Verilog-A 或大规模网表。

## 停止与转向条件

- 若 BlockStamp 对 B2-strong/dense baseline 无稳定可归因优势，停止 Claim E 或降级为 restricted checker/system work。
- 若 pointwise verified checker 已足够便宜且 interface propagation 不构成问题，停止 slab headline。
- 任一 confirmed false accept、严格算术 containment 失败或 theorem counterexample 被 `ACCEPT`，立即停止 Claim S，修复后全量回归。
- 若成熟 SPICE 的自然错误很少，动机改为 `untrusted / approximate / accelerated producer`，不得声称“成熟 SPICE 经常错误”。

## 复现与回归

从 `paper2/` 运行：

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

本轮验证环境为 Python 3.12.3、MPFR 4.2.1。最新完整回归：仓库级 Ruff 通过、54 tests passed、70 个仓库 Python 文件逐文件 Black check 通过、artifact/source hash audit 通过、`git diff --check` 通过。当前机器上的 Black 多文件 worker 在完成并报告全部文件 unchanged 后未正常退出，因此最终格式判定使用逐文件 `--check`。

## 历史文件读取规则

- 正常继续研究只读取本文件、当前源码/测试/结果、`paper2/research/research_direction.md` 和最新正式 review。
- 只有需要追溯 paper2 决策时才读取 `.codex/handoff/TRANSCRIPT.md`。
- `paper2/research/notes/stage_assessment_before_ccfb_review.md` 是历史阶段技术笔记，不是正式 reviewer round，也不能覆盖当前事实。
