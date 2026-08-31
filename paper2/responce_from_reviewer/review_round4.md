# Review Round 4

## 1. 🎯 强CCF-B达标判定

- **当前状态**：未达标
- **核心差距**：本轮已经把严格算术、受限 BE MNA、可执行 Krawczyk checker 和 BlockStamp 块递推从计划推进到机器 canary，但尚未完成决定 CCF-B 录用的 `B2-strong + component ladder + diode-RC/ring matched M2`；同时，当前 formal contract 中用于证明 `C` 必须可逆的 `C=0` 反例存在代数错误，递推的新颖性也尚未完成 theorem-level prior-art closure。
- **高分录用潜力**：否（当前）。本轮进展使方向明显更接近可验证的 Paper Candidate，但现有证据只证明“一个受限实现目前能正确包围测试对象”，尚未证明 BlockStamp 是非平凡的新算法，也没有证明其相对强基线具有实际资源或认证能力优势。若 M2 在两个非线性 transient workload 上给出可归因的稳定信号，并完成理论修正与干净重放，则具备高分 CCF-B 潜力。

## 2. 🔄 改进效果评估

针对 `paper2/steps/` 和 `response_round3.md` 中的最新修改：

- ✅ **有效改进**：
  1. `experiments/rigorous_backend.py` 已用 MPFR 4.2.1、256-bit 精度和显式 `RNDD/RNDU` 实现 `add/sub/mul/div/exp/expm1/log/sqrt`。机器产物记录 400,056 个输入、400,044 个支持输入、12 个结构化 `UNSUPPORTED` 和 0 个 observed containment violation。与上一轮 Decimal canary 相比，这是真正改变 soundness 判断的实现进展。
  2. `experiments/mna/fixed_be.py` 已形成 R/C、独立电流源、独立电压源和 diode 的固定步长 BE residual、history、point Jacobian 与 interval Jacobian assembly；`mna_canary.json` 中 RC 与 diode-RC 各 100 步全部 `ACCEPT`，1,800 个 Jacobian sample 无发现 containment violation，17 个负例无 confirmed false accept。项目已不再停留在器件局部 stamp 层面。
  3. `steps/007_blockstamp_operator_spec.md` 冻结了唯一的 `M,D_k,L_k,R_k,U_k` 定义，将 Claim I、W、E、D 分离，并明确普通 block forward substitution 不是 novelty。该文档给出了递推 containment lemma、复杂度边界、fail-closed 条件和 component gate，技术叙事比上一轮清楚。
  4. `experiments/blockstamp_operator.py` 已实现 `VSolve`、块递推和 dense verified reference；`operator_canary.json` 覆盖 12 个 dimension/slab 组合、2,400 个非奇异系统和 1 个奇异系统，递推结果在已登记测试中均包含 exact Fraction dense action，奇异系统返回 `UNSUPPORTED`。因此 `Claim I: IMPLEMENTATION-CANARY-PASS` 是有机器证据支持的窄结论。
  5. `generate_numerical_defects.py` 已真实区分 float32/float64 二进制参数与残差路径，并调用 executable checker 生成 `checker_verdict`，不再把解析 oracle 直接冒充 checker 输出。24 个 root-excluding tube 均返回 `UNKNOWN`，0 false accept；这一修改解决了上一轮指出的“precision 只是标签、verdict 被硬编码”问题。
  6. `steps/008_next_round_gate.md` 与 `next_round_gate.json` 将证据分为 M0、M1、M2，并明确当前状态为 `M0 PASS-CANARY / M1 ITERATE / M2 NOT-STARTED / Paper Candidate FAIL-UNVERIFIED`。没有把 canary 成功包装成算法新颖性或性能优势，研究纪律良好。
  7. 结果文件包含 backend、命令、配置哈希、输入哈希和源码哈希；虽然当前还不是干净重放，但已经建立了比上一轮更可审计的 provenance 结构。

