# Step 002: Complete Experimental Protocol for BlockStamp-Cert

## 1. Purpose and freeze rules

本协议用于验证或否定 `paper2/research/research_direction.md` 中的 Claim S/C/E/R/P。
阶段顺序固定为环境 canary、baseline 缺陷、简单/强 baseline、最小算法、机制诊断、
killer baseline、主实验、消融/鲁棒性/效率和独立重复。前一门禁未通过时不得启动后续
大规模矩阵。

所有依赖安装在 `auto_research`，Python 固定为 3.12。原始输入、producer 输出、配置、
随机种子、版本、命令、机器信息和 SHA-256 必须记录。禁止人工标注或开放式人评；所有
结论使用解析电路、独立高精度求解、区间包含或故障注入 oracle。

## 2. Reproducibility contract

每次运行产生唯一 `run_id`，目录结构固定为：

```text
paper2/results/blockstamp/<run_id>/
  config.snapshot.yaml
  environment.json
  input_manifest.json
  producer_trace.npz
  certificate.bin
  checker_result.json
  metrics.json
  timing.json
  stdout.log
```

配置必须包含：seed、circuit、model、producer、producer tolerance、precision、method、
step size、steps、slab length、tube initializer、preconditioner、checker backend、故障
注入和重复编号。输出采用临时文件加原子重命名；失败运行也保留结构化 failure code。

主随机种子冻结为 `17, 29, 43, 71, 101`。确定性解析测试不使用随机种子。计时前一次
warm-up，正式报告至少五次独立进程重复的 median、IQR 和全范围；不得删除超时或拒绝
样本。

## 3. Circuit and model suite

### 3.1 Analytic oracle set

用于最早 soundness canary：

- RC step、RLC damping：线性闭式/高精度离散根；
- 单二极管整流/钳位：单变量或小系统单调性 oracle；
- 小型交叉耦合非线性系统：专门测试局部而非全局唯一性。

### 3.2 Nonlinear mechanism set

- 3/5/7-stage ring oscillator；
- 6T SRAM read/write/hold transient；
- differential-pair op-amp step response；
- 可选 LDO load transient，仅在前三类通过后加入。

每类至少三个规模/负载设置。网表必须公开或程序化生成，器件参数和激励写入 manifest。
首轮只用 diode 和 Level-1 MOS；不得把 BSIM 兼容性工作提前混入算法门禁。

### 3.3 Scale grid

- state dimension: approximately `10, 30, 100, 300, 1000`；
- time steps: `100, 300, 1000, 3000, 10000`；
- slab length: `1, 2, 4, 8, 16, 32, 64`；
- fixed BE step size：由每类电路 dev case 预先冻结三个解析度，不在 test 上调参。

只在 canary 证明更大格点有判别价值时扩展；不得为填表运行无信息矩阵。

## 4. Producer matrix

至少包括：

1. independent high-precision reference producer：MPFR 或等价多精度 Newton；
2. tight double producer：严格容差的独立实现或 ngspice/Xyce；
3. loose double producer：放宽 nonlinear tolerance；
4. mixed/low precision producer：float32 center 或量化 trajectory；
5. corrupted producer：程序化注入 state、Jacobian/factor、history、permutation 和 stamp
   错误。

Checker 不得导入 producer 的 evaluator 或 Jacobian 模块。若使用 ngspice/Xyce，记录
版本、命令和原始输出；producer 的“converged”只作为输入字段，不作为 oracle。

## 5. Baselines

### B0: residual-only check

以 double residual norm 与常见 SPICE tolerance 判断。用途是复现“小 residual 不能保证
小 forward error/局部唯一性”的缺陷；不得作为 sound baseline。

### B1: independent strict rerun

Checker 侧独立多精度 Newton，从候选中心重新求解全部时间步。报告成功率和成本，但不
将其等同于存在唯一性证明。

### B2: pointwise verified Krawczyk

每个时间点独立构造区间方程，上一点输出作为参数，使用通用 verified linear solve。
这是最关键的 DATE-style killer baseline。

### B3: dense whole-slab Krawczyk

显式组装 slab Jacobian 和通用稠密/稀疏区间运算，测量 wrapping、内存和成本。

### B4: validated integration reference

在能转换为显式 ODE 的小型子集上使用 CAPD/VNODE 类工具，比较连续 enclosure 的成功率
和成本。由于证明对象不同，只作为邻近强 baseline，不做不公平胜负宣称。

