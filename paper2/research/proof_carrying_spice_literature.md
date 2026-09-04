# Proof-Carrying SPICE 文献检索与新颖性红队审计

检索截止日期：2026-09-04（Asia/Shanghai）

目标层级：弱 CCF-B / 强 CCF-C full paper

状态：Research Opportunity audit；不是 Paper Candidate 结论。

## 0. 范围、证据等级与检索方法

本报告审计如下交集是否已有直接工作：晶体管级非线性瞬态、外部不可信
producer、可携带证书、独立 checker、离散 MNA 根的存在唯一性、长轨迹组合、
规格保持，以及低于高精度重算的检查成本。检索覆盖 IEEE/DATE 官方页面、ACM、
SIAM、Springer、Elsevier 元数据、arXiv、作者主页与机构仓库，并对 DATE 2019、
Nakaya 2009、validated ODE/DAE、Rump verified numerics、AMS formal verification、
proof-carrying computation、稀疏可靠线性代数和 Verilog-A 编译链做关键词与引文扩展。

证据标记：`full-text/theorem` 表示已取得公开全文并检查目标公式或定理；既有条目的
`abstract-only` 是仅限
摘要/元数据的旧标记；正式 Round 3 起细分为 `publisher-abstract`（只核验出版社摘要与
书目信息）和 `institutional-metadata`（只核验作者主页或机构出版记录）。后三类均不
支持定理编号、精确前提、公式等价或复杂度证明的断言。`book` 表示依据出版商目录及
经典专著，不声称逐页精读。本地 PDF
位于 `../reference_papers_origin/`，转换文本位于
`../reference_papers_processed/`。双栏或字体编码导致转换器标为 `partial` 时，PDF
仍是唯一权威来源。

使用过的代表检索式包括：

- `validated|verified|rigorous transient circuit simulation`；
- `interval Newton|Krawczyk circuit MNA transistor`；
- `validated integration DAE time slab trajectory tube`；
- `proof-carrying simulation independently checkable numerical certificate`；
- `formal verification nonlinear analog circuit reachability transistor-level`；
- `verified sparse linear systems LU preconditioner`；
- `Verilog-A interval arithmetic automatic differentiation Jacobian generation`。

检索的阴性证据不能证明不存在；这里的结论是“在上述数据库、检索式和引文链中
未发现”，不是无条件首创声明。

## 1. 最相关论文表格

