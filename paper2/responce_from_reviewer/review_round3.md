# Review Round 3 — BlockStamp-Cert 阶段性评审与后续研究路线

## 0. 本轮审查范围

本轮将 `paper2` 视为 CoVoL 停止后的新选题进行阶段评审。远程 `paper2` 分支当前
HEAD 为 `b633970070c5fedbcc4f4c241a4baf98160adc45`；该提交已经包含
`review_round2.md`，但尚无 `response_round2.md` 或该评审后的方法增量。因此，本轮结论
主要是**选题与研究路线评审**，不是对 Round 2 改进结果的验收。

审查对象包括：

- `ideas/01_proof_carrying_spice.md`；
- `research/research_direction.md`；
- `research/proof_carrying_spice_literature.md`；
- `steps/001` 至 `steps/006`；
- 当前 interval backend、device stamps、recovery 原型、baseline-defect canary 与测试；
- Round 1 response 和 Round 2 review；
- 对块结构 verified computation / Krawczyk 近邻的补充检索。

## 1. 阶段性判定

- **Research Opportunity Gate**：**PASS**。
- **Minimal Problem Probe**：**尚未完成**。
- **Paper Candidate Gate**：**FAIL / UNVERIFIED**。
- **强 CCF-C 潜力**：**有，条件性较强**。若完成严格算术、可执行 transient MNA、
  component-matched B2/B3/B5 和 BlockStamp 结构性信号，受限器件与两个非线性电路也
  可能形成一篇扎实 CCF-C/领域会议工作。
- **DAC / 强 CCF-A 潜力**：**有较高上限，但当前距离很远**。必须新增可辨认的
  operator recurrence/bound，而不能只把标准块三角求解、区间 Krawczyk 和 proof-carrying
  接口组合起来；还要在多个电路类别、规模和 producer 路径上形成端到端 Pareto 优势。

### 当前成熟度估计

| 维度 | 当前成熟度 | 强 CCF-C 基线 | DAC/强 CCF-A 基线 | 主要缺口 |
| --- | ---: | ---: | ---: | --- |
| 问题定义与边界 | 82/100 | 75 | 85 | 离散局部根的边界清楚；但真实使用场景和 producer 威胁模型仍偏抽象 |
| 新颖性边界 | 55/100 | 65 | 85 | 已主动撤回通用 Krawczyk/S-param/factor novelty；核心 recurrence 尚不存在且新增 block-Krawczyk prior art |
| 数学与方法完整性 | 25/100 | 65 | 85 | S-fixed 定理缺少 `C` 非奇异条件；无 BlockStamp recurrence、完整 MNA 或 verified operator |
| 实验证据 | 18/100 | 70 | 85 | 只有静态病态 canary 与算术/器件单元测试；无真实 transient checker 或强 baseline 数据 |
| 可复现性与研究纪律 | 62/100 | 65 | 80 | 门禁、范围和测试意识较强；无 CI、正式 TCB、运行 artifact 或主表重放 |

按强 CCF-C 口径，当前约为 **43/100**，距离可投稿基线约 **27 分**；按 DAC/强
CCF-A 口径约为 **33/100**，差距约 **50 分以上**。这不是线性补代码即可弥补的差距，
核心取决于 recurrence 是否成立并带来可归因优势。

## 2. 为什么该方向值得继续

### 2.1 问题比一般“提高 SPICE 精度”更清楚

当前证明对象已经严格限定为：给定网表语义、固定初值/激励、固定步长 Backward Euler
离散方程，在声明 tube 内存在局部唯一离散根。它明确不覆盖连续时间截断误差、模型误差、
全局唯一性或真实硅片。这一边界能够避免把 numerical certification、formal AMS
verification 和 silicon sign-off 混在一起。

### 2.2 资源条件友好，但知识门槛高

该方向主要依赖 CPU、可靠浮点/区间算术、稀疏线性代数和小中型电路，不依赖大规模私有
数据或多卡训练。对单机/单卡研究者而言，计算资源不是首要瓶颈；真正瓶颈是定理正确性、
TCB 可信度和强 baseline 的公平实现。

