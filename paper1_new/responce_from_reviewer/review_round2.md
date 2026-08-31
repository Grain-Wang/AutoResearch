# Review Round 2

## 1. 🎯 强CCF-A达标判定
- **当前状态**：未达标
- **核心差距**：本轮已把数学量词、TCB 边界、器件分支和 recovery 依赖从概念声明推进到可执行 canary，但论文唯一可能成立的核心贡献——BlockStamp 隐式递推及其相对 B2-strong/verified sparse baseline 的结构性收益——仍未实现；现有区间后端也尚不能作为严格 soundness 的最终算术基础。
- **A类顶流潜力**：否（当前）。方向仍保留较高上限，但 Best Paper Nomination 至少要求一个新的器件—时间结构化 operator bound/recurrence、对应 soundness/complexity 证明，以及跨真实非线性瞬态电路的可归因 Pareto 优势；本轮产物主要属于前置可信性建设。

## 2. 🔄 改进效果评估
针对 `paper2/steps/` 中 Round 1 后的提交：

- ✅ **有效改进**：
  1. `003_formal_soundness_contract.md` 将 Claim S 拆为 `S-fixed` 与 `S-param`，明确了 incoming interface 的量词、统一 residual/Jacobian enclosure、局部唯一性、outgoing projection、组合条件和 TCB 条件。该修改直接回应了上一轮“固定参数结论被误写成区间参数结论”的核心质疑。
  2. `004_theorem_prior_art_closure.md` 明确认定 parameterized Krawczyk、initial-set propagation 和 verified factor witness 均属于既有方法，剩余候选贡献仅为“同时利用 device stamp 与时间块下双对角结构的隐式 Krawczyk operator 计算”。这一收缩显著提高了 novelty 定位的可信度。
  3. `006_selective_recovery_contract.md` 已将“只重算失败 slab”改造成依赖安全合同：新 outgoing enclosure 只有被缓存 incoming assumption 包含时才允许 replay；否则从第一个 containment failure 起使后缀失效。`recovery.py` 与对应测试覆盖 subset、equal、overlap、disjoint、扩大区间和后续边界失效。
  4. `interval_backend.py`、diode/受限 Level-1 NMOS stamp 与 25 个参数化测试，使仓库从“只有实验协议”推进到“存在可运行 Stage-0 canary”。代码拒绝非有限区间、除零区间、非法 `log/sqrt` 域及跨 MOS 区域 box，体现了正确的 fail-closed 设计倾向。
  5. `005_baseline_defect_gate.md` 使用弱电导导致的自然病态 MNA，展示了 small residual 与 1 V forward error 可以分离，并明确把结论标记为 `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`，没有把该例外推为工业普遍性。
  6. `response_round1.md` 对未完成部分表述克制：没有宣称 BlockStamp soundness、Claim E/R 性能或 Paper Candidate 状态，且把下一门禁固定为 B2-strong 与显式 dense operator 交叉检查。

- ⚠️ **部分解决**：
  1. `S-fixed/S-param` 目前仍是标准 Krawczyk 论证的 proof skeleton。合同没有显式写出所采用定理版本要求的 `C` 非奇异性或等价 regularity 条件，也没有精确定义“producer factor 所诱导的固定实算子 C”与 checker 区间求值之间的对象关系。正式 soundness 证明尚未闭合。
  2. 当前 Decimal 后端只对 binary64 输入建立 exact Decimal image；`exp/log/sqrt` 在默认 nearest rounding 的有限精度 Decimal 上求值，再相对该近似值做一次 binary64 outward conversion。这不能证明返回端点相对真实超越函数值向外。除法也缺少对 Decimal 舍入误差的显式包围。随机点 0 violation 只能作为回归信号，不能使该后端进入最终 TCB。
  3. device stamp 测试使用 `diode_point/mos_point` 与 interval 实现共享公式和 binary64 参数运算，存在 common-mode error。尤其 `saturation_current / thermal_voltage` 先在普通 float 中计算，再作为点区间使用；测试无法排除该比例舍入导致的 derivative enclosure 缺口。
  4. 当前 device 代码只覆盖 diode 与受限 NMOS 的标量值/导数，没有 R/C/L、独立源、charge stamp、BE history、节点装配和完整 MNA Jacobian。因此它尚未验证“瞬态离散 MNA checker”这一核心对象。
  5. recovery canary 只处理一维 `Interval` 和静态缓存链，`certificate_digest` 未参与检查，也没有执行真实 certificate replay/recheck。它验证了边界包含逻辑，但尚未验证多维 box、输入哈希、slab 配置变化和重算后的完整状态机。
  6. 本轮提交没有 B2-strong、dense slab Krawczyk、verified sparse kernel、BlockStamp recurrence 或任何 runtime/memory/certificate-size 数据，因而没有推进 Claim E 的实证状态。

