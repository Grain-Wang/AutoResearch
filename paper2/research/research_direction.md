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
- 用于逐块可逆性与 verified solve 的近似逆或 LU/ILU 提示；
- 缩放向量和条件性提示；
- 离散规格 monitor 的候选关键时间点。

在 checker TCB、输入语义绑定和区间后端正确的前提下，错误 hint 只能通过已验证的
包含前提影响接受；故障注入只能测试实现，不能证明对任意错误均 sound。

### 3.2 Trusted checker reconstruction

Checker 独立解析受限网表，依据固定器件语义构造数值值、区间值和区间 Jacobian
stamp。应用输入绑定的排列与非零对角缩放后，checker 从自己的 interval Jacobian
enclosure 确定 point midpoint block-lower-bidiagonal matrix `M`，并验证其每个对角块
可逆。首版证明只允许一个固定实算子：

\[
C:=M^{-1}.
\]

Producer 的 factor/approximate-inverse 只作为加速可逆性证明和 verified solve 的不可信
hint，不能定义或替换 `M`。Checker 不显式形成 `C`，而是用向外舍入 verified block
solve 计算其作用，再检查整个 slab 的 Krawczyk 型包含：

\[
K_S(\bar x,X)=\bar x-CF_S(\bar x)
+\left(I-C[J F_S(X)]\right)(X-\bar x)
\subset \operatorname{int}(X).
\]

严格包含逐坐标要求 checker 得到的下端点严格大于 `X` 的下端点、上端点严格小于
`X` 的上端点；边界相等或比较不确定只能返回 `UNKNOWN`。`C=0` 等奇异算子即使产生
表面上的 strict inclusion 也不能 `ACCEPT`。完整前提和反例见
`steps/003_formal_soundness_contract.md`。

### 3.3 BlockStamp structure

Backward Euler 的 slab Jacobian 具有块下双对角结构。单个对角/次对角块又是器件
stamp 的稀疏和。令 `D_k`、`L_k` 为 checker-defined `M` 的对角与次对角 point
blocks，`[R_k]` 为由 residual 与 `M-[J_zG]` 构造的 outward-rounded remainder。
BlockStamp-Cert 不形成稠密 `C` 或完整区间逆，而是：

1. 检查每个器件局部值/Jacobian enclosure；
2. 用向外舍入 pivot enclosure 或等价 verified residual witness 证明每个 `D_k` 可逆；
3. 执行唯一递推
   `U_a=VSolve(D_a,[R_a])`、
   `U_k=VSolve(D_k,[R_k]-L_k[U_{k-1}])`；
4. 用器件局部 streaming 形成与完整矩阵表达式相同语义的 outward remainder enclosure；
5. 若某块失败，从该 slab 启动拆分或重算，并按 boundary containment replay 或重新检查
   其依赖后缀；不得无条件复用后缀。

递推、containment lemma、复杂度和失败条件固定在
`steps/007_blockstamp_operator_spec.md`。普通 block forward substitution 本身不是
novelty。当前核心可证伪假设是：在同一算术、tube、scaling、ordering 和 factor 条件
下，器件—时间联合表示能否相对强 pointwise、dense-slab 和 verified-sparse baseline
带来可归因收益；在数据出现前不声称减少 wrapping、运行时间或端到端成本。

## 4. Certificate and checker contract

证书必须包含版本、输入哈希、离散方法、时间网格、状态中心/tube、slab 划分、变量
排列、稀疏见证和规格 monitor 数据。不得包含 checker 无法重新验证的布尔“成功”标志。

Checker 的可信计算基（TCB）仅包括：

- 受限网表解析器及规范化器；
- 固定器件方程与拓扑/MNA 装配；
- Backward Euler 历史项语义；
- 向外舍入区间算术和受支持特殊函数；
- 稀疏索引、逐块可逆 witness、verified solve 和包含关系检查；
- 证书解析及离散规格 monitor。

