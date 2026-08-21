# 005 Repository-Owned Frozen Experts

## Status

`SPECIFIED, IMPLEMENTATION NEXT`。不再等待 TR2M 训练代码，也不把 TR2M released checkpoint 当正式双候选。

## Shared-backbone contract

- 冻结一个锁定 SHA256 的 DepthAnything ViT-S checkpoint；
- 每次前向只计算一次相对深度与 frozen multi-scale image features；
- D0/D1 使用两个独立训练、结构同构、参数不共享的 metric heads；
- 两个 head 都含相同的 `768→256→C` context adapter 和同构 decoder；
- D0 context 是冻结 image global feature；D1 context 是冻结 caption feature；
- context 通过同一 FiLM 位置调制 decoder；除输入 modality 外，decoder 层数、通道和输出 resolution 一致；
- 输出 pixel-wise inverse-depth affine maps，再与 frozen relative depth 组合为 metric depth。

该设计不声称复现 TR2M；它是为回答本研究问题而建立的最小公平双候选基线。

## Training contract

- 只用 003 生成的 official-train train split；dev 仅 early stopping/selection，internal-test 不参与；
- D0/D1 独立运行 seeds `17/29/43`；
- 同一 optimizer、learning-rate schedule、batch size、update steps、loss、augmentation 和有效 mask；
- D1 只读 verified-clean caption，不读 structured/natural error、router labels 或 internal-test；
- trainable parameter count 差异 ≤10%；若不能满足，增加不读取 text 的 capacity-matched D0 control；
- 选择规则、超参数和 checkpoint epoch 在 dev 冻结后才能读取 internal-test。

## Verification

32 样本 smoke test 必须验证：

1. frozen backbone 和 frozen context encoders 梯度均为 `None`；
2. 当前 expert head 有非零有限梯度；
3. D0 对 caption permutation 逐元素不变；
4. D1 对 clean caption permutation 至少一个样本变化；
5. 两 expert 输出 shape/mask 一致；
6. 保存/重载后输出绝对误差 <`1e-6`；
7. manifest 记录 checkpoint、训练数据、代码 commit 和配置 SHA256。

## Expected artifacts

- `paper1/experiments/covol/models/dual_candidate_depth.py`
- `paper1/experiments/covol/train_expert.py`
- `paper1/tests/test_dual_candidates.py`
- `paper1/artifacts/covol/expert_manifest.json`

本地 `auto_research` 环境当前没有 PyTorch；模型代码实现与 GPU 环境锁定是下一原子动作，但这已是仓库自有实现路线，不再依赖上游发布日期。