- ❌ **无效/偏离**：
  1. `generate_numerical_defects.py` 中的 `float32`/`float64` 只是标签，计算路径没有执行相应 cast；两组数据完全重复。该文件也没有运行 producer 或 checker，而是直接写入 `producer_converged` 与硬编码的 `certificate_verdict`。它是解析示例表，不是仿真或认证实验。
  2. `REJECT_ROOT_OUTSIDE_TUBE` 是由已知解析根得到的 oracle 标签，不是当前 checker 的输出。Krawczyk inclusion 失败通常只能返回 `UNKNOWN/NOT_CERTIFIED`；只有额外无根判据成立时才能声称 tube 内无根。当前字段名会混淆 oracle 与 checker verdict。
  3. `stage0_arithmetic_summary.json` 声称 `boundary_cases_per_operation = 7`，但现有边界测试只对 `add` 执行七个值，没有对 subtract/multiply/divide 分别执行七组边界输入；该汇总不是由测试程序自动生成，存在与代码漂移的风险。
  4. `research_direction.md` 的 BlockStamp 步骤仍写有“失败后只拆分或重算该 slab”，与已修订的 suffix invalidation 合同不一致。Claim R 段落是正确版本，但算法描述仍保留上一轮 overclaim。
  5. 提交说明记录 `25 passed`，但该 commit 没有 GitHub Actions workflow/status、测试日志、环境快照或机器可核验的 run artifact。当前只能确认测试文件数量与声明相符，不能从远程仓库独立确认执行结果。

## 3. 🔍 强CCF-A维度深度审查
- **问题与动机**：
  - 弱电导 canary 证明了一个严格但很窄的事实：病态 MNA 中 small residual 不控制 forward error。这个事实足以保留 Research Opportunity，却不足以证明成熟 transient SPICE 的实际痛点严重到支撑强 CCF-A。
  - 当前例子是二维线性、静态、解析构造；没有 Newton 提前终止、非线性器件、BE history、相位漂移、错误阈值判定或真实 ngspice/Xyce trajectory。下一门禁必须在 diode 或 ring oscillator 的自然 tolerance/conditioning sweep 中复现可信缺口。
  - “低成本认证比严格重算更有价值”仍完全没有数据。若 candidate 生成成本、certificate generation、checker 和 suffix recheck 的总成本不低于 strict rerun，系统动机将明显削弱。

- **技术完备性与创新深度**：
  - 本轮形式化收缩是必要工作，但 `S-fixed`、`S-param`、区间初值传播、factor witness 与 recovery containment 均不能作为 headline novelty。核心 novelty 仍只有 BlockStamp recurrence。
  - 强 CCF-A 版本需要给出明确矩阵对象：每步 diagonal block、history subdiagonal block、producer witness、checker 实算子 `C`、区间 remainder，以及沿时间前代得到的 center/radius bound。随后用归纳证明该递推包含显式 dense Krawczyk operator 的真实作用。
  - 当前 interval backend 的多项式基本运算可以作为原型，但超越函数链尚不具备严格下界/上界证明。由于 diode 和 compact model 大量依赖 `exp/log/sqrt`，该问题属于 Claim S 的 P0 阻断项，而不是普通数值精度问题。
  - device branch policy 选择 `UNKNOWN` 是正确的，但 `None` 返回值没有结构化 reason、分支边界、建议 split point 或输入 digest。最终 checker 需要 machine-checkable failure code，才能支持自适应 slab/box split 与可复现失败分析。
  - 当前没有 topology normalization、index-1 support checker、MNA state layout、charge-oriented residual 或 sparse factor verification。A1/A5 仍是文档义务，尚未成为可执行前提。