Producer 与 checker 不共享器件 evaluator、Jacobian、收敛判断或稀疏 factor 实现。
允许共享规范文本和输入文件，但不得共享可能产生相同实现缺陷的可执行代码路径。

## 5. Formal claims under test

### Claim S-fixed / S-param: sound local discrete root certification

`S-fixed` 对一个固定 incoming state 使用普通 Krawczyk 包含证明 tube 内的局部唯一根。
更强的 `S-param` 必须用 incoming box 上统一的 residual 与 interval Jacobian enclosure，
证明对每个 incoming state 都存在各自唯一的局部离散根，并由 outgoing box 包含全部末态。
两者的量词、假设和 checker 义务见 `steps/003_formal_soundness_contract.md`。

### Claim C: compositional trajectory certification

若从初始条件开始所有 slab 依次 `ACCEPT`，且每个 outgoing interval 包含在下一 slab
的 incoming assumption 中，则通过归纳得到整条离散轨迹的局部唯一根管道。

### Claim I: implicit exact-operator containment

在 `C=M^{-1}`、每个对角块可逆且每次 `VSolve` 包含精确实 solve 的条件下，BlockStamp
递推包含与显式 dense slab 计算相同的精确实 operator action。该 claim 不要求两种
interval evaluation 产生相同端点，也不声称递推天然更紧。它必须通过归纳 lemma 与独立
exact/MPFR dense-action cross-check 共同验证。

### Claim W: slab-coupling hypothesis

在相同 backend、candidate、tube initializer、scaling、ordering 和 witness 下，联合 slab
相对 B2 pointwise propagation 是否提高 certification rate 或 certified prefix，属于待检验
假设。仅改变 interval evaluation order 不足以预先声称 less wrapping；若无稳定信号，停止
Claim W。

### Claim D: device-locality hypothesis

相对先装配完整 global interval Jacobian 后执行相同 temporal recurrence，device-local
stamp streaming 是否降低 assembly time、peak RSS 或 certificate bytes，必须由
`temporal-only` 与 `temporal+device` 的直接消融决定。普通稀疏实现收益不得归入 Claim D。

### Claim E: structure-sensitive efficiency hypothesis

只有在至少两个非线性电路类别和多个配置上，BlockStamp 相对 component-matched B2、
dense-slab 与 verified-sparse baseline 在检查时间、peak RSS 或 certificate bytes 中至少一项
出现稳定优势，且未用 acceptance/tube strength 换取该优势时，才报告 Claim E。任何
end-to-end 主张还必须计入 certificate generation、check 和必要 fallback；当前无完成时态
性能结论。

### Claim R: safe selective recovery

注入 producer 误差或放宽 producer 容差时，checker 不接受已知错误样本。失败 slab
重算后，从该 slab 开始恢复；只有新 outgoing enclosure 被下一 slab 的既有 incoming
assumption 包含时才可 replay 其证书，并对每个后续边界重复该检查。首次 containment
failure 使对应未检查后缀失效并重新检查。低于完整严格重算的成本仍是待验证假设。

### Claim P: discrete specification preservation

若认证 tube 在所有采样点满足电压/电流阈值或离散 peak/overshoot/settling predicate，
则对应的离散规格成立。该 claim 不排除网格之间峰值。

## 6. Explicit non-claims

- 不声称 Krawczyk、interval Newton、proof-carrying 或 circuit interval analysis 新颖；
- 不声称 block Krawczyk、block forward substitution 或 verified factor witness 新颖；
- 不声称递推与 dense interval evaluation 端点相同或天然减少 wrapping；
- 不声称 Claim W/I/E/D 已被当前实现或实验支持；
- 不声称整个状态空间全局唯一；
- 不声称连续时间 DAE 真解或真实硅片被包含；
- 不声称任意 Verilog-A/BSIM、奇异拓扑或 index-2 电路可支持；
- 不把 producer/checker 接口、序列化格式或规格 monitor 单独列为算法贡献；
- 不把与不同仿真器一致或小 residual 当作数学证明。

