# BAR-Depth：预算自适应区域深度细化

## 状态

`SELECTED_RESEARCH_OPPORTUNITY / V1_INVALID_METRIC_ALIGNMENT /
V2_REPAIR_REQUIRED / NOT_PAPER_CANDIDATE`。

## 问题与最近邻缺口

高分辨率单目深度同时需要全局上下文和局部细节。现有代表性路径包括：

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

这些工作已经覆盖“局部高分辨率有用”“tile 可以融合”和“可在高分辨率推理”。
剩余待证伪缺口不是再发明一种融合模块，而是：**在严格区域计算预算下，固定全量
tile 是否浪费大部分计算，以及能否从一次便宜全图前向预测每个候选动作的边际误差
下降。**

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
  safety metric。
- 统计：scan 为独立 cluster，固定 5,000 次 cluster bootstrap。

## Post-canary algorithm hypothesis

若缺陷成立，方法阶段学习成本约束的边际收益：

$$
S^*=\arg\max_{S:\sum_{i\in S}c_i\le B}
\left[\sum_{i\in S}\widehat u_i-
\lambda\sum_{i,j\in S}\rho_{ij}\right],
$$

其中 `c_i` 是同步实测成本，`rho_ij` 是重叠或同质区域冗余。router 只能读取 base
前向已有的 RGB/depth/features；不得读取 GT、patch prediction、文件名、数据集 ID 或
专家执行后信息。初版使用 scan-held-out cross-fitting，比较 random、uniform、RGB
edge、base-depth edge、2021 content-adaptive selection、uncertainty 和 oracle。

## STOP and upgrade

当前只执行 oracle canary。主门禁失败即归档该表述；通过只说明问题和动作空间存在，
不说明可路由。只有 learned router 在 unseen scans 上恢复大部分 oracle headroom，且
真实 latency/accuracy Pareto 超过全部 killer，才可能成为 Paper Candidate。

v1 虽生成了原始 gate STOP，但 affine inverse-depth 在 outdoor 产生非正值并触发
epsilon clipping，故该 STOP 已由 [Step 019](../../steps/019_bar_depth_v1_metric_audit.md)
判为无效科学结论。v2 只修复为 positive median scale-only metric alignment；所有
研究门禁与动作定义不变。
