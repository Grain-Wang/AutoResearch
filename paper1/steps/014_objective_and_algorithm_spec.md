# 014 Objective and Algorithm Specification — ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED

## Status and boundary

`ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED`。本文件只保存 CoVoL-Depth 的历史优化目标规范；配置入口为 `configs/covol/baseline_contract.yaml` version 3。方法暂名 **Main-PR**（cross-fitted partial-residual router），但训练、真实 cache/outcome 和方法结果有意不存在。full-crop weighting、cluster-balanced estimand、per-seed retention LCB 与 test stop 的 helper QA 不是算法证据，任何 CoVoL 下游入口均由最终 scientific gate 阻断。

TIGER 使用自然语言任务指令在多个冻结异构 VFM 特征之间做 token-level 融合，并用移除专家后的预测变化对齐 routing contribution。Main-PR 不学习任务指令、不融合 VFM feature，也不把 expert-exclusion contribution 当作新颖性；它只解决两个已冻结、同任务 metric-depth 候选之间的局部决策：在预注册 clean utility 下最小化受控 caption 错误的尾部 regret。该边界必须由 Risk-L2D-C、TIGER-style LOO、DeferredSeg、Regression-L2D 与 DR-L2D 对照共同否证。

## Variables and aggregation

| 符号 | 定义 |
| --- | --- |
| `i,r,v` | image、eligible region、同 family caption variant；`v=1,2,3` |
| `s(i),n_s,S` | 图像所属 frozen cluster、该 cluster 图像数、当前 split 的 cluster 数 |
| `D0,D1` | 冻结纯视觉与图文 metric-depth 候选 |
| `L0_ir,L1_ir(c)` | official crop、valid-depth mask 内的 region AbsRel |
| `a_ir` | clean empirical advantage，`L0_ir-L1_ir(c_clean)`，正值表示 D1 更好 |
| `zB_ir` | 图像难度、候选差异、confidence 等非语义特征 |
| `s_ir,m_ir` | 固定宽度 semantic block 及其 observation mask |
| `g_ir` | 使用 D1 的 soft gate；推理时由 dev 冻结 threshold 二值化 |

所有方法先在 region 内算损失；对每个完整 caption variant 先按同一组 region 权重聚合成 image regret，再在三个完整 variants 上取 worst-of-3，最后才跨 image 计算上尾 CVaR。禁止把不同 region 各自最坏的 variant 拼成现实中不存在的 Frankenstein caption。patch、variant 和 image 都不充当独立 cluster。

主 estimand 冻结为 **cluster-balanced image distribution**：split 内图像 `i` 的权重为

$$
\omega_i=\frac{1}{S\,n_{s(i)}}. \tag{0}
$$

所以每个 cluster 总权重相同，cluster 内图像等权。训练按 cluster 均匀抽样、再在 cluster 内均匀抽图；dev threshold、internal-test clean retention 和 tail risk 都使用同一组 `omega_i`。原来的 image-uniform 指标只作为 sensitivity，不得与主训练约束混写。

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

令 cluster-balanced clean gain

$$
G_1=\sum_i\omega_i(L^0_i-L^1_{i,clean}),\qquad
G_g=\sum_i\omega_i(L^0_i-L^g_{i,clean}). \tag{5}
$$

只有 `G1` 的 cluster CI 下界大于 0，且

$$
G_1>\delta_{clean}
=\max(2q^{repeat}_{0.95},\;0.01\,\sum_i\omega_iL^0_i) \tag{6}
$$

时 retention 才可计算。主约束为 `Gg >= kappa G1`，其中 `kappa=0.80`。bootstrap replicate 若 `G1<=delta_clean` 记为 invalid；invalid 比例超过 5% 时返回 `STOP_UNSTABLE_CLEAN_GAIN`，不生成 CI。

## Tail regret and primal-dual objective

每图 corruption tail input 固定为

$$
Q_i(\theta)=
\left[\max_{v\in\{1,2,3\}}
\sum_r w_{ir}(L^g_{irv}-L^0_{ir})\right]_+. \tag{7}
$$

令 `M_i` 为图像 official crop 内的全部 valid-depth pixels，`M_ir` 为固定、不重叠 region partition 中属于 eligible region `r` 的 valid pixels。Round6 后权重唯一允许定义为

$$
w_{ir}=\frac{|M_{ir}|}{|M_i|},\qquad
w_{i0}=1-\sum_r w_{ir}. \tag{7a}
$$

非 eligible residual mass `w_i0` 始终走 D0，所以其 regret 为 0。因而 `sum_r w_ir` 允许小于 1，且局部路由 regret 与 full-official-crop AbsRel difference 处于同一尺度；不得再用 eligible-region pixels 作分母。`main_pr_objective.image_worst_variant_regret` 已实现该合同，并用“50% eligible、局部 regret 0.2、全图 regret 0.1”的单测锁定。

上尾比例 `alpha=0.20` 的 cluster-balanced Rockafellar–Uryasev estimator 为

$$
\widehat{\operatorname{CVaR}}_\alpha(Q)
=\min_\eta\left[
\eta+\frac{1}{\alpha}\sum_i\omega_i(Q_i-\eta)_+
\right]. \tag{8}
$$

Main-PR 的唯一训练目标为

$$
\min_{\theta,\eta}\;
\underbrace{\frac1{|B_S|}\sum_{s\in B_S}\frac1{|B_s|}
\sum_{i\in B_s}\frac1{|P_i|}\sum_{r\in P_i}
\rho(q_\theta(z^{BC}_{ir})-u_{ir})}_{L_{PR}}
+\beta\widehat{\operatorname{CVaR}}_{0.20}(Q)
+\lambda(\kappa G_1-G_g), \tag{9}
$$

