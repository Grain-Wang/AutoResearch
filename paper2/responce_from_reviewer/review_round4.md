# Review Round 4

## 1. 🎯 强CCF-B达标判定

- **当前状态**：未达标
- **核心差距**：当前已经形成可信的问题定义、先例边界和若干 soundness canary，但能够支撑 CCF-B 技术贡献的核心对象——BlockStamp 的可执行块递推、严格 operator enclosure，以及相对组件匹配的 B2-strong/verified-sparse baseline 的稳定结构性收益——仍不存在，因此目前还不能证明这是一个“非平凡的新算法”，而不是既有 Krawczyk、块三角求解与 circuit interval stamp 的组合应用。
- **高分录用潜力**：否（当前）。该方向本身具有高于普通 CCF-B 工程论文的潜在技术上限；如果后续能够给出严格的 BlockStamp recurrence、在至少两个代表性非线性 transient workload 上获得可归因的 runtime/memory/certification Pareto 优势，并完成基本可复现闭环，则有机会成为高分 CCF-B 工作。当前证据尚未跨过这一门槛。

## 2. 🔄 改进效果评估

针对 `paper2/steps/` 中的最新修改：

- ✅ **有效改进**：
  1. `003_formal_soundness_contract.md` 已将原先模糊的单一 Claim S 拆成 `S-fixed` 与 `S-param`，明确了 incoming interface 的量词、统一 residual/Jacobian enclosure、outgoing projection、局部唯一性和 slab composition 条件。对于 CCF-B，能够清楚说明“究竟证明什么、不证明什么”已经显著降低方法完整性风险。
  2. `004_theorem_prior_art_closure.md` 主动承认 parameterized Krawczyk、validated initial-set propagation、verified LU/factor witness 和通用 proof-carrying 架构均有先例，把候选技术贡献收缩到“device-local stamp + transient MNA 时间带状结构的联合 verified operator evaluation”。这一收缩符合 CCF-B 对清晰技术增量的要求，比继续维护宽泛的 Proof-Carrying SPICE 首创叙事更可信。
  3. `006_selective_recovery_contract.md` 已解决上一轮指出的后缀依赖问题：失败 slab 重算后，只有新的 outgoing enclosure 被下一 slab 已缓存 incoming assumption 包含时才允许复用；否则从首次 containment failure 开始重新检查。该问题目前不再是主要拒稿点。
  4. `interval_backend.py`、diode/受限 Level-1 NMOS interval stamps 与对应测试把研究从纯协议推进到可执行 canary；跨 MOS cutoff/triode/saturation 边界时 fail closed，而不是根据中心点分支，这一实现选择符合严格数值检查器的基本要求。
  5. `005_baseline_defect_gate.md` 用弱电导造成的自然病态 MNA 展示 residual 与 forward error 可以显著分离，并明确标注为 `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`。这一结果足以支撑“residual 不是 forward-error certificate”的基础动机，但尚不足以说明成熟 transient SPICE 中该现象具有普遍严重性。
  6. 当前研究纪律较好：仓库持续保留 `Research Opportunity / Paper Candidate FAIL-UNVERIFIED` 状态，没有在缺少 BlockStamp 数据时提前声称 lower end-to-end cost，也没有提前扩展 SRAM、BSIM、Verilog-A 或大规模工业网表。

