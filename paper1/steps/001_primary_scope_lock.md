# 001 Primary Scope Lock

## Current state

用户于 2026-08-27 明确将唯一研究主线切换为 **BAR-Depth：
Budget-Adaptive Regional Refinement for High-Resolution Depth**。当前状态是
`SELECTED_RESEARCH_OPPORTUNITY / V1_INVALID_METRIC_ALIGNMENT /
V2_REPAIR_REQUIRED / NOT_PAPER_CANDIDATE`。

v1 已完成但被 Step 019 判为 `INVALID_METRIC_ALIGNMENT`，因为 unconstrained affine
inverse depth 在 outdoor 产生非正值后被 epsilon clipping。该输出不是科学 STOP。
当前状态收紧为 `V2_REPAIR_REQUIRED / NOT_PAPER_CANDIDATE`；只允许在其余合同完全
不变时改用 positive median scale-only metric alignment 重跑。

本轮只授权一个 defect canary：在 DIODE validation 的 200 张公开高分辨率
RGB-D 图像上，冻结 Depth Anything V2-S，枚举每张图的 3×4 个区域细化动作，
判断可改善误差是否足够大且集中到少量区域。该 canary 不训练 router，不声称
端到端加速，也不进入完整 Paper Build。

协议、算法差异和停止阈值见
[BAR-Depth candidate](../ideas/candidates/02_budget_adaptive_regional_depth.md) 与
[018 oracle canary](018_bar_depth_oracle_canary.md)。

## Superseded active opportunity

SR-VEP 曾被 Gate-017 选为 Research Opportunity，但在任何 annotation 获取、CPU
defect canary、媒体下载或模型训练发生前，被用户的显式方向变更取代。它现在是
`PARKED_BEFORE_CANARY / NO_REPOSITORY_SCIENTIFIC_RESULT`，不得与 BAR-Depth 并行
消耗研究预算；历史定义保留用于追溯，不能解释为缺陷已否定。

## BAR-Depth task

给定高分辨率 RGB 图像、冻结的低分辨率全图深度预测和最多 `B` 次区域细化预算，
选择区域集合 `S` 并合并局部预测，使细节加权深度误差最小，同时约束全图误差与
实际推理成本。当前 canary 仅验证 oracle 选择空间：

$$
S_B^*=\arg\max_{|S|\le B}\sum_{i\in S}\max(\Delta E_i,0),
\qquad
\Delta E_i=E_i(D_0)-E_i(\operatorname{Merge}(D_0,D_i)).
$$

候选区域的写回支持互不重叠，因此 canary 中的区域效用可加；后续算法阶段才研究
重叠、多尺度、成本不等和学习式边际效用。

## Candidate algorithm difference

如果 oracle gate 通过，候选算法必须同时包含：

1. 从一次低分辨率全图前向中预测每个候选区域的误差下降与置信区间；
2. 在真实预算下联合考虑收益、区域重叠冗余和不同尺度成本，而非固定网格或边缘阈值；
3. 用全局相对深度作低频锚点，只把被选择区域的局部高频残差写回；
4. 输出 accuracy–latency Pareto，并与 2021 content-adaptive patch selection、
   PatchFusion、PRO 和全量网格细化等 killer baselines 同预算比较。

仅做 saliency map、固定 Top-K、调整 tile size 或报告 FLOPs 不构成算法贡献。

## Oracle canary gate

预注册主门禁必须同时满足：

- 恰好 200 张图、20 个 DIODE validation scans，每 scan 10 张；
- 正向可细化 headroom 相对 base 细节加权 AbsRel 至少 3%；
- 25% 区域预算捕获至少 70% 的全部正向 oracle utility；
- 25% oracle 使细节加权 AbsRel 至少下降 2%；
- 使用同一个 base metric alignment 时，全图普通 AbsRel 的相对劣化不超过 1%；
- 上述前三个效应的 scan-cluster bootstrap 95% 下界仍越过阈值。

任一条件失败则当前区域选择表述 `STOP`；不得通过改 grid、改模型、挑 indoor/outdoor
切片或改 utility 权重反向恢复。若主 gate 通过但便宜启发式仍接近随机，只能记为
`GO_ORACLE / ROUTABILITY_UNVERIFIED`，下一步先做严格 scan-held-out router probe。

## Archive boundary

CoVoL 的最终状态仍是
`ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`；所有旧 downstream
入口继续由最终 scientific gate 停止。本次换题不修改、复活或重解释 CoVoL 结果。

## Upgrade gate

BAR-Depth 只有在 oracle gate、scan-held-out router、2021 patch-selection killer、
跨数据集/跨 backbone、真实同步 latency 与组件消融均通过后，才允许升级为 Paper
Candidate。当前没有算法增益、加速或投稿级 claim。
