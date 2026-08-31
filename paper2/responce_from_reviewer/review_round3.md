# Review Round 3

## 1. 🎯 强CCF-B达标判定

- **当前状态**：未达标
- **核心差距**：当前已经形成可信的问题定义、先例边界和若干 soundness canary，但能够支撑 CCF-B 技术贡献的核心对象——BlockStamp 的可执行块递推、严格 operator enclosure，以及相对组件匹配的 B2-strong / verified-sparse baseline 的稳定结构性收益——仍不存在，因此目前还不能证明这是一个非平凡的新算法，而不是既有 Krawczyk、块三角求解与 circuit interval stamp 的组合应用。
- **高分录用潜力**：否（当前）。如果后续能够给出严格的 BlockStamp recurrence、在至少两个代表性非线性 transient workload 上获得可归因的 runtime / memory / certificate-size / certification Pareto 优势，并完成基本可复现闭环，则具备高分 CCF-B 潜力。

## 2. 🔄 改进效果评估

针对 `paper2/steps/` 中已经完成的修改：

- ✅ **有效改进**：
  1. `003_formal_soundness_contract.md` 已将单一 Claim S 拆成 `S-fixed` 与 `S-param`，明确 incoming interface 的量词、统一 residual/Jacobian enclosure、outgoing projection、局部唯一性和 slab composition 条件。
  2. `004_theorem_prior_art_closure.md` 主动承认 parameterized Krawczyk、validated initial-set propagation、verified factor witness 和通用 proof-carrying 架构均有先例，把候选技术贡献收缩到 device-local stamp 与 transient-MNA 时间带状结构的联合 verified operator evaluation。
  3. `006_selective_recovery_contract.md` 已解决后缀依赖问题：失败 slab 重算后，只有新的 outgoing enclosure 被下一 slab 已缓存 incoming assumption 包含时才允许复用；否则从首次 containment failure 开始重新检查。
  4. `interval_backend.py`、diode / 受限 Level-1 NMOS interval stamps 与对应测试把研究从纯协议推进到可执行 canary；跨 MOS 工作区间的 box 采用 fail-closed 策略。
  5. `005_baseline_defect_gate.md` 用弱电导造成的自然病态 MNA 展示 residual 与 forward error 可以分离，并将结论限定为 `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`。

- ⚠️ **部分解决**：
  1. `S-fixed/S-param` 的量词已清楚，但预条件算子 `C` 尚未被定义为 checker 可验证的可逆实算子；当前条件无法排除 `C=0` 等反例，正式 soundness 尚未闭合。
  2. Decimal 后端适合作为 reference canary，但 `exp/log/sqrt/div` 尚未形成对真实数学值的严格 directed enclosure，不能作为最终 certificate TCB。
  3. 当前器件代码只覆盖局部 diode/NMOS 值与导数，没有 R/C/source、charge/history、节点/支路装配、ground normalization 和完整 BE MNA residual/Jacobian。
  4. recovery 原型只验证一维 interval containment，没有真实多维 state box、certificate digest/input hash 和 actual slab replay；这一项不再阻断核心算法门禁，但不能写成已完成系统结果。
  5. fixed-step BE 与 Level-1 MOS 可支撑最小机制实验，但最终 CCF-B 版本仍需至少两个代表性非线性 transient 电路，并报告 unsupported rate 与适用范围。

- ❌ **无效/偏离**：
  1. 当前 `generate_numerical_defects.py` 中 `float32/float64` 仅为标签，未执行真实精度转换；`certificate_verdict` 为硬编码 oracle 结论，不是 checker 输出，因此不能作为论文主实验。
  2. `stage0_arithmetic_summary.json` 由人工维护，测试覆盖与汇总字段存在漂移风险；关键 soundness summary 必须由 runner 自动生成。
  3. 自上一轮有效研究修改后尚无 BlockStamp recurrence、B2-strong、dense-slab checker、BE MNA assembly、真实 transient probe 或性能结果，因此 CCF-B 录用判断没有获得新的核心证据。