### 2.3 有明确的系统价值假设

若轨迹来自云端仿真器、GPU 加速器、近似求解器或不可信第三方，消费者希望检查结果而非
完整重复执行。该动机可以成立，但论文必须实证说明 certificate 生成、传输、检查和失败
回退的总成本低于独立严格重算；仅说明“普通 convergence flag 不是数学证明”不够。

### 2.4 负结果路径清楚

仓库已经写明：如果 pointwise verified checker 足够便宜、slab wrapping 迅速爆炸、
BlockStamp 与 dense/verified-sparse baseline 无差异，或 checker 基本复制完整模拟成本，
就停止效率/论文主张。这种可证伪性应继续保留。

## 3. 新颖性红队：剩余空间比当前文档还窄

### 3.1 已知覆盖不得作为贡献

仓库正确认定以下内容属于既有方法：Krawczyk/interval Newton、参数化 root enclosure、
initial-set propagation、verified factor witness、proof-carrying producer/checker 架构、
DC circuit interval verification 和 validated ODE/DAE integration。

补充检索还发现三类必须加入高威胁近邻：

1. Chen 与 Hashimoto 2003 已提出基于 **Krawczyk-type interval operator 的块分解**的
   非线性方程快速验证算法，并与通用 Krawczyk/interval-Newton 比较。故“block Krawczyk”
   或“按矩阵块分解验证”不能成为 novelty。
2. Schwandt 1989 已研究 interval coefficient 三对角系统的 cyclic reduction；更早还有
   truncated interval cyclic reduction 与任意块维度的相关工作。故“对带状/块三对角
   interval system 做递推”本身也不能成为 novelty。
3. Frommer 与 Hashemi 2012 等工作利用 factorized preconditioner 和问题结构降低
   Krawczyk 型 verified computation 的复杂度。故“隐式使用 factorized preconditioner，
   不显式形成 Kronecker/逆矩阵”同样有强先例。

这些工作不直接覆盖 transistor-level transient MNA certificate，但会使算法审稿人要求：
BlockStamp 的数学差异必须落在**电路器件 stamp 与离散时间依赖的联合表示/界**上，而非
泛化的 block solve。

### 3.2 当前唯一可辩护的 headline

保守而可检验的候选贡献应拆成：

- **Claim W（slab coupling）**：相同可靠算术和相同 tube initialization 下，联合 slab
  Krawczyk 相对逐点 S-param 传播减少 interface wrapping 或提高 certified-prefix/acceptance。
- **Claim I（implicit equivalence）**：BlockStamp 递推严格包含与显式 dense-slab
  Krawczyk 相同的实 operator action，不依赖显式形成完整 slab preconditioner/Jacobian。
- **Claim E（efficiency）**：在保持 Claim I 的 inclusion 强度时，隐式递推降低 wall time、
  peak memory 或 certificate bytes。
- **Claim D（device locality）**：device-local stamp streaming 相对“先装配全局 interval
  Jacobian 再递推”提供额外可测的内存/证书/运行时收益。

其中 W 解释“为什么要 slab”，I/E 解释“为什么不是 dense slab”，D 解释“为什么是
circuit-specific，而不是通用 block solver”。这四层必须分开消融。

### 3.3 不应预先声称 recurrence 改善 wrapping

若 BlockStamp 只是对**同一个**点预条件器 `C` 和**同一个** interval Jacobian enclosure
重新安排计算顺序，那么它最稳妥的贡献是降低时间/内存；接受率理论上应与 dense operator
接近，差异只能来自 interval evaluation order。若要声称更少 wrapping，必须定义一种新的
依赖保持表示，例如 centered device remainder、block affine form 或局部 slope budget，并
证明该表示比直接 interval matrix product 更紧。否则“更少 wrapping”会被认为是实现顺序
偶然性，而非算法贡献。

## 4. 数学与 soundness 的 P0 阻断项

### 4.1 S-fixed / S-param 当前定理按现有 A1–A7 不成立