### B5: verified sparse-linear kernels

至少实现/调用一种 Rump/Ogita 风格可靠线性验证，分别测试 exact LU、ILU 和 producer
factor witness。BlockStamp 必须报告相对该内核的增量，而不是拿朴素 interval inverse
做稻草人。

## 6. Primary metrics

### Soundness

- false accept count，理论目标和实测都必须为 0；
- high-precision root 是否包含于 tube；
- Krawczyk inclusion margin；
- malformed certificate/factor/permutation 的拒绝覆盖率；
- 跨 slab interface containment violations。

### Utility

- trajectory certification rate；
- certified prefix length；
- tube relative width及随时间增长率；
- discrete specification decisive rate：`PROVED/REFUTED/UNKNOWN`。

### Efficiency

- checker wall time / producer wall time；
- checker wall time / strict rerun wall time；
- certificate generation time、check time、recovery time；
- certificate bytes / raw trajectory bytes；
- peak RSS、非零元数、factor fill ratio；
- device stamp、factor verification、block propagation、monitor 各阶段时间。

### Selective recovery

- rejected slab fraction；
- recomputed time-step fraction；
- end-to-end time including producer, certificate generation, checking and fallback；
- 相对 full strict rerun 的 speedup；
- 错误注入位置到最早报告失败位置的 localization distance。

## 7. Experimental stages and gates

### Stage 0: environment and arithmetic canary

验证 Python 3.12、向外舍入模式、特殊值、区间基本运算、稀疏索引和序列化 round-trip。
使用精确有理/MPFR oracle 做随机性质测试。

Gate 0 PASS：所有包含性质通过；跨进程/重复运行证书哈希稳定；不支持的平台明确 STOP。

### Stage 1: reproduce the baseline defect

构造良态和病态单步/短轨迹，使 producer 返回 converged 和小 residual；以多精度根、
condition slice 和区间检查判断 forward error/唯一性是否仍可能失败。故障注入包括：

- 单点 state perturbation：`1e-12` 到 `1e-2`；
- 过时 history state；
- 一处错误器件参数/stamp；
- Jacobian 符号/节点排列错误；
- factor 元素和 permutation corruption。

Gate 1 PASS：至少一种非实现 bug 的数值机制证明 residual/convergence flag 不足，同时
sound checker 对全部已知坏样本零 false accept。若缺陷不存在则 STOP 当前 problem claim。

### Stage 2: strongest simple baselines

在 analytic + 小型 nonlinear set 上完成 B0–B3/B5；冻结 tube initialization、缩放和
slab dev grid。test circuits 不参与选择。

Gate 2 PASS：pointwise verified baseline 可工作，确保后续比较不是因 baseline 做坏；
同时 dense/pointwise 方法至少暴露可量化的成本、wrapping 或证书大小缺陷。

### Stage 3: minimal BlockStamp prototype

仅实现 BE、diode/Level-1 MOS、slab `2–16`。验证 block-recursive bound 与 dense slab 在
相同 tube 上的包含关系；在随机小矩阵上与显式 dense operator 逐元素交叉检查。

Gate 3 ITERATE/PASS：Claim S 的单元/性质证据成立，且至少一个机制指标优于 B2/B3。
初版无增益不自动淘汰；先按 conditioning、device nonlinearity、slab length 和 wrapping
来源切片，最多尝试三种非等价算法路径：块前代 bound、局部重心/缩放、adaptive slab。

### Stage 4: compositional and specification probe

把 accepted endpoint 投影为下一 slab interface；证明并测试归纳合同。实现离散 max、
threshold、overshoot 和 settling predicates，所有不确定交叉返回 `UNKNOWN`。

Gate 4 PASS：长轨迹组合与单个 whole-trajectory dense oracle 一致；monitor 不发生错误
decisive verdict；明确标注仅离散采样点。

### Stage 5: killer baselines and TCB audit

完成 B1–B5，对 producer/checker 模块依赖图做自动 denylist 检查；producer evaluator、
Jacobian 和 convergence code 不得进入 checker import closure。比较 verified factor 方法和
不同 ordering/fill。

Gate 5 PASS：BlockStamp 优势在强 B2/B5 下仍存在，且不是语言、缓存、线程或不公平精度
造成。否则 REFINE 或 STOP efficiency claim。

### Stage 6: main experiment

