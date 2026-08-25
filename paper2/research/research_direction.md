# BlockStamp-Cert: Refined Research Direction

## 1. Working title

**BlockStamp-Cert: Independently Checkable, Circuit-Structured Certificates for
Discrete Nonlinear Transient Simulation**

中文题目：**面向非线性瞬态离散 MNA 的器件—时间结构化可独立检查证书**

“Proof-Carrying SPICE”保留为系统愿景，不作为暗示首次提出 proof-carrying、区间电路
分析或严格积分的主张。算法名 BlockStamp-Cert 强调两个可被消融的结构来源：时间块
带状结构和器件局部 stamp。

## 2. Refined problem

给定结构正则的 index-1 电路、固定初值和激励、固定步长 (h)、Backward Euler
离散规则及外部 producer 返回的候选状态序列

\[
\hat x_{0:T}=(\hat x_0,\ldots,\hat x_T),
\]

检查器需要在不信任 producer 的 Newton 迭代、Jacobian、终止条件、变量排列、稀疏
因子和浮点计算的前提下，对每个时间块 (S=[a,b]) 验证离散残差系统

\[
F_k(x_{k-1},x_k)=
q(x_k)-q(x_{k-1})+h\,i(x_k,t_k)=0,
\quad k=a,\ldots,b,
\]

在声明的区间管道 (X_S=X_a\times\cdots\times X_b) 中存在唯一局部根。这里
(q) 和 (i) 由 checker 自己的器件语义和 MNA 装配生成。证明对象严格限定为给定
离散模型的局部根，不覆盖连续时间截断误差、模型误差或真实硅片行为。

## 3. Core algorithmic hypothesis

### 3.1 Untrusted certificate payload

Producer 可以提供但 checker 完全不信任：

- 候选中心和各变量 tube radius；
- slab 边界和建议拆分点；
- 变量/方程排列；
- 稀疏近似逆、LU/ILU 因子或块消元见证；
- 缩放向量和条件性提示；
- 离散规格 monitor 的候选关键时间点。

错误 hint 只能导致 `REJECT/UNKNOWN` 或额外计算，不能导致错误接受。

### 3.2 Trusted checker reconstruction

Checker 独立解析受限网表，依据固定器件语义构造数值值、区间值和区间 Jacobian
stamp；验证稀疏索引、排列和 factor residual；再对整个 slab 检查 Krawczyk 型包含：

\[
K_S(\bar x,X)=\bar x-CF_S(\bar x)
+\left(I-C[J F_S(X)]\right)(X-\bar x)
\subset \operatorname{int}(X).
\]

其中 (C) 只是 producer 提供的候选预条件器所诱导的线性算子；soundness 仅来自
checker 对全部区间运算和包含关系的重新验证。

### 3.3 BlockStamp structure

Backward Euler 的 slab Jacobian 具有块下双对角结构。单个对角/次对角块又是器件
stamp 的稀疏和。BlockStamp-Cert 不形成稠密 (C) 或完整区间逆，而是：

1. 检查每个器件局部值/Jacobian enclosure；
2. 验证 producer 的单步稀疏因子见证；
3. 通过块前代把 Krawczyk 中心修正和 radius bound 沿时间递推；
4. 用显式 remainder budget 隔离非线性区间余项、接口不确定性和浮点向外舍入；
5. 若某块失败，定位到最早失败时间并只拆分或重算该 slab。

核心可证伪命题不是“分块可组合”，而是：这种器件—时间双层结构能在保持同等
soundness 的同时，比逐点通用 Krawczyk 或稠密 slab 验证减少检查成本、证书大小或
wrapping 失败。

## 4. Certificate and checker contract

证书必须包含版本、输入哈希、离散方法、时间网格、状态中心/tube、slab 划分、变量
排列、稀疏见证和规格 monitor 数据。不得包含 checker 无法重新验证的布尔“成功”标志。

Checker 的可信计算基（TCB）仅包括：

- 受限网表解析器及规范化器；
- 固定器件方程与拓扑/MNA 装配；
- Backward Euler 历史项语义；
- 向外舍入区间算术和受支持特殊函数；
- 稀疏索引、因子 residual 和包含关系检查；
- 证书解析及离散规格 monitor。

Producer 与 checker 不共享器件 evaluator、Jacobian、收敛判断或稀疏 factor 实现。
允许共享规范文本和输入文件，但不得共享可能产生相同实现缺陷的可执行代码路径。

