# 007 Fair Gate Baselines

## Status

`SPECIFIED, PENDING STEP 006`。公平性按 heuristic 与 learned gate 分开处理。

## Heuristics

always-D0、always-D1、oracle、CLIP similarity、uncertainty、`|D1-D0|` 与 residual-norm gate 保留原始零参数定义；不做虚假的 ±10% 参数匹配。所有 heuristic 仍必须读取同一 expert cache、eligible regions 和 dev-calibrated coverage grid。

## Learned gates

| Baseline | Features | Objective | 用途 |
| --- | --- | --- | --- |
| L2D-B | 完整 zB | standard best-expert/defer loss | 非语义 information baseline |
| L2D-C | 与主方法完全相同的 zC 列 | standard best-expert/defer loss | 区分更多语义输入与算法差异 |
| Risk-L2D-C | 与主方法完全相同的 zC 列 | 同一 clean constraint + CVaR objective | 区分风险目标与 orthogonalized routing |
| Main | zC；cross-fitted nuisance residual | 同一 clean constraint + CVaR objective | 未验证候选方法 |

learned gates 必须：

- trainable parameters 与 Main ±10%；
- 相同 optimizer、updates、seeds `17/29/43`；
- 每个方法恰好 20 组预注册 trial；
- 相同 early-stopping budget、fold/dev 数据和 metric implementation；
- 输出逐列 feature schema hash；L2D-C、Risk-L2D-C 与 Main 的原始输入列必须逐项相等。

## Decision

- C 优于 B 只能支持语义信息增量；
- Main 优于 L2D-C 但不优于 Risk-L2D-C，说明收益来自风险目标；
- 只有 Main 相对 Risk-L2D-C 的 hypervolume 增量在两数据集 95% CI 下界均 >0，才可能支持 Claim-M；
- 参数、trial、feature schema 或 seed 缺失的 baseline 行视为未完成。

契约机器可读版本见 `paper1/configs/covol/baseline_contract.yaml`。
