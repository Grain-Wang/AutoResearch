# CoVoL Metrics Specification

## Status and implementation

`ROUND6-SPEC-FROZEN, CODE-REVISION-PENDING`。已有 image-weighted 标量公式实现位于 `metrics.py` 与 `bootstrap.py`，NYUv2 official crop/valid-depth adapter 位于 `build_nyuv2_source_manifest.py`；但 Round6 冻结的 full-crop local-risk weighting、cluster-balanced primary estimand、retention LCB、test-retention stop 和 seed×cluster inference 尚未实现。因此指标层不能继续整体标为 `DONE-CODE`，真实 AUROC、CI 和结果表也均不存在。

## Input shapes and statistical unit

- `N`：图像数，只用于图像内损失与风险聚合；
- `S`：pilot manifest 中 scene–sequence connected component（KITTI 退化为 drive）的 `cluster_id` 数，是所有置信区间、power 和显著性报告的统计单位；
- `V=3`：每张图、每个 corruption family 的 caption variants；
- `P_i`：图像 `i` 中满足有效深度条件的 eligible regions；
- patch 和 image 都保留在所属 scene cluster 内，不作为可交换独立样本。

主 estimand 对 frozen split 中的 `S` 个 clusters 等权。若 cluster `s` 有 `n_s` 张图，则图像 `i` 的主权重为

$$
\omega_i=\frac{1}{S n_{s(i)}}.
$$

训练抽样、dev threshold 和 internal-test 主指标必须使用同一 `omega_i`。令所有图 `1/N` 等权的旧口径只保留为明确标记的 `image_weighted_sensitivity`。

每图基础损失固定为官方 crop 与有效 mask 上的 mean pixel AbsRel：

$$
R_i(D)=\frac{1}{|M_i|}\sum_{u\in M_i}
\frac{|D_u-D^*_u|}{\max(D^*_u,10^{-3})}.
$$

## Corruption regret

signed regret：

$$
r_{i,v}=R_i(\hat D(c_{i,v}))-R_i(D_0).
$$

先在每张图内聚合 variants：

$$
\bar r_i=\frac{1}{V}\sum_v r_{i,v},\qquad
w_i=\max_v r_{i,v}.
$$

再按 cluster-balanced image distribution 报告：

$$
\text{MeanRegret}=\sum_i\omega_i\bar r_i,\qquad
\text{WorstOf3}=\sum_i\omega_i w_i.
$$

region router 的 `r_{i,v}` 必须与上述 full-image AbsRel 处于同一尺度。eligible region `p` 的权重为 `valid_pixels(p)/valid_pixels(full_official_crop)`；未被 eligible regions 覆盖的 residual mass 固定输出 D0、regret 为 0。禁止把 eligible pixels 重新归一化到权重和 1。

## CVaR@20%

图像级尾部输入固定为 `q_i=[w_i]_+`。主 estimator 是 cluster-balanced weighted empirical distribution 上的 Rockafellar–Uryasev CVaR：

$$
\operatorname{CVaR}_{20\%}
=\min_\eta\left[\eta+\frac{1}{0.20}\sum_i\omega_i(q_i-\eta)_+\right].
$$

禁止直接把 `N×V×P` 个 patch regret 混在一起取尾部。

## Coverage

主 coverage 先在每个 cluster 内按 eligible-region micro denominator 计算，再对 `S` 个 clusters 等权：

$$
\text{Coverage}_{cluster}=
\frac1S\sum_s
\frac{\sum_{i:s(i)=s}\sum_{p\in P_i}\mathbb 1[g_{i,p}=1]}
{\sum_{i:s(i)=s}|P_i|}.
$$

同时报告全数据 eligible-region micro coverage 与每图 coverage 后再平均的 macro diagnostic。无 eligible region 的图像属于数据错误，不进入静默过滤。

## Clean gain retention

先计算 paired clean gain：

$$
\Delta_{clean}=\sum_i\omega_i[R_i(D_0)-R_i(D_{1,clean})].
$$

只有其 scene/drive-cluster paired-bootstrap 95% CI 下界大于 0，且均值超过

$$
\delta_{clean}=\max(2q^{repeat}_{0.95},0.01R(D_0))
$$

其中 $R(D_0)=\sum_i\omega_iR_i(D_0)$，与主 estimand 一致。

时才计算：

$$
\text{Retention}=
\frac{\sum_i\omega_i[R_i(D_0)-R_i(\hat D_{clean})]}
{\Delta_{clean}}.
$$