- ⚠️ **部分解决**：
  1. `S-fixed/S-param` 的量词已经澄清，但 `003_formal_soundness_contract.md` 中 `A5` 对预条件算子 `C` 的条件仍不足。仅要求 checker 能 enclosure `C v` 和 `C A`，不能排除 `C=0` 这类奇异算子；因此当前 proof skeleton 还不能作为正式 soundness 定理。该问题对 CCF-B 仍是 P0，因为论文的核心卖点之一就是“可独立检查且 sound”。
  2. 当前 `interval_backend.py` 适合作为透明原型，但 `exp/log/sqrt` 先在有限精度 Decimal 中得到近似结果，再向 binary64 扩一格，不能证明相对真实超越函数值的 directed enclosure。对于普通性能型 SPICE 论文这可能只是实现细节，但对于本文这种 certificate 论文，它直接决定主要 claim 是否成立。
  3. diode/NMOS stamp 只覆盖局部器件函数，尚未形成 R/C/source、charge/history、节点/支路变量、ground normalization 和 BE MNA assembly。当前还没有真正的 transient discrete MNA checker，因此技术完整性仍明显低于 CCF-B 投稿状态。
  4. `recovery.py` 已验证一维 interval containment 逻辑，但还没有真实多维 state box、certificate digest/input hash replay 或 actual slab checker 参与。其“逻辑规则”已解决，系统实证仍未完成；在核心 BlockStamp probe 之前，这一点可以保持 P1/P2，而不应继续占用 P0 资源。
  5. Level-1 MOS + fixed-step BE 可以满足最小机制实验，但如果最终 CCF-B 版本只停留在这一范围，工程相关性会偏弱。强 CCF-B 不要求完整 BSIM/商业 FastSPICE，但最终至少需要两个有代表性的非线性 transient 电路，并最好增加一个比单管 Level-1 更接近实际模拟模块的公开 workload。
  6. `ideas/01_proof_carrying_spice.md` 仍保留较早的“accepted slab endpoint becomes next interval；rejected slab split or recompute”等宽泛表述，没有同步记录 `C` 可逆性、suffix invalidation 和当前唯一候选 novelty。作为原始 Idea 可保留历史价值，但如果它继续被下游 Agent 当成主规格，会与 `research_direction.md` / `steps/003-006` 发生语义漂移。

- ❌ **无效/偏离**：
  1. `generate_numerical_defects.py` 中 `float32` 与 `float64` 当前只是标签，没有真实执行不同精度计算；两组记录实质重复。`certificate_verdict` 还是直接由解析知识写成 `REJECT_ROOT_OUTSIDE_TUBE`，不是实际 checker verdict。该 CSV 只能算解析 motivation artifact，不能作为 CCF-B 实验结果。
  2. `stage0_arithmetic_summary.json` 是手工汇总文件，不是由测试自动生成；其中 `boundary_cases_per_operation=7` 与现有测试覆盖并不完全一致。CCF-B 不要求形式化验证整个软件栈，但论文关键 soundness 数据不能由人工维护的 summary 与代码事实发生漂移。
  3. Round 3 之后仓库没有新增 B2-strong、dense-slab checker、BlockStamp recurrence、BE MNA assembly、真实 transient probe 或性能结果。因此最新历史评审提出的核心 P0 仍全部未被实验关闭；继续扩写愿景、related work 或 recovery 逻辑不会改变当前录用判断。

## 3. 🔍 强CCF-B维度深度审查

- **问题与动机**：
  - 当前问题具有足够的 CCF-B 学术价值。论文并不需要重新定义整个 SPICE 范式；只要能够证明“对外部产生的固定离散 transient MNA 结果做独立严格检查”在一类有意义的近似/松容差 producer 上比可信重算更便宜，就已经是一个明确而非平凡的 EDA 数值验证问题。
  - 现有弱电导 canary 已经证明一个基础数学事实：小 residual 不等价于小 forward error。但它仍是静态、线性、人工参数 sweep。对于 CCF-B，不要求证明成熟 SPICE 经常出错；但至少需要一个真实 nonlinear transient tolerance/precision case，说明独立 certificate 的使用场景不是纯理论构造。
  - 最合适的动机不应是“现有 SPICE 经常给错结果”，而应是“当 producer 为松容差、低精度、加速器或外部服务时，消费者需要一种结果级独立检查方式”。这一表述与当前证据更匹配，也更容易达到 CCF-B 的实际价值门槛。

