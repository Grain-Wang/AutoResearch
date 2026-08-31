# Review Round 1

## 1. 🎯 强CCF-A达标判定
- **当前状态**：未达标
- **核心差距**：BlockStamp-Cert 的局部离散根 soundness、参数化 slab 组合和器件—时间结构性效率仍停留在假设与实验协议层面；仓库尚无可运行实现、定理证明草案或实验结果，因而无法排除“DATE 2019 式区间验证 + validated integration + 常规 proof-carrying wrapper”的组合式增量评价。
- **A类顶流潜力**：否（当前）。该问题具有较高辨识度和潜在影响力，但 Best Paper Nomination 需要一个可清楚归因于 MNA 时间带状结构与器件局部 stamp 的新算法/定理，并在强 verified baselines 下给出显著且可复现的端到端证据；当前材料尚未提供这些证据。

## 2. 🔄 改进效果评估
针对 `paper2/steps/` 中的最新修改：

- ✅ **有效改进**：
  1. `001_literature_novelty_gate.md` 已完成较严格的红队式文献审计，明确承认晶体管 DC Krawczyk、validated ODE/DAE、proof-carrying computation、可靠稀疏线性代数和 Verilog-A 代码生成均有强先例，并将当前结论限定为 `GO_TO_MINIMAL_PROBLEM_PROBE`，没有把阴性检索结果误写成领域不存在性证明。
  2. `research/research_direction.md` 将泛化的 “Proof-Carrying SPICE” 收缩为可被消融的 BlockStamp-Cert，把潜在论文贡献聚焦到 device-local interval stamps、时间块递推、稀疏 factor witness 和 selective recovery；同时列出了局部唯一性、固定离散、受限器件模型和离散规格等 non-claims，显著降低了 overclaim 风险。
  3. `002_complete_experiment_protocol.md` 给出了 B0–B5、Stage 0–8、独立重复、失败样本保留、五次独立进程计时、Wilson interval、clustered bootstrap、TCB denylist 和 end-to-end 成本分解。该协议在基线覆盖、公平性意识、负结果处理和复现契约方面达到高质量研究计划水平。
  4. 当前门禁坚持在最小 BE/diode/MOS probe 产生结构性信号前，不投入通用 Verilog-A、BSIM、高阶积分和大规模矩阵。这一执行顺序能够限制高风险系统工程对核心科学假设的掩盖。

- ⚠️ **部分解决**：
  1. Claim S 把 incoming interface interval 写成全称量化参数，但当前没有给出参数化 Krawczyk 定理、统一正则性条件、解映射连续性条件或 outgoing enclosure 的严格构造。固定接口状态下的局部唯一根与“对所有接口状态均存在唯一根”不是同一个结论。
  2. B2 被描述为 pointwise verified Krawczyk，但尚未冻结它与 BlockStamp 共享的 tube initializer、变量缩放、device-local stamps、稀疏 ordering、factor witness 和区间后端。若 B2 使用通用实现而主方法使用专用稀疏组件，时间结构贡献无法被单独归因。
  3. TCB 合同已经列出，但独立性仍是文字约束。仓库中的 `experiments/` 与 `tests/` 目前只有 `__init__.py`，`configs/` 与 `results/` 只有占位 README，`pyproject.toml` 的运行时依赖为空，因此不存在可审计的 producer/checker 依赖边界、向外舍入后端或证书重放链路。
  4. Level-1 MOS 与固定步长 BE 适合作为 canary，但不足以单独支撑强 CCF-A 的工业相关性。会议最终版本至少需要一个开放、可复现、非手写玩具器件语义，或清楚证明算法贡献与具体 compact model 解耦。
  5. B1 的多精度 strict rerun 只能作为高精度数值参考，不能替代存在唯一性证明；B4 的连续 ODE enclosure 与离散 MNA 根证书证明对象不同；B5 只验证线性子问题。当前协议需要一张 guarantee/trust matrix，防止把这些方法放在同一“正确性”列中直接排名。