## 7. Frozen minimum scope

核心机制门禁冻结为：

- 正则 index-1 charge-oriented MNA；
- 固定步长 Backward Euler；
- R/C、独立电流/电压源、diode，以及形成 resistor-loaded ring 所需的受限 Level-1
  NMOS 语义；
- RC analytic 与 diode-RC MPFR root 作为 correctness oracle；
- diode-RC 和 3-stage ring oscillator 两个非线性 transient probe；
- `steps={100,300,1000}`、`slab={1,2,4,8,16}`，每个 timing 配置至少五个独立进程；
- component-matched B2、dense-slab、verified-sparse、temporal-only 与
  temporal+device 对照。

SRAM、op-amp/LDO、第二 producer、BDF2、Trapezoidal、EKV、受限 Verilog-A、现代
BSIM 和大规模网表都是核心门禁通过后的扩展，不得用这些工程规模补偿最小机制无信号。

## 8. Algorithm sketch

```text
BLOCKSTAMP-CHECK(netlist, semantics, candidate, certificate):
    independently normalize netlist and hash all declared inputs
    reject unsupported topology, device, method, or malformed sparse indices
    Y <- certified initial-state interval
    for slab S in certificate order:
        reconstruct F_S and interval device stamps from checker semantics
        verify candidate centers, tube boxes, permutation, and nonzero scaling
        reconstruct checker-defined M and bind its exact point blocks to the digest
        prove every diagonal block invertible; initialize verified solves
        stream outward-rounded [R_k] blocks from checker-side stamps
        apply U_a = VSolve(D_a, [R_a])
        apply U_k = VSolve(D_k, [R_k] - L_k U_{k-1}) for later blocks
        if inclusion fails:
            return UNKNOWN(first failing time, machine-checkable diagnostics)
        Y <- project accepted final block to certified outgoing interface
    evaluate discrete specification monitors over accepted tubes
    return ACCEPT(trajectory digest, tube digest, specification verdicts)
```

## 9. Novelty statement

保守版本：

> We study certification of fixed-discretization nonlinear MNA trajectories that is
> independent of the trajectory-generation algorithm provided it satisfies a declared
> certificate interface. Under a restricted BE/netlist semantics and a correct checker
> TCB, the checker targets local roots of the discrete equations only.
> Unlike prior DC interval verification and validated continuous-time
> integration, the proposed checker reconstructs circuit semantics independently and
> verifies untrusted sparse witnesses over compositional discrete time slabs.

结果版本只能在 Claim I/W/D/E 的对应门禁通过后，按真实数据填入，不得预写完成时态：

> On [supported workloads/configurations], BlockStamp-Cert encloses the same exact
> real midpoint-inverse action as the dense reference while [measured metric and
> effect size] relative to [component-matched baseline], including certificate
> generation, checking, and required fallback costs where end-to-end cost is claimed.

## 10. Current gate

方向通过 Research Opportunity Gate，但 Claim S/C/I/W/D/E/R/P 均未形成完整实现—实验
证据。只有以下条件同时满足，才允许升级为 Pre-Paper Candidate：`C=M^{-1}` 的可逆性、
directed rounding 和 BE MNA 链闭合且已知坏样本 0 false accept；B2 与 BlockStamp 的共享
组件 hash 一致；Claim I 的 dense-action cross-check 通过；BlockStamp 相对 B2/dense/
verified-sparse 在至少一个核心指标上跨多个配置稳定占优；diode-RC 与 ring 的未筛选结果
可重放；所有端到端性能主张计入 certificate generation、check 和必要 fallback。若递推
只是标准块前代且 W/D/E 无稳定收益，停止 BlockStamp 算法 headline，而不是扩张工程范围。