- ⚠️ **部分解决**：
  1. 当前 MNA 正例使用解析/高精度 oracle 根作为 candidate center，并围绕该根构造固定微小 tube。RC/diode-RC 的 200 次 `ACCEPT` 能验证 assembly 与 checker 的理想输入链，却不能说明真实 double/float32 producer 的输出可被稳定认证，也不能测量 tube initializer、producer tolerance 或 accumulated interface uncertainty。
  2. diode-RC oracle 实际是 `Decimal-160 bisection bracket`，而 `research_direction.md` 的冻结范围仍写作 “diode-RC MPFR root”。更重要的是，Decimal residual 的符号判断没有显式 directed error bound，因此它是高精度独立测试 oracle，而不是已经证明严格的 root bracket。当前应统一术语并限制证据强度。
  3. Operator canary 的 2,400 个主样本全部使用严格行对角占优的易解 point blocks；每个 grid 只有 2 个 nonzero-width interval RHS，共 24 个，而真实 Krawczyk remainder 是 interval box。该实验足以验证基本递推实现，不足以覆盖 near-singular pivot、强耦合、非正规矩阵、宽 remainder 和真实 MNA Jacobian 分布。
  4. `operator_canary.json` 的最大绝对 enclosure inflation 已达到 `0.1321725812626729`，并随 block dimension/slab length 增大而出现明显放大。当前尺度未归一化，不能据此判定 Claim W 失败；但它说明“递推天然更紧或更少 wrapping”没有证据，下一轮必须做条件数与真实 MNA 切片。
  5. 当前 dense pointwise checker 与 BlockStamp operator 共用 rigorous backend 和 `verified_solve`，这有利于组件匹配；但 `b2_fairness.json` 明确记录 `all_required_hashes_present=false`、`all_shared_hashes_match=null`、`strong_baseline_status=UNIMPLEMENTED-VERIFIED-SPARSE`。因此 B2 仍只是 correctness canary，不能作为 killer baseline。
  6. 当前 operator timing 不可用于性能结论：recursive 路径对每个 grid 跑 200 个 case，dense verified 路径只跑 2 个 interval-RHS case。两者的 seconds 字段样本量不同，不能计算 speedup。
  7. Chen--Hashimoto、Schwandt 和 Frommer--Hashemi 已进入高威胁矩阵，但关键条目仍是 `PUBLISHER-ABSTRACT + INSTITUTIONAL-METADATA`，没有完成 target-full-text/theorem/formula comparison。新颖性边界比以前诚实，但尚未闭合。
  8. 所有核心 artifacts 均记录 `dirty_worktree=true`，并把 `git_commit` 绑定到 `1fc3d6...`，而当前远程实验提交是 `3c758dd...`。源码哈希能够帮助追踪，但目前还没有从固定干净源码提交生成的一套可独立重放结果。

- ❌ **无效/偏离**：
  1. **本轮必须纠正上一轮评审及当前 Step 003 的数学错误。** 按文档自己的定义
     \[
     K(X)=\bar x-CF(\bar x)+(I-C[J F(X)])(X-\bar x),
     \]
     当 `C=0` 时应有 `K(X)=X`，而不是 `{0}`。因此 `F(x)=x+2, X=[-1,1], C=0` 不会产生 strict inclusion；`steps/003_formal_soundness_contract.md` 第 3 节、`research_direction.md` 中“奇异 C 可产生表面 strict inclusion”的句子，以及 `test_krawczyk_soundness_contract.py` 的注释都建立在错误代数上。常见 Kahan/Krawczyk 定理表述允许一般矩阵 `C`，由 strict inclusion 给出存在/唯一性；至少不能用当前反例声称 `C` 非奇异是该定理的必要前提。`C=M^{-1}` 可以继续作为首版 checker 的保守设计选择，但必须与“定理逻辑必要条件”区分。
  2. 当前 Claim I 只能证明 block recurrence 实现包含 exact dense action，不能证明该 recurrence 新颖。若后续没有 device-local remainder representation、证书组织或可测资源优势，当前实现会被归类为标准 verified block forward solve，而不是 CCF-B 级新算法。
  3. `component_ladder.csv` 和 `minimal_probe.csv` 仍不存在，3-stage ring 也尚未形成可执行 MNA workload。因而 Claim W/D/E、实际 nonlinear transient value、scalability 和 end-to-end benefit 均没有结果支持。
  4. `run_next_round_gate.py` 当前无条件把 `THEOREM_LEVEL_NOVELTY_UNRESOLVED`、`B2_STRONG_UNIMPLEMENTED`、`COMPONENT_LADDER_NOT_RUN`、`MATCHED_NONLINEAR_M2_NOT_RUN` 加入 blockers，并把 M2 固定为 `NOT-STARTED`。如果不修改，未来即使证据文件齐全，机器 gate 也无法自动晋级；该 runner 目前只能描述本轮状态，不能作为后续通用门禁实现。