- ❌ **无效/偏离**：
  1. 当前完整 Stage 0–8 协议是计划，不是论文证据。尚无代码、测试、配置、证书、结果或 timing 产物，不能据此宣称 Claim S/C/E/R/P 已得到任何程度的验证。
  2. Stage 1 将病态数值机制、松容差、stale history、错误 stamp、Jacobian 符号、permutation 和 factor corruption 放在同一缺陷集合中。实现破坏可以证明 checker 的防篡改能力，却不能单独证明成熟 SPICE 工作流存在足够重要的数值可信瓶颈；论文主 motivation 必须由非人为软件破坏的数值案例支撑。
  3. “所有 producer 错误只能导致拒绝”只有在 checker 语义、区间算术、证书解析、输入哈希和定理假设均正确时才成立，不能由有限故障注入实验推出。当前应写成条件式 soundness theorem，而不是经验性全错误覆盖主张。
  4. selective recovery 目前忽略了失败 slab 重算后对下游证书的依赖传播。只有当新的 outgoing interval 被下一 slab 的 incoming assumption 包含时，下游证书才可复用；否则必须使后缀证书失效并重新检查。未定义该合同前，“只重算失败 slab”存在技术性 overclaim。

## 3. 🔍 强CCF-A维度深度审查
- **问题与动机**：
  - 问题本身具有真实价值：FastSPICE、松容差、混合精度和学习型 producer 增加了“快速候选结果如何被低成本接受”的需求；传统 convergence flag、残差和双仿真器一致性不等价于局部存在唯一性。
  - 当前动机仍缺少实际严重度证据。仓库没有展示真实或自然产生的 `small residual + large forward error`、near-singular Jacobian、松容差错误接受、低精度相位漂移或错误规格判定案例。若主要证据来自手工篡改 stamp/permutation，审稿人会把问题降级为软件完整性检查，而不是 SPICE 数值算法瓶颈。
  - 强 CCF-A 需要证明两件事同时成立：第一，近似 producer 在有价值的工作负载上确实能显著减少生成成本；第二，独立认证比严格重算更便宜，并且认证失败率不会吞噬收益。当前没有任何数据支撑这两个必要条件。

- **技术完备性与创新深度**：
  - 当前最有潜力的贡献不是 Krawczyk、time slab 或 producer/checker 接口，而是一个新的 circuit-structured certifying algorithm：在不显式构造全局区间逆的前提下，利用 BE Jacobian 的块下双对角结构、器件 stamp 局部性和可验证稀疏 factor witness，计算严格 Krawczyk center/radius bound。该算法若只有工程缓存或稀疏矩阵实现差异，而没有新的递推界、复杂度结论或更低 wrapping 的机制说明，则达不到强 CCF-A。
  - Claim S 必须拆成固定接口状态与区间接口参数两个定理。后者需要明确量词：对每个 `y ∈ Y_in` 是否存在唯一 `x_S(y) ∈ X_S`，以及 outgoing interval 是否包含所有 `x_b(y)`。普通固定参数 Krawczyk inclusion 不能自动推出这一参数化结论。
  - Level-1 MOS、diode `exp` 和分区器件方程可能在 tube 内跨越 cutoff/triode/saturation 边界或非光滑点。经典 Krawczyk 条件通常要求声明区域内连续可微并具有有效 interval Jacobian enclosure。实现必须定义分支切分、interval slope/generalized derivative 或拒绝规则，不能让普通浮点分支选择隐式决定 soundness。
  - Producer 提供的 LU/ILU 不是直接可接受的逆算子。Checker 需要对 permutation、pivot、triangular solve rounding、factor residual、`C[J]` 乘积和中心修正建立完整包含链。只验证 `A≈LU` 的普通 residual 不足以证明最终 nonlinear inclusion。
  - Interface box 投影会丢失跨变量与跨时间相关性，可能导致 wrapping 指数式增长。论文必须给出 axis-aligned interval、affine/Taylor representation 或重中心策略的明确选择，并通过定理或机制实验解释 BlockStamp 为什么比 pointwise propagation 更窄；“block recursion”本身不保证更少 wrapping。
  - “结构正则 index-1”目前是自然语言限制。需要给出 checker 可判定的支持条件，包括拓扑奇异性、独立电压源/电感约束、初始一致性、质量矩阵结构、器件状态变量和不支持构造。否则定理假设与网表前端无法对应。
  - Claim P 只能证明采样点上的离散 predicate。Peak、overshoot 和 settling 若涉及网格间行为，必须返回 `UNKNOWN` 或重新定义为 discrete sampled property；当前 non-claim 已意识到这一点，最终论文必须保持相同边界。