- **实验可信度**：
  - 本轮新增的是单元/性质 canary，不是论文主实验。没有任何数据能够比较 B2-strong 与 BlockStamp，也没有 certification rate、tube growth、inclusion margin、accepted throughput、runtime、RSS、fill ratio 或 certificate bytes。
  - 算术测试随机分布集中在 `[-1e100, 1e100]`，几乎不覆盖次正规数、接近 overflow、除数接近零、强 cancellation 和超越函数 hard-to-round 区域；特殊函数只测试约 `[-50,50]`。现有“0 violation”不能外推到全 binary64 域。
  - device 测试对每个 box 只抽取有限点，并用共享实现作为 point oracle。强回归测试应使用独立高精度表达式与系统化边界样本，尤其覆盖阈值、区域边界、极小/极大参数和指数溢出前沿。
  - numerical-defect CSV 的 24 行来自 12 个解析参数点乘两个无效 precision 标签，不应按 24 个独立 case 报告；统计或主图中必须按唯一电路/参数 instance 计数。
  - 远程分支没有 CI check。对于以 soundness 为核心的论文，测试、环境和生成摘要必须由自动流程绑定到 commit SHA，不能依赖手工 JSON 与 handoff 描述。

- **叙事克制性**：
  - 研究方向对 local/discrete/non-global/non-silicon 边界保持克制，且已将 producer-agnostic 限定到声明接口，这是本轮最成熟的部分。
  - `response_round1.md` 对“canary 不等于 theorem”“fault injection 不等于统计 soundness”“尚非 Paper Candidate”的表述可信，应继续保留。
  - 需要删除或重命名所有把 oracle 事实写成 checker verdict 的字段，并把“only failed slab”统一改成“从失败 slab 开始恢复，并对依赖后缀执行 containment replay 或 recheck”。
  - 在 rigorous backend、B2-strong 和 BlockStamp recurrence 出现之前，不能在摘要或 novelty statement 中使用 `sound checker implementation`、`lower cost`、`safe acceleration` 或 `independent certificate verifier` 的完成时表述。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong CCF-A)

### Risk 1：核心方法仍不存在，贡献仍可能是标准方法的组合
**攻击方式**：审稿人会承认形式化合同和 canary 做得认真，但指出仓库中没有 BlockStamp recurrence、没有隐式 operator bound、没有 complexity/wrapping theorem，也没有 B2-strong 对比；因此论文核心仍是 DATE 2019、validated propagation 和 proof-carrying 接口的组合。

**现有内容能否扛住**：不能。`004_theorem_prior_art_closure.md` 甚至主动把除 recurrence 外的候选贡献全部归入既有方法。下一轮若仍未产生 recurrence + dense equivalence proof/test，不应进入 SRAM、Verilog-A 或大规模实验。

### Risk 2：当前算术实现不能支撑严格 soundness
**攻击方式**：审稿人会检查 Decimal special functions、参数比例、普通 float point oracle 和随机采样，指出 lower/upper endpoint 没有相对真实函数值的证明；diode interval 与 point test 共享同一舍入路径，可能共同通过错误实现。

**现有内容能否扛住**：不能。当前可以称为 arithmetic canary，但不能称为 verified arithmetic backend。必须建立显式 directed-rounding chain、独立高精度 oracle 和极值域回归，再把该链连接到 device stamp 与 Krawczyk operator。

### Risk 3：问题证据和实验结果仍是合成标签，而非真实 transient certification
**攻击方式**：审稿人会指出二维静态矩阵没有运行 SPICE，float32/float64 标签未改变计算，certificate verdict 是硬编码，且没有任何 transient MNA、实际 checker、runtime 或 scale 数据。

**现有内容能否扛住**：不能。该 canary只能证明线性代数可能性，不能证明论文 utility。需要实际 BE circuit assembly、真实 candidate、独立 root oracle 和 checker verdict，并在 ring oscillator 或 diode transient 上报告未筛选结果。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

