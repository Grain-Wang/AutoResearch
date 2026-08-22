# 014 Objective and Algorithm Specification

## Status and boundary

`SPECIFIED, UNVERIFIED`。本文件是 CoVoL-Depth 的唯一优化目标规范；配置入口为 `configs/covol/baseline_contract.yaml` version 3。方法暂名 **Main-PR**（cross-fitted partial-residual router），不使用 `orthogonalized`、`causal` 或理论风险保证等术语。

TIGER 使用自然语言任务指令在多个冻结异构 VFM 特征之间做 token-level 融合，并用移除专家后的预测变化对齐 routing contribution。Main-PR 不学习任务指令、不融合 VFM feature，也不把 expert-exclusion contribution 当作新颖性；它只解决两个已冻结、同任务 metric-depth 候选之间的局部决策：在预注册 clean utility 下最小化受控 caption 错误的尾部 regret。该边界必须由 Risk-L2D-C、TIGER-style LOO、DeferredSeg、Regression-L2D 与 DR-L2D 对照共同否证。

## Variables and aggregation

| 符号 | 定义 |
| --- | --- |
| `i,r,v` | image、eligible region、同 family caption variant；`v=1,2,3` |
| `D0,D1` | 冻结纯视觉与图文 metric-depth 候选 |
| `L0_ir,L1_ir(c)` | official crop、valid-depth mask 内的 region AbsRel |
| `a_ir` | clean empirical advantage，`L0_ir-L1_ir(c_clean)`，正值表示 D1 更好 |
| `zB_ir` | 图像难度、候选差异、confidence 等非语义特征 |
| `s_ir,m_ir` | 固定宽度 semantic block 及其 observation mask |
| `g_ir` | 使用 D1 的 soft gate；推理时由 dev 冻结 threshold 二值化 |

所有方法先在 region 内算损失；对每个完整 caption variant 先按同一组 region 权重聚合成 image regret，再在三个完整 variants 上取 worst-of-3，最后才跨 image 计算上尾 CVaR。禁止把不同 region 各自最坏的 variant 拼成现实中不存在的 Frankenstein caption。patch、variant 和 image 都不充当独立 cluster。

## Capacity-identical Claim-F controls

B/C controls 共用同一输入宽度与第一层：

$$
z^{BC}_{ir}=[z^B_{ir},\;m_{ir}\odot s_{ir},\;m_{ir}]. \tag{1}
$$

`B-direct` 固定 `s=0,m=0`；`C-direct` 使用观测 semantic block 和 `m=1`。两者的网络、第一层、参数量、初始化方案、目标、trial 与训练行完全相同。两个 C-permuted controls 分别使用跨 cluster 的 caption-length/scene-category 匹配置换，以及只破坏目标实体或局部关系的置换；不得再用同 scene 邻帧 cyclic permutation 作为唯一负控制。

## Cross-fitted partial residual

在每个 outer-train fold 内，用 cluster-grouped inner OOF 只基于 `zB` 拟合 nuisance：

$$
\widehat m_B^{(-k)}(z^B_{ir})\approx \mathbb E[a_{ir}\mid z^B_{ir}],
\qquad
u_{ir}=a_{ir}-\widehat m_B^{(-k)}(z^B_{ir}). \tag{2}
$$

Main-PR 的 score 为

$$
h_\theta(z^B_{ir},s_{ir})
=\widehat m_B(z^B_{ir})+q_\theta(z^{BC}_{ir}),
\qquad
g_{ir}(\tau)=\sigma((h_\theta-\tau)/T). \tag{3}
$$

`q_theta` 只用 inner-OOF residual `u` 训练。式 (2) 是 partial residualization，不声称 Neyman-orthogonal moment 或对 nuisance 的一阶不敏感性。

## Routed loss and clean constraint

soft training gate 下的 region loss为

$$
L^g_{irv}=(1-g_{ir})L^0_{ir}+g_{ir}L^1_{ir}(c_{iv}). \tag{4}
$$

式 (4) 是 Bernoulli hard route 的期望损失，不等于先混合两张深度图再计算 AbsRel。正式实现只对已经冻结的候选 region losses 做凸组合；推理使用 deterministic binary gate。soft、straight-through hard 与 train/infer 都 hard 的 relaxation-gap 对照为强制消融，不能把 soft surrogate 的优势直接写成 hard-routing 结果。

令 clean gain

$$
G_1=\mathbb E_w[L^0-L^1_{clean}],\qquad
G_g=\mathbb E_w[L^0-L^g_{clean}]. \tag{5}
$$

只有 `G1` 的 cluster CI 下界大于 0，且

$$
G_1>\delta_{clean}
=\max(2q^{repeat}_{0.95},\;0.01\,\mathbb E_w[L^0]) \tag{6}
$$

时 retention 才可计算。主约束为 `Gg >= kappa G1`，其中 `kappa=0.80`。bootstrap replicate 若 `G1<=delta_clean` 记为 invalid；invalid 比例超过 5% 时返回 `STOP_UNSTABLE_CLEAN_GAIN`，不生成 CI。

## Tail regret and primal-dual objective

每图 corruption tail input 固定为