`A5` 只要求 checker 对实算子 `C` 的作用给出 enclosure，却没有要求 `C` 非奇异。
这是实质性 soundness 漏洞，不是文字问题。

反例：令一维 `F(x)=x+2`、`X=[-1,1]`、`x_bar=0`、`C=0`。则

```text
K(X) = {0} ⊂ int(X)
```

但 `F` 在 `X` 内没有零点。因此必须在定理与 checker obligation 中加入并验证 `C` 的
非奇异性，或者使用一个已经由结构证明可逆的算子定义。

建议最小修正：

- 将 `C` 定义为 checker 可精确解释的置换+块下三角 solve operator；
- 每个对角 block 的三角因子对角元必须被严格证明不含 0；
- 由块下三角矩阵行列式为各对角块行列式乘积，推出全 slab operator 非奇异；
- certificate 中的 factor 不需要被“相信为 Jacobian 的准确分解”，只需定义一个可逆
  preconditioner；近似质量只影响 inclusion 是否通过。

这会显著简化信任链：普通 factor residual 可以用于效率/诊断，但不是 soundness 的唯一
支柱。

### 4.2 必须精确定义 `C`，不能在三种对象间滑动

当前文字在“近似逆”“LU/ILU witness”“块消元见证”之间切换。正式算法必须只保留一个
首版定义，例如：

```text
M = checker-side point midpoint Jacobian with block lower-bidiagonal structure
C = exact real inverse action of M, evaluated by outward-rounded verified block solves
```

或：

```text
C = exact real operator induced by producer-supplied nonsingular point L/U factors
```

两者的 theorem、certificate 和 checker obligations 不同，不能同时模糊使用。首版更推荐
第一种：checker 重建 midpoint blocks，producer 只提供 permutation/scaling/factor hints，
checker 最终定义并验证 operator。

### 4.3 推荐的最小 BlockStamp recurrence

令点矩阵 `M` 是 `[J_z G](Y,X)` 的 checker-side midpoint，具有对角块 `D_k` 和
次对角块 `L_k`。将 Krawczyk remainder 写成

\[
R=-[G](Y,\bar z)+(M-[J_zG](Y,X))(X-\bar z).
\]

若 `M` 非奇异，则

\[
K_Y(X)\subseteq \bar z+M^{-1}R.
\]

对块下双对角 `M`，不形成 `M^{-1}`，而递推：

\[
U_a=\operatorname{VSolve}(D_a,R_a),
\qquad
U_k=\operatorname{VSolve}(D_k,R_k-L_kU_{k-1}).
\]

`VSolve` 必须返回包含对应精确实 solve 的区间。需要证明：按向外舍入执行该递推得到的
`U` 包含显式 dense `M^{-1}R` 的全部实值。小矩阵中还要与显式高精度 dense operator
逐元素交叉检查。

该 recurrence 本身可能仍被认为是标准块前代；论文价值取决于：

1. 它与 slab Krawczyk/器件 remainder 结合后的严格 theorem；
2. 相对 dense slab 的量化复杂度/内存收益；
3. device-local streaming 是否带来独立收益；
4. slab 联合认证相对 pointwise 是否真正减少 wrapping。

## 5. TCB 与电路语义的阶段性判断

### 5.1 当前 Decimal backend 只能叫 canary

二进制基本运算利用 exact Decimal image 的思路适合原型，但 `exp/log/sqrt` 在有限
Decimal precision 下先产生 nearest-rounded 近似，再对该近似做一次 binary64
`nextafter`，不能证明端点相对真实超越函数值向外。二极管和后续 compact model 依赖这些
函数，因此它是 Claim S 的 P0 项。

建议首版最终 checker 使用 MPFR/MPFI、Arb 或另一个明确支持 directed rounding、可追溯
版本的后端；Python Decimal 仅保留为透明 reference harness。至少需要：

- `RNDD/RNDU` 的 `exp/expm1/log/sqrt/div`；
- 次正规数、接近 overflow、接近零除数、强 cancellation 和 hard-to-round 输入；
- 与独立高精度 oracle 的系统测试；
- 所有器件参数组合（如 `Is/Vt`）也必须在可靠算术内形成 interval，禁止先用普通 float
  相除再装成 point interval。

