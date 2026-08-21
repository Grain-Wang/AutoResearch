# CoVoL Metrics Specification

## Status and implementation

`DONE-CODE FOR CORE METRICS`。公式实现位于 `paper1/experiments/covol/metrics.py`，手算测试位于 `paper1/tests/test_metrics.py`。bootstrap、AUROC 和完整结果表仍未实现。

## Input shapes and statistical unit

- `N`：图像/scene 数，是所有置信区间的独立统计单位；
- `V=3`：每张图、每个 corruption family 的 caption variants；
- `P_i`：图像 `i` 中满足有效深度条件的 eligible regions；
- patch 只用于图像内构造 prediction/risk，不作为独立统计样本。

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

只有其 image-level paired-bootstrap 95% CI 下界大于 0 时才计算：

$$
\text{Retention}=
\frac{\frac1N\sum_i[R_i(D_0)-R_i(\hat D_{clean})]}
{\Delta_{clean}}.
$$

否则输出 `STOP_NO_CLEAN_GAIN`，禁止用 `10^{-6}` 人工稳定一个无意义比值。

## Pareto hypervolume

每个方法在同一 dev-calibrated coverage grid 上产生点 `(retention,CVaR)`，前者越大越好、后者越小越好。所有方法共用预注册 reference point：

- `reference_retention=0`；
- `reference_cvar` 等于 dev 上 always-D1 与全部候选方法 CVaR 的较大值，再向上取 5% margin；冻结后用于 internal-test。

hypervolume 只计算 reference point 内非支配矩形的并集。C-B 或 Main−Risk-L2D-C 的 hypervolume 差使用相同 bootstrap image indices 进行 10,000 次 paired bootstrap。

## Three hand-calculated cases

1. `D0=[1,2]`，variant losses 为 `[[1.1,0.9,1.3],[2.2,2.4,1.8]]`：MeanRegret=7/60，WorstOf3=0.35，CVaR@50%=0.4。
2. `D0=[1,2]`，clean D1=`[0.8,1.8]`，route=`[0.9,1.9]`：在 clean-gain CI 下界 >0 时 Retention=0.5。
3. Pareto points `[(0.5,0.4),(0.8,0.5),(0.7,0.3)]`，reference `(0,1)`：hypervolume=0.54。

单元测试容差为 `pytest.approx` 默认浮点容差；正式 metrics regression 使用绝对误差 `<1e-8`。