- **技术完备性与创新深度**：
  - 对 CCF-B 来说，不要求 BlockStamp 必须是范式级数值理论突破，但必须存在一个能够与 prior art 清楚区分、可实现、可消融的技术增量。当前最合理的增量是：针对 BE transient MNA 的 block-lower-bidiagonal 时间依赖和 device-local stamp，构造一种不显式形成全 slab inverse/operator 的 verified recurrence，并在同等 enclosure 语义下减少 check cost、memory 或 certificate size。
  - 当前仓库还没有这个 recurrence，因此目前无法判断它是“新算法”还是标准 block forward substitution 的直接应用。若最终只是把通用 Krawczyk 中的矩阵乘法改成标准块前代，且相对 strong pointwise/verified-sparse baseline 没有明确收益，则技术贡献不足以稳定达到 CCF-B。
  - `C` 的数学定义必须固定。首版建议只保留一个可审计定义，例如 checker-side midpoint Jacobian `M` 的可逆 block solve operator；producer 只提供 permutation/scaling/factor hints。不要在“approximate inverse / ILU / producer LU / block elimination witness”之间切换，否则 theorem、certificate 与实现三者无法一一对应。
  - 对 CCF-B，S-param、composition、property monitor 和 selective recovery 都可以作为系统增量，而不必全部成为新定理。真正需要投入论文技术篇幅的是 `BlockStamp recurrence + enclosure proof + component-matched complexity/experimental evidence`。
  - 当前 Level-1 MOS 分支策略是保守且合理的：跨分支直接 `UNKNOWN`。不需要为了 CCF-B 强行解决所有非光滑 compact model，但论文必须报告 unsupported rate，并证明核心 benchmark 不依赖大量人工避开分支边界。

- **实验可信度**：
  - 当前最主要的问题不是 benchmark 数量少，而是尚无真正的主方法实验。CCF-B 不要求一开始就覆盖商业 SPICE、百万器件或完整 BSIM；但至少需要一个可执行的 B2-strong、一个 dense/verified-sparse 对照、一个 BlockStamp 实现，以及两个代表性的 nonlinear transient workload。
  - B2-strong 必须与 BlockStamp 共享 interval backend、device stamps、candidate、tube initializer、scaling、ordering、factor hint、线程和硬件。否则 runtime/acceptance 差异无法归因于 temporal recurrence，主要 speedup claim 会失去可信度。
  - 最小可投稿级 benchmark 可以是：RC/diode oracle 用于 correctness；diode-RC transient 用于 nonlinear BE root；3/5-stage ring oscillator 用于长时间 propagation；再增加一个 op-amp step 或 SRAM 作为第二类模拟模块。对于“稳定 CCF-B”而言，至少两个非线性类别比单纯把状态规模扩到 1000 更重要。
  - 主要指标应围绕本文 claim，而不是照搬普通 SPICE solver 指标：`certification rate`、`certified prefix`、`inclusion/tube width`、`checker time`、`certificate generation time`、`fallback time`、`peak RSS`、`certificate bytes`、`end-to-end certified throughput`。如果同时声称 producer speedup，再报告 producer runtime 与 strict rerun runtime。
  - 当前没有性能数据，所以不存在“baseline 不公平”的已发生实验错误，但 baseline 设计必须在第一次正式跑数前冻结。否则后续很容易通过不同 scaling/tube/factor 路径人为制造 BlockStamp 优势。
  - 可复现性目前处于“协议强、实际弱”的状态：有固定随机种子、run artifact 规划和测试意识，但没有锁定 rigorous arithmetic backend、正式 runtime dependencies、CI、主实验 CLI 和自动生成的结果 summary。对于 CCF-B，这些不必全部达到 artifact-evaluation 水平，但 Table/Figure 对应结果必须能从固定配置重建。

- **叙事克制性**：
  - 当前将 `Proof-Carrying SPICE` 降为系统愿景、把核心对象改成 `BlockStamp-Cert` 是正确方向。论文 headline 应围绕“circuit-structured certification of fixed-discretization transient MNA”，而不是“首次可信 SPICE”。
  - `Krawczyk`、parameterized interval root proof、time-slab composition、verified factor witness、proof-carrying producer/checker 都不能单独作为 contribution bullet。当前 related-work 审计已经支持这一克制定位。
  - 在 Claim E 尚未有结果前，不得在 Abstract/Introduction 使用“lower end-to-end cost”“significantly faster”“less wrapping”等完成时态主张。可以写成研究目标或 hypothesis。
  - 如果真实 ngspice/Xyce tolerance sweep 很少产生错误 candidate，不应把它解释为方向失败；应将使用场景限定到 `untrusted/approximate/accelerated producer`，并用独立检查成本证明实用性。
  - 最终 CCF-B 版本即使只支持 fixed BE + restricted device semantics 也不是自动拒稿点，前提是标题、abstract、experiment table 和 limitation 都明确限定该范围，且核心算法收益足够清楚。

