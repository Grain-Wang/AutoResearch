# 007 Fair Gate Baselines

## Status

`STOPPED-BY-004-A`。004-A 的 semantic-preserving 控制条件失败已停止 CoVoL，不再实现或运行本步骤的模型实验。以下公平合同仅作为预注册记录保留。

## Heuristics

always-D0、always-D1、oracle、CLIP similarity、uncertainty、`|D1-D0|` 与 residual-norm gate 保留原始零参数定义；不做虚假的 ±10% 参数匹配。所有 heuristic 仍必须读取同一 OOF/final expert cache、eligible regions 和 dev-calibrated coverage grid。

## Learned gates

| Baseline | Features | Objective | 用途 |
| --- | --- | --- | --- |
| L2D-B | 完整 zB | standard best-expert/defer loss | 非语义 information baseline |
| L2D-C | 与主方法完全相同的 zC 列 | standard best-expert/defer loss | 区分更多语义输入与算法差异 |
| Risk-L2D-C | 与主方法完全相同的 zC 列 | 同一 clean constraint + CVaR objective | 区分风险目标与 cross-fitted partial residualization |
| Regression-L2D | zC；相同 OOF experts | Mao et al. two-stage regression-deferral surrogate | 连续损失/冻结 predictor 直接近邻 |
| DR-PostHoc-L2D | zC；相同 OOF experts | Soen et al. density-ratio CPE scorer + dev threshold | 冻结专家 post-hoc 直接近邻 |
| Dense-Coherence-L2D | zC；相同 region grid | DeferredSeg-style dense collaboration surrogate + spatial coherence | dense defer/空间一致性直接近邻 |
| LOO-Uncertainty-Router | zC；相同 OOF experts | MRUF-style leave-one-out contribution target + uncertainty calibration | 经验贡献教师/多粒度路由直接近邻 |
| Main-PR | zC；cross-fitted nuisance partial residual | 同一 clean constraint + CVaR objective | 未验证候选方法 |

learned gates 必须：

- trainable parameters 与 Main ±10%；
- 相同 optimizer、updates、seeds `17/29/43`；
- 每个方法恰好 20 组预注册 trial；
- 相同 early-stopping budget、fold/dev 数据和 metric implementation；
- 输出逐列 feature schema hash；L2D-C、Risk-L2D-C 与 Main 的原始输入列必须逐项相等。
- Risk-L2D-C 与 Main-PR 还必须共享 network、batch indices、cluster-balanced CVaR、clean constraint、dual/optimizer schedule、trial 与 threshold budget；唯一允许差异是 direct advantage target 与 inner-OOF partial-residual target，并由自动 contract test 验证；
- 全部读取 Step 005 的 OOF expert cache；任何 in-sample cache 行使 baseline 和 Main 同时失效；
- 全部 feature schema 通过 intervention-metadata denylist，不得读取模板、生成器、error family 或 split 标签；
- 主表使用 cluster-balanced estimand；三个固定训练 seed 各自运行 10,000 次 paired scene/drive-cluster bootstrap并报告 CI，跨 seed 只报 mean±SD，逐 seed 方向必须一致；image-weighted 只作 sensitivity。

## Artifact and grounding controls

- text-only artifact classifier：只读原始 caption content，不读模板 ID 或 D0/D1 loss；
- frozen VLM contradiction/grounding scorer：只读原图和 caption，不读 GT/候选 loss。

它们在 held-out template、captioner 和 error family 上使用相同 coverage grid。若任一在 dev retention one-sided 95% LCB≥0.80 后冻结的 threshold 上达到 Main-PR 的 `CVaR/WorstOf3@Dev-Ret≥0.80`，删除方法贡献；HV 只作 secondary。

## Robust expert killer baselines

以下方法不强行读取 frozen cache，而是用相同 frozen backbone、expert-training scenes、head 容量、updates 和 seeds 独立训练：

1. caption dropout；
2. seen-family corruption augmentation；
3. three-caption prediction ensemble；
4. image-caption consistency filtering。

报告 clean AbsRel/δ1、clean gain、mean/worst/CVaR regret、参数、训练成本和推理成本。若任一单专家方法支配 Main 的 retention–CVaR Pareto，Claim-M 停止。

## Decision

- C 优于 B 只能支持语义信息增量；
- Main 优于 L2D-C 但不优于 Risk-L2D-C，说明收益来自风险目标；
- Claim-M 要求 Main-PR 相对 Risk-L2D-C、TIGER-style LOO 以及四个 direct published-method adaptations，在 dev retention LCB≥0.80 后冻结的 threshold 上，三个固定 seed 各自的 internal-test `CVaR/WorstOf3@Dev-LCB-Ret≥0.80` 风险差 cluster CI 上界均 <0；
- published methods 各报告 `faithful` 与 `capacity-matched` 两版；±10% 参数规则只约束 matched 版，不能裁剪 faithful 公式；
- 任一 direct baseline 缺失时 Claim-M 不得判定；
- 参数、trial、feature schema 或 seed 缺失的 baseline 行视为未完成。

契约机器可读版本见 `paper1/configs/covol/baseline_contract.yaml`。