运行冻结的 circuit × scale × producer × slab grid。主表同时报告 certification rate、
end-to-end runtime、certificate size 和 fallback fraction，不允许只挑成功样本。每一配置
五个独立重复；确定性 soundness 测试另行全量运行。

预定义解释：

- 好结果：更优 Pareto 前沿且零 false accept；
- 一般结果：只在良态/短 slab 有收益，收缩 claim 和支持范围；
- 负结果：相对 B2/B5 无稳定增益或 fallback 吞噬收益，停止 Paper Candidate 升级。

### Stage 7: ablation, robustness, and efficiency

消融：

- 去掉 device-local stamp，改全局 interval Jacobian；
- 去掉 block recursion，改 pointwise 或 dense slab；
- 去掉 factor witness，checker 自建 factor；
- 去掉 adaptive slab；
- 去掉缩放/重心策略；
- 固定 slab 与自适应 slab；
- certificate monitor 与离线 monitor。

鲁棒性切片：PVT 参数、step size、producer tolerance、condition estimate、nonlinearity、
slab length、ordering、precision 和故障类型。报告失败案例和最早失败原因分布。

### Stage 8: independent replay and Paper Candidate Gate

在全新输出目录和独立进程重放冻结配置；核对 input、certificate、result hashes。至少一组
核心表由第二个 producer 路径复现。

只有同时满足以下条件才标记 `PAPER_CANDIDATE`：

1. Claim S/C 有测试和理论草案支撑，故障注入零 false accept；
2. killer baseline 未消除结构性增益；
3. 主指标跨至少两个非线性电路类别稳定；
4. 端到端收益包含证书生成、检查和 fallback；
5. 增益不能由工程实现差异解释；
6. 每个核心组件有对应消融。

否则决策只能是 `ITERATE`、`REFINE` 或 `STOP`。

## 8. Statistical protocol

运行时间采用配对配置比较，报告 median ratio 及按 circuit instance 聚类的 bootstrap
95% CI。成功/失败率报告 Wilson interval；certificate size 和 tube width 报 median/IQR
及 worst case。电路 instance 而非 time step 是独立统计单位，禁止把成千时间点伪装成
样本量。多规模曲线报告原始点，不用单一平均数掩盖失败区。

不对 soundness 做统计放宽：任何确认的 false accept 都使 Claim S 立即 STOP，直到根因
修复并全量回归。

## 9. Planned command contract

实现完成后，所有阶段必须提供以下等价 CLI；当前文档不声称这些入口已经存在：

```bash
conda run -n auto_research python -m paper2.experiments.generate_circuits --config <yaml>
conda run -n auto_research python -m paper2.experiments.run_producer --config <yaml>
conda run -n auto_research python -m paper2.experiments.build_certificate --config <yaml>
conda run -n auto_research python -m paper2.experiments.check_certificate --config <yaml>
conda run -n auto_research python -m paper2.experiments.run_matrix --config <yaml>
conda run -n auto_research python -m paper2.experiments.summarize --results <dir>
```

每个 CLI 必须支持 `--help`、明确输入输出、非零失败码和配置快照。新增代码后从仓库根
运行：

```bash
conda run -n auto_research ruff check .
conda run -n auto_research black --check .
conda run -n auto_research pytest tests/
```

若仓库级检查被无关既存债务阻断，同时报告仓库级失败和 `paper2` 范围结果，不得把范围
检查冒充全仓库通过。

## 10. Expected paper artifacts

- theorem/assumption table：Claim S/C 及不支持拓扑；
- Algorithm 1：BlockStamp certificate checking；
- Table 1：各方法 guarantee/trust/structure；
- Table 2：主结果四指标；
- Figure 1：producer–certificate–checker TCB；
- Figure 2：时间—器件双层稀疏结构；
- Figure 3：规模与 end-to-end Pareto；
- Figure 4：故障注入/局部回退；
- 消融、失败案例、资源和 Threats to Validity。

## 11. Threats to validity

- Level-1 MOS 不能代表现代 BSIM/Verilog-A；
- 固定 BE 不能外推自适应步长或高阶规则；
- 局部唯一性不能排除 tube 外其他解；
- 离散 monitor 不能证明网格间无峰值；
- checker 独立性受共同规范误解和编译器/硬件错误限制；
- 开放小电路上的净收益可能不能外推工业 FastSPICE；
- verified arithmetic backend 本身仍属于 TCB。

这些限制必须在论文中保留，不能通过措辞隐藏。