## 4. ⚔️ 模拟评审攻击
### Top 3 Rejection Risks for Strong CCF-B

### Risk 1：核心方法仍可能只是已有 verified numerics 的组合

1. **审稿人可能如何质疑**：`Krawczyk + block lower-triangular solve + circuit stamps` 都已有基础，BlockStamp 是否只是把标准块前代写进 transient MNA，而没有新的技术机制？
2. **当前论文有什么证据可以回应**：已有文献审计主动排除了通用 Krawczyk、S-param、verified factors 和 time-slab novelty，并把剩余缺口锁定在 device/time joint operator evaluation；这一定位是可信的。
3. **当前证据能否扛住该攻击**：不能。仓库没有 BlockStamp recurrence、operator theorem、complexity 或 B2/B3/T-only/T+D component ladder 数据。
4. **如果不能，缺少什么具体证据**：需要一个唯一、明确的 recurrence；需要 dense real-operator containment 交叉检查；需要 `device-local pointwise → temporal-only → temporal+device` 的消融；需要至少一个 runtime/memory/certificate-size 指标在两个非线性电路类别上稳定优于 component-matched baseline。

### Risk 2：论文的“sound certificate”主张尚未由完整算术与 MNA 链闭合

1. **审稿人可能如何质疑**：当前 Krawczyk 定理缺少 `C` 可逆前提；Decimal transcendental 路径不是严格 directed rounding；器件 point/interval 实现共享公式；尚无 BE history/MNA assembly。论文如何保证 ACCEPT 真正对应数学上的局部唯一根？
2. **当前论文有什么证据可以回应**：S-fixed/S-param 量词已经明确；跨 MOS region 返回 UNKNOWN；大量点/box canary 目前无 observed containment violation；TCB 条件也已显式声明。
3. **当前证据能否扛住该攻击**：不能。对于一篇以 independent certification 为核心的 CCF-B 论文，soundness 不能只靠随机测试与 proof skeleton。
4. **如果不能，缺少什么具体证据**：需要修正 `C` 可逆性前提；使用真正 directed-rounded backend；完成 R/C/source/diode 的 BE MNA assembly；让 checker 在 analytic/MPFR oracle 上真实输出 ACCEPT/UNKNOWN；对 hard arithmetic/domain/boundary cases 做自动回归。

### Risk 3：没有主实验，无法证明方法具有 CCF-B 级实际价值

1. **审稿人可能如何质疑**：当前只有静态病态 canary、算术测试和器件局部测试；没有 transient certification rate、runtime、memory、certificate size、strict-rerun cost 或 nonlinear benchmark。即使理论上可行，为什么这不是一个高成本但无收益的 checker？
2. **当前论文有什么证据可以回应**：实验协议已经定义 B0–B5、stage gates、end-to-end accounting 和失败样本保留；研究设计意识是充分的。
3. **当前证据能否扛住该攻击**：不能。实验协议不是实验结果。
4. **如果不能，缺少什么具体证据**：至少需要 diode-RC + ring oscillator 两类 nonlinear transient probe；B2-strong、dense slab、verified sparse kernel 和 BlockStamp 使用同一配置；每个配置至少 5 次独立 timing；报告 acceptance、tube/prefix、runtime、RSS、certificate bytes；如果主张 end-to-end gain，再把 producer、certificate generation、check 和 fallback 全部计费。

## 5. 🛠️ 下一轮原子化改进工单
### Atomic Action Items

