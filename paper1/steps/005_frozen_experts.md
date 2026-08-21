# 005 Repository-Owned Frozen Experts

## Status

`IN-PROGRESS`。scene-group OOF stacking 计划与泄漏审计代码已完成；PyTorch 双候选、训练和真实 cache 尚未完成。不再等待 TR2M 训练代码，也不把 TR2M released checkpoint 当正式双候选。

## Shared-backbone contract

- 冻结一个锁定 SHA256 的 DepthAnything ViT-S checkpoint；
- 每次前向只计算一次相对深度与 frozen multi-scale image features；
- D0/D1 使用两个独立训练、结构逐层同构、参数不共享的 metric heads；
- 两个 head 均接收完全相同的 frozen image-global feature 和 frozen multi-scale image features；
- 两个 head 都含相同的 `768→256→C` text-channel adapter、FiLM 位置和同构 decoder；
- D0 的 text channel 固定输入同一个 null/zero embedding，D1 的 text channel 输入冻结 caption embedding；D0 不以 image context 替换 text channel；
- 对应层使用同一初始化 seed，层名、shape、trainable parameter count 必须完全相等，而不只是 ±10%；
- 输出 pixel-wise inverse-depth affine maps，再与 frozen relative depth 组合为 metric depth。

该设计不声称复现 TR2M；它是为回答本研究问题而建立的最小公平双候选基线。

## Scene-group OOF stacking contract

- router-train scene 固定为 5 folds；第 k 个 D0/D1 只在“全部 official-training scene 减去 router-dev、internal-test 和 fold-k”上训练，并只预测 fold-k；
- 另训练 final D0/D1：使用全部 official-training scene 减去 router-dev/internal-test，只预测 router-dev 和 internal-test；
- router-train 的 advantage label 只能来自对应 OOF experts；禁止任何 in-sample expert prediction 进入 router、nuisance、tie band 或 threshold；
- `cache_oof_experts.py` 生成 `PLANNED_NOT_TRAINED` 计划，列出每个 expert 的 training/prediction scene hash set；它不是 checkpoint 或真实 cache；
- `expert_cache_manifest.json` 必须令每个 router image 恰有一行、`scene_hash` 不在对应 training set，且 D0/D1 cache SHA256 完整。任一交集或缺行硬失败。

实现与测试：`paper1/experiments/covol/cache_oof_experts.py`、`paper1/tests/test_expert_cache_no_leakage.py`。

## Optimization contract

- D0/D1 独立运行 seeds `17/29/43`，但每一对候选的对应层从相同 seed 初始化；
- 同一 optimizer、learning-rate schedule、batch size、update steps、loss、augmentation 和有效 mask；
- D1 只读 predicate-clean caption，不读 structured/natural error、router labels 或 internal-test；
- 选择规则、超参数和 checkpoint epoch 在 dev 冻结后才能读取 internal-test。

## Expert negative controls

每个 seed 还必须训练：

1. 两个独立 image-only twin heads：结构、输入、训练数据与预算完全相同，仅保留随机优化差异；
2. shuffled-caption D1：在 scene 内打乱 caption 与图像对应关系，其他设置与正式 D1 相同。

每个 control 使用相同 OOF stacking 和同容量 router。正式 D0/D1 的 clean gain、Claim-F 与 routing hypervolume 必须相对 image twins 和 shuffled-caption controls 的 paired scene-cluster CI 下界均 >0；否则语言特异性解释失败。

## Verification

32 样本 smoke test 必须验证：

1. frozen backbone 和 frozen context encoders 梯度均为 `None`；
2. 当前 expert head 有非零有限梯度；
3. D0 对 caption permutation 逐元素不变；
4. D1 对 clean caption permutation 至少一个样本变化；
5. 两 expert 的层名、shape、参数量和 FiLM 位置逐项一致；
6. 两 expert 输出 shape/mask 一致；
7. 保存/重载后输出绝对误差 <`1e-6`；
8. OOF cache 的每个 prediction scene 不在对应 training-scene hash set；
9. manifest 记录 checkpoint、训练数据、代码 commit 和配置 SHA256。

## Expected artifacts

- `paper1/experiments/covol/models/dual_candidate_depth.py`
- `paper1/experiments/covol/train_expert.py`
- `paper1/experiments/covol/cache_oof_experts.py`
- `paper1/experiments/covol/run_expert_controls.py`
- `paper1/tests/test_dual_candidates.py`
- `paper1/tests/test_expert_cache_no_leakage.py`
- `paper1/artifacts/covol/expert_manifest.json`
- `paper1/artifacts/covol/expert_stacking_plan.json`
- `paper1/artifacts/covol/expert_cache_manifest.json`
- `paper1/results/covol/expert_negative_controls.csv`

本地 `auto_research` 环境当前没有 PyTorch；真实训练、checkpoint、cache 和 negative-control 结果均为 PENDING。已完成的 OOF 代码只锁定数据依赖并防止 stacking 泄漏。
