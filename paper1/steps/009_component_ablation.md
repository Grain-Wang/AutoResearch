# 009 Component and Boundary Ablation — ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED

状态：`ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED, NOT_EXECUTED`。Claim-M 的上游门禁已停止，本步骤不会执行；以下只保留历史消融协议。

## 目的

区分三件事：

1. region-level replacement 是否优于 global candidate selection；
2. 16×16 是否是必要粒度，而不是任意网格选择；
3. hard nearest-neighbor 上采样是否制造块状深度断裂。

## 固定输入

- 使用步骤 005 锁定的同一组 `D0/D1` cache，不重训专家。
- 使用步骤 007 锁定的同一 router 特征、训练预算、seeds `17/29/43` 和 20 组超参数 trial。
- 只在 dev 选择 threshold；internal-test 每个 seed 只评估一次。
- 统计单位为 image；caption variants 先在 image 内聚合，定义见 [metrics_spec.md](metrics_spec.md)。

## 消融矩阵

| 轴 | 取值 | 控制变量 |
| --- | --- | --- |
| 空间粒度 | global、8×8、16×16、32×32 | 相同特征、风险目标、预算和 coverage grid |
| gate 上采样 | hard-nearest、soft-bilinear | 相同 16×16 logits；soft 版本用插值后的 `p(D1)` 混合冻结深度，不再二次阈值化 |
| residualization | raw advantage、5-fold sequence/drive-cluster OOF partial residual | 相同 `z_C`、风险目标与模型容量 |
| 风险目标 | mean regret、CVaR@20% + clean constraint | 相同训练样本、trial 数和 seeds |

主表报告全部预注册组合；不得只展示最佳粒度或最佳插值方式。

## 边界伪影测量

对每个可验证错误区域 mask `M`，构造 5-pixel 形态学边界带 `B5(M)`，并分别报告：

- 目标区域 `M \ B5(M)` 的 AbsRel；
- 边界带 `B5(M)` 的 AbsRel；
- 非目标区域 `not M` 的 AbsRel；
- 边界带内的 depth-gradient absolute error；
- gate cell boundary 与预测深度梯度峰值的重合率。

所有 mask 必须满足步骤 003 的有效像素门禁。没有可验证 mask 的 natural error 只进入 image-level 表，不进入边界分析。

## 判定

- 若最佳 region 策略相对 global 的 retention–CVaR hypervolume 差值 95% CI 跨 0，删除 region mechanism 贡献。
- 若 16×16 未显著优于相邻的 8×8 和 32×32，不声称 16×16 具有机制必要性，只把它记录为开发选择。
- 若 hard-nearest 的边界带 AbsRel 或 depth-gradient error 显著高于 soft-bilinear，最终方法不得使用 hard-nearest。
- 若去掉 residualization 或 CVaR 后 Claim-M 仍保持且差值 CI 跨 0，对应组件不得列为贡献。

预期结果文件：`paper1/results/covol/ablation_region_granularity.csv`。当前没有该产物，也没有任何消融结果。
