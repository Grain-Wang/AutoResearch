# CoVoL Metrics Specification

## Status and implementation

`DONE-CODE FOR CORE METRICS AND CLUSTER-HV BOOTSTRAP`。公式实现位于 `metrics.py` 与 `bootstrap.py`，测试位于 `paper1/tests/`。official crop/valid-depth adapter、AUROC、真实结果表仍未实现。

## Input shapes and statistical unit

- `N`：图像数，只用于图像内损失与风险聚合；
- `S`：独立 scene/drive 数，是所有置信区间、power 和显著性报告的统计单位；
- `V=3`：每张图、每个 corruption family 的 caption variants；
- `P_i`：图像 `i` 中满足有效深度条件的 eligible regions；
- patch 和 image 都保留在所属 scene cluster 内，不作为可交换独立样本。

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

再跨图像报告：

$$
\text{MeanRegret}=\frac1N\sum_i\bar r_i,\qquad
\text{WorstOf3}=\frac1N\sum_i w_i.
$$

## CVaR@20%

图像级尾部输入固定为 `q_i=[w_i]_+`。令 `k=\lceil0.2N\rceil`，`q_{(1)}\ge\cdots\ge q_{(N)}`：

$$
\operatorname{CVaR}_{20\%}=\frac1k\sum_{j=1}^{k}q_{(j)}.
$$

禁止直接把 `N×V×P` 个 patch regret 混在一起取尾部。

## Coverage

主 coverage 使用 eligible-region micro denominator：

$$
\text{Coverage}_{micro}=
\frac{\sum_i\sum_{p\in P_i}\mathbb 1[g_{i,p}=1]}
{\sum_i|P_i|}.
$$

同时报告每图 coverage 后再平均的 macro diagnostic。无 eligible region 的图像属于数据错误，不进入静默过滤。

## Clean gain retention

先计算 paired clean gain：

$$
\Delta_{clean}=\frac1N\sum_i[R_i(D_0)-R_i(D_{1,clean})].
$$

只有其 scene/drive-cluster paired-bootstrap 95% CI 下界大于 0 时才计算：

$$
\text{Retention}=
\frac{\frac1N\sum_i[R_i(D_0)-R_i(\hat D_{clean})]}
{\Delta_{clean}}.
$$

否则输出 `STOP_NO_CLEAN_GAIN`，禁止用 `10^{-6}` 人工稳定一个无意义比值。

## Pareto hypervolume

每个方法在同一 dev-calibrated coverage grid 上产生点 `(retention,CVaR)`，前者越大越好、后者越小越好。所有方法共用预注册 reference point：

- `reference_retention=0`；
- `reference_cvar=1.05×CVaR_dev(always-D1)`，只读取 dev always-D1，不读取任何待比较候选；若该值不为有限正数则停止 HV 判定。

hypervolume 只计算 reference point 内非支配矩形的并集。加入/删除 dominated candidate、重复 retention 点或改变候选列表不得改变 reference。

## Scene/drive cluster bootstrap

所有主差值使用 10,000 次 paired cluster bootstrap：

1. 以 `scene_id`（NYUv2）或 `drive_id`（KITTI）有放回抽样 S 个 clusters；
2. 每次保留抽中 cluster 的全部 images、regions 和 caption variants；
3. replicate 内从原始 losses 重新计算 clean-gain denominator、retention、worst-of-N、CVaR、Pareto front 和 hypervolume；
4. 左右方法使用完全相同的 cluster indices 和同一固定 reference；
5. 报告 cluster 数、image 数、seed、replicates 和 percentile 95% CI。

实现见 `paper1/experiments/covol/bootstrap.py`。禁止只对最终 Pareto points 做近似重采样，也禁止用 image/patch 数替代独立 cluster 数。

## Hand-calculated cases

1. `D0=[1,2]`，variant losses 为 `[[1.1,0.9,1.3],[2.2,2.4,1.8]]`：MeanRegret=7/60，WorstOf3=0.35，CVaR@50%=0.4。
2. `D0=[1,2]`，clean D1=`[0.8,1.8]`，route=`[0.9,1.9]`：在 clean-gain CI 下界 >0 时 Retention=0.5。
3. Pareto points `[(0.5,0.4),(0.8,0.5),(0.7,0.3)]`，reference `(0,1)`：hypervolume=0.54。
4. 两个数值相同但 scene 不同的样本：方法 L 的 `retention=1,CVaR=0`，方法 R 的 `retention=0.5,CVaR=0.2`，reference `(0,1)`；每次 cluster bootstrap 的 HV 差均为 0.6。

单元测试覆盖 dominated points、duplicate retention、候选集合不改变 reference、cluster 成员共同重采样和 replicate 内指标重算。正式 metrics regression 使用绝对误差 `<1e-8`。