## 3. 🔍 强CCF-B维度深度审查

- **问题与动机**：
  当前问题继续具有足够的 CCF-B 价值：对松容差、低精度、加速器或外部服务产生的固定离散 transient MNA 轨迹进行独立结果级认证，是明确且非平凡的 EDA 数值问题。本轮静态病态 MNA 已经更真实地执行了不同精度与 checker 路径，但它仍然是对角线性系统、在迭代 0 提前停止的构造案例。论文的主 motivation 不能写成“成熟 SPICE 经常给错结果”；下一轮需要在 diode-RC 或 ring 中由真实 tolerance/precision producer 自然产生 candidate，并展示认证或拒绝行为。

- **技术完备性与创新深度**：
  M0 从“文字合同”推进到“有实现 canary”，Claim I 也拥有了明确递推和 exact-action cross-check，这是本轮最大的实质进展。当前 checker 选择 `C=M^{-1}` 是合法且易审计的实现约束，但 formal contract 必须先修正错误反例，并精确引用所采用的 Krawczyk theorem 版本。

  CCF-B 的核心仍不能是 `Krawczyk + block forward substitution`。最可辩护的技术增量应落在以下至少一项：

  - 由 device-local charge/current stamps 直接生成 `[R_k]`，避免 materialize global interval Jacobian，并给出等价 containment contract；
  - 为 transient MNA 的 block-lower-bidiagonal结构设计可验证 sparse factor/witness 复用，使检查成本或 certificate bytes 明确低于 pointwise verified path；
  - 采用一种可说明的 dependency-preserving remainder representation，使 slab coupling 在 acceptance/prefix/tube 指标上优于 pointwise propagation。

  若 M2 只显示 Python 层 dense materialization 比 streaming 慢，而 strong verified-sparse B2 消除全部收益，则技术贡献不足以稳定达到 CCF-B。

- **实验可信度**：
  本轮结果属于高质量 implementation canary，而不是论文主实验。算术测试数量充分，operator oracle 使用 exact Fraction 对 dyadic systems 是一个优点；但矩阵分布过易、interval RHS 比例过低、MNA 正例由 oracle root 居中、没有真实 producer、没有 ring、没有 complete fairness hash，也没有 matched runtime/RSS/bytes 数据。

  下一轮 M2 必须满足：同一 candidate trace、tube、backend、semantics、scaling、ordering、factor quality、线程和硬件；至少 diode-RC 与 3-stage ring 两个 workload；每个配置 5 个独立进程；保留全部 `UNKNOWN/UNSUPPORTED`；同时报告 certification rate、certified prefix、tube width/growth、generation/check/fallback time、peak RSS、certificate bytes 和 strict-rerun cost。小型电路可使用 dense component-matched B2 验证机制；verified-sparse B2 的效率对比应增加足够规模的 RC ladder/ring replication，避免稀疏库固定开销主导结论。