## 3. 🔍 强CCF-B维度深度审查

- **问题与动机**：
  当前问题具有足够的 CCF-B 学术价值。最合理的使用场景不是声称成熟 SPICE 经常给错结果，而是针对松容差、低精度、加速器、远程服务或其他不完全可信 producer，提供结果级独立检查。现有弱电导 canary 只证明 residual 不等于 forward-error certificate；还需要至少一个 nonlinear transient tolerance / precision 案例证明该场景不是纯静态构造。

- **技术完备性与创新深度**：
  CCF-B 不要求重新定义整个 SPICE 范式，但必须存在可执行、可消融且非平凡的技术增量。当前唯一合理 headline 是：针对 BE transient MNA 的 block-lower-bidiagonal 时间结构和 device-local stamp，构造不显式形成全 slab inverse/operator 的 verified recurrence。若最终只是标准块前代，且相对组件匹配的 pointwise / verified-sparse baseline 没有稳定收益，则技术贡献不足以稳定录用。

  首版必须固定 `C` 的数学定义。推荐使用 checker-side midpoint Jacobian `M` 的可逆 block-solve operator；producer 只提供 permutation / scaling / factor hints，checker 定义并验证最终算子。S-param、composition、property monitor 和 selective recovery 可以作为系统增量，而不必全部成为新定理。

- **实验可信度**：
  当前没有主方法实验。最小稳定 CCF-B 闭环至少需要：一个真正 directed-rounded backend；R/C/source/diode 的 BE MNA；B2-strong；dense slab 或 verified sparse baseline；BlockStamp；diode-RC 与 ring oscillator 两类 nonlinear transient probe；并报告 certification rate、certified prefix、tube width、checker/generator/fallback time、peak RSS、certificate bytes 和 end-to-end certified throughput。所有对比必须共享 candidate、tube、scaling、ordering、factor、线程与硬件配置。

- **叙事克制性**：
  `Proof-Carrying SPICE` 应继续作为系统愿景，论文 headline 应聚焦 `circuit-structured certification of fixed-discretization transient MNA`。Krawczyk、S-param、time-slab composition、verified factor witness 和 producer/checker 架构不能单独列为创新。在 Claim E 获得数据前，禁止使用 `faster`、`less wrapping`、`lower end-to-end cost` 等完成时态结论。

## 4. ⚔️ 模拟评审攻击
### Top 3 Rejection Risks for Strong CCF-B

### Risk 1：核心方法可能只是已有 verified numerics 组件的直接组合

1. **审稿人可能如何质疑**：BlockStamp 是否仅等价于对块下双对角矩阵执行标准前代，再套入已有 Krawczyk 框架？
2. **当前论文有什么证据可以回应**：文献审计已经明确缩小 novelty，并提出 device-local + temporal structure 的候选方向。
3. **当前证据能否扛住该攻击**：不能。仓库没有 recurrence、operator theorem、dense-equivalence 或 component ladder 数据。
4. **如果不能，缺少什么具体证据**：需要唯一明确的递推公式、包含性证明、复杂度/内存分析，以及 `dense generic → device-local pointwise → temporal-only → temporal+device` 四级对照。

### Risk 2：sound certificate 的数学与算术链尚未闭合

1. **审稿人可能如何质疑**：奇异 `C`、非严格特殊函数区间、器件参数普通浮点组合和不完整 MNA assembly 是否会让错误结果被 ACCEPT？
2. **当前论文有什么证据可以回应**：已有 S-fixed/S-param 合同、跨器件分支 fail closed 和随机 containment canary。
3. **当前证据能否扛住该攻击**：不能。随机测试不能替代定理前提和 directed rounding。
4. **如果不能，缺少什么具体证据**：需要显式 `C` 可逆前提与反例测试、MPFR 类定向舍入后端、完整 BE MNA assembly，以及 analytic/MPFR oracle 上的真实 checker verdict。