其中 `B_S` 是本 batch 抽中的 clusters、`B_s` 是 cluster `s` 中抽中的 images，`rho` 为配置冻结的 Huber loss。该写法使每个 cluster 与每图总权重相同，不让长 sequence 或 region 更多的图支配 residual loss。dual update 为

$$
\lambda\leftarrow
\Pi_{[0,100]}\{\lambda+0.01(\kappa G_1-G_g)\}. \tag{10}
$$

式 (9)–(10) 是同一个标准 Lagrangian 与 projected dual-ascent 问题；不再把 hinge penalty 与 signed dual update 混用。每个 optimizer step 用同一 cluster batch 的 signed constraint 更新一次 `lambda`，约束满足时允许下降但不得小于 0。

## Frozen optimization constants

- `beta=1.0`；`kappa=0.80`；CVaR tail fraction `alpha=0.20`；
- partial-residual target 只用 outer-train 的 median/MAD 标准化，Huber `delta=1.0`；
- 每 batch 均匀抽 8 个 frozen `cluster_id`，再从每 cluster 均匀、不放回抽至多 4 图，故至多 32 图；采样顺序由 seed 冻结并在 epoch 间轮换，不能永久只保留稳定哈希最小的 4 图；不足 8 clusters 时不放回使用全部，禁止把同 cluster 拆开当独立单位；
- AdamW learning rate `1e-3`、weight decay `1e-4`；gate temperature `0.10`；
- `eta` 以 outer-train image risks 在 `omega_i` 下的加权经验 0.80 quantile 初始化，learning rate `1e-3`，每 optimizer step 更新；
- `lambda=0` 初始化，dual learning rate `0.01`，每 optimizer step 更新，投影到 `[0,100]`；
- trial、seed、early-stop 和 update budget 继续由 baseline contract 的公平预算共同约束，Main-PR 与 Risk-L2D-C 不得使用不同搜索预算。

`Risk-L2D-C` 使用相同式 (4)–(10)、network、input schema、batch indices、feature、optimizer、dual schedule、trial/early-stop budget 与 threshold calibration，只把 `L_PR` 的 inner-OOF partial-residual target 换成 direct advantage target。两者必须由 executable contract test 逐项比较；测试完成前，不能声称 Claim-M 的可执行差异只有 target construction。B/C-direct 只使用相同 standard direct advantage objective，不混入 Main。

## Dev calibration and internal-test decision

每个训练 seed `17/29/43` 独立产生模型和 21 个固定 coverage 候选 threshold。对每个 threshold 运行 10,000 次 paired cluster bootstrap，并在 replicate 内重算 clean-gain denominator 与 retention；只有 one-sided 95% retention LCB `>=0.80` 的候选才进入 dev CVaR 排序。并列时先取 retention LCB 更高者、再取 point retention 更高者、最后取预注册 threshold ID 更小者。每个 seed 的 `tau*` 单独冻结。

internal-test 对每个 seed 只评估一次对应 `tau*`，同时报告 retention 点估计与 two-sided 95% cluster CI。任一方法的 test retention 点估计 `<0.80` 时返回 `STOP_TEST_RETENTION_VIOLATION`，不得判 Claim-M PASS。正式风险列名为 `CVaR@Dev-Ret>=0.80` 与 `WorstOf3@Dev-Ret>=0.80`，明确约束是在 dev 上以 LCB 冻结；全曲线 hypervolume 与 image-weighted 指标仅为 secondary sensitivity。

三个训练 seeds 作为固定重复：每 seed 使用 10,000 次 paired cluster bootstrap，左右方法共享 cluster indices；逐 seed 报告风险差与 cluster CI，跨 seed 只报告三个点估计的 mean±sample SD，不报告 seed-population CI。任一 seed 点方向相反或任一 seed 未满足预注册 cluster-CI 门禁时 Claim-M 不通过。

operating-point artifact 必须绑定 `seed`、raw outcome table、coverage grid、expert cache、metric-spec version、minimum-clean-gain artifact、method config 与 code commit 的实际 SHA256。internal-test evaluator 只能读取并验证该 artifact，不接受手工裸传 `threshold_index`。

## Executable pseudocode

```text
freeze source/split manifests, cluster folds, per-seed expert caches, zBC schema
for seed in [17, 29, 43]:
    for outer cluster fold:
        build inner cluster-OOF mB predictions using zB only
        form u = advantage - mB_oof
        for preregistered trial:
            optimize Main-PR with full-crop risk and cluster-balanced equations
            rank on outer-validation only
    choose trial by frozen mean-rank rule and refit from OOF residuals
    for each dev threshold:
        recompute G1, retention and risk from raw losses
        retain only thresholds with one-sided retention LCB >= 0.80
    freeze this seed's tau* = feasible threshold with minimum dev CVaR
    apply tau* once to internal-test; audit retention point and CI
for each fixed seed, paired-bootstrap whole sequence/drive clusters
report per-seed CI and cross-seed mean +/- SD; require all directions agree
require no test-retention STOP
report cluster-balanced CVaR/WorstOf3 primary; image-weighted/HV secondary
```

对于 `N` images、每图 `R` regions、`V=3` variants 和 router width `d`，训练期决策层复杂度为 `O(NR(d+V))`，额外内存为 `O(NR)`；冻结 D0/D1 前向成本单独报告。推理只增加一次 router 前向和 region-wise threshold，复杂度 `O(NRd)`。

## Falsification

- 若 TIGER-style LOO 或任一 faithful/matched direct baseline 在两个主指标上不劣，Claim-M 为 `UNSUPPORTED`。
- 若只在 structured errors 成立，论文限定为 controlled caption stress test。
- 若 clean-gain 稳定性、coverage 或 power 门禁失败，不执行 Main 大规模训练。
- 本规范是待实现算法定义，不是正结果或理论保证。