- **叙事克制性**：
  `response_round3.md`、README 和 Step 008 对 `PASS-CANARY`、`IMPLEMENTATION-CANARY-PASS`、`ITERATE`、`NOT-STARTED` 的区分基本准确。需要删除 `C=0` 错误反例衍生的所有表述，并把 “diode-RC MPFR oracle” 改为与实际 artifact 一致的名称，或真正实现 MPFR/Arb directed bracket。Claim I 只能写成“tested implementation encloses the registered exact actions”；在 M2 和 prior-art closure 前，不得写成“novel BlockStamp algorithm”、`less wrapping`、`faster` 或 `lower end-to-end cost`。

## 4. ⚔️ 模拟评审攻击
### Top 3 Rejection Risks for Strong CCF-B

### Risk 1：Formal soundness 章节包含可被一行代数推翻的错误

1. **审稿人可能如何质疑**：作者声称 `C=0` 时 Krawczyk image 为 `{0}`，但代入定义立即得到 `K(X)=X`；作者是否真正理解所引用的 Krawczyk theorem？其他 soundness claim 是否也未经核验？
2. **当前论文有什么证据可以回应**：当前实际 checker 固定 `C=M^{-1}`，通过 verified solve 证明所用 point operator 可逆，并在登记 canary 中未出现 false accept；因此该文字错误不直接证明当前实现不 sound。
3. **当前证据能否扛住该攻击**：不能。对一篇以 independently checkable certificate 为核心的论文，基本定理解释错误会显著损害可信度。
4. **如果不能，缺少什么具体证据**：需要逐式纠正 Step 003、research direction 和测试注释；从原始/可靠 theorem source 写出精确条件；增加一个直接计算 arbitrary-C Krawczyk image 的回归测试，确认 `C=0` 得到 `X` 且不能 strict-accept；将 `C=M^{-1}` 明确标为实现约束。

### Risk 2：核心算法可能仍是标准 verified block solve 的直接实例

1. **审稿人可能如何质疑**：2,400 个 exact-action containment case 只证明代码实现了块前代；Chen--Hashimoto、interval block cyclic reduction、factorized Krawczyk 和 verified sparse solve 已覆盖大量结构化 verified computation。BlockStamp 新在哪里？
2. **当前论文有什么证据可以回应**：项目已把 Claim I/W/D/E 分离，给出 device-local streaming 假设和严格 component ladder 计划，并主动承认普通 block forward substitution 不新。
3. **当前证据能否扛住该攻击**：不能。高威胁全文尚未读完，device-local circuit path 和 component ladder 尚不存在。
4. **如果不能，缺少什么具体证据**：需要全文公式级 prior-art matrix；需要 `dense-slab → device-local pointwise → temporal-only → temporal+device` 的同组件实验；需要至少一个不能被普通 sparse implementation解释的机制或资源收益。

### Risk 3：现有正结果是 oracle-centered canary，不是实际 producer 认证

1. **审稿人可能如何质疑**：RC/diode-RC 的 center 直接取解析/高精度根，tube 也围绕真根构造；100% ACCEPT 是否只是理想输入的必然结果？BlockStamp 面对松容差、float32、累计 history uncertainty 和真实 nonlinear trajectory 时是否仍可工作？
2. **当前论文有什么证据可以回应**：负例测试、静态 residual early-stop 案例和严格区间后端说明 checker 在登记错误输入上能够 fail closed。
3. **当前证据能否扛住该攻击**：不能。没有 independent double/float32 transient producer、无 ring、无 slab propagation、无 B2-strong、无 end-to-end 成本。
4. **如果不能，缺少什么具体证据**：需要不读取 oracle 的 candidate/tube 生成流程；需要 diode-RC/ring tolerance × precision sweep；需要 component-matched M2 和 clean replay；需要报告接受与失败边界，而不是只报告 easy accepts。

## 5. 🛠️ 下一轮原子化改进工单
### Atomic Action Items