### Risk 3：缺少能够证明实际价值的主实验

1. **审稿人可能如何质疑**：即使 checker 理论成立，为什么它不是比严格重算更慢、认证率很低、只能处理玩具电路的系统？
2. **当前论文有什么证据可以回应**：已有完整实验协议和 end-to-end 计费设计。
3. **当前证据能否扛住该攻击**：不能。协议不是结果。
4. **如果不能，缺少什么具体证据**：需要 diode-RC 与 ring oscillator 的未筛选结果；B2-strong / dense / BlockStamp 同配置比较；每个 timing 配置至少 5 次独立进程；报告 acceptance、prefix/tube、runtime、RSS、bytes 和 failure code。

## 5. 🛠️ 下一轮原子化改进工单
### Atomic Action Items

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-B对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 写作规范 | 在 formal contract 中将 `C` 固定为 checker 可验证的可逆实算子；首版定义为 checker 重建的 point midpoint block-lower-bidiagonal Jacobian `M` 的 inverse action；加入 `F(x)=x+2, X=[-1,1], C=0` 反例并新增自动测试 | 数值假设透明度、技术完整性；当前定理存在直接反例 | `003_formal_soundness_contract.md` 出现明确可逆条件；奇异 `C` 测试返回 `UNSUPPORTED/UNKNOWN`，不得 ACCEPT | `paper2/steps/003_formal_soundness_contract.md`, `paper2/tests/test_krawczyk_soundness_contract.py` |
| P0 | 实验补充 | 新建 MPFR/等价 directed-rounding 后端，实现 `add/sub/mul/div/exp/expm1/log/sqrt` 的 RNDD/RNDU；每项运行至少 50,000 个随机及边界输入，runner 自动写 summary | 核心 soundness、可复现性 | `rigorous_backend_summary.json` 中 supported 输入 containment violation 为 0；覆盖 subnormal、overflow frontier、near-zero denominator 和 cancellation | `paper2/experiments/rigorous_backend.py`, `paper2/tests/test_rigorous_backend.py`, `paper2/results/blockstamp/rigorous_backend_summary.json` |
| P0 | 实验补充 | 在 `paper2/experiments/mna/` 实现 R、C、独立电流源、独立电压源和 diode 的 fixed-step BE residual、history、point Jacobian 与 interval Jacobian assembly；运行 RC analytic 与 diode-RC MPFR oracle 各 100 个时间步 | 技术完整性、问题真实性 | RC 离散解与解析 oracle 一致；diode-RC MPFR roots 全部被合法 certificate tube 包含；错误 history/节点映射不得 ACCEPT | `paper2/experiments/mna/`, `paper2/tests/test_be_mna_assembly.py` |
| P0 | 实验补充 | 新建 `blockstamp_operator.py`，实现 `U_a=VSolve(D_a,R_a)`、`U_k=VSolve(D_k,R_k-L_kU_{k-1})`；在 block dimension=`1,2,4,8`、slab=`2,4,8` 上各生成至少 200 个非奇异实例，并与 MPFR dense action 逐元素核对 | 方法创新性、技术完整性 | recursive enclosure 在全部实例中包含 MPFR dense action；生成 `operator_canary.json`，记录实例数、失败数和最大 enclosure inflation | `paper2/experiments/blockstamp_operator.py`, `paper2/tests/test_blockstamp_dense_equivalence.py`, `paper2/results/blockstamp/operator_canary.json` |
| P0 | 实验补充 | 实现 `B2-strong` pointwise Krawczyk checker；与 BlockStamp 共享 backend、MNA/device semantics、candidate、tube、scaling、ordering、midpoint factor 与单线程设置；将共享项 SHA-256 写入 fairness manifest | Baseline 公平性 | `b2_fairness.json` 中共享组件 hash 一致；RC/diode-RC easy cases 可认证；坏 tube 0 false accept | `paper2/experiments/checkers/pointwise_krawczyk.py`, `paper2/configs/blockstamp/b2_canary.yaml`, `paper2/results/blockstamp/b2_fairness.json` |
| P0 | 消融补全 | 实现 `dense-slab generic`、`device-local pointwise`、`temporal-only`、`temporal+device BlockStamp` 四级 component ladder；固定同一输入、tube、backend 和 factor，记录 assembly、verified solve、总检查时间、RSS、bytes、acceptance 与 inclusion margin | 核心模块必要性、方法创新性 | 生成 `component_ladder.csv`，保留全部失败配置和 failure code | `paper2/experiments/checkers/`, `paper2/experiments/blockstamp_operator.py`, `paper2/results/blockstamp/component_ladder.csv` |
| P0 | 实验补充 | 在 diode-RC 和 3-stage ring oscillator 上冻结 `steps={100,300,1000}`、`slab={1,2,4,8,16}`；B2-strong、dense slab 与 BlockStamp 使用相同 producer trace/tube/backend；每个 timing 配置运行 5 个独立进程 | Benchmark代表性、Baseline公平性、Scalability | 生成未筛选的 `minimal_probe.csv`，包含 certification、prefix/tube、runtime、RSS、bytes 和 failure code；输出 slab-length–acceptance 与 steps–runtime/RSS 曲线 | `paper2/configs/blockstamp/minimal_probe.yaml`, `paper2/experiments/run_minimal_probe.py`, `paper2/results/blockstamp/minimal_probe.csv` |
| P1 | 实验补充 | 修改 `generate_numerical_defects.py`：真实执行 float32/float64 center cast；调用实际 checker 产生 `checker_verdict`；把解析事实单独保存为 `oracle_root_in_tube`；删除硬编码 `REJECT_ROOT_OUTSIDE_TUBE` | Motivation 真实性、实验可信度 | float32/float64 至少存在可观察数值差异；`checker_verdict` 只来自 checker API；无无根证明时仅允许 `ACCEPT/UNKNOWN/UNSUPPORTED` | `paper2/experiments/generate_numerical_defects.py`, `paper2/results/blockstamp/numerical_defect_cases.csv`, `paper2/tests/test_numerical_defects.py` |
| P1 | 文献增补 | 将历史阶段审计已识别的 block-Krawczyk、interval cyclic reduction、factorized Krawczyk 高威胁近邻正式写入 prior-art matrix；逐篇记录 proof object、结构假设、复杂度与 BlockStamp 的差异 | Related Work 定位、方法创新性 | prior-art matrix 写明这些工作的直接重叠；novelty statement 不再使用泛化“block Krawczyk”作为差异 | `paper2/steps/004_theorem_prior_art_closure.md`, `paper2/research/proof_carrying_spice_literature.md` |
| P1 | 可复现性 | 在 `paper2/pyproject.toml` 写入实际 rigorous backend 和运行依赖并生成锁定环境；新增 CI 只运行 arithmetic、operator dense-equivalence、BE MNA、B2 canary 和 recovery tests；在 `paper2/README.md` 写一条重建 `minimal_probe.csv` 的命令 | 可复现性 | 干净环境安装成功；CI 全绿；README 命令可重建 `minimal_probe.csv` 和配置快照 | `paper2/pyproject.toml`, `.github/workflows/paper2-blockstamp.yml`, `paper2/README.md` |
| P1 | 叙事修正 | 在最小 probe 出结果后，根据实际数据更新 Claim E；若只降低 memory/runtime 则删除“less wrapping”，若只在短 slab 有收益则写明支持范围，若 B2 已足够则将 BlockStamp headline 降级 | 贡献克制性、结果-主张一致性 | Claim E 中每个定量词都能映射到 `minimal_probe.csv` 对应字段 | `paper2/research/research_direction.md`, `paper2/README.md` |