- **实验可信度**：
  - 目前不存在实验结果，因此实验可信度只能评价为“协议设计较强、证据为零”。`experiments/`、`tests/`、`configs/` 和 `results/` 均未形成可运行研究产物。
  - 最关键 killer baseline 应是 **B2-strong**：与 BlockStamp 使用完全相同的 device evaluator、interval backend、tube、scaling、ordering、factor witness 和线程设置，只移除 temporal block recursion。除此之外还需构造 `dense generic → sparse global → device-local pointwise → BlockStamp` 四级消融，才能把收益分解到稀疏性、器件局部性和时间递推。
  - B1、B2、B3、B4、B5 的保证类型不同，主表不能只比较 runtime。应同时报告 `guarantee target`、`trusted components`、`accept/reject semantics`、`certification rate`、`tube width`、`checker time`、`generator time`、`fallback time`、`peak RSS`、`fill ratio` 和 `certificate bytes`。
  - 所有性能对比必须冻结网表、器件参数、初值、时间网格、producer trajectory、tube initializer、精度、线程数、CPU affinity、BLAS 线程、ordering 和缓存策略。计时应区分一次性模型装配、证书生成、checker、恢复和重放；否则“checker 更快”可能来自复用 producer 未计费数据。
  - `false accept = 0` 只能作为实现回归指标，不能作为 soundness 的统计证据。Soundness 依赖定理与可信算术实现；实验只验证已知 oracle 与故障集合内未观察到实现违例。
  - 第一轮不需要同时运行 SRAM、op-amp、LDO 和 1000 状态。最有判别力的序列是 analytic/diode canary、3/5-stage ring oscillator、再到 op-amp step。SRAM 的多稳态与 metastability 会同时引入局部唯一性和初始化问题，不适合作为最早算法门禁。
  - 建议新增 `accepted steps per second` 与 `end-to-end certified throughput = accepted steps / (generation + check + fallback)`，防止只看 checker runtime 而忽略低认证率。

- **叙事克制性**：
  - 当前将 “Proof-Carrying SPICE”降为系统愿景、把算法名改为 BlockStamp-Cert，并显式排除 Krawczyk、proof-carrying、全局唯一性、连续时间和真实硅片首创，这是正确的叙事选择。
  - “producer-agnostic”应限定为“对满足声明证书接口的 trajectory generation algorithm 不敏感”。受限网表语义、固定 BE、固定器件集合和证书格式仍然是强约束，不能写成支持任意 SPICE 或任意 Verilog-A。
  - DAC 版本 novelty statement 中的 “lower end-to-end cost” 只能在 Claim E/R 通过冻结基线和完整计费后使用；当前只能写成待验证假设。
  - “错误 hint 只能导致 REJECT/UNKNOWN”应补充条件：“在 checker TCB、输入语义绑定和 interval backend 正确的前提下”。
  - 当前标题聚焦 discrete nonlinear transient MNA，优于宽泛的 SPICE 可信性标题；最终摘要仍需在首段明确“只认证给定离散方程的局部根，不认证时间离散误差”。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong CCF-A)

### Risk 1：核心贡献可能退化为已有组件的组合
**攻击方式**：审稿人会指出 DC circuit Krawczyk、validated time propagation、proof-carrying architecture 和 verified sparse solves 均已有成熟先例，并要求作者展示一个不是“按时间执行 DATE 2019 + 包装证书接口”的新算法或新定理。

**现有内容能否扛住**：不能。当前只有 BlockStamp 结构假设和伪代码，没有递推公式、soundness proof、complexity/wrapping 分析或相对 B2-strong/B5 的实验信号。若 Stage 3 无法产生可归因的结构性优势，应停止强 CCF-A 主张。

### Risk 2：Soundness 合同存在数学与实现缺口
**攻击方式**：审稿人会追问区间接口的全称量化、器件分支非光滑性、index-1 可判定条件、implicit factor operator 的可靠求值、向外舍入特殊函数和失败 slab 后的下游证书有效性。

**现有内容能否扛住**：不能。当前 Claim S/C/R 是研究声明，不是形式化定理；checker 代码、区间后端、device stamp tests、factor witness verifier 和 TCB 依赖图均不存在。任何一个环节使用普通浮点近似而无 enclosure 都会使“independently checkable soundness”失效。

