# 备用想法：Q-GeoRoute Phase 0——问题条件的模型相对最小充分深度

## 当前结论

- **状态：PARKED Research Opportunity，不是并行主线。**
- 只有 CoVoL 的 H-defect 或 H-semantic Gate-0 被否定并完成范围变更记录后，才允许启动。
- 当前只验证一个问题：同一场景的不同空间问题，是否对应不同的、相对于冻结模型/答案损失/容差 `ε` 的最小充分最大执行层 `Lmax`。
- 暂停 token routing、Top-K、联合预算、LoRA、动态 region grounding 和完整方法训练。

“最小充分层”不是任务固有真值，而是 **model-relative oracle**。未实现真实 early exit 前，只能称层选择分析，不能称预算化推理方法。

## 1. Phase-0 假设

> 在同一场景的配对问题中，question-conditioned 决策相对最佳全局深度能提高至少 2 个百分点；实现 layer-11/17/23 early exit 后，准确率下降不超过 1 个百分点时，端到端 latency 至少降低 20%。

任一阈值未达到即归档。即使阈值达到，也只保留为 Research Opportunity，尚不足以升级 Paper Candidate。

## 2. 固定定义

冻结 SpatialStack/VGGT/VLM 及 projector，候选 tap 层为 `L={11,17,23}`。对每个样本 `(I,q,y)` 枚举 7 个非空子集 `S⊆L`，答案损失为冻结模型对 ground-truth answer 的 `L_ans`。给定预注册容差 `ε`：

$$
S^*(I,q)=\arg\min_{S\subseteq L,\,S\ne\varnothing} C(S)
\quad\text{s.t.}\quad
\mathcal L_{ans}(S)\le
\mathcal L_{ans}(L)+\epsilon.
$$

Phase 0 的核心标签只取：

$$
L^*_{max}(I,q)=\max S^*(I,q).
$$

7 子集枚举用于检查同一 `Lmax` 内不同 tap 组合是否造成混杂；router 首轮只预测 `Lmax∈{11,17,23}`，不预测 tap subset 和 token subset。

## 3. 实验设计

- 至少 1,000 组“同一场景、不同问题”样本，按 scene 分 train/dev/test。
- 问题覆盖局部实体关系、距离/尺寸、全局布局和跨视角关系；同义改写仅作稳定性检查。
- 比较：最佳全局 `Lmax`、per-task oracle、per-example oracle、question-only classifier、image-only classifier、question+cheap-2D-summary classifier。
- 统计单位为 scene；3 个种子，scene-level paired bootstrap 95% CI。
- 必须报告 `P(Lmax|question type)`、同场景问题间差异、oracle recall、accuracy 和真实 latency。
- 若 question-only 的增益完全由题型词表解释，且同一题型内不随问题变化，则只能算 task-level policy，不构成 per-query routing。

## 4. 成本分账

禁止把离线缓存或 FLOPs 直接写成加速。每个设置单列同步计时：

| 成本项 | tap subset 能否减少 | `Lmax` early exit 能否减少 | 报告项 |
| --- | --- | --- | --- |
| VGGT encoder | 否 | 是 | ms、FLOPs、peak memory |
| projector | 是 | 可能 | ms、输入 tap 数 |
| LLM prefill | 是 | 可能 | ms、注入 token 数 |
| sparse packing/kernel | 可能增加 | 可能增加 | packing ms、有效 batch |
| end-to-end | 需实测 | 需实测 | warm/cold latency、吞吐 |

只有 `Lmax` 真正提前停止 VGGT block 才能主张 encoder 节省。完整 VGGT 已执行后再丢层，只能报告 projector/LLM 成本变化。

## 5. Go / No-Go

仅在以下条件全部满足时继续：

1. question-conditioned oracle 相对最佳全局 `Lmax` 的 accuracy 提高 ≥2 pp；
2. question+2D router 显著优于 image-only，且不是只记忆题型；
3. 真实 early exit 的端到端 latency 降低 ≥20%，accuracy drop ≤1 pp；
4. 结果在 scene bootstrap 95% CI 下稳定；
5. 最新近邻审计确认 GeoSR/其他方法未实质覆盖模型相对充分深度与真实 early exit。

否则记录 STOP。禁止把负结果改写成 token pruning、attention 可视化或普通效率工程论文。

## 6. 与主线的资源隔离

- 在 CoVoL 步骤 006 决策前，本文件不产生代码、数据下载或 GPU 任务。
- 启动时只执行 `paper1/steps/012_qgeoroute_go_no_go.md`，不复用 CoVoL 的主张、结果或实验预算。
- 任何从 CoVoL 切换到本方向的决定必须先更新 `001_primary_scope_lock.md`，保证仓库始终只有一个主线。
