# 想法 2：Q-GeoRoute——问题条件下的预算化层级几何路由

## 当前结论

- **状态：Research Opportunity（研究机会），尚不是 Paper Candidate。**
- **优先级：2。** 可复现性和算力可控，但近邻比想法 1 更拥挤，必须正面击败 GeoSR。
- **一句话算法差异：** 对每个空间问题先求一个满足答案损失容差的**最小充分几何子集**，再由离散路由器按问题联合选择 VGGT 的最大执行深度、中间特征层和空间 token 预算；这不同于固定多层注入，也不同于在已经算出的全部几何 token 上做软门控。

## 1. 为什么它仍可能是研究机会

### 1.1 可复现缺陷

[SpatialStack](../reference_papers_processed/Zhang_SpatialStack_Layered_Geometry-Language_Fusion_for_3D_VLM_Spatial_Reasoning_CVPR_2026_paper.md) 的关键观察是：VGGT 浅/中层更适合局部、低层几何任务，深层更适合高层空间语义；天真融合多层还会产生干扰。论文最终固定选取若干 VGGT 层，并固定注入 LLM 的前部层。也就是说，**论文证明了层级需求因任务而异，但推理时仍对所有问题采用同一层集合和同一注入方式。**

这产生一个可检验缺陷：边界/相对位置问题、全局房间尺寸问题、跨视角关系问题是否真的需要同样的层级和 token 数？若逐样本 leave-one-layer-out 的最优子集显著不同，固定融合就同时存在精度干扰和计算浪费。