> P0 门禁未通过时，不启动 SRAM、Verilog-A、BDF2、第二 producer 或完整规模矩阵。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-A对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 写作规范 | 在 `S-fixed` 与 `S-param` 定理中写明所采用 Krawczyk 定理的正式出处、`C` 的固定实算子解释、非奇异/regularity 前提、严格包含定义及 uniqueness 适用范围；删除“由 strict inclusion 自动隐含全部 nonsingularity”但未证明的表述 | 强CCF-A要求定理假设可由 checker 执行且与标准理论一致 | `003_formal_soundness_contract.md` 包含精确引用、完整前提和一条从 certificate floats 到固定实 `C` 的语义定义；两条定理不依赖未声明条件 | `paper2/steps/003_formal_soundness_contract.md` |
| P0 | 实验补充 | 将 `exp/log/sqrt/divide` 改为分别计算向下与向上界的实现：使用 MPFR/MPFI 显式 rounding mode，或对 Decimal nearest result 构造有证明的 decimal predecessor/successor 包围后再转换到 binary64；为每个操作加入次正规数、接近 overflow、近零除数、cancellation 和 hard-to-round 输入集 | Claim S 依赖全链路向外舍入；当前 fixed-precision nearest Decimal 不能构成严格包含证明 | 生成 `stage0_arithmetic_summary.json` 的自动脚本；每个 operation/function 至少 10,000 个随机 interval box 加固定 edge corpus，独立 512-bit oracle 下 0 violation；所有 overflow/domain 失败返回结构化状态 | `paper2/experiments/interval_backend.py`, `paper2/tests/test_interval_soundness.py`, `paper2/experiments/run_stage0_arithmetic.py`, `paper2/results/blockstamp/stage0_arithmetic_summary.json` |
| P0 | 实验补充 | 把 diode 的 `Is/Vt` 改为 interval division，不在普通 float 中预计算比例；使用独立 MPFR 表达式对 current/conductance 生成 oracle；新增跨 0 V、接近指数 overflow 和参数极值的 box；将 device failure 从 `None` 改为带 reason/region/split-point 的结构化结果 | 强CCF-A的 device semantics 必须避免 common-mode oracle 与未包围参数运算 | 10,000 个 diode box 与每个 MOS region 3,000 个 box 均由独立 oracle 验证；跨区域 box 返回确定 failure code；生成机器可重建的 `device_stamp_coverage.json` | `paper2/experiments/devices/stamps.py`, `paper2/tests/test_device_interval_stamps.py`, `paper2/results/blockstamp/device_stamp_coverage.json` |
| P0 | 实验补充 | 实现 R/C、独立源和 diode 的一阶 BE MNA assembly，明确 `q(x_k)-q(x_{k-1})+h i(x_k)`、变量顺序、数值 residual、点 Jacobian 和 interval Jacobian；用 RC 闭式离散根与单二极管多精度根交叉检查 | 当前代码没有瞬态、charge 或 MNA，无法检验论文证明对象 | 新增 1-step 与 10-step analytic tests；数值 residual/Jacobian 与独立 oracle 在冻结容差内一致，interval Jacobian 包含 1,000 个采样 Jacobian；非法拓扑返回 `UNSUPPORTED` | `paper2/experiments/mna/`, `paper2/tests/test_be_mna_assembly.py` |
| P0 | 实验补充 | 实现 B2-strong pointwise Krawczyk checker，并让 valid tube、root-excluding tube、过宽/跨分支 tube 分别返回 `ACCEPT`、`NOT_CERTIFIED/NO_ROOT_ONLY_IF_PROVED`、`UNKNOWN/UNSUPPORTED`；禁止从解析 root 直接写 checker verdict | 强CCF-A要求 killer baseline 与主方法共享 soundness 链，且 verdict 语义不能与 oracle 混合 | analytic RC/diode canary 上 checker verdict 与 dense oracle 一致；`numerical_defect_cases.csv` 新增独立的 `oracle_root_in_tube` 与 `checker_verdict` 字段，删除硬编码 `REJECT_ROOT_OUTSIDE_TUBE` | `paper2/experiments/baselines/pointwise_krawczyk.py`, `paper2/tests/test_pointwise_krawczyk.py`, `paper2/results/blockstamp/numerical_defect_cases.csv` |
| P0 | 写作规范 | 新建 BlockStamp recurrence 文件，逐步定义 diagonal/subdiagonal block、固定实算子 `C`、中心修正、radius/remainder 递推和 outward-rounded实现；给出“递推结果包含显式 dense operator action”的归纳证明和复杂度假设 | 这是当前唯一未被 prior art closure 消除的候选算法贡献 | `007_blockstamp_recurrence.md` 包含公式、伪代码、proof lemma、复杂度和失败条件；不把普通 block forward substitution 写成首创 | `paper2/steps/007_blockstamp_recurrence.md`, `paper2/research/research_direction.md` |
| P0 | 实验补充 | 实现小矩阵 BlockStamp recurrence，并对 1,000 个随机 block-lower-bidiagonal 系统（block size `2,4,8`，slab length `2,4,8,16`）与显式 dense interval operator 逐元素交叉检查；所有方法共享同一 tube、scaling、ordering、factor witness 和 interval backend | 强CCF-A要求核心递推先通过等价/包含 canary，再进入电路主实验 | 每个 BlockStamp bound 包含对应 dense real/operator oracle；0 false containment；输出 `blockstamp_dense_crosscheck.json` 与 failure seeds | `paper2/experiments/blockstamp_checker.py`, `paper2/tests/test_blockstamp_dense_crosscheck.py`, `paper2/results/blockstamp/blockstamp_dense_crosscheck.json` |
| P0 | 消融补全 | 建立 `dense generic → sparse global → device-local pointwise/B2-strong → device-local + temporal BlockStamp` 四级方法链，冻结 candidate、tube、precision、线程、ordering 和 witness，并分别计时 assembly、factor checking、operator propagation 与内存 | 强CCF-A要求收益可归因到稀疏性、device locality 与 temporal recurrence，而非实现差异 | 生成 `baseline_fairness.json`，共享字段哈希完全一致；生成 `stage3_component_ladder.csv`，含 verdict、inclusion margin、time、RSS、nnz/fill 和 certificate bytes | `paper2/experiments/baselines/`, `paper2/configs/blockstamp_canary.yaml`, `paper2/results/blockstamp/baseline_fairness.json`, `paper2/results/blockstamp/stage3_component_ladder.csv` |
| P0 | 实验补充 | 在 diode transient 与 3/5-stage ring oscillator 上执行 tolerance=`tight,default,loose`、precision=`float64,float32`、steps=`100,300,1000`、slab length=`1,2,4,8,16` 的冻结网格；实际 cast candidate，使用独立多精度 root，记录 SPICE-style scaled residual、forward error、condition estimate、checker verdict 和失败原因 | 当前静态线性表不能证明真实 nonlinear transient 可信缺口或结构收益 | 输出未筛选 `minimal_probe.csv`；至少出现一个自然 residual/convergence 通过而 certificate 未通过的非线性案例，否则将 Gate 1 改为 `FAIL_REAL_WORKLOAD`；同时报告 certification rate、tube growth、runtime 和 accepted steps/s | `paper2/configs/minimal_probe.yaml`, `paper2/experiments/run_minimal_probe.py`, `paper2/results/blockstamp/minimal_probe.csv`, `paper2/steps/005_baseline_defect_gate.md` |
| P0 | 叙事修正 | 将 `research_direction.md` 中“只拆分或重算失败 slab”替换为“从失败 slab 启动恢复，并按 boundary containment replay 或 recheck 依赖后缀”；把 `certificate_verdict`、`oracle verdict` 和 `implementation regression result` 三类术语在 README、结果 schema 与回应中分开 | 强CCF-A要求 Claim R 与实现状态机一致，且 oracle 事实不能伪装为 checker 输出 | 全仓库检索不存在无条件 `only failed slab` 或硬编码 `REJECT_ROOT_OUTSIDE_TUBE` 主张；结果 schema 为三类结论使用不同字段 | `paper2/research/research_direction.md`, `paper2/README.md`, `paper2/responce_from_reviewer/response_round1.md` |
| P1 | 可复现性 | 在 `pyproject.toml` 写入实际 runtime/dev 依赖并生成锁定文件；新增 GitHub Actions，在 Python 3.12 上运行 Ruff、Black、全部 `paper2/tests` 和结果 schema 校验；由 CLI 自动写入 commit SHA、环境、命令和测试计数 | 强CCF-A要求远程提交可独立核验，当前 25 passed 只有文字记录 | paper2 分支出现绿色 CI status；workflow artifact 包含测试日志与 Stage-0 JSON；从干净环境执行 README 命令可重建两个 canary 结果 | `paper2/pyproject.toml`, `.github/workflows/paper2-canary.yml`, `paper2/README.md` |
| P1 | 实验补充 | 将 recovery 数据结构扩展为多维 interval box，并在实际 certificate replay 中校验 digest、netlist/time-grid hash、incoming assumption、outgoing enclosure 与 failure index；执行连续两次重算和中间 slab 失效场景 | Claim R 需要验证真实依赖图，不只是标量 subset 函数 | 至少 12 个状态机场景全部通过；任何 digest/hash 或 containment 不匹配均使最早依赖后缀失效；输出机器可读 replay trace | `paper2/experiments/recovery.py`, `paper2/tests/test_recovery_contract.py`, `paper2/results/blockstamp/recovery_replay_trace.json` |
| P1 | 文献增补 | 在 BlockStamp recurrence 公式冻结后，以该公式中的 block operator、verified block triangular solve、interval block forward substitution 和 banded Krawczyk 为精确检索式，核验至少 8 篇全文并记录定理号 | 强CCF-A要求最终 headline recurrence 不与数值线性代数中的标准 block verified solve 重复 | `004_theorem_prior_art_closure.md` 新增 recurrence-specific matrix；若发现直接覆盖，立即收缩或停止算法首创主张 | `paper2/steps/004_theorem_prior_art_closure.md`, `paper2/research/proof_carrying_spice_literature.md` |