> 以下任务按“先修正理论事实，再关闭新颖性与公平基线，最后运行 M2”的依赖顺序排列。P0 未完成前，不扩展 SRAM、BSIM、Verilog-A、第二 producer 或大规模工业网表。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-B对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 写作规范 | 重写 Krawczyk theorem 段落：把 `C=0` 代入当前定义并明确得到 `K(X)=X`；删除“`C=0` 产生 `{0}` strict inclusion”和“非奇异 C 是由该反例证明的必要定理前提”；保留 `C=M^{-1}` 作为首版 checker 的冻结实现选择，并逐条写明该选择带来的可逆性与 verified-solve obligation | 数值假设透明度、核心理论正确性；当前错误可被审稿人直接推翻 | Step 003、research direction 和测试注释中的错误表述全部消失；文档给出精确 theorem source/条件；新增测试直接计算 `C=0` operator 并验证 image 等于 `X`、strict inclusion 为 false | `paper2/steps/003_formal_soundness_contract.md`, `paper2/research/research_direction.md`, `paper2/tests/test_krawczyk_soundness_contract.py` |
| P0 | 文献增补 | 获取并阅读全文级核验 Chen--Hashimoto 2003、Schwandt 1987/1989、Frommer--Hashemi 2012；对每篇记录 operator 公式、矩阵结构、interval dependency representation、保证、复杂度和可复用 witness，并逐项对照 `D_k/L_k/R_k/U_k` | Related Work 定位、方法创新性；摘要级阴性证据不能支撑 CCF-B novelty | `004_theorem_prior_art_closure.md` 中三类条目均标为 `FULL-TEXT/THEOREM` 或明确记录无法获得全文；新增一张 formula-level overlap 表，并给出 `CONTINUE-ALGORITHM` 或 `REFRAME-SYSTEM` 二选一结论 | `paper2/steps/004_theorem_prior_art_closure.md`, `paper2/research/proof_carrying_spice_literature.md` |
| P0 | 实验补充 | 扩展 operator stress runner：每个 `dimension={1,2,4,8}`、`slab={2,4,8,16}` 单元生成至少 200 个 nonzero-width interval-RHS 实例；按目标 condition/pivot-growth 桶 `{1e0–1e2,1e2–1e4,1e4–1e6,1e6–1e8}` 记录结果；加入强 subdiagonal coupling、非正规 blocks、near-singular supported 和 expected-unsupported cases | 技术完整性、数值稳定性；当前 2,376/2,400 个 point RHS 与严格对角占优矩阵不足以代表 Krawczyk remainder | 生成 `operator_stress.json`；每桶记录 attempted/supported/violation/inflation/UNKNOWN；supported case 对 exact Fraction/MPFR dense hull 为 0 containment violation；所有 singular/inconclusive case 不得返回 OK | `paper2/experiments/run_operator_canary.py`, `paper2/tests/test_blockstamp_dense_equivalence.py`, `paper2/results/blockstamp/operator_stress.json` |
| P0 | 实验补充 | 实现可执行 `nmos_ring_3stage` fixed-BE MNA：固定三组 load/initial-state 参数；用独立 double producer 与高精度 reference producer生成 100/300/1000-step trace；candidate/tube initializer 不读取 oracle，只使用 producer residual、局部 Jacobian scale 和冻结 radius rule | Benchmark 代表性、真实使用场景；当前全部正例由 oracle root 居中 | 生成 `ring_producer_canary.json`；记录 producer tolerance、precision、iterations、residual、reference error、tube rule、checker verdict；至少覆盖 3 个实例且保留全部失败状态 | `paper2/experiments/mna/`, `paper2/experiments/producers/`, `paper2/configs/blockstamp/minimal_probe.yaml`, `paper2/results/blockstamp/ring_producer_canary.json` |
| P0 | 实验补充 | 实现 B2-strong：对小型电路保留同组件 dense pointwise path；对扩展 RC ladder/ring replication 接入一种 verified-sparse kernel。为 B2、dense slab、temporal-only、BlockStamp 写入相同 candidate/tube/backend/semantics/scaling/ordering/factor-quality/thread/hardware hashes，仅允许 verification organization 不同 | Baseline 公平性、效率可信度 | `b2_fairness.json` 中 `all_required_hashes_present=true`、`all_shared_hashes_match=true`、`strong_baseline_status=IMPLEMENTED`；easy cases 可认证、已知坏样本 0 confirmed false accept；任何允许差异均有 machine-readable reason | `paper2/experiments/checkers/pointwise_krawczyk.py`, `paper2/experiments/checkers/verified_sparse.py`, `paper2/results/blockstamp/b2_fairness.json` |
| P0 | 消融补全 | 实现四级 matched ladder：`dense_slab_generic`、`device_local_pointwise_b2`、`temporal_only`、`temporal_device_blockstamp`；每个方法使用同一 trace/tube/backend/factor；分别计时 stamp assembly、factor verification、operator propagation、total check，并记录 RSS、bytes、acceptance、prefix、tube width 与 inclusion margin | 核心模块必要性、方法创新性；需要把 dense/materialization、时间递推和 device locality 的收益分开 | 生成 `component_ladder.csv` 与 manifest；每个 input hash 同时拥有四种方法记录；不存在 success-only filtering；Claim I/W/D/E 各自只能引用对应对照 | `paper2/experiments/checkers/`, `paper2/experiments/run_component_ladder.py`, `paper2/results/blockstamp/component_ladder.csv` |
| P0 | 实验补充 | 执行冻结 M2：`diode_rc` 与 `nmos_ring_3stage` 各 3 个实例，`steps={100,300,1000}`、`slab={1,2,4,8,16}`、每个 timing 配置 5 个独立进程；方法包含 strict high-precision rerun、B2-strong、dense slab、temporal-only、BlockStamp；所有 candidate 由 producer 生成且 tube rule 预先冻结 | Benchmark 代表性、Baseline 公平性、Scalability、实际价值 | 生成未筛选 `minimal_probe.csv` 与 manifest；含 certification rate、prefix、tube growth、generation/check/fallback/end-to-end time、RSS、certificate bytes、failure code；按 Step 008 输出 clustered bootstrap CI 和 W/D/E 独立判定 | `paper2/experiments/run_minimal_probe.py`, `paper2/configs/blockstamp/minimal_probe.yaml`, `paper2/results/blockstamp/minimal_probe.csv`, `paper2/steps/009_m2_result_gate.md` |
| P0 | 可复现性 | 先提交冻结源码，再从该干净 commit 的独立 checkout 将输出写入仓库外临时目录；完成后复制结果进入后续 artifact commit。每个 artifact 记录源码 commit 且 `dirty_worktree=false`，再执行第二次独立进程重放并核对结果哈希/容许的 timing 差异 | 可复现性；当前 artifacts 绑定旧 commit 且 dirty，不能作为稳定论文证据 | M0/M1/M2 所有 JSON/CSV manifest 均记录同一冻结源码 commit、`dirty_worktree=false`；确定性 artifact 哈希一致；timing 结果满足预先定义的重复容差；生成 `clean_replay_report.json` | `paper2/experiments/provenance.py`, `paper2/results/blockstamp/clean_replay_report.json`, `paper2/README.md` |
| P1 | 实验补充 | 在 diode-RC 上执行 producer tolerance × precision × tube-radius sweep：precision=`float32,float64`，至少 4 个 nonlinear tolerance，至少 4 个冻结 radius multiplier；center 只来自 producer；独立 oracle 仅用于事后评估 | Motivation 真实性、认证边界；当前 100% ACCEPT 是 oracle-centered easy case | 生成 `diode_rc_producer_sweep.csv`，包含 producer error、residual、checker verdict、oracle containment、margin 和 cost；至少同时出现可解释的 ACCEPT 与 UNKNOWN 区域，不得按结果调 radius | `paper2/experiments/run_diode_rc_sweep.py`, `paper2/results/blockstamp/diode_rc_producer_sweep.csv` |
| P1 | 实验补充 | 将 diode-RC oracle 改成与 checker backend 独立的 sign-certified bracket，或将所有文档统一改写为 `Decimal-160 high-precision test oracle` 并明确非严格性质；禁止继续在实际为 Decimal 时写 “MPFR root” | 精度证据、叙事准确性 | oracle 名称在 config、artifact、README、research direction 中一致；若采用严格 bracket，记录上下端 residual 的 directed sign certificate；否则不使用 `rigorous root bracket` 字样 | `paper2/experiments/mna/oracles.py`, `paper2/research/research_direction.md`, `paper2/README.md`, `paper2/results/blockstamp/mna_canary.json` |
| P1 | 可复现性 | 在 `pyproject.toml` 声明运行依赖与 MPFR 系统版本要求；新增 Ubuntu CI，执行 theorem algebra regression、rigorous backend edge corpus、MNA canary 的缩小版、operator exact-action 测试和 gate unit test | 可复现性、TCB 可移植性；当前 dependencies 为空且远程 commit 无 CI status | 干净环境安装说明可执行；CI 对每个 commit 给出通过/失败状态；记录 `libmpfr` SONAME/version；核心测试失败时 workflow 非零退出 | `paper2/pyproject.toml`, `.github/workflows/paper2-blockstamp.yml`, `paper2/README.md` |
| P1 | 可复现性 | 修改 `run_next_round_gate.py`，根据 fairness、component-ladder 和 minimal-probe artifact 的真实存在与字段条件动态生成 blockers/M2 status；新增 synthetic complete-evidence 单元测试验证满足条件时可输出 `PRE_PAPER_CANDIDATE` | 门禁可执行性；当前 runner 将 blockers 和 M2 状态硬编码，未来无法晋级 | `test_next_round_gate.py` 同时覆盖当前 `NOT-STARTED` 与 synthetic `PRE_PAPER_CANDIDATE`；不存在已满足条件仍保留 `UNIMPLEMENTED/NOT-RUN` blocker 的情况 | `paper2/experiments/run_next_round_gate.py`, `paper2/tests/test_next_round_gate.py` |
| P1 | 叙事修正 | 在完成 M2 后按 W/I/D/E 分别更新 claim：只把通过冻结判据的 claim 写成完成时态；若只有 runtime/RSS 优势则删除 less-wrapping 语言；若 B2 在认证率与成本上不差则停止 slab headline并转为受限 pointwise certificate system | 贡献克制性、结果与主张对应 | `research_direction.md` 每个完成时态主张可定位到 `minimal_probe.csv` 字段和对照方法；失败 claim 明确标记 STOP/REFRAME；摘要候选中无未经数据支持的绝对化词语 | `paper2/research/research_direction.md`, `paper2/steps/009_m2_result_gate.md` |

### 本轮阶段决策

当前可更新为：

```text
Research Opportunity: PASS
M0 soundness implementation chain: PASS-CANARY（需修正 theorem 叙事并 clean replay）
Claim I exact-action implementation: PASS-CANARY
M1 algorithm novelty: ITERATE / UNRESOLVED
B2-strong: NOT READY
M2 matched nonlinear probe: NOT STARTED
Pre-Paper Candidate: FAIL-UNVERIFIED
Paper Candidate: FAIL-UNVERIFIED
```

本轮结果足以证明项目已经跨过“只有研究计划、没有任何 checker 实现”的阶段，也足以继续投入一轮严格的 M2 工作；但它还不足以降低到只做文档或直接进入论文写作。下一轮唯一能改变 CCF-B 判断的证据是：**纠正理论事实后，在真实 producer 轨迹和组件匹配强基线下，证明 W、D、E 中至少一项具有稳定且可归因的信号。**