[SpaceMind](https://arxiv.org/abs/2511.23075) 使用相机引导的双编码器融合，但论文明确描述其几何重要性权重是 query-independent；因此也没有解决逐问题的层级分配。

### 1.2 必须规避的强近邻

- [GeoSR](https://arxiv.org/abs/2603.26639) 已经提出 Geometry-Guided Fusion，并在动态场景利用问题相关的几何 attention 做 Top-K masking。它是本想法最危险的近邻和首要 killer baseline。
- [Grounded 3D-Aware Spatial VLM / GR3D](../reference_papers_processed/Cheng_Grounded_3D-Aware_Spatial_Vision-Language_Modeling_CVPR_2026_paper.md) 会在生成过程中定位被提及实体并插入 region token，已经覆盖问题驱动的区域 grounding。
- [VLM-3R](../reference_papers_processed/Fan_VLM-3R_Vision-Language_Models_Augmented_with_Instruction-Aligned_3D_Reconstruction_CVPR_2026_paper.md) 和 SpatialStack 覆盖几何特征融合，但没有预算化逐问题层选择。

因此，“加一个 query gate”“选 Top-K token”或“做动态 region grounding”都不足以构成创新。唯一值得验证的窄假设是：**把层级几何选择定义为带成本约束的最小充分证据决策，并让选择真正减少 encoder 深度/LLM token 成本。**

### 1.3 可证伪假设

> 同一图像上的不同空间问题具有不同的最小充分 VGGT 层级与区域证据。通过全子集反事实产生自动路由 oracle，再学习问题条件的离散层—token 路由，可在相同 FLOPs 下提高答案准确率，或在不显著损失准确率时减少几何编码和 LLM 融合成本。

如果最优层子集主要由图像而非问题决定，或者 full soft attention / GeoSR 达到相同准确率—FLOPs Pareto，则假设被否证。

## 2. 算法草案

### 2.1 三个离散决策

给定图像/视频 $I$、问题 $q$，VGGT 候选层集合 $\mathcal L=\{11,17,23\}$，路由器作三个相关决策：

1. **最大执行深度 $L_{max}$：** 对只需浅层几何的问题允许 VGGT early exit；
2. **tap 层子集 $S_L\subseteq\mathcal L$：** 决定将哪些中间层特征投影给 VLM；
3. **空间 token 子集 $S_T$ 与预算 $K$：** 在选中层内只暴露问题相关的 patch/frame token。

路由器输入只使用问题 embedding、廉价 2D 视觉摘要和可选的 VGGT 浅层 preview，避免“先计算全部几何再声称节省计算”。首轮实现可先缓存完整特征，验证选择规律；只有规律成立后再实现真正 early exit。

### 2.2 自动构造最小充分子集 oracle

SpatialStack 只使用 3 个候选层，层子集仅 7 种，适合做精确反事实枚举。冻结基础 VLM 后，对训练样本 $(I,q,y)$ 计算：

$$
S_L^*=\arg\min_{S\subseteq\mathcal L} C(S)
\quad\text{s.t.}\quad
\mathcal L_{ans}(S)\leq \mathcal L_{ans}(\mathcal L)+\epsilon.
$$

$C(S)$ 同时计算最大 VGGT 层带来的 encoder FLOPs、投影器开销和注入 LLM 的 token 开销。答案标签 $y$ 和模型损失提供自动 oracle，不使用另一个 LLM 评分。

空间 token 不做指数枚举，而在 oracle 层集合内用预算化 hard top-k / straight-through routing 学习；可以用移除 token 后的答案损失增量作为稀疏教师分数。这个 teacher 只在训练或离线缓存阶段使用。

### 2.3 目标函数

$$
\mathcal L=
\mathcal L_{ans}
+\lambda_o\mathcal L_{oracle}(R_q,S_L^*)
+\lambda_c\max(0,C(R_q)-B)
+\lambda_p\mathcal L_{para}
+\lambda_f\mathcal L_{faith}.
$$

- $\mathcal L_{ans}$：标准空间问答交叉熵；
- $\mathcal L_{oracle}$：预测最小充分层子集的多标签/排序损失；
- 成本项：显式约束期望 FLOPs 或 token 数，而不是事后报告 attention 稀疏度；
- $\mathcal L_{para}$：同义问题应选择相近证据，减少语言表面形式造成的路由漂移；
- $\mathcal L_{faith}$：删除已选择证据应显著提高答案损失，删除未选择证据不应明显影响答案，验证选择的充分性与必要性。

对同一场景构造问题对：局部实体关系、距离/尺寸、全局布局、跨视角/动态关系。问题标签来自现有 benchmark；同义改写可以模板化生成，路由正确性仍由 ground-truth answer loss 决定。

## 3. 与 GeoSR、GR3D 的明确边界

| 方法 | 问题相关区域 | 选择几何层 | 硬预算 | 可减少几何 encoder 深度 | 最小充分子集 oracle |
| --- | --- | --- | --- | --- | --- |
| SpatialStack | 否 | 固定多层 | 否 | 否 | 否 |
| SpaceMind | 几何权重与 query 无关 | 否 | 否 | 否 | 否 |
| GR3D | 是，实体 region | 否 | 否 | 否 | 否 |
| GeoSR | 是，动态设置中用于相关性/遮蔽 | 否 | 否 | 否 | 否 |
| **Q-GeoRoute（候选）** | 是 | **逐问题离散选择** | **是** | **浅层问题可 early exit** | **是** |

这张表是需要实验兑现的主张，不是已经成立的结论。尤其要检查 GeoSR 的完整代码与最新版论文；如果其实现已经联合选择层级并带真实计算预算，本想法应直接降级或终止。

## 4. 最小可证伪实验（先做这个）

### 4.1 Defect reproduction：先证明固定层确实有问题

1. 选择 SpatialStack 的公开模型/设置，冻结全部参数；
2. 缓存层 11、17、23 特征；
3. 对 VSI-Bench 或 SPAR-Bench 的固定子集枚举 7 个非空层子集；
4. 统计每个问题的最小充分子集、按题型分布、跨同义改写稳定性；
5. 计算全层方案相对 per-example oracle 的准确率与 FLOPs regret。

进入方法开发的最低条件：

- 至少两类问题的最优层分布显著不同；
- 固定全层相对 oracle 存在非平凡的准确率干扰或至少 25% 可节省成本；
- 差异不能只由视频长度、分辨率等表面变量解释。

### 4.2 Canary

只训练一个小型层路由器，暂不做空间 token 路由，也不更新 VLM。比较：

- 固定 11/17/23；
- 最佳全局单层/双层；
- question-conditioned soft mixture；
- oracle-supervised hard subset router。

若 hard router 无法接近 oracle，或者 soft mixture 同时更准更省，则没有必要继续复杂化。

## 5. 正式实验矩阵

### 数据与指标

- 静态/多视角：VSI-Bench、SPAR-Bench、SQA3D；
- 通用空间：CV-Bench、BLINK；
- 若验证动态版本，再加入 GeoSR 使用的动态 benchmark，避免首轮扩散范围。
- 精度：总体 accuracy、按题型 accuracy、定量距离/尺寸误差；
- 效率：实际 latency、峰值显存、VGGT FLOPs、注入 token 数、LLM prefill FLOPs；
- 路由：oracle recall、层选择熵、同义问题一致性、选择证据的 deletion faithfulness；
- 主结果必须是 accuracy—cost Pareto，而非只报平均 token 降幅。

### 必须击败的 killer baselines

- SpatialStack 固定层和最佳全局层组合；
- full soft attention、learned global layer weights；
- query-conditioned soft layer mixture（无离散预算）；
- random / 2D saliency / attention Top-K；
- GR3D implicit grounding；
- GeoSR masking + Geometry-Guided Fusion；
- SpaceMind、VLM-3R；
- per-task oracle（上界）和 per-example exhaustive oracle（小规模上界）。

### 必做消融

- 去掉 oracle supervision、cost、paraphrase consistency、faithfulness；
- 只选层、只选 token、联合选择；
- 只减少 LLM token 与真正 VGGT early exit；
- 路由输入：仅问题、问题+2D 摘要、问题+浅层 geometry preview；
- 不同预算 $B$、不同 $\epsilon$、不同 backbone 和题型；
- 实际 wall-clock 加速，排除稀疏算子没有硬件收益的情况。

## 6. 结果解释与止损条件

- **最佳情况：** 问题类型对应稳定而可解释的层级选择，hard routing 在等 FLOPs 下优于 GeoSR/soft mixture，并产生真实 wall-clock 收益。
- **普通情况：** 准确率不变但 token 明显减少；这更像高质量效率论文，是否符合目标 venue 需重新判断。
- **负结果：** 不同问题的 oracle 子集几乎相同；或 LLM 自注意力已经能忽略无关几何；或 GeoSR/soft attention 支配 Pareto。此时应停止，不把 pruning 包装成算法创新。

最强反对意见是：**VLM 已能用问题对固定几何 token 做注意力，这只是额外 pruning。** 唯一有力的回应是证明固定全层存在可重复的任务相关干扰，并且“最小充分子集 oracle + 联合层/计算决策”带来软注意力无法得到的准确率—成本前沿。

## 7. 算力与实现顺序

- Phase 0：离线缓存 3 层特征，7 个子集枚举；可拆批运行，1 张 A800 即可；
- Phase 1：冻结 encoders/VLM，只训练 router 与 projector；
- Phase 2：信号成立后再加 LoRA，并实现真实 early exit 与稀疏 token packing；
- 优先小模型和固定 benchmark 子集，不在缺陷未证明前训练 8B 全模型；
- 保存每个样本的子集损失、成本、随机种子和 router 决策，确保 oracle 可审计。

## 8. 升级为 Paper Candidate 的必要条件

目前只能登记为 **Research Opportunity**。升级前必须满足：

1. 层级需求的逐问题差异被重复实验确认；
2. hard router 接近 exhaustive oracle，并超过 query soft mixture 与 GeoSR；
3. 有实际计算收益，不只是 attention 可视化；
4. 最新近邻审计确认没有同构的 query-conditioned layer/early-exit 方法；
5. 方法能写成明确的约束优化、伪代码和可复现实验，而不是普通模块组合。