$$
Q_i(\theta)=
\left[\max_{v\in\{1,2,3\}}
\sum_r w_{ir}(L^g_{irv}-L^0_{ir})\right]_+. \tag{7}
$$

`w_ir` 固定为该 region 在 official crop 内的 valid-depth pixel count 除以该图所有 eligible regions 的 valid-depth pixel count；每图权重和必须为 1。代码实现为 `main_pr_objective.image_worst_variant_regret`。

上尾比例 `alpha=0.20` 的 Rockafellar–Uryasev batch estimator 为

$$
\widehat{\operatorname{CVaR}}_\alpha(Q)
=\min_\eta\left[
\eta+\frac{1}{\alpha |B|}\sum_{i\in B}(Q_i-\eta)_+
\right]. \tag{8}
$$

Main-PR 的唯一训练目标为

$$
\min_{\theta,\eta}\;
\underbrace{\frac1{|B_R|}\sum_{ir\in B_R}
\rho(q_\theta(z^{BC}_{ir})-u_{ir})}_{L_{PR}}
+\beta\widehat{\operatorname{CVaR}}_{0.20}(Q)
+\lambda(\kappa G_1-G_g), \tag{9}
$$

其中 `rho` 为配置冻结的 Huber loss。dual update 为

$$
\lambda\leftarrow
\Pi_{[0,100]}\{\lambda+0.01(\kappa G_1-G_g)\}. \tag{10}
$$

式 (9)–(10) 是同一个标准 Lagrangian 与 projected dual-ascent 问题；不再把 hinge penalty 与 signed dual update 混用。每个 optimizer step 用同一 cluster batch 的 signed constraint 更新一次 `lambda`，约束满足时允许下降但不得小于 0。

## Frozen optimization constants

- `beta=1.0`；`kappa=0.80`；CVaR tail fraction `alpha=0.20`；
- partial-residual target 只用 outer-train 的 median/MAD 标准化，Huber `delta=1.0`；
- 每 batch 抽 8 个 frozen `cluster_id`，每 cluster 至多稳定哈希选 4 图，故至多 32 图；不足 8 clusters 时不放回使用全部，禁止把同 cluster 拆开当独立单位；
- AdamW learning rate `1e-3`、weight decay `1e-4`；gate temperature `0.10`；
- `eta` 以 outer-train image risks 的经验 0.80 quantile 初始化，learning rate `1e-3`，每 optimizer step 更新；
- `lambda=0` 初始化，dual learning rate `0.01`，每 optimizer step 更新，投影到 `[0,100]`；
- trial、seed、early-stop 和 update budget 继续由 baseline contract 的公平预算共同约束，Main-PR 与 Risk-L2D-C 不得使用不同搜索预算。

`Risk-L2D-C` 使用相同式 (4)–(10)、同一 batch、feature、预算与 gate，只把 `L_PR` 换成直接 advantage loss；这使 Claim-M 的差异只剩 cross-fitted partial-residual 决策过程。B/C-direct 只使用相同 standard direct advantage objective，不混入 Main。

## Dev calibration and internal-test decision

dev 产生 21 个固定 coverage 候选 threshold。对每个 threshold 重新计算 clean retention 与 corruption risk，只在 retention `>=0.80` 的候选中选 dev CVaR 最小者；并列时先取 retention 更高者，再取预注册 threshold ID 更小者。选定 `tau*` 后完全冻结。

internal-test 只评估一次 `tau*`。Claim-M 的主差值是 `CVaR@Ret>=0.80` 与 `WorstOf3@Ret>=0.80` 的 paired scene/drive-cluster CI；全曲线 hypervolume 仅为 secondary sensitivity，不再决定唯一 Claim-M。

## Executable pseudocode

```text
freeze source/split manifests, cluster folds, expert caches, zBC schema, seeds
for outer cluster fold:
    build inner cluster-OOF mB predictions using zB only
    form u = advantage - mB_ooo
    for preregistered trial:
        optimize Main-PR with equations (7)-(10) on outer-fit only
        rank on outer-validation only
choose trial by frozen mean-rank rule and refit with full-train inner OOF residuals
for each dev threshold:
    recompute G1, delta_clean, retention, CVaR and WorstOf3 from raw losses
freeze tau* = feasible threshold with minimum dev CVaR
apply tau* once to internal-test
paired-bootstrap whole sequence/drive clusters; mark unstable denominators invalid
report primary CVaR/WorstOf3 differences; report hypervolume only as secondary
```

对于 `N` images、每图 `R` regions、`V=3` variants 和 router width `d`，训练期决策层复杂度为 `O(NR(d+V))`，额外内存为 `O(NR)`；冻结 D0/D1 前向成本单独报告。推理只增加一次 router 前向和 region-wise threshold，复杂度 `O(NRd)`。

## Falsification

- 若 TIGER-style LOO 或任一 faithful/matched direct baseline 在两个主指标上不劣，Claim-M 为 `UNSUPPORTED`。
- 若只在 structured errors 成立，论文限定为 controlled caption stress test。
- 若 clean-gain 稳定性、coverage 或 power 门禁失败，不执行 Main 大规模训练。
- 本规范是待实现算法定义，不是正结果或理论保证。