| Paper | Year/Venue | Problem | Method | Guarantee | 与本方向重叠 | 威胁程度 |
|---|---|---|---|---|---|---|
| Akhter, Reiher, Greenstreet, [Finding All DC Operating Points Using Interval Arithmetic Based Verification Algorithms](https://doi.org/10.23919/DATE.2019.8714966) (`full-text`, PDF pp. 1–4) | 2019/DATE | CMOS 全部 DC 工作点、ring-oscillator start-up DC 条件 | 区间分支、Krawczyk、器件模型界 | 对搜索盒中的 DC 根作排除或唯一包含；自动搜索全部工作点 | 晶体管级、Krawczyk、可靠器件求值直接重叠；无 transient、外部轨迹或 certificate/checker 协议 | **High** |
| Nakaya, Nishi, Oishi, Claus, [Numerical Existence Proof of Five Solutions for Certain Two-Transistor Circuit Equations](https://doi.org/10.1007/BF03186538) (`abstract/full-view`, §2–4) | 2009/JJIAM | 两晶体管电路五个 DC 解 | IEEE-754 向外舍入与 Krawczyk | 严格证明五个解存在；不是长轨迹 | 证明 Krawczyk+晶体管电路绝非新颖 | **High** |
| Kolev, Mladenov, [An Interval Method for Finding All Operating Points of Non-linear Resistive Circuits](https://doi.org/10.1002/cta.4490180302) (`abstract-only`) | 1990/IJCTA | 非线性电阻电路全部工作点 | 区间分析与分支 | DC 工作点集合包含/搜索 | 更早的 DC 区间电路 prior art | **Medium** |
| Moore, Kearfott, Cloud, [Introduction to Interval Analysis](https://doi.org/10.1137/1.9780898717716) (`book`) | 2009/SIAM | 区间分析基础 | interval Newton、Krawczyk、向外舍入 | 条件式存在/唯一性与包含定理 | 全部数学基础；不能作为算法 novelty | **High** |
| Rump, [Verification Methods: Rigorous Results Using Floating-Point Arithmetic](https://doi.org/10.1017/S096249291000005X) (`full-text`, §§2, 10–13) | 2010/Acta Numerica | 浮点上的可靠数值计算 | error-free transforms、区间法、线性/非线性验证 | 在明确浮点模型下的数学可靠界 | checker 算术、线性/非线性证书的基础 | **High** |
| Chen, Hashimoto, [Verification methods for nonlinear equations with saddle point functions](https://doi.org/10.1016/S0377-0427(03)00570-3) (`publisher-abstract` + `institutional-metadata`) | 2003/Journal of Computational and Applied Mathematics 159(1), 13–24 | 具有鞍点函数的非线性方程 | 摘要所述的 Krawczyk 型区间算子分块分解 | 摘要称为 fast verification algorithm；本轮未核验具体定理 | 直接威胁“分块 Krawczyk/结构化非线性验证”这一宽泛 novelty；未核验到 transient MNA 或 BlockStamp 递推 | **High** |
| Schwandt, [A truncated cyclic reduction algorithm for interval arithmetic tridiagonal systems of equations](https://doi.org/10.1080/00207168708803564) (`publisher-abstract` + `institutional-metadata`) | 1987/International Journal of Computer Mathematics 21(2), 161–184 | 区间系数三对角线性系统 | 截断 cyclic reduction，以廉价区间替代省略步骤并保持包含性 | 出版社摘要明确声称保持 inclusion；本轮未核验具体定理 | 直接威胁“带状区间递推/截断仍保包含”宽泛 claim | **High** |
| Schwandt, [Cyclic Reduction for Tridiagonal Systems of Equations with Interval Coefficients on Vector Computers](https://doi.org/10.1137/0726039) (`publisher-abstract` + `institutional-metadata`) | 1989/SIAM Journal on Numerical Analysis 26(3), 661–680 | 区间系数三对角线性系统 | 面向向量机的 interval cyclic reduction | 摘要报告算法、数值行为和实验；本轮未核验具体定理 | 否定“interval cyclic reduction 首创”；不等同于非线性时域 MNA 证书 | **High** |
| Schwandt, [Truncated interval arithmetic block cyclic reduction](https://doi.org/10.1016/0168-9274(89)90047-0) (`official-metadata`) | 1989/Applied Numerical Mathematics 5(6), 495–527 | 题名明确指向 interval block cyclic reduction；目标全文未取得 | 具体 block recurrence 与 truncation 规则未核验 | 定理、包含条件与复杂度均未核验 | 题名本身构成强威胁，但不能据此声称与 BlockStamp 公式等价 | **High** |
| Frommer, Hashemi, [Verified error bounds for solutions of Sylvester matrix equations](https://doi.org/10.1016/j.laa.2010.12.002) (`full-text/theorem`, Theorems 1–2, Proposition 1, Algorithm 1, Proposition 2, pp. 4–11) | 2012/Linear Algebra and its Applications 436(2), 405–420 | Sylvester 矩阵方程的可靠解包围 | factorized Krawczyk；对角/块对角变换；不显式形成大逆，改用向外舍入逐项除法或 block back substitution；对角化算法 `O(m^3+n^3)`，固定 block size 下 substitution `O(nmb)` | strict inclusion 推出非奇异与唯一解包围 | 公式级覆盖“因子化算子作用、避免显式大逆、结构降复杂度与三角区间依赖风险” | **High** |
| Nedialkov, Jackson, Corliss, [Validated Solutions of Initial Value Problems for ODEs](https://doi.org/10.1016/S0096-3003(98)10083-8) (`abstract-only`) | 1999/AMC | ODE 初值问题的严格积分 | Taylor series、区间 remainder、wrapping 控制 | 成功时证明唯一解并给出真解包围 | 已覆盖“逐步唯一性+轨迹管道”的一般思想 | **High** |
| Lin, Stadtherr, [Validated Solutions of IVPs for Parametric ODEs](https://doi.org/10.1016/j.apnum.2006.10.006) (`abstract-only`) | 2007/Applied Numerical Mathematics | 区间初值和参数下的 ODE 解集 | Taylor model/区间传播 | 对所有允许参数/初值给出验证包围 | 直接威胁参数化 slab 接口这一普通表述 | **High** |
| Berz, Makino, [Verified Integration of ODEs and Flows Using Differential Algebraic Methods on High-Order Taylor Models](https://doi.org/10.1023/A:1024467732637) (`abstract-only`) | 1998/Reliable Computing | 长时间 ODE 严格积分与 wrapping | 高阶 Taylor models | 连续流严格包围 | time-slab/tube 组合的理论近邻 | **High** |
| Kapela et al., [CAPD::DynSys](https://doi.org/10.1016/j.cnsns.2020.105578) (`full-text`, §§1, 4–6) | 2021/CNSNS | ODE、变分方程和 Poincaré map 的严格计算 | Lohner 型 set propagation、自动微分 | C0/C1/Cr 严格包围 | 成熟 validated integrator；不是 SPICE 离散根或独立 certificate | **High** |
| Nedialkov, [VNODE-LP: A Validated Solver for IVPs in ODEs](https://www.cas.mcmaster.ca/~nedialk/vnodelp/) (`metadata/tool`) | 2006/technical report+tool | ODE IVP | Taylor/Hermite–Obreschkoff、literate programming | 唯一解和 enclosure | 普通 validated integration 的强 baseline | **High** |
| März, Tischendorf, [Recent Results in Solving Index-2 DAEs in Circuit Simulation](https://doi.org/10.18452/2534) (`abstract-only`) | 1996/2005 repository | charge-oriented MNA 的 index-2 结构、可解性与积分 | DAE 结构分析、BDF、defect correction | 分析条件，不是逐轨迹浮点证书 | 直接限定可支持拓扑和 DAE 假设 | **High** |
| Chaudhry, Lewis, Molla, [Adjoint-based A Posteriori Error Analysis for Semi-explicit Index-1 and Hessenberg Index-2 DAEs](https://arxiv.org/abs/2507.03712) (`full-text`, Thms. 3.1, 4.1; §§3–6) | 2025/arXiv | DAE 时间离散对 QoI 的后验误差 | DAE/ODE adjoint error representations | 估计 QoI 离散误差；数值上准确，不是区间存在唯一性 | 会挑战规格误差故事，但保证和 trust model 不同 | **High** |
| Auzinger, Weinmüller, [Defect-based A-posteriori Error Estimation for DAEs](https://doi.org/10.1002/pamm.200700484) (`abstract-only`) | 2008/PAMM | index-1 DAE collocation 全局误差 | defect correction/QDeC | 渐近正确估计，不是严格浮点包含 | 必须与 nonlinear solve certificate 区分 | **Medium** |
| Cao, Petzold, [A Posteriori Error Estimation and Global Error Control for ODEs by the Adjoint Method](https://escholarship.org/uc/item/3c59x9vs) (`full-text available`) | 2004/SIAM JSC | ODE 全局误差与 QoI | adjoint sensitivity | error estimate/condition estimate | 规格导向误差控制近邻；非独立证书 | **Medium** |
| Dang, Donzé, Maler, [Verification of Analog and Mixed-Signal Circuits](https://www-verimag.imag.fr/~tdang/Papers/fmcad04.pdf) (`full-text`, §§2–4) | 2004/FMCAD | 非线性 AMS 时域属性 | hybrid abstraction、reachability | 抽象模型上的可达性/属性保证 | 已能证明 transient property，但对象不是某条 SPICE 离散轨迹 | **High** |
| Zaki, Tahar, Bois, [Formal Verification of Analog and Mixed Signal Designs: A Survey](https://doi.org/10.1016/j.mejo.2008.05.013) (`abstract-only`) | 2008/Microelectronics Journal | AMS equivalence/model checking/reachability/runtime/deduction | 多类形式化方法 | 依方法而异 | 阻止“首次严格证明模拟规格”的宽泛表述 | **Medium** |
| Yasmin et al., [Formal Verification of Nonlinear Analog Circuits](https://www.em.cs.uni-frankfurt.de/fileadmin/em_files/Paper/2024/PVLYasmin.pdf) (`full-text`, §§II–IV) | 2024/MBMV | 晶体管模型下非线性模拟电路可达性 | 多项式/分段模型与 reachability | 抽象模型可达集合 | 近期 transistor-level formal baseline；不检查外部数值轨迹 | **High** |
| Hunt, Ramanathan, Moore, [VWSIM: A Circuit Simulator](https://arxiv.org/abs/2205.11698) (`full-text`, Abstract; §§2, 6) | 2022/ACL2 Workshop | RSFQ/SPICE-like 电路模拟的逻辑建模 | ACL2 中网表、方程和模拟器定义 | 电路模型有逻辑语义；论文说明浮点矩阵求解仍未纳入 ACL2 | 最接近“可信仿真架构”，但无 CMOS transient 数值根证书 | **High** |
| Ivanov et al., [Reasoning about Safety of Learning-Enabled Components](https://doi.org/10.1109/DAC.2019.00103) (`full-text author version`) | 2019/DAC | 学习组件 CPS 安全 | simulation traces + barrier certificates | barrier 条件下安全性 | trajectory→property 架构近邻；非电路数值正确性 | **Low** |
| Love, Jin, Makris, [Proof-Carrying Hardware Intellectual Property](https://doi.org/10.1109/TIFS.2011.2160627) (`abstract-only`) | 2012/TIFS | 不可信硬件 IP 的安全属性 | vendor proof + Coq consumer checking | 给定逻辑策略的形式证明 | producer/certificate/checker trust model 直接可借鉴，证明对象不同 | **Medium** |
| Guo et al., [Information Flow Tracking in AMS Designs through Proof-Carrying Hardware IP](https://doi.org/10.23919/DATE.2017.7927268) (`abstract-only`) | 2017/DATE | AMS IP 信息流 | proof-carrying information-flow tracking | 安全/信息流属性 | “proof-carrying analog”术语已被占用；非数值仿真轨迹 | **Medium** |
| Cheung et al., [Verifying Integer Programming Results](https://arxiv.org/abs/1611.08832) (`full-text`, §§1–4) | 2017/IPCO | MIP 黑盒求解结果 | VIPR certificate + 独立 checker | 精确有理证书检查 | producer-agnostic 数值证书架构强近邻 | **Medium** |
| Ogita, Oishi, [Fast Verified Solutions of Sparse Linear Systems](https://interval.louisiana.edu/reliable-computing-journal/volume-19/reliable-computing-19-pp-127-141.pdf) (`full-text`, §§3–6) | 2013/Reliable Computing | H-matrix 稀疏线性系统 | componentwise bounds、无需显式逆/完整 LU | 计算解的严格误差界 | 证书内线性核与性能 claim 的 killer baseline | **High** |
| Rump, Ogita, [Super-fast Validated Solution of Linear Systems](https://doi.org/10.1016/j.cam.2005.08.019) (`abstract-only`) | 2007/JCAM | 快速可靠线性求解 | residual verification、精确点积 | 严格解包围，成本可接近普通求解 | 否定“可靠检查必然昂贵”或“快速检查全新” | **High** |
| Rump, Ogita, [Verified Error Bounds for Matrix Decompositions](https://doi.org/10.1137/24M165096X) (`abstract-only`) | 2024/SIMAX | 浮点矩阵分解验证 | factorization residual/error bounds | 分解误差严格界 | producer 提供 LU witness 的近期理论近邻 | **High** |
| Lemaitre, McAndrew, Hamm, [ADMS—Automatic Device Model Synthesizer](https://doi.org/10.1109/CICC.2002.1012760) (`abstract-only`) | 2002/CICC | Verilog-AMS 紧凑模型到模拟器代码 | 解析和代码生成 | 无区间/可靠浮点保证 | 否定“首次自动生成 device code”；三语义仍未覆盖 | **Medium** |
| Bűrmen et al., [Free Software Support for Compact Modelling with Verilog-A](https://ojs.midem-drustvo.si/index.php/InfMIDEM/article/view/1999) (`full-text`, §§2–5) | 2024/Inf. MIDEM | ADMS/OpenVAF/VerilogAE 等开源 Verilog-A 栈 | AST/IR、代码生成、导数支持 | 工程语义和兼容性；无向外舍入证明 | 近期 compiler killer baseline；区间第三语义仍是缺口 | **High** |
| Drzevitzky, Kastens, Platzner, [Proof-Carrying Hardware: Concept and Prototype Tool Flow](https://doi.org/10.1155/2010/180242) (`full-text available`) | 2010/IJRC | FPGA 模块在线验证 | SAT proof trace + 小 checker | 组合等价性证明 | 证明 producer/checker 接口不是新概念 | **Low** |
| Hartong, Hedrich, Barke, [On Discrete Modeling and Model Checking for Nonlinear Analog Systems](https://doi.org/10.1007/3-540-45657-0_33) (`abstract-only`) | 2002/CAV | 非线性模拟系统形式验证 | 离散抽象/model checking | 抽象上的属性结论 | transient formal verification 经典近邻 | **Medium** |
| Kearfott, Xing, [An Interval Step Control for Continuation Methods](https://doi.org/10.1137/0731048) (`full-text`, abstract + algorithm description) | 1994/SIAM JNA | 沿隐式解曲线的可靠 continuation | interval uniqueness test 下选择尽可能大的 verified step | 保证 corrector 留在同一唯一曲线分支 | 直接覆盖“失败后缩短并可靠选择最大步长”的一般算法形态 | **High** |
| Immler, [A Verified ODE Solver and the Lorenz Attractor](https://doi.org/10.1007/s10817-017-9448-y) (`full-text`, §§6.2–6.3) | 2018/JAR | 形式化可靠 ODE 流包围 | verified Runge--Kutta、adaptive step-size control、set splitting | Isabelle/HOL refinement 下的 flow enclosure | 覆盖 adaptive verified stepping/splitting；证明对象不是固定离散 MNA 根 | **High** |
| Duff, Lee, [Certified homotopy tracking using the Krawczyk method](https://doi.org/10.1145/3666000.3669699) (`full-text/algorithm`) | 2024/ISSAC | 参数 homotopy 的 certified solution-path tracking | parametric Krawczyk、adaptive step selection、preconditioning | correctness 与 termination | 直接威胁“adaptive Krawczyk slab/path tracking” | **High** |
| Lee, [A priori bounds for certified Krawczyk homotopy tracking](https://arxiv.org/abs/2512.01355) (`preprint/full-text`, Thms. 2, 4; Algorithms 2–3) | 2025/arXiv | Krawczyk certified tracking 的步长与复杂度 | 用局部几何先验界替代反复 interval Krawczyk 试探 | 成功步长界与按 weighted path length 的迭代数界 | 进一步覆盖 adaptive/cost-aware Krawczyk step control；不是电路证书 | **High** |

表中工作没有一篇被判为整个系统交集的 **Direct prior art**：没有证据显示其同时满足本文定义的
全部交集条件。这个“0 篇”是当前审计结果，不是领域不存在性证明。

### 1.1 Round 4 高威胁先例：访问与公式级对照

Chen–Hashimoto 和 Schwandt 的合法目标全文仍未取得。这里把所有未知项显式写成
`NOT VERIFIED`，不以“未读到”推断 non-overlap。Frommer–Hashemi 的
[Wuppertal 作者预印本](https://www-ai.math.uni-wuppertal.de/SciComp/preprints/SC1003.pdf)
已归档并逐式检查，证据等级升级为 `full-text/theorem`。

| 先例 | Operator | 结构 | dependency representation | 保证 | 复杂度 | witness / proof object | 对 `D_k/L_k/R_k/U_k` 的裁决 |
|---|---|---|---|---|---|---|---|
| Chen–Hashimoto 2003 (`publisher-abstract`) | 摘要只确认 Krawczyk 型算子的 block decomposition；公式 `NOT VERIFIED` | saddle-point nonlinear equations；块布局 `NOT VERIFIED` | `NOT VERIFIED` | 摘要称 verification algorithm；定理前提与唯一性范围 `NOT VERIFIED` | “fast”只有定性表述 | `NOT VERIFIED` | “block Krawczyk/fast structured nonlinear verification”不是安全贡献；不能声称与当前递推相同或不同 |
| Schwandt 1987/1989 (`publisher-abstract` / `official-metadata`) | interval cyclic reduction；标量及 block 递推公式 `NOT VERIFIED` | 三对角区间系数系统；另有题名明确的 block cyclic reduction | 1987 摘要确认以廉价区间替代省略计算并保持 inclusion；具体依赖表示 `NOT VERIFIED` | 只确认 1987 摘要范围内的 inclusion 描述；前提 `NOT VERIFIED` | `NOT VERIFIED` | 未从可访问主来源确认 portable witness | “带状/块带状区间递归”和“截断保持包含”不是安全贡献；与单向 BE 前代的等价性未证 |
| Frommer–Hashemi 2012 (`full-text/theorem`) | 线性 Krawczyk `k=-R(Ax_tilde-b)+(I-RA)z`（p. 4）；令 `S_A=(W_A A)IWA`、`S_B=IVB(BV_B)`、`vec(D)=diag(Delta)`，Sylvester 公式 (15)–(18) 为 `R_res=W_A(AX_tilde+X_tilde B-C)V_B`、`M=(D_A-S_A)Z`、`N=Z(D_B-S_B)`、`U=(-R_res+M+N)./D`，包围以 `Delta^{-1}` 预条件的 Krawczyk 作用 | `P=I_n kron A+B^T kron I_m`；谱对角化，或 (20)–(21) 的 sparse upper-triangular block `Delta` | verified inverse-transform enclosures `IWA/IVB`；不形成 `Delta^{-1}`，用向外舍入逐项除法或 block back substitution。pp. 10–11 明确展示 RHS 重复出现，并警告 substitution 越长 dependency widening 可指数恶化 | Theorem 2 + Proposition 1：`U subset int(Z)` 推出非奇异与唯一 Sylvester 解，回变换包围为 `X_tilde+IWA U IVB` | 通用向量化法报告 `O(m^3n^3)`；Algorithm 1 为 `O(m^3+n^3)`；固定 block size `b` 时 substitution 为 `O(nmb)` | directed rounding、`IWA/IVB` verified inverse enclosures、epsilon inflation、strict inclusion；原文未规定 portable independent-checker certificate | 已公式级覆盖 factorized Krawczyk、避免显式大逆、区间三角 solve 与 dependency 风险；不同 Sylvester/BE-MNA 结构不足以单独构成新算法 |
| 当前 BlockStamp | `K=x_bar-CG+(I-C[JG])(X-x_bar)`，checker profile 为 `C=M^{-1}`；`U_a=VSolve(D_a,R_a)`、`U_k=VSolve(D_k,R_k-L_kU_{k-1})` | BE block-lower-bidiagonal + device-local MNA stamps | 普通 interval boxes 与向外舍入 block forward substitution；尚无新的 dependency-preserving representation | strict inclusion 调用既有 nonlinear Krawczyk 定理；verified solve 包围固定 exact inverse action | 稠密 `n`-block、`p` 步时为保守 `O(pn^3)` factor verification + `O(pn^2)` recurrence；不推出优于 verified sparse | checker 重建语义、逐块 solve/invertibility 证据、digest、tube 与 strict-inclusion 结果 | 当前递推是标准 block forward substitution；device-local reconstruction 与 portable certificate 属于系统组织差异 |

页码差异说明：T&F 正式记录与 Schwandt 作者书目均给 1987 年 IJCM 论文为
161–184；本报告采用原刊记录。证据边界和二元裁决详见
`../steps/004_theorem_prior_art_closure.md`。

## 2. 最危险的既有工作簇

### 2.1 Akhter et al., DATE 2019

该文把 Krawczyk、区间分支和现代短沟道器件模型用于 CMOS DC 全工作点验证，并
公开实现。危险之处是晶体管级 equation reconstruction、器件区间界和自动验证均已
存在；若新工作只是把每个 BE 时间点看成一个 DC 方程逐点跑 Krawczyk，就很像机械
扩展。它没有外部 transient producer、长轨迹接口不确定性、可携带证书、独立 checker、
规格保持或局部回退。新方法必须有不同的时空算法和复杂度证据，而不是改分析类型。

### 2.2 Nedialkov–Jackson–Corliss 1999 / VNODE-LP

validated integrator 成功时已经证明 IVP 唯一解并提供全程 enclosure；逐步传播前一
时间点的区间也是标准结构。它高度威胁“首次严格轨迹管道”和“首次 time slab
composition”。剩余差异是：本文认证的是给定时间离散规则的非线性代数根而非连续
ODE 真解；接受任意外部 producer；certificate 可由独立小 checker 重放；并利用 MNA
稀疏块结构。若没有 checker TCB/证书格式和成本优势，容易被视为 validated integrator
重新命名。

### 2.3 Lin–Stadtherr 2007

它对区间参数和区间初值统一验证一族 ODE 解，直接覆盖“对所有 slab 接口状态传播”
的抽象数学形态。它没有 charge-based MNA 的离散块根、器件 stamp 或外部证书接口。
因此 slab 参数化存在定理本身大概率不足以成为主贡献；新颖点必须落在电路结构化
certificate construction/checking、anti-wrapping 接口表示或可证明复杂度上。

### 2.4 Rump 2010

该综述系统覆盖用普通浮点和向外舍入获得严格结果，包括线性、非线性方程与稀疏问题。
其中 Theorem 13.3（p. 89）允许任意固定实矩阵 `R`；若 Krawczyk image strict-includes
于中心化 box，则 `R` 和 interval Jacobian 的所有成员非奇异，并得到唯一根。因而
`C=M^{-1}` 是本项目 checker profile，不是该定理预先要求的非奇异条件。
它会否定任何“首次用浮点构造严格数值证明”“预条件器由不可信 producer 给出所以不
可靠”的论断：候选近似逆可以完全不可信，只要 checker 重新验证包含关系。剩余空间是
为 MNA 时空结构设计小证书、局部 stamp TCB 和低 fill-in 检查，而非 Krawczyk 定理。

### 2.5 Ogita–Oishi 2013 / Rump–Ogita 2007

这些工作表明某些稀疏/H-matrix 或一般线性系统可以快速获得严格误差界，且不必显式
形成完整逆。它们直接威胁“verified LU witness 是全新”及“checker 肯定显著便宜”的
未经证明主张。它们没有非线性 MNA slab 或器件语义，但应作为 checker 线性核的 killer
baseline；论文必须报告 fill-in、病态性、失败率和相对高精度重算的端到端成本。

### 2.6 VWSIM 2022

VWSIM 在 ACL2 中定义 SPICE-like 网表和 RSFQ 电路模拟语义，目标是可推理的电路
模型。其关键限制是论文明确说明矩阵求解和评价仍使用 Common Lisp 浮点，尚未完全
纳入 ACL2；也没有 producer-carried transient root certificate。它仍会挑战“首次可信
电路仿真”这种宽泛定位，因此安全表述只能是特定于非线性离散 MNA 结果的独立数值
证书，而不是首个形式化电路模拟器。

### 2.7 Dang–Donzé–Maler 2004 与 Yasmin et al. 2024

两者说明模拟电路 transient property/reachability 已经能被形式化方法处理，后者还更
接近非线性晶体管模型。它们证明的是模型的一组连续行为或抽象可达性，而不是验证某次
SPICE 离散运行的数值正确性。故“从严格轨迹证明 threshold/overshoot”不是独立新颖点；
可能的新意是把已认证离散 tube 以很低增量成本交给离散规格 monitor，并明确不声称
网格间连续峰值。

### 2.8 Bűrmen et al. 2024 / ADMS 2002

Verilog-A 到数值代码、Jacobian/导数和多模拟器接口已有成熟编译链。当前未发现其生成
带可靠特殊函数和向外舍入的区间第三语义，但“自动生成器件 stamp/Jacobian”本身绝非
创新。若会议版包含编译器贡献，必须定义受限语言、数值/AD/interval 三语义一致性定理，
并对 `limexp`、分支、状态、事件和不可微点给出拒绝或 sound enclosure 规则。

### 2.9 Chen–Hashimoto 2003

正式摘要已经把“基于 Krawczyk 型区间算子的 block decomposition 的快速非线性验证”
置于 prior art。因而 BlockStamp 不能把 block Krawczyk、结构化预条件或比标准 Krawczyk
更快作为孤立贡献。当前仍可能区分的是具体方程与 proof object：该先例的摘要对象是
鞍点函数，并提到凸优化和离散定常 Navier–Stokes；可访问主来源没有确认它处理 BE
瞬态 MNA、器件局部 stamp、跨时间接口量词或可携带 checker。官方全文端点受
API/account gate 限制，作者/机构页未找到合法公开副本，故 operator、dependency、保证、
复杂度与 witness 均明确记为 `NOT VERIFIED`。这个访问缺口不能作为 non-overlap 证据。

### 2.10 Schwandt 1987/1989

1987 T&F 摘要确认三对角区间系统上的 cyclic reduction，并明确描述在 reduction 与
solution 两个阶段以廉价区间替代省略计算且保留 inclusion；1989 SIAM 摘要确认区间系数
三对角 cyclic reduction 与数值/向量化研究。另一个 1989 论文的正式题名确认 block
cyclic reduction 这一近邻，但本轮没有取得能核验其公式或定理的正文/摘要。因此“沿带状
结构作区间递归”和“inclusion-preserving truncation”均是既有方法描述；却不能进一步
声称 Schwandt 的 block recurrence、dependency treatment 或 theorem 与 BlockStamp
等价。所有这些项在公式矩阵中保持 `NOT VERIFIED`。

### 2.11 Frommer–Hashemi 2012

作者预印本已完成公式级核验。论文先把 `AX+XB=C` 写成
`P vec(X)=vec(C)`，其中 `P=I_n kron A+B^T kron I_m`，再以谱变换把 `P` 近似化为
`Delta`。Proposition 1 的 (15)–(18) 不显式形成 `Delta^{-1}`，而是把 residual 和两个
结构化 remainder 分别形成后逐项除以对角 `D`；block diagonalization 情形则对 (20)–(21)
的 sparse upper-triangular blocks 做 outward-rounded back substitution。

这个先例不仅覆盖 factorized Krawczyk/避免显式大逆；pp. 10–11 还给出三角回代中同一
RHS 分量重复出现的展开式，并明确警告 interval dependency widening 随 substitution
长度恶化。因此当前 `U_k=VSolve(D_k,R_k-L_kU_{k-1})` 若仍使用普通 interval boxes，
只能视为另一矩阵结构上的标准 block substitution。真实差异是非线性 BE-MNA、器件
stamp、参数化时间接口和独立 certificate/checker；这些是系统对象/组织差异，不自动
产生新的数值算法。

### 2.12 Adaptive verified stepping and Krawczyk path tracking

Kearfott–Xing 1994 已在 interval uniqueness test 下为 continuation 选择可靠步长；
Immler 2018 的形式化 ODE solver 包含 adaptive step-size control 与 set splitting；
Duff–Lee 2024 将 parametric Krawczyk 用于 certified homotopy tracking 与 adaptive step
selection；Lee 2025 又给出 Krawczyk tracking 的先验成功步长界与迭代复杂度。它们的
证明对象分别是隐式解曲线、连续 ODE flow 或 homotopy path，不是固定 BE-MNA 外部结果
证书；但“失败后缩短 slab”“选择最大可验证 slab”或“adaptive certified partition”
本身已被直接覆盖，不能成为独立算法 novelty。

M2 后的强简单 baseline 进一步削弱了追逐这一机制的理由：传播每个已接受 Krawczyk
image 的 pointwise B2 在六个 100-step 实例上均改善旧 pointwise prefix，没有 fixed slab
或 largest-first adaptive policy 击败它。该结果是 canary 证据而非普遍不可能性定理，
但足以停止当前 fixed/adaptive slab headline。

## 3. 核心问题：是否已有直接 Proof-Carrying SPICE？

**当前检索范围内未发现。** 更准确地说，没有找到一项工作被证据确认同时具备：

1. transistor-level nonlinear transient SPICE/MNA；
2. 接受任意外部、可不可信的候选轨迹；
3. producer → portable certificate → independently implemented checker；
4. 对指定离散规则的根证明局部存在且唯一；
5. 参数化 slab 接口与长轨迹组合；
6. device-local/时空稀疏结构；
7. 从 tube 到离散规格；
8. checker 成本低于可信重算并支持失败块回退。

但各组成部分几乎都有成熟 prior art：DC 晶体管区间验证（DATE 2019/Nakaya）、严格
轨迹包围与接口传播（validated ODE）、模拟 transient 属性（reachability）、不可信
producer 的证书架构（PCC/VIPR）、分块/因子化 Krawczyk 与 interval block cyclic
reduction（Chen–Hashimoto、Schwandt、Frommer–Hashemi）、可靠稀疏线性核
（Rump/Ogita）和 Verilog-A 编译（ADMS/OpenVAF）。因此当前证据只保留“受限
Proof-Carrying SPICE 系统交集”这一 Research Opportunity；当前 block forward
substitution 不是已成立的新结构化算法，更不支持“各个组件首次出现”。

## 4. 与 DATE 2019 的逐项对比及 reviewer 攻击

| 维度 | DATE 2019 | Proof-Carrying SPICE 必须做到 |
|---|---|---|
| 方程 | 静态 DC 非线性方程 | 给定 BE/BDF2 等规则的跨时间离散 MNA |
| 目标 | 在搜索域找全/排除全部 DC 工作点 | 验证给定 candidate tube 内每个 slab 的局部唯一离散根 |
| producer | 验证器自身搜索 | 任意外部 producer，不信任其 Newton/Jacobian/浮点 |
| 时间组合 | 无 | 对所有接口状态的参数化包含与归纳组合 |
| 结构 | 电路变量/器件模型 | 单步稀疏结构 + 块下双/多对角时间结构 + device-local stamps |
| 产物 | 验证结果 | 版本化、可序列化、可独立重放的 certificate |
| 属性 | DC 工作点/启动问题 | 仅离散时间 peak、overshoot、threshold、settling monitor |
| 失败 | 搜索盒继续细分 | 只回退失败 slab，保持已验前缀 |
| 性能对手 | dReal/Z3 | strict SPICE rerun、逐步 Krawczyk、validated integrator、可靠稀疏 solver |

**会被评价为 “DATE 2019 transient extension” 的风险很高**，如果实现仅为：对每个时间
点重新构造方程，调用现成 Krawczyk，然后顺序传播点区间。避免这一评价至少需要：

- 一个针对离散 charge-based MNA slab 的参数化组合定理，清楚处理历史项和接口量词；
- 一个可审计的器件局部/时间结构 certificate organization，而非把标准 block forward
  substitution 改名；若继续算法主张，还须新增 dependency representation、witness reuse
  或优化机制及其定理；
- 明确、独立的 checker TCB 与证书语法，producer 数据全部作为不可信 hint；
- 与逐点 DATE-style Krawczyk、可信严格重跑、CAPD/VNODE 类方法以及可靠稀疏线性核
  的 killer comparisons；
- 端到端展示宽松/近似 producer 被安全接受、失败仅导致局部重算，且总成本净获益。

## 5. 十个候选创新点的红队结论

| 候选点 | 审计判断 | 安全边界 |
|---|---|---|
| transistor-level nonlinear transient | 未见直接相同证书，但 transient formal/validated integration 很成熟 | 限定“指定离散 MNA 根”，不声称连续真解 |
| untrusted external producer | 数值优化/PCC 中成熟，电路交集未见 | 新意在电路证书实例化和 TCB，不在架构口号 |
| independent checker | 已有广泛 certifying algorithms | 必须实现语义独立、不能复用 producer stamp/Jacobian |
| trajectory certificate | validated integrator 已输出 enclosure，portable checker 差异尚可 | 需明确格式、重放算法和 proof obligation |
| time-slab composition | 一般传播和区间初值已标准化 | 单独不是 novelty；需 MNA 专用定理/算法 |
| block-banded temporal structure | verified structured solve、interval cyclic reduction 与 factorized Krawczyk 已高度重叠；当前 `D/L/U` 是标准块前代 | 只能作为 checker kernel；需非等价 dependency/witness 机制才可重开算法 claim |
| device-local interval stamp | DATE 2019 已有器件区间求值思想 | 需局部可组合 checker 与现代模型证据 |
| sparse LU/preconditioner witness | verified linear algebra 已高度重叠 | 只能作为子算法，需胜过 killer baseline |
| Verilog-A interval compilation | AD/代码生成成熟；未见可靠区间三语义工具 | 有空间但范围巨大，会议版宜受限子集 |
| tube→simulation specifications | reachability/monitoring 已覆盖一般思想 | 作为端到端必要组件，不宜单列主创新 |

## 6. 当前新颖性判断

**`REFRAME-SYSTEM`；Round 5 reframe action 已完成。**

Frommer–Hashemi 的全文公式已经覆盖 factorized Krawczyk、implicit inverse action、
outward-rounded block triangular solve 及其 dependency 风险；Chen–Hashimoto 和 Schwandt
的可访问主来源又把 block Krawczyk、interval banded/block reduction 放入高威胁先例。
而当前 `D_k/L_k/R_k/U_k` 没有定义新的 dependency representation 或 witness 机制，
故不能继续作为算法 headline。

该 closure 只表示研究主张已经按 prior art 缩窄：算法新颖性为
`ABANDONED-FOR-CURRENT-METHOD`，系统机会为 `OPEN / M2-FAILED-ECONOMICS`，Paper Candidate
仍为 `FAIL-UNVERIFIED`。它不把文献阴性检索转写成首创证据，也不满足 Step 008 的
algorithmic-difference promotion 条件。精确 claim register、最近邻、non-equivalence 与
证据义务见 `../steps/004_theorem_prior_art_closure.md` 第 6 节。

最安全的当前系统定位是：

> 在当前检索范围内，尚未有可访问证据确认一种面向受限晶体管级非线性瞬态离散 MNA
> 的 producer-agnostic 结果认证系统：它把外部候选轨迹和不可信数值 hint 转换为由独立、
> 可靠舍入 checker 重建器件/BE 语义后重放的 portable slab certificate，并支持参数化接口
> 组合、fail-closed verdict 和选择性恢复。这里不把标准 block substitution 当作新算法。

不能使用的表述包括：首次把 interval/Krawczyk 用于电路；首次严格包围电路轨迹；首次
证明模拟 transient property；首次 proof-carrying hardware；首次自动生成 Verilog-A
Jacobian；或证明真实硅片/连续时间总误差。

### 是否已达到 Paper Candidate？

**否。** 当前只有系统方向的 Research Opportunity：交集问题有根据，但系统组合的直接
prior art 仍需继续审计，也没有 killer baseline、主指标稳定增益、证书大小或真实电路
可行性信号。按照 `AGENTS.md`，不得直接进入完整 Paper Build。只有提出并证明一种
非等价的 dependency/witness/optimization 机制后，算法主线才可重新打开。

### 最强反方意见

“数值核心只是 DATE 2019 式电路 Krawczyk 加标准 block forward solve；Frommer–Hashemi
已经展示结构化 Krawczyk 与 interval triangular action，validated ODE 已覆盖传播，而
独立 checker 只是 certifying algorithms 的常规系统接口。”

反驳成立的前提不是换术语，而是证明独立语义重建、portable proof object、故障隔离与
端到端净收益形成不可由普通重算/现有 verified solver 替代的系统价值；若再声称算法
贡献，还必须另有新机制与定理。

## 7. 最需要继续检索与核验的方向

1. 若出版社或作者后续提供无需账户/API key 的合法 Chen–Hashimoto/Schwandt 全文，补做
   recurrence、dependency、保证、复杂度与 witness 的逐式核验；在此之前保持
   `NOT VERIFIED`，不重复下载受限/伪 PDF。
2. DATE 2019 的全部前向引用与 Greenstreet 组后续工作，尤其是否有未显式写
   “certificate”的 transient 扩展。
3. validated DAE（非 ODE）对 index-1 charge-based MNA、区间初值和隐式多步法的直接
   定理与实现；这是当前最大全文缺口。
4. 2024–2026 一般稀疏线性系统 verified error bounds，以及 factor witness 的可检查格式、
   fill-in 和失败区间。
5. OpenVAF/VerilogAE 的 IR、导数生成和特殊函数语义；确认是否有实验性 interval backend。
6. 专利、博士论文和工业技术报告中的“simulation result validation”“selective transient
   rerun”，防止系统故事已有但未进入主流会议。

## 8. Research Opportunity Gate 与最小可证伪 probe

当前仅保留一个主机会，避免把同一方向拆成伪多贡献：

**RO-1：Circuit-structured proof-carrying certificates for discrete transient MNA。**

- baseline 缺陷：普通 SPICE 成功标志和残差不提供独立的局部存在唯一性证明；通用
  validated integrator 不提供指定离散 SPICE 结果的 producer-agnostic portable checker。
- 系统假设：对固定 BE 的多个时间点构造 slab residual/Jacobian obligations；producer
  提供中心轨迹和稀疏 factor hints；独立 checker 以 device-local interval stamps 重建
  义务，使用标准块递推作为验证 kernel，检查 portable certificate 并在失败时二分 slab。
  当前不把该递推计为算法贡献。
- 最小 probe：R/C/diode + Level-1 MOS 的 10–100 节点、100–1000 步电路；比较逐点
  Krawczyk、整 slab dense Krawczyk、块结构 checker 和高精度重算的接受率、宽度、时间、
  certificate size 与局部失败率。
- 证伪条件：块结构检查不能优于逐点/高精度 baseline；接口 wrapping 在几十步内普遍
  爆炸；或者 checker 为复算器件/Jacobian 和 factor 而成本接近完整严格重跑。
- 当前门禁：prior-art **REFRAME-SYSTEM**；冻结 M2 的原始 W 信号被 contractive
  pointwise killer canary 解释，D/E 已停止；Research Opportunity **PASS**；Paper
  Candidate **FAIL/UNVERIFIED**。

## 9. 下载与可复现说明

公开可下载且相关性最高的论文已保存在 `paper2/reference_papers_origin/`。每次转换命令：

```bash
conda run -n auto_research python tools/scripts/convert_reference_papers.py \
  --input-dir paper2/reference_papers_origin \
  --output-dir paper2/reference_papers_processed
```

Frommer–Hashemi 的作者预印本已保存为
`reference_papers_origin/frommer_hashemi2012_sylvester.pdf`，SHA-256 为
`5dec1a9b01321a1f8b7ebfea86570f4976e7f0d04fa62e9f16c5bfee9c4c6e80`。Chen–Hashimoto
和 Schwandt 目标论文未取得可读合法公开全文，因此没有创建伪 PDF，并在上文逐项标记
`NOT VERIFIED`。本地 `reference_papers_processed/manifest.json` 记录既有转换统计；
原始 PDF 始终是公式、图表、页码和定理核验的权威来源。