### 5.2 当前器件实现尚不是 transient MNA

已有 diode 和受限 Level-1 NMOS 的值/导数 enclosure 是合适 canary，但还缺：

- R/C、独立电流/电压源和 MNA state layout；
- capacitor/charge stamp 与 BE history；
- 节点/支路装配及 ground 规范化；
- PMOS 或可实际形成振荡器的受限等价结构；
- topology/index-1 support checker；
- 完整 residual 与 Jacobian assembly。

最小机制实验不应直接上 6T SRAM。推荐顺序是：

1. RC step：验证 history 与线性 analytic oracle；
2. diode-RC clamp/rectifier：第一个非线性 BE root；
3. 三阶段 resistor-loaded NMOS oscillator，或在实现 PMOS 后使用 CMOS ring；
4. 只有上述通过，再进入 SRAM/op-amp。

## 6. 推荐的后续研究路线

### Phase A：theorem-first operator microkernel

目标不是做完整 SPICE，而是回答“BlockStamp 是否有独立算法对象”。

1. 修正 `C` 非奇异条件并给出机器可检查表示；
2. 写出 `D_k/L_k/R_k/U_k` 的唯一 recurrence；
3. 给出 exact-real containment theorem 和复杂度；
4. 对 `n=1..8`、slab `2..8` 的随机 block-bidiagonal 小矩阵，用 MPFR dense reference
   逐元素验证；
5. 建立四级 component ladder：
   - B2 pointwise verified；
   - B3 dense slab；
   - T-only implicit block recursion；
   - T+D BlockStamp device-local streaming。

只有这一阶段通过，才值得继续扩展器件和电路。

### Phase B：可靠算术与最小 MNA microkernel

1. 选定一个真正 directed-rounded backend；
2. 实现 R/C/源/diode 的 point、interval value、interval Jacobian 三语义；
3. 实现固定 BE residual、history 和 sparse assembly；
4. 用 RC 与单二极管电路建立解析/MPFR root oracle；
5. checker verdict 只允许 `ACCEPT/UNKNOWN/UNSUPPORTED`，禁止把已知 oracle 事实写成
   checker 的 `REJECT_NO_ROOT`，除非另有严格排除定理。

### Phase C：最强简单 baseline 先行

B2-strong 必须先能工作，否则主方法可能只是在比较一个做坏的 baseline。所有方法共享：

- 同一 interval backend；
- 同一 circuit semantics 与 Jacobian enclosure；
- 同一 candidate center、tube、scaling、ordering 和 factor witness；
- 同一线程、精度和计时环境。

B2/B3/B5 的差异只能是验证组织方式。记录 acceptance、inclusion margin、tube width、
wall time、RSS、nonzeros、factor fill 和 certificate bytes。

### Phase D：最小非线性 transient probe

冻结以下小矩阵即可，暂不扩张 Verilog-A/BSIM：

- diode-RC：至少 3 个 conditioning/step-size 设置；
- 3-stage ring：至少 3 个负载/初值设置；
- steps：`100, 300, 1000`；
- slab：`1, 2, 4, 8, 16`；
- producer：MPFR reference 与一个独立 double producer；
- 每个 timing 配置至少 5 个独立进程重复。

主图应是：

1. acceptance/certified-prefix vs slab length；
2. check time and peak RSS vs steps/state dimension；
3. certificate bytes vs raw trajectory bytes；
4. component ladder 的增量；
5. failure reason/first failing time。

### Phase E：通过门禁后才做 composition/recovery/specification

只有 Claim S/I/W/E 至少出现一个稳定机制信号后，再实现：

- S-param interface composition；
- suffix containment replay；
- discrete threshold/overshoot/settling monitor；
- second producer path；
- SRAM/op-amp；
- 受限 Verilog-A third semantics。

## 7. 原子化下一步工单

