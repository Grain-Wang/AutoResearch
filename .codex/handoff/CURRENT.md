# AutoResearch 当前接续状态

> **当前有效项目：paper2 / BlockStamp-Cert**
>
> 本文件仅保存 `paper2` 分支的当前研究状态。不得从其他 paper 分支、旧 CoVoL/深度估计项目或历史数据门禁推断本项目状态。事实优先级始终为：`AGENTS.md` > 当前 Git/源码/测试/实验产物 > 本文件 > `TRANSCRIPT.md`。

## 1. 当前研究方向

- 分支：`paper2`
- 项目：`paper2`
- 工作题目：**BlockStamp-Cert: Independently Checkable, Circuit-Structured Certificates for Discrete Nonlinear Transient Simulation**
- 系统愿景：Proof-Carrying SPICE
- 当前阶段：**Research Opportunity**
- Opportunity Gate：PASS
- Paper Candidate Gate：FAIL / UNVERIFIED
- 当前目标：推进到稳定 CCF-B 级别的 Paper Candidate；不以 CCF-A 范式级要求提前淘汰方向。

核心研究问题：对固定步长 Backward Euler 离散的 nonlinear MNA 瞬态轨迹，能否利用 **device-local stamps + block-lower-bidiagonal temporal structure** 构造一个严格、独立、比通用逐点验证更高效的 certificate checker。

## 2. 已确认的非创新部分

以下内容不得作为 headline novelty：

- Krawczyk / interval Newton 本身；
- transistor-level DC interval verification；
- parameterized root enclosure / S-param 的一般方法；
- generic time-slab / initial-set propagation；
- verified LU/factor witness；
- producer/certificate/checker 的通用 proof-carrying 架构；
- Verilog-A 解析、代码生成或普通自动微分。

当前唯一可证伪的核心算法机会是：**联合利用器件局部 stamp 与瞬态 MNA 时间带状结构，对 slab Krawczyk operator 做严格隐式递推，并在 component-matched baselines 下获得可归因的 runtime / memory / certificate-size / certification Pareto 优势。**

## 3. 已完成证据

1. `paper2/research/proof_carrying_spice_literature.md`：完成首轮红队文献审计；没有发现完全相同的直接 prior art，但存在强相邻工作。
2. `paper2/steps/003_formal_soundness_contract.md`：已区分 `S-fixed` / `S-param`，明确局部离散根、incoming/outgoing interface、组合与 TCB 边界。
3. `paper2/steps/004_theorem_prior_art_closure.md`：已确认 S-param、initial-set propagation、verified factor witness 等不是核心创新。
4. `paper2/experiments/interval_backend.py`：存在 Decimal-based Stage-0 canary；**它不是最终严格 directed-rounded backend**。
5. `paper2/experiments/devices/stamps.py`：已有 diode 与受限 Level-1 NMOS interval-stamp canary；跨器件工作区间返回 unsupported/unknown。
6. `paper2/steps/005_baseline_defect_gate.md`：弱电导病态 MNA 展示 residual 与 forward error 可分离；状态仅为 `PASS-CANARY / REAL-WORKLOAD-UNVERIFIED`。
7. `paper2/steps/006_selective_recovery_contract.md`：已定义 dependency-safe suffix replay；仅当新 outgoing enclosure 被下一 cached incoming assumption 包含时才复用后缀。
8. 正式评审链：`review_round1.md`、`review_round2.md`、`review_round3.md`。历史阶段评估已移到 `paper2/research/notes/`，不计入 reviewer round。

## 4. 当前 P0 阻断项

1. **Soundness 前提未闭合**：当前 formal contract 需要显式要求 proof operator `C` 为 checker 可验证的可逆实算子；`C=0` 反例必须被排除。
2. **严格算术后端未完成**：Decimal `exp/log/sqrt/div` 只能作为 canary；正式 checker 需要 MPFR/等价 directed rounding。
3. **完整 transient MNA 未实现**：尚缺 R/C/source、BE history、节点/支路装配和完整 residual/Jacobian。
4. **BlockStamp recurrence 未实现**：没有可执行 operator microkernel，也没有 dense-equivalence enclosure test。
5. **B2-strong 未实现**：没有 component-matched pointwise verified Krawczyk baseline。
6. **主实验未出现**：没有 diode-RC / ring oscillator 的 certification rate、runtime、RSS、certificate bytes 或 end-to-end 数据。

## 5. 下一原子动作（按顺序）

1. 修正 `003_formal_soundness_contract.md`：固定 `C` 的可逆定义，并加入 `F(x)=x+2, X=[-1,1], C=0` 反例测试。
2. 新建真正 directed-rounded 的 rigorous arithmetic backend。
3. 实现 R/C/source/diode 的 fixed-step BE MNA microkernel 与 analytic/MPFR oracle。
4. 实现 BlockStamp block-bidiagonal recurrence，并与 MPFR dense operator action 逐元素交叉检查。
5. 实现与主方法共享全部组件的 B2-strong pointwise checker。
6. 运行 `dense-slab generic → device-local pointwise → temporal-only → temporal+device BlockStamp` component ladder。
7. 在 diode-RC 与 3-stage ring oscillator 上运行冻结的最小 nonlinear transient probe。

在上述最小机制门禁通过前，不扩张到 SRAM、BSIM、通用 Verilog-A、第二 producer 或大规模工业网表。

## 6. 当前停止/转向条件

- 若 BlockStamp 与 B2-strong / dense baseline 无稳定可归因优势，停止 Claim E 或降级为 restricted checker/system work。
- 若 pointwise verified checker 已足够便宜且 interface propagation 不构成问题，停止 slab headline。
- 任一 confirmed false accept、严格算术 containment 失败或 theorem counterexample 被 ACCEPT，立即停止 Claim S 并修复后全量回归。
- 若成熟 SPICE 的自然错误很少，动机改为 `untrusted / approximate / accelerated producer`，不得声称“成熟 SPICE 经常错误”。

## 7. 历史文件读取规则

- 正常继续研究只读取本文件、当前源码/测试/结果、`paper2/research/research_direction.md` 和最新正式 review。
- 只有需要追溯 paper2 决策时才读取 `.codex/handoff/TRANSCRIPT.md`。
- `paper2/research/notes/stage_assessment_before_ccfb_review.md` 是历史阶段技术笔记，不是正式 reviewer round，也不能覆盖当前事实。
