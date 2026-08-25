# 005 Repository-Owned Frozen Experts

## Status

`BLOCKED-BY-STEP003, DESIGN-IN-PROGRESS`。现有 stacking plan/cache validator 只能审计 scene-level 计划，尚未满足 Round6 的 sequence/drive-cluster、seed/control/checkpoint 实体绑定合同；PyTorch 双候选、训练和真实 cache 也未完成。当前 `STOP_TWO_DATASET_CLAIM` 下不得启动本步骤，A800 shared CUDA canary 通过不改变该门禁。不再等待 TR2M 训练代码，也不把 TR2M released checkpoint 当正式双候选。

## Shared-backbone contract

- 冻结一个锁定 SHA256 的 DepthAnything ViT-S checkpoint；
- 每次前向只计算一次相对深度与 frozen multi-scale image features；
- D0/D1 使用两个独立训练、结构逐层同构、参数不共享的 metric heads；
- 两个 head 均接收完全相同的 frozen image-global feature 和 frozen multi-scale image features；
- 两个 head 都含相同的 `768→256→C` text-channel adapter、FiLM 位置和同构 decoder；
- D0 的 text channel 输入一个可训练、所有样本共享的 learned-null token，且经过与 D1 caption embedding 完全相同的 adapter/FiLM 路径；D0 不以 zero embedding 或 image context 绕过 text channel；
- 对应层使用同一初始化 seed，层名、shape、trainable parameter count 必须完全相等，而不只是 ±10%；
- 除总参数量外，32 样本 smoke test 还逐层报告 nonzero-gradient parameter count/ratio；D0/D1 每个对应层的 active-gradient 状态必须一致，否则容量公平门禁失败；
- 输出 pixel-wise inverse-depth affine maps，再与 frozen relative depth 组合为 metric depth。

该设计不声称复现 TR2M；它是为回答本研究问题而建立的最小公平双候选基线。

## Sequence/drive-cluster OOF stacking contract

- router-train 的 frozen `cluster_id` 固定为 5 folds；NYUv2 的 scene–sequence connected component 与 KITTI drive 不能拆分。第 k 个 D0/D1 只在“全部 official-training clusters 减去 router-dev、internal-test 和 fold-k”上训练，并只预测 fold-k；
- 另训练 final D0/D1：使用全部 official-training clusters 减去 router-dev/internal-test，只预测 router-dev 和 internal-test；
- router-train 的 advantage label 只能来自对应 OOF experts；禁止任何 in-sample expert prediction 进入 router、nuisance、tie band 或 threshold；
- `cache_oof_experts.py` 当前只能生成 `PLANNED_NOT_TRAINED` 的旧 scene-level 计划；它不是 checkpoint 或真实 cache，不得作为本合同已完成的证据；
- 正式 cache 的主键为 `(dataset,image_id,seed,candidate_id,control_type)`。`seed` 只允许 `17/29/43`；`candidate_id` 至少覆盖 D0/D1；`control_type` 覆盖 formal、image-twin 与 shuffled-caption；
- 每行必须记录 `cluster_id`、OOF/final scope、checkpoint path/SHA256、config path/SHA256、expert-training-manifest path/SHA256、code commit、cache path/SHA256。validator 必须打开 repository/remote-workspace 内的实际文件重算 SHA256，不能只检查 JSON 中是否存在 64 位字符串；
- 每个 router image×seed×required candidate/control 恰有一行，对应 prediction cluster 不在 training cluster set。任一交集、缺行、重复、路径越界、文件缺失或实际 hash 不同均硬失败。

实现与测试：`paper1/experiments/covol/cache_oof_experts.py`、`paper1/tests/test_expert_cache_no_leakage.py`。

## Expert training manifest

每个 OOF/final expert 在训练前由 `build_expert_training_manifest.py` 冻结逐行训练输入：

- `dataset,image_id,cluster_id,seed,candidate_id,control_type`；
- RGB、valid-depth target、predicate-clean caption 的 repository/remote-workspace-relative path 与实际 SHA256；
- captioner ID、revision、prompt hash、decoding config hash；
- prediction fold、training cluster-set hash 和 source/split manifest hash。

D1 的 predicate-clean caption 缺失率必须为 0；同一 seed/scope/control 下成对 D0/D1 的训练 image 与 depth-target 集合必须逐项相同。D0 虽不读取 caption content，仍绑定同一训练行集合，防止以数据差异制造候选优势。任何 prediction-cluster overlap 或 caption/source hash 漂移均在训练前停止。

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
9. manifest 记录 seed、candidate/control identity、checkpoint、训练数据、代码 commit 和配置的实际 SHA256，并由 validator 重算；
10. 三个 seeds 的 OOF/final formal、twins 与 shuffled-caption 行覆盖完整且无重复。

## Expected artifacts

- `paper1/experiments/covol/models/dual_candidate_depth.py`
- `paper1/experiments/covol/train_expert.py`
- `paper1/experiments/covol/build_expert_training_manifest.py`
- `paper1/experiments/covol/cache_oof_experts.py`
- `paper1/experiments/covol/run_expert_controls.py`
- `paper1/tests/test_dual_candidates.py`
- `paper1/tests/test_expert_cache_no_leakage.py`
- `paper1/artifacts/covol/expert_manifest.json`
- `paper1/artifacts/covol/expert_training_manifest.jsonl`
- `paper1/artifacts/covol/expert_stacking_plan.json`
- `paper1/artifacts/covol/expert_cache_manifest.json`
- `paper1/results/covol/expert_negative_controls.csv`

远程 A800 的 shared CUDA canary 已确认 PyTorch/CUDA 执行链可用，但它没有加载真实数据或模型。真实训练、checkpoint、cache 和 negative-control 结果均为 PENDING；exclusive queue 已暂停并保留状态。现有 OOF 代码只锁定旧 scene-level 数据依赖并防止一部分 stacking 泄漏，不能满足本轮新增的实体级审计。