## 5. Formal claims under test

### Claim S: sound local discrete root certification

若 checker 对 slab (S) 返回 `ACCEPT`，则对所有被认证的 incoming interface states，
声明的 tube 内存在唯一离散根，并且 slab 末状态包含于导出的 outgoing interval。

### Claim C: compositional trajectory certification

若从初始条件开始所有 slab 依次 `ACCEPT`，且每个 outgoing interval 包含在下一 slab
的 incoming assumption 中，则通过归纳得到整条离散轨迹的局部唯一根管道。

### Claim E: structure-sensitive efficiency

在至少两个非线性电路类别和多个规模上，BlockStamp 检查相对逐点 Krawczyk、稠密
slab Krawczyk 和独立高精度重算具有更好的检查时间—接受率—证书大小 Pareto 前沿。

### Claim R: safe selective recovery

注入 producer 误差或放宽 producer 容差时，所有错误只能导致 checker 拒绝；只重算
失败 slab 后的总成本低于完整严格重算，并保持最终已接受轨迹的 Claim S/C。

### Claim P: discrete specification preservation

若认证 tube 在所有采样点满足电压/电流阈值或离散 peak/overshoot/settling predicate，
则对应的离散规格成立。该 claim 不排除网格之间峰值。

## 6. Explicit non-claims

- 不声称 Krawczyk、interval Newton、proof-carrying 或 circuit interval analysis 新颖；
- 不声称整个状态空间全局唯一；
- 不声称连续时间 DAE 真解或真实硅片被包含；
- 不声称任意 Verilog-A/BSIM、奇异拓扑或 index-2 电路可支持；
- 不把 producer/checker 接口、序列化格式或规格 monitor 单独列为算法贡献；
- 不把与不同仿真器一致或小 residual 当作数学证明。

## 7. DAC conference scope

首轮冻结范围：

- 正则 index-1 charge-oriented MNA；
- 固定步长 Backward Euler；
- R/C/L、独立源、diode、Level-1 MOS；
- ring oscillator、SRAM cell、op-amp/LDO 中至少两个类别；
- 10--1000 状态变量、100--10000 时间步的可扩展曲线；
- 离散局部唯一性、组合、离散规格和局部回退；
- ngspice/Xyce 或自写参考 producer 中至少两个互异 producer 路径。

BDF2、Trapezoidal、EKV、受限 Verilog-A interval backend 和现代 BSIM 是门禁通过后的
扩展，不得在最小机制信号前扩张。

## 8. Algorithm sketch

```text
BLOCKSTAMP-CHECK(netlist, semantics, candidate, certificate):
    independently normalize netlist and hash all declared inputs
    reject unsupported topology, device, method, or malformed sparse indices
    Y <- certified initial-state interval
    for slab S in certificate order:
        reconstruct F_S and interval device stamps from checker semantics
        verify candidate centers, tube boxes, permutations, and factor residuals
        compute block-recursive Krawczyk center and radius bounds with outward rounding
        if inclusion fails:
            return UNKNOWN(first failing time, machine-checkable diagnostics)
        Y <- project accepted final block to certified outgoing interface
    evaluate discrete specification monitors over accepted tubes
    return ACCEPT(trajectory digest, tube digest, specification verdicts)
```

## 9. Novelty statement

保守版本：

> We study producer-agnostic certification of fixed-discretization nonlinear MNA
> trajectories. Unlike prior DC interval verification and validated continuous-time
> integration, the proposed checker reconstructs circuit semantics independently and
> verifies untrusted sparse witnesses over compositional discrete time slabs.

目标 DAC 版本只有在 Claim E/R 被实验支持后才能使用：

> BlockStamp-Cert is a circuit-structured proof-carrying algorithm for nonlinear
> transient MNA. It combines device-local interval stamps with block-recursive
> verification of the time-banded Jacobian, enabling independently checkable local
> uniqueness certificates and selective slab recovery at lower end-to-end cost than
> pointwise certification or strict reruns.

## 10. Current gate

方向通过 Research Opportunity Gate，但 Claim S/C/E/R/P 均未实验验证。只有最小真实
电路 probe 复现 baseline 缺陷、BlockStamp 在 killer baselines 下出现稳定有效信号且
收益不是实现优化假象时，才允许升级为 Paper Candidate。
