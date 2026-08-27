# 020 BAR-Depth Oracle Canary v2 Repair

## Scope

本步骤只修复 Step 019 证明无效的 v1 metric alignment。机器可读合同为
[`oracle_canary_v2.json`](../configs/bar_depth/oracle_canary_v2.json)。相对 v1，唯一
科学变化是：image-level base-to-GT alignment 从 unconstrained affine 改为
`positive_median_scale`，预测深度按预先存在的 DIODE evaluation range
`[0.1, 350]m` 截断，并记录触发范围截断的 base pixel 数。

以下内容逐项保持不变：DIODE 200 图与固定 seed、20 scans × 10、Depth Anything
V2-S 与输入尺寸、3×4 grid、1.5× context、high-pass residual merge、25%/3-region
预算、boundary-weighted AbsRel、普通 AbsRel safety、5,000 次 scan-cluster bootstrap
以及全部 GO/STOP 阈值。

## Alignment definition

对正值 base disparity `d` 与 GT inverse depth `z^-1`：

$$
a=\frac{\operatorname{median}(z^{-1})}{\operatorname{median}(d)},
\qquad \hat z^{-1}=a d,\qquad a>0.
$$

没有 shift，因此非零 base disparity 不会跨越 inverse-depth 的负值域；模型 ReLU
产生的零 disparity 对应 evaluation max depth，而不是 v1 的 `1e6m` 伪深度。该
alignment 仍只用于 metric evaluation；patch 只对 base disparity 对齐，GT 不参与
patch merge 或区域启发式。

## Decision

- 必须报告 base prediction 触发 `[0.1, 350]m` 范围截断的像素数；
- 在有限 evaluation range 下，原 v1 的四项门禁原样执行；
- 门禁失败：归档当前固定-grid/high-pass action formulation；
- 门禁通过：仅记 `GO_ORACLE_ROUTABILITY_UNVERIFIED`，下一步仍必须做 killer heuristic
  与 scan-held-out router probe，不能升级 Paper Candidate。

## Outcome

v2 完成 200 图/2400 rows，四项门禁全部通过，状态为
`GO_ORACLE_ROUTABILITY_UNVERIFIED`。完整数值、domain slices 与 claim boundary 见
[Step 021](021_bar_depth_oracle_canary_v2_result.md)。