否则输出 `STOP_UNSTABLE_CLEAN_GAIN`，禁止用 `10^{-6}` 人工稳定一个无意义比值。

## Primary constrained operating point

Claim-M 不以全曲线面积作为唯一主判据。三个训练 seeds 各自在 dev 上对 21 个 thresholds 执行 10,000 次 cluster bootstrap；只有 one-sided 95% retention LCB `>=0.80` 的候选可行，再选择 cluster-balanced CVaR 最低者。并列时依次取 retention LCB 更高、point retention 更高、预注册 threshold ID 更小者。

每 seed 的 threshold 冻结后，在 internal-test 单次报告 retention 点估计、two-sided 95% CI 和 constraint status。test retention 点估计 `<0.80` 时返回 `STOP_TEST_RETENTION_VIOLATION`，不得判 Claim-M PASS。风险列统一命名为 `CVaR@Dev-Ret>=0.80` 与 `WorstOf3@Dev-Ret>=0.80`；这表示 dev 可行性，不暗示 test retention 必然满足约束。hypervolume 仅作 secondary sensitivity。

## Pareto hypervolume

每个方法在同一 dev-calibrated coverage grid 上产生点 `(retention,CVaR)`，前者越大越好、后者越小越好。所有方法共用预注册 reference point：

- `reference_retention=0`；
- `reference_cvar=1.05×CVaR_dev(always-D1)`，只读取 dev always-D1，不读取任何待比较候选；若该值不为有限正数则停止 HV 判定。

hypervolume 只计算 reference point 内非支配矩形的并集。加入/删除 dominated candidate、重复 retention 点或改变候选列表不得改变 reference。

## Scene/drive cluster bootstrap

单个训练 seed 的差值使用 10,000 次 paired cluster bootstrap：

1. 以 frozen `cluster_id` 有放回抽样 S 个 clusters；NYUv2 的同 sequence/scene 连通帧与 KITTI 的同 drive 帧始终共同抽样；
2. 每次保留抽中 cluster 的全部 images、regions 和 caption variants；
3. replicate 内从原始 losses 重新计算 clean-gain denominator、retention、worst-of-N、CVaR、Pareto front 和 hypervolume；
4. 左右方法使用完全相同的 cluster indices 和同一固定 reference；
5. 报告 cluster 数、image 数、training seed、bootstrap seed、replicates 和 percentile 95% CI。

每个 denominator `<=delta_clean` 的 replicate 记为 invalid，不能静默删除或使整次 bootstrap 抛异常。invalid 比例超过 5% 时不生成 CI，并返回 `STOP_UNSTABLE_CLEAN_GAIN`；否则同时报告 valid/invalid replicate 数与比例。

三训练 seeds 的主差值使用 paired seed×cluster hierarchical bootstrap：外层对 seeds `17/29/43` 等权有放回抽样，内层在每个被抽 seed 中对完整 clusters 有放回抽样，左右方法共享所有索引；同时逐 seed 报告差值并要求方向一致。实现仍待加入 `bootstrap.py`。禁止只对最终 Pareto points 做近似重采样，也禁止用 image/patch 数替代独立 cluster 数。

## Hand-calculated cases

1. 在同 cluster 或 cluster size 相同的 image-weighted sensitivity 中，`D0=[1,2]`，variant losses 为 `[[1.1,0.9,1.3],[2.2,2.4,1.8]]`：MeanRegret=7/60，WorstOf3=0.35，CVaR@50%=0.4。
2. `D0=[1,2]`，clean D1=`[0.8,1.8]`，route=`[0.9,1.9]`：在 clean-gain CI 下界 >0 时 Retention=0.5。
3. Pareto points `[(0.5,0.4),(0.8,0.5),(0.7,0.3)]`，reference `(0,1)`：hypervolume=0.54。
4. 两个数值相同但 scene 不同的样本：方法 L 的 `retention=1,CVaR=0`，方法 R 的 `retention=0.5,CVaR=0.2`，reference `(0,1)`；每次 cluster bootstrap 的 HV 差均为 0.6。
5. eligible region 覆盖 full official crop 的 50%，该 region 的 routed-minus-D0 loss 为 0.2，其余像素固定走 D0，则 full-image regret 必须为 0.1，而不是 0.2。

现有单元测试覆盖 dominated points、duplicate retention、候选集合不改变 reference、cluster 成员共同重采样和 replicate 内指标重算；它们尚未覆盖本轮新增的第 5 项、weighted CVaR、retention LCB、test-retention stop 或 seed×cluster bootstrap。正式 metrics regression 使用绝对误差 `<1e-8`。