> ⚠️ 以下任务按 CCF-B 录用影响排序。P0 任务只围绕“核心算法是否成立、soundness 是否闭合、最小强 baseline 是否公平”展开；不要求提前建设 CCF-A 级工业大规模系统。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-B对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 写作规范 | 在 `003_formal_soundness_contract.md` 中将 `A5` 改为显式要求 `C` 为 checker 可验证的可逆实算子；固定首版 `C=M^{-1}`，其中 `M` 为 checker 重建的 point midpoint block-lower-bidiagonal Jacobian；新增 `F(x)=x+2, X=[-1,1], C=0` 反例并说明旧条件为何错误 | 数值假设透明度、技术完整性；当前定理存在直接反例，未修正前不能支撑核心 ACCEPT claim | 文件中出现明确的 `C` 可逆假设、checker obligation 和反例；新建测试使奇异 `C` 配置返回 `UNSUPPORTED/UNKNOWN`，不得 ACCEPT | `paper2/steps/003_formal_soundness_contract.md`, `paper2/tests/test_krawczyk_soundness_contract.py` |
| P0 | 实验补充 | 新建 `blockstamp_operator.py`，对 block-lower-bidiagonal point matrix `M` 实现唯一的 verified recurrence `U_a=VSolve(D_a,R_a)`、`U_k=VSolve(D_k,R_k-L_k U_{k-1})`；使用 MPFR dense solve 作为独立 oracle，在 block dimension=`1,2,4,8`、slab length=`2,4,8` 上各生成至少 200 个非奇异随机实例 | 方法创新性、技术完整性；CCF-B 核心必须存在一个可执行且可验证的算法对象，而不是架构描述 | `test_blockstamp_dense_equivalence.py` 全部通过；每个 recursive enclosure 包含对应 MPFR dense action；输出 `operator_canary.json`，记录实例数、失败数、最大 enclosure inflation | `paper2/experiments/blockstamp_operator.py`, `paper2/tests/test_blockstamp_dense_equivalence.py`, `paper2/results/blockstamp/operator_canary.json` |
| P0 | 实验补充 | 新建 `rigorous_backend.py`，使用 MPFR/等价库的显式 RNDD/RNDU 实现 `add/sub/mul/div/exp/expm1/log/sqrt`；对每个操作执行至少 50,000 个随机/边界输入，并覆盖 subnormal、overflow frontier、near-zero denominator 和 cancellation；测试代码自动生成 summary | 核心 soundness、可复现性；本文 certificate claim 依赖真正的 outward rounding，Decimal nearest 近似不足以支撑 CCF-B 主要结论 | 生成 `rigorous_backend_summary.json`；全部已支持输入 0 containment violation；unsupported domain 返回结构化状态；summary 由测试/runner 自动生成而非人工编辑 | `paper2/experiments/rigorous_backend.py`, `paper2/tests/test_rigorous_backend.py`, `paper2/results/blockstamp/rigorous_backend_summary.json` |
| P0 | 实验补充 | 在 `paper2/experiments/mna/` 实现 R、C、独立电流源、独立电压源、diode 的固定步长 BE MNA residual、history term、point Jacobian 和 interval Jacobian assembly；用 RC step 的解析离散解和 diode-RC 的 MPFR Newton root 各运行至少 100 个 time steps | 技术完整性、问题真实性；当前局部 device stamp 尚未形成真正 transient MNA，无法支撑论文对象 | `test_be_mna_assembly.py` 中 RC 每步 root 误差满足 oracle tolerance，diode-RC 的 MPFR root 全部落入声明 tube；错误 history/节点映射样本不得被 checker ACCEPT | `paper2/experiments/mna/`, `paper2/tests/test_be_mna_assembly.py` |
| P0 | 实验补充 | 实现 `B2-strong` pointwise Krawczyk checker；与 BlockStamp 共用同一 rigorous backend、MNA/device semantics、candidate center、tube initializer、scaling、ordering、midpoint factor 和单线程设置；为每个共享输入写 SHA-256 到 fairness manifest | Baseline 公平性；只有 component-matched pointwise baseline 才能判断 temporal block recurrence 是否提供非平凡增量 | 生成 `b2_fairness.json`，其中所有共享组件哈希一致；RC/diode-RC easy cases 上 B2 给出有效 certificate；已知坏 tube 0 false accept | `paper2/experiments/checkers/pointwise_krawczyk.py`, `paper2/configs/blockstamp/b2_canary.yaml`, `paper2/results/blockstamp/b2_fairness.json` |
| P0 | 消融补全 | 实现四级 component ladder：`dense-slab generic`、`device-local pointwise`、`temporal-only block recurrence`、`temporal+device BlockStamp`；在相同 candidate/tube/backend/factor 下记录 assembly time、verified solve time、total check time、peak RSS、certificate bytes、acceptance 和 inclusion margin | 核心模块必要性、方法创新性；需要区分收益来自普通稀疏实现、device locality 还是 temporal recurrence | 生成 `component_ladder.csv`；每行包含统一输入 hash 与四个方法的上述字段；任何未认证配置保留 failure code，不得过滤 | `paper2/experiments/checkers/`, `paper2/experiments/blockstamp_operator.py`, `paper2/results/blockstamp/component_ladder.csv` |
| P0 | 实验补充 | 在 diode-RC 和 3-stage ring oscillator 上冻结 `steps={100,300,1000}`、`slab={1,2,4,8,16}`；B2-strong、dense slab 与 BlockStamp 使用相同 producer trace/tube/backend；每个 timing 配置运行 5 个独立进程 | Benchmark代表性、Baseline公平性、Scalability；这是判断稳定 CCF-B 技术价值的最小 nonlinear transient 闭环 | 生成未筛选的 `minimal_probe.csv`；至少包含 `certification_rate, certified_prefix, tube_width, check_time_median, check_time_iqr, peak_rss, certificate_bytes, failure_code`；输出 slab-length–acceptance 和 steps–runtime/RSS 曲线 | `paper2/configs/blockstamp/minimal_probe.yaml`, `paper2/experiments/run_minimal_probe.py`, `paper2/results/blockstamp/minimal_probe.csv` |
| P1 | 实验补充 | 修改 `generate_numerical_defects.py`：真实执行 float32/float64 center cast；调用实际 checker 产生 `checker_verdict`；把解析事实单独保存为 `oracle_root_in_tube`；删除硬编码 `REJECT_ROOT_OUTSIDE_TUBE` 字段 | Motivation真实性、实验可信度；当前 CSV 是解析示例而非 checker 实验 | 新 CSV 中 float32/float64 至少存在可观察数值差异；`checker_verdict` 只来自 checker API；无无根证明时仅允许 `ACCEPT/UNKNOWN/UNSUPPORTED` | `paper2/experiments/generate_numerical_defects.py`, `paper2/results/blockstamp/numerical_defect_cases.csv`, `paper2/tests/test_numerical_defects.py` |
| P1 | 文献增补 | 将 Round 3 已识别的 Chen–Hashimoto block-Krawczyk、Schwandt interval cyclic reduction、Frommer–Hashemi factorized Krawczyk 三类工作正式写入 prior-art matrix；逐篇记录 proof object、结构假设、复杂度与 BlockStamp 的差异 | Related Work定位、方法创新性；CCF-B 不要求范式突破，但必须证明新增技术不是通用 block verified solve 的直接改名 | `004_theorem_prior_art_closure.md` 新增三类高威胁条目；`proof_carrying_spice_literature.md` 中每篇含来源与明确 overlap；novelty statement 不再使用泛化“block Krawczyk”作为差异 | `paper2/steps/004_theorem_prior_art_closure.md`, `paper2/research/proof_carrying_spice_literature.md` |
| P1 | 可复现性 | 在 `paper2/pyproject.toml` 写入实际 rigorous backend 和运行依赖并生成锁定环境；新增 CI 只运行 arithmetic、operator dense-equivalence、BE MNA、B2 canary 和 recovery tests；在 `paper2/README.md` 写一条重建 `minimal_probe.csv` 的命令 | 可复现性；强 CCF-B 要求核心表格能由固定环境重建，不要求完整商业工具 artifact | 干净环境安装成功；CI 在当前 commit 全绿；README 命令从空 `results/blockstamp/` 重建 `minimal_probe.csv` 和配置快照 | `paper2/pyproject.toml`, `.github/workflows/paper2-blockstamp.yml`, `paper2/README.md` |
| P1 | 叙事修正 | 在最小 probe 出结果后，根据实际数据更新 `research_direction.md` 的 Claim E：若 BlockStamp 只降低 memory/runtime，则删除“less wrapping”表述；若只在短 slab 有收益，则明确写入支持范围；若 B2 已足够，则将 BlockStamp headline 降级为 pointwise certificate system | 贡献克制性、结果-主张一致性；CCF-B 可以接受范围受限的方法，但不能让 headline 超出实验 | Claim E 中每个定量词都能映射到 `minimal_probe.csv` 对应字段；不存在无数据支撑的 `faster/less wrapping/lower end-to-end cost` | `paper2/research/research_direction.md`, `paper2/README.md` |
