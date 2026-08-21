# 006 Semantic Incrementality Gate

## Status

`SPECIFIED, PENDING FAIR EXPERT CACHE`。本步骤先判断 Claim-F，不默认支持主方法。

## Frozen inputs

- 只读取 Step 005 的 frozen expert cache 和 SHA manifest；
- official-train 的 train/dev/internal-test scene splits 已由 Step 003 冻结；
- 同一 image 的 clean/natural/structured/null captions 与所有 regions 必须在同一 fold；
- official benchmark test 不进入任何 fold、scaler、trial、threshold 或结果选择。

## Five-fold scene-group cross-fitting

仅在 internal `train` split 上构建 5 folds，按 dataset 与 error family 做近似分层，但 `scene_id` 是不可拆分 group。

对每个 outer fold `k`：

1. outer fold-k 只作 OOF test；
2. 其余 scene 按固定 hash 再分 80% fold-fit / 20% fold-validation；
3. scaler、缺失值处理、feature selection 和 nuisance model 只在 fold-fit 拟合；
4. 20 组预注册超参数 trial 只用 fold-validation 选择；
5. 对 fold-k 只输出一次 OOF prediction，不更新任何状态。

每个训练样本最终恰有一次 OOF prediction；同 scene 跨 fold、scaler 读取 fold-test 或同样本多次 OOF 都是硬失败。

## Tie band and targets

连续 advantage `a_p` 是主诊断 target。tie band：

$$
\delta_{tie}=\max(q_{0.95}^{repeat},q_{0.95}^{mask}),
$$

其中 `q^{repeat}` 来自相同 checkpoint/cache 配置独立运行两次的 `|a_p^{(1)}-a_p^{(2)}|`；`q^{mask}` 来自有效 mask 向内腐蚀 1 pixel 后的 `|a_p-a_p^{eroded}|`。二者只在 train split 估计一次。

- `a_p>\delta_{tie}`：D1-positive；
- `a_p<-\delta_{tie}`：D0-positive；
- `|a_p|\le\delta_{tie}`：tie。

tie 不进入 AUROC/AUPRC 的二元标签，但保留在连续回归、Spearman 和所有策略效用计算中。

## Nested predictors

- A：视觉难度、D0 uncertainty、纹理/边界与 region size；
- B：A + D0/D1 difference、residual norm、candidate confidence；
- C：B + text–region semantic alignment、caption entity/relation features。

对每个 outer fold，先用 fold-fit/validation 得到 nuisance `m_B(z_B)`；只用 OOF nuisance prediction形成：

$$
r_p=a_p-m_B(z_B).
$$

semantic branch 预测 `r_p`，最终 `s_C=m_B+\hat r`。所有标准化和超参数选择遵守同一 fold 边界。

## Threshold calibration and policy utility

- 用全部 OOF-train predictions 拟合最终训练过程；
- 只在独立 dev split 上把 score quantiles 冻结成 21 个 coverage thresholds（0%,5%,…,100%）；
- internal-test 只应用冻结 thresholds，一次性计算，不重新校准。

除 AUROC/AUPRC/Spearman 外，B/C 使用完全相同 thresholds 与 [metrics spec](metrics_spec.md) 生成 clean-gain retention–CVaR 曲线。

## H-semantic decision

Claim-F 仅在以下条件同时满足时通过：

1. internal-test 上 C-B AUROC ≥0.03，image-level paired-bootstrap 95% CI 下界 >0；
2. held-out captioner 和 held-out error family 上方向一致；
3. C-B retention–CVaR Pareto hypervolume 增量 95% CI 下界 >0；
4. 连续 advantage regression/Spearman 不与分类结论矛盾。

任一失败记录 `STOP_CLAIM_F` 或 `REFRAME_NON_SEMANTIC`，不得进入语义算法叙事。

## Pseudocode

```text
freeze split manifest, expert cache, feature schema, tie band
for outer_fold in SceneGroupKFold(K=5):
    fit_scenes, validation_scenes = hash_split(outer_train_scenes, 80/20)
    fit preprocessing and each of 20 trials on fit_scenes only
    choose trial on validation_scenes only
    predict nuisance m_B and A/B/C scores on outer_fold exactly once
calibrate 21 coverage thresholds on independent dev
evaluate frozen A/B/C policies once on internal_test
paired-bootstrap images 10,000 times
apply AUROC and Pareto-hypervolume gates
```

## Expected artifacts

- `paper1/experiments/covol/crossfit_semantic_advantage.py`
- `paper1/tests/test_crossfit_no_leakage.py`
- `paper1/results/covol/predictability_probe.csv`
- fold manifest、feature schema、scaler/trial hashes 与 OOF uniqueness audit。