### Risk 3：实验尚为空，且最终范围可能缺乏工业说服力
**攻击方式**：审稿人会指出仓库只有实验协议，未展示真实 producer、真实网表、非人为数值失败、认证率、端到端成本、内存、证书大小或 scale curve；固定 BE + Level-1 MOS 的正结果也未必外推到现代 compact models 和工业 SPICE。

**现有内容能否扛住**：不能。当前只能说明实验设计意识较强。至少需要两个非线性电路类别、两个互异 producer 路径、一个非玩具开放器件模型、强 pointwise/verified sparse baselines 和完整计费，才具备强 CCF-A 实验说服力。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

> 以下任务按门禁依赖排序。P0 未通过时，不启动 P1/P2 的大规模工作。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-A对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 写作规范 | 新建形式化合同文件，把 Claim S 拆成 `S-fixed` 与 `S-param`；逐项写出变量域、量词、`C1`/interval-Jacobian 条件、index-1 条件、incoming/outgoing interface 关系、Krawczyk inclusion 和 `ACCEPT` 结论，并给出一页 proof skeleton | 强CCF-A要求定理主张与实现支持范围一一对应；当前参数化接口结论强于普通固定参数 Krawczyk | 生成 `003_formal_soundness_contract.md`；文件包含两条独立定理、假设表和每个假设对应的 checker 检查项；不存在“全局唯一”或无条件“所有错误”表述 | `paper2/steps/003_formal_soundness_contract.md`, `paper2/research/research_direction.md` |
| P0 | 文献增补 | 对 parameterized interval Newton/Krawczyk、validated DAE with interval initial sets、block time-slab nonlinear certification、verified LU/factor witness 四组关键词执行前向/后向引文追踪；对最接近的 10 篇全文记录定理号、证明对象和与 `S-param`/factor verification 的重叠 | 强CCF-A要求核心定理不能是相邻领域标准结论；当前文献审计仍存在 validated DAE 全文缺口 | 在文献矩阵中新增或更新至少 10 条 full-text 证据；单独输出“是否直接覆盖 S-param/implicit factor checking”的结论，不以未搜到同名论文作为新颖性证据 | `paper2/research/proof_carrying_spice_literature.md`, `paper2/steps/004_theorem_prior_art_closure.md` |
| P0 | 实验补充 | 实现 IEEE-754 向外舍入区间标量运算、`exp/log/sqrt` 支持和序列化 round-trip；使用 MPFR/有理 oracle 对每种运算生成 10,000 组边界、次正规数、溢出和随机输入，检查精确值均落入返回区间 | 强CCF-A的 soundness 依赖可信算术链，普通单元测试不能替代包含性质测试 | `pytest` 全部通过；`stage0_arithmetic_summary.json` 中 containment violation 为 0；不支持输入返回结构化 `UNSUPPORTED`，不得静默产生 NaN 区间 | `paper2/experiments/interval_backend.py`, `paper2/tests/test_interval_soundness.py`, `paper2/results/blockstamp/stage0_arithmetic_summary.json` |
| P0 | 实验补充 | 实现 R/C/L、独立源、diode、Level-1 MOS 的数值值、点 Jacobian 和 interval Jacobian stamp；对每个器件生成 1,000 个随机 bias box，并在 cutoff/triode/saturation 边界两侧采样 MPFR 导数，检查 interval stamp 包含全部样本 | 强CCF-A要求器件语义与定理的连续可微/分支假设可执行；跨分支 box 是当前 soundness 高风险点 | 生成每个器件的 branch-coverage 报告；所有采样值/导数被 interval enclosure 包含；跨不支持非光滑边界的 box 明确 split 或 `UNKNOWN` | `paper2/experiments/devices/`, `paper2/tests/test_device_interval_stamps.py`, `paper2/results/blockstamp/device_stamp_coverage.json` |
| P0 | 实验补充 | 构造 B2-strong：与 BlockStamp 共享相同 candidate、tube initializer、scaling、device-local stamps、ordering、factor witness、区间后端和单线程设置，只把时间处理替换为逐点认证；把所有共享字段写入 machine-readable fairness manifest | 强CCF-A要求 killer baseline 公平；否则无法把收益归因到 temporal block recursion | 生成 `baseline_fairness.json`，其中主方法与 B2-strong 的共享字段哈希完全一致；B2-strong 在 analytic canary 上返回与 dense oracle 一致的 verdict | `paper2/experiments/baselines/pointwise_krawczyk.py`, `paper2/configs/blockstamp_canary.yaml`, `paper2/results/blockstamp/baseline_fairness.json` |
| P0 | 消融补全 | 实现四级方法链：`dense generic`、`sparse global`、`device-local pointwise`、`device-local + temporal BlockStamp`；固定同一 candidate/tube/precision，分别记录 assembly、factor verification、bound propagation、peak RSS 和 verdict | 强CCF-A要求把稀疏性、器件局部性和时间结构的贡献拆开；当前组合方法无法排除普通工程实现差异 | 输出 `stage3_component_ladder.csv`，每行包含四阶段 timing、RSS、nnz/fill、certification verdict 和 inclusion margin；主论文每个核心组件均有对应对照 | `paper2/experiments/baselines/`, `paper2/experiments/blockstamp_checker.py`, `paper2/results/blockstamp/stage3_component_ladder.csv` |
| P0 | 实验补充 | 在 RC/diode analytic canary 与 3/5-stage ring oscillator 上运行 steps=`100,300,1000`、slab length=`1,2,4,8,16` 的冻结网格；比较 B2-strong、dense slab、verified sparse kernel 和 BlockStamp，报告 certification rate、最大连续 certified prefix、tube width、checker time、peak RSS 和 certificate bytes | 强CCF-A需要先证明结构性机制存在，再扩展 SRAM/Verilog-A；该网格直接测试 wrapping 与时间结构收益 | 生成完整未筛选的 `minimal_probe.csv` 和三张曲线：slab length–acceptance、slab length–tube width、slab length–runtime；所有失败样本保留 failure code | `paper2/configs/minimal_probe.yaml`, `paper2/experiments/run_minimal_probe.py`, `paper2/results/blockstamp/minimal_probe.csv` |
| P0 | 实验补充 | 构造非人为软件破坏的数值缺陷组：通过 Jacobian condition sweep、Newton tolerance sweep 和 float32/float64 center 生成至少 20 个 `converged + small normalized residual` 案例；使用 MPFR root 与 interval certificate 报告 residual、forward error、condition estimate 和 verdict | 强CCF-A的问题动机必须来自真实数值机制，不能只依赖 stamp/permutation 篡改 | 至少一个电路类别出现 residual 通过而 forward error 或唯一性证书失败；若没有出现，删除“传统收敛标志造成实际可信缺口”的强动机并记录 STOP/REFINE | `paper2/experiments/generate_numerical_defects.py`, `paper2/results/blockstamp/numerical_defect_cases.csv`, `paper2/steps/005_baseline_defect_gate.md` |
| P0 | 写作规范 | 定义 selective recovery 合同：失败 slab 重算后，仅当新 outgoing interval 是下一 slab incoming assumption 的子集时复用后缀证书；否则从第一个 containment failure 起使后缀失效并重新检查；把该规则写入伪代码和状态机 | 强CCF-A要求 Claim R 在依赖传播上 sound；当前“只重算失败 slab”可能复用无效下游证书 | 生成 recovery 状态机图和 6 个单元场景，覆盖 subset、overlap、disjoint、扩大/缩小 interval 与连续多 slab 失败；所有无效复用均被拒绝 | `paper2/steps/006_selective_recovery_contract.md`, `paper2/experiments/recovery.py`, `paper2/tests/test_recovery_contract.py` |
| P1 | 可复现性 | 在 `pyproject.toml` 中写入实际运行依赖与精确版本范围，生成锁定环境文件；为 canary 增加六个 CLI 的 `--help`、非零失败码、配置快照和 SHA-256 manifest；从干净环境执行一次全流程重放 | 强CCF-A要求结果可由独立环境重建；当前运行时依赖为空且 CLI 尚不存在 | `paper2` 干净环境安装成功；一条 README 命令重建 `minimal_probe.csv`；输入、证书和汇总哈希与记录一致 | `paper2/pyproject.toml`, `paper2/environment.yml`, `paper2/README.md`, `paper2/experiments/` |
| P1 | 可复现性 | 生成 checker import graph，并设置 denylist 阻止导入 producer evaluator、producer Jacobian、producer convergence 与 producer factorization 模块；在 CI/pytest 中加入自动失败规则 | 强CCF-A的“独立 checker”必须由代码边界证明，而不是仅靠叙述 | 生成 `tcb_import_graph.json`；人为加入任一禁止 import 时测试失败；checker 包的 TCB 文件数与代码行数被记录 | `paper2/tests/test_tcb_independence.py`, `paper2/results/blockstamp/tcb_import_graph.json`, `paper2/experiments/checker/` |
| P1 | 实验补充 | 对全部性能方法固定单线程、CPU affinity、BLAS 线程、编译选项和 warm-up；每个配置运行 5 个独立进程，分别计时 model assembly、certificate generation、checking、fallback 与 serialization，并报告 median/IQR/全范围 | 强CCF-A要求精度—性能对比公平、可解释；聚合 wall time 会隐藏 producer 数据复用和一次性成本 | 生成 `timing_breakdown.csv` 与环境快照；每项时间均有独立字段；不存在只报告成功样本或删除 timeout/reject 的记录 | `paper2/experiments/benchmark.py`, `paper2/results/blockstamp/timing_breakdown.csv`, `paper2/results/blockstamp/environment.json` |
| P1 | 实验补充 | 新增 `certified_steps_per_second` 与 `end_to_end_certified_throughput = accepted_steps/(generation+check+fallback)`；在相同 workload 上绘制 certification rate–runtime–certificate size Pareto，而非只报告 checker speedup | 强CCF-A要求同时衡量成功率和成本；低认证率的快速 checker 不能证明系统价值 | 主结果 CSV 包含两个吞吐量字段；Pareto 图保留所有方法与失败点；结论不以单一平均 speedup 代替完整前沿 | `paper2/experiments/summarize.py`, `paper2/results/blockstamp/main_metrics.csv`, `paper2/results/blockstamp/pareto.pdf` |
| P1 | 叙事修正 | 在 Claim E/R 通过前，把 novelty statement 中 “enabling ... at lower end-to-end cost” 改为待验证假设；把 “producer-agnostic” 限定为“对满足声明接口的 trajectory-generation algorithm 独立”；在摘要式方向描述中加入固定 BE、局部离散根和 TCB 条件 | 强CCF-A要求贡献主张与现有证据严格匹配；当前无性能或 soundness 实证 | `research_direction.md` 中不出现未经结果支持的 lower-cost 结论；所有 soundness 句子均带 TCB/模型/离散条件；不暗示任意 SPICE/Verilog-A 支持 | `paper2/research/research_direction.md`, `paper2/ideas/01_proof_carrying_spice.md` |
| P2 | 实验补充 | 在 P0/P1 门禁通过后，接入第二个互异 producer 路径，并使用完全相同的网表规范化、时间网格和输出变量映射运行 ring oscillator 与 op-amp；记录 producer 版本、命令、容差和原始输出 | 强CCF-A需要证明 checker 接口不是为单一自研 producer 定制，并排除共享实现缺陷 | ngspice/Xyce 或 ngspice/独立 solver 两条 producer 路径均可生成可检查证书；主结论在两个 producer 上方向一致；变量映射和模型差异写入 manifest | `paper2/experiments/producers/`, `paper2/configs/two_producer_replay.yaml`, `paper2/results/blockstamp/two_producer_results.csv` |
| P2 | 实验补充 | 在结构性门禁通过后加入一个开放、可复现的非 Level-1 compact model 或受限 Verilog-A 模型；列出支持的语法/分支/特殊函数，运行至少一个 op-amp 或 ring oscillator transient，并报告相对 Level-1 的 certification rate 与 tube growth | 强CCF-A最终实验需要超越玩具器件模型，同时保持支持边界可审计 | 生成模型 digest、许可证、语法覆盖表和结果 CSV；不支持构造返回 `UNSUPPORTED`；至少一个非手写模型完成 300 个以上时间步的认证尝试 | `paper2/experiments/models/`, `paper2/steps/007_real_model_gate.md`, `paper2/results/blockstamp/real_model_results.csv` |