| 优先级 | 原子动作 | 研究依据 | 产出物 / 验收标准 | 关联路径 |
| --- | --- | --- | --- | --- |
| P0 | 在 formal contract 中加入 `C` 非奇异前提，并加入 `C=0, F(x)=x+2, X=[-1,1]` 反例测试，确保旧定理配置被拒绝 | 当前 S-fixed/S-param 存在直接反例，属于 soundness 阻断 | 新 A5 明确可逆性；测试在缺少可逆 witness 时返回 `UNSUPPORTED`；proof skeleton 不再使用未声明前提 | `paper2/steps/003_formal_soundness_contract.md`, `paper2/tests/test_krawczyk_soundness_contract.py` |
| P0 | 新建 BlockStamp 数学规范，唯一写出 `M,D_k,L_k,R_k,U_k`、operator `C` 和向外舍入 recurrence | 核心方法目前不存在；没有 recurrence 就只是既有方法组合 | 文档含定理、归纳证明、复杂度和 non-claims；不使用“块结构自然更紧”之类未证表述 | `paper2/steps/007_blockstamp_operator_spec.md` |
| P0 | 补入 Chen–Hashimoto 2003 block-Krawczyk、Schwandt 1989 interval cyclic reduction、Frommer–Hashemi 2012 factorized Krawczyk 三项高威胁近邻 | “block/structured Krawczyk”已有明确 prior art | 近邻矩阵写出 proof object、复杂度和与 BlockStamp 的唯一剩余差异；novelty statement 相应收缩 | `paper2/research/proof_carrying_spice_literature.md`, `paper2/steps/004_theorem_prior_art_closure.md` |
| P0 | 用 MPFR 定向舍入替换正式 `exp/expm1/log/sqrt/div` 路径；保留 Decimal 仅作 reference | 当前特殊函数不能证明对真实值 outward-rounded | 10 万组边界/随机输入 0 containment violation；覆盖 subnormal、overflow frontier、near-zero denominator；记录后端版本和 rounding mode | `paper2/experiments/rigorous_backend.py`, `paper2/tests/test_rigorous_backend.py` |
| P0 | 实现 block-bidiagonal point system 的 dense reference 与 recursive verified apply | Claim I 的最小可执行对象 | `n=1..8, slab=2..8` 的至少 10,000 个实例中，recursive enclosure 全部包含 MPFR dense action；点算术差 `<1e-12`；0 false accept | `paper2/experiments/blockstamp_operator.py`, `paper2/tests/test_blockstamp_dense_equivalence.py` |
| P0 | 实现 R/C/独立源/diode 的完整 BE MNA residual、history 与 Jacobian assembly | 当前 device stamp 尚不能形成 transient equation | RC closed-form 和 diode MPFR roots 均被 checker tube 包含；故意错误 history/stamp/permutation 全部不被 ACCEPT | `paper2/experiments/mna/`, `paper2/tests/test_be_mna_assembly.py` |
| P0 | 实现 B2-strong pointwise checker，复用与 BlockStamp 完全相同的 backend、stamps、tube、factor 和 scaling | 强 baseline 公平性；B2 是最关键 killer | analytic suite 上 B2 对所有合法 easy cases可认证；所有坏证书 0 false accept；逐阶段 timing 可用 | `paper2/experiments/checkers/pointwise_krawczyk.py`, `paper2/results/blockstamp/b2_canary.json` |
| P0 | 修复 baseline-defect generator：真正执行 float32/float64 cast、运行 checker，区分 oracle label 与 checker verdict | 当前 24 行含重复 precision 标签和硬编码 verdict | 两种 precision 至少一列数值确实不同；checker verdict 来自函数调用；无根未证明时只写 `UNKNOWN` | `paper2/experiments/generate_numerical_defects.py`, `paper2/results/blockstamp/numerical_defect_cases.csv` |
| P1 | 运行 diode-RC 与 3-stage ring 的 component ladder：B2、B3、T-only、T+D | 直接检验 slab、时间递推和器件 locality 三类来源 | 每行包含同一输入/tube/backend/factor hash；报告 acceptance、margin、runtime、RSS、bytes；不得删除失败配置 | `paper2/configs/blockstamp/minimal_probe.yaml`, `paper2/results/blockstamp/minimal_probe.csv` |
| P1 | 将 Claim W、I、E、D 拆成四个独立门禁 | 避免把 wrapping、运行时和 circuit specificity 混成一个 headline | `stage_gate.json` 分别给 PASS/ITERATE/STOP 和证据路径；任一 claim 只能引用对应 component contrast | `paper2/steps/008_minimal_probe_gate.md`, `paper2/results/blockstamp/stage_gate.json` |
| P1 | 新增 CI workflow，在固定 Python/后端版本上运行 theorem counterexample、arithmetic、dense-equivalence、MNA 与 recovery tests | soundness 论文不能依赖手工“tests passed”描述 | 每个 commit 可见 CI status；失败测试阻止将阶段标为 DONE；artifact 绑定 commit SHA | `.github/workflows/paper2-blockstamp.yml` |
| P2 | 仅在最小 probe 通过后实现 S-param composition 与 recovery replay | 防止在核心算法无信号前扩张系统 | 真实多维 outgoing/incoming boxes；subset 才复用；overlap/disjoint 均使后缀失效；端到端成本被记录 | `paper2/experiments/recovery.py`, `paper2/tests/test_compositional_recovery.py` |

