# BAR-Depth：选择性的尺度对齐区域深度细化

## 状态

`RESEARCH_OPPORTUNITY_JOINT_SET_PROBE_ONLY /
STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER / W08_CURRENT_CONTRACT_STOPPED /
FORMAL_W07_V2_PENDING / NOT_PAPER_CANDIDATE`。

## 问题与最近邻缺口

高分辨率单目深度同时需要全局上下文和局部细节。本文当前只研究
**逐图中位数尺度对齐的相对深度细化**；当前证据不外推到无需 GT
对齐的度量深度。
现有代表性路径包括：

- [Boosting MDE, CVPR 2021](https://openaccess.thecvf.com/content/CVPR2021/papers/Miangoleh_Boosting_Monocular_Depth_Estimation_Models_to_High-Resolution_via_Content-Adaptive_Multi-Resolution_CVPR_2021_paper.pdf)
  已用边缘密度启发式选择 patch，是本方向最重要的 novelty killer；
- [PatchFusion, CVPR 2024](https://openaccess.thecvf.com/content/CVPR2024/papers/Li_PatchFusion_An_End-to-End_Tile-Based_Framework_for_High-Resolution_Monocular_Metric_Depth_CVPR_2024_paper.pdf)
  学习全局/局部 tile 融合；
- [PRO, ICCV 2025](https://openaccess.thecvf.com/content/ICCV2025/papers/Kwon_One_Look_is_Enough_Seamless_Patchwise_Refinement_for_Zero-Shot_Monocular_ICCV_2025_paper.pdf)
  用 grouped consistency 和一次 patch refinement 降低固定网格的边界与效率问题；
- [Scalable Autoregressive MDE, CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Wang_Scalable_Autoregressive_Monocular_Depth_Estimation_CVPR_2025_paper.html)
  采用空间分辨率与深度区间的 coarse-to-fine 自回归；
- [InfiniDepth, CVPR 2026](https://openaccess.thecvf.com/content/CVPR2026/html/Yu_InfiniDepth_Arbitrary-Resolution_and_Fine-Grained_Depth_Estimation_with_Neural_Implicit_Fields_CVPR_2026_paper.html)
  面向任意分辨率和细粒度预测。
- [SaccadeCam, ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/papers/Tilmon_SaccadeCam_Adaptive_Visual_Attention_for_Monocular_Depth_Sensing_ICCV_2021_paper.pdf)
  已学习固定数量高分辨率 foveae 的注意区域，因此普通 learned score + Top-K
  不是充分 novelty；
- [Depth Pro, ICLR 2025](https://openreview.net/forum?id=aueXfY0Clv)
  以一次快速多尺度前向输出高分辨率 metric depth，是等延迟全图推理 killer。

这些工作已经覆盖“局部高分辨率有用”“tile 可以融合”和“可在高分辨率推理”。
剩余待证伪缺口不是再发明一种融合模块，而是：**在严格区域计算预算下，固定全量
tile 是否浪费大部分计算，以及能否从一次便宜全图前向预测每个候选动作的边际误差
下降。这里的“误差下降”必须是 signed utility；只统计所选区域中的正效用不能验证
router。**

对 target cell 的像素集合 $\Omega_i$、GT depth $y_p$、固定边界权重 $w_p$，定义

$$
E_i(D)=\sum_{p\in\Omega_i}w_p\frac{|D_p-y_p|}{y_p},\qquad
u_i=E_i(D_0)-E_i(D^{(i)}),\qquad
t_i=\frac{u_i}{E_0(x)}.
$$

$D^{(i)}$ 表示只执行动作 $i$ 后的结果。$u_i>0$ 表示改善，$u_i<0$ 表示有害；
$E_0(x)>0$ 是同一图像 12 个 target cells 的 base primary error 总和，故 $t_i$
与 raw $u_i$ 在图像内严格保序；它只用于训练标签构造，不是推理特征。v1 的
`u_i/weight_sum` 在 K=3 只恢复 raw oracle 的 93.70%，已经由 Step 027 停用。

## Defect hypothesis

对图像 `x`、base 深度 `D0`、候选区域细化动作 `ri` 和误差 `E`，定义：

$$
u_i(x)=E_i(D_0)-E_i(\operatorname{Merge}(D_0,r_i(x))).
$$

缺陷假设为：`u_i` 在图像内高度非均匀；只执行 25% 区域可捕获至少 70% 的正向
效用，并获得至少 2% 的预注册细节误差下降。如果效用近似均匀、总量太小或只来自
全图误差恶化，本方向不存在。

## Canary representation

- 数据：DIODE validation，1024×768，indoor/outdoor 共 20 scans；每 scan 由固定哈希
  选择 10 张，共 200 张。DIODE 官方页面给出 validation archive MD5、RGB/depth/mask
  和 MIT 许可。
- 模型：冻结 Depth Anything V2-S；全图短边缩放到 518，区域也缩放到 518。
- 动作：3×4 非重叠 target cells；每个局部前向读取 1.5× context，只把中心 target
  的高频残差以 raised-cosine window 写回。
- 对齐：局部预测只对 base disparity 做稳健 affine alignment；GT 只用于固定一次
  image-level base metric alignment 和计算 oracle utility。
- 主误差：GT depth-boundary 加权 AbsRel，边界权重 5、其余权重 1；普通 AbsRel 为
  safety metric。它是自定义 canary metric，必须由标准 depth/boundary 指标和阈值
  敏感性支持后才能进入论文主张。
- 统计：scan 为独立 cluster，固定 5,000 次 cluster bootstrap。

## Post-canary algorithm status

以下逐动作 point probe 只保留为已否定的诊断基线：

$$
S_{\mathrm{probe}}=\arg\max_{S:\lvert S\rvert\le K}
\sum_{i\in S}\widehat u_i,
$$

通用算法近邻审计表明，point regression、训练期阈值校准、Top-K 和弃权的组合已被
selective regression、conformal decision calibration 与 spatial adaptive inference
实质覆盖，不能作为论文算法。当前只保留一个非等价、待预注册的机制 probe：直接估计
自适应所选集合的联合、预算条件 utility 分布，并为 selected-set utility 构造
selection-aware lower confidence bound。它必须用相同 features/folds 同时超过 point
Top-K、Learn-then-Test 和直接 conformal decision calibration，并证明图像内依赖确实
改变集合风险与有效 utility；否则方向最终记为 `STOP_NOVELTY`。正式 W07 v2 返回
Pareto 空间前，不生成 DIODE-train patch labels，也不执行当前 W08。

## STOP and upgrade

当前 oracle canary 只说明问题和动作空间存在，不说明可路由。只有 joint-set 机制在
unseen scans 上超过三类通用 killer，且正式 latency/accuracy Pareto 超过全部直接与
完整近邻，才可能成为 Paper Candidate。

v1 虽生成了原始 gate STOP，但 affine inverse-depth 在 outdoor 产生非正值并触发
epsilon clipping，故该 STOP 已由 [Step 019](../../steps/019_bar_depth_v1_metric_audit.md)
判为无效科学结论。v2 只修复为 positive median scale-only metric alignment，并在
预定义 `[0.1, 350]m` evaluation range 内计算误差；所有研究门禁与动作定义不变。

v2 的有效结果通过全部 oracle gate：headroom 10.42% [7.03%, 13.15%]，oracle 在
每图至多选择 3 个正效用区域时捕获 92.72% [88.25%, 97.54%] 的正效用，primary
reduction 9.66%
[6.59%, 12.36%]。这把方向保留为 Research Opportunity，但不验证 router；下一出口
见 [Step 021](../../steps/021_bar_depth_oracle_canary_v2_result.md)。

历史 summary 中的 `uniform_primary_reduction_ratio` 实际执行全部 12 个区域，只能
解释为 `all_12_regions_primary_reduction_ratio`。历史 JSON 为保持哈希绑定不改写；
后续文档和分析禁止称其为预算匹配 uniform baseline。