## 8. 预注册停止与转向条件

### STOP-E：只有标准块 solve，没有论文级结构增益

若 recursive operator 与 dense slab 等价，但在 `slab>=8` 时 wall time、RSS 和证书大小均
无稳定优势，则停止 Claim E。不要用更大的电路掩盖无增益的小机制。

### REFRAME-SYSTEM：数学新颖性不足，但工程证书有价值

若 recurrence 被确认属于标准 block Krawczyk/triangular verification 的直接实例，但独立
checker 相对 strict rerun 在受限 MNA 上有稳定端到端收益，可把目标从 DAC 算法论文收缩为
CCF-C/领域系统论文：贡献是受限语义、portable certificate、独立 TCB 和完整复现，而不是
新数值定理。

### STOP-W：pointwise baseline 已足够

若 B2 在长轨迹上几乎不发生 interface wrapping，且成本不高于 slab 方法，则 slab 是不必要
复杂性。保留逐点 certificate checker，停止 BlockStamp headline。

### STOP-S：可靠算术或器件语义无法闭合

任何确认的 false accept、特殊函数 containment 失败、branch-crossing box 被错误 ACCEPT、
或 theorem 反例通过 checker，都立即停止 Claim S，修复后必须全量回归。

### REFRAME-MOTIVATION：真实 SPICE 缺陷不常见

如果 ngspice/Xyce 的自然 tolerance sweep 很少产生错误 candidate，不代表证书方向无价值，
但动机必须从“成熟 SPICE 经常错误”改成“对不可信/近似/加速 producer 提供独立检查”。
随后必须用端到端成本证明检查比可信重算更有意义。

## 9. 总体阶段意见

这是一个**比 CoVoL 更高风险、也更有技术上限**的方向。它的优势是问题边界清楚、无需
大规模数据、能够形成 theorem—checker—circuit experiment 的完整闭环；风险是 verified
numerics 的先行工作非常深，任何“把 Krawczyk 按时间块递推”的普通实现都可能被审稿人
判为标准方法应用。

因此，下一阶段不应继续扩写 Proof-Carrying SPICE 愿景，也不应先做 SRAM、Verilog-A、
BSIM、第二 producer 或大规模网表。唯一正确的主线是：

> **先修正 Krawczyk soundness 前提，写出并实现可与 dense operator 逐元素核对的最小
> BlockStamp recurrence；再用同组件 B2/B3/T-only/T+D 阶梯证明 slab coupling、隐式递推
> 与 device locality 各自贡献了什么。**

若这个最小机制门禁通过，方向可以升级为 Pre-Paper Candidate；若失败，应快速收缩为受限
独立 checker 系统工作或停止 BlockStamp 算法主张，而不是用工程规模补偿核心差异不足。
