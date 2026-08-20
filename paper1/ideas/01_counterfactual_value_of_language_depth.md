# 想法 1：CoVoL-Depth——基于反事实“语言价值”的安全度量深度路由

## 当前结论

- **状态：Research Opportunity（研究机会），尚不是 Paper Candidate。**
- **优先级：1。** 在现有 30 篇参考文献中，这个缺陷最明确、自动评测最直接、前置算力最低。
- **一句话算法差异：** 不再无条件把描述文本注入深度网络，也不只预测一个“文本可信度”，而是学习每个图像区域使用语言后相对纯视觉分支的**预期误差收益**（value of language），仅在预期收益为正时采用语言残差，并用错误描述的反事实风险显式约束其最坏退化。

## 1. 为什么它通过“研究机会”门槛

### 1.1 可复现的算法缺陷

[Iris: Integrating Language into Diffusion-based Monocular Depth Estimation](../reference_papers_processed/Zeng_Iris_Integrating_Language_into_Diffusion-based_Monocular_Depth_Estimation_CVPR_2026_paper.md) 证明语言能够改善小目标和视觉歧义区域，但其 Figure 9 同时给出直接反例：把“玻璃书柜”替换成错误的“带窗帘的窗户”后，模型的结构预测被误导；Discussion 也把对文本准确性和完整性的依赖列为主要局限。

[TR2M](../reference_papers_processed/Cui_TR2M_Transferring_Monocular_Relative_Depth_to_Metric_Depth_with_Language_CVPR_2026_paper.md) 用图像与 LLaVA 描述预测逐像素 scale/shift，将相对深度转换为度量深度；论文同样指出复杂场景可能误导描述，并且文本本身不足以表达完整布局。两篇论文共同暴露了同一个结构性问题：**语言既是有价值的尺度/语义先验，也是可能造成负迁移的干预变量，而现有融合没有“何时应拒绝语言”的可验证决策规则。**

这个问题可以自动复现，不依赖人工主观判断：同一 RGB 图像保持不变，只替换描述，直接测量 AbsRel、RMSE、δ1 和区域误差相对纯视觉模型的变化。

### 1.2 最近邻并未覆盖本假设

- Iris 的正文只提出“uncertainty estimation 或 consistency filtering”作为未来可能方案，没有定义相对纯视觉分支的收益决策、反事实训练目标或非退化约束。
- TR2M 的图文融合用于生成尺度/偏移图，但没有把语言负收益作为优化对象。
- [WorDepth](https://arxiv.org/abs/2404.03635) 将文本建模为度量深度的变分先验，目标仍是利用语言消除尺度歧义，而不是在错误语言下选择性回退。
- caption dropout、CLIP 相似度阈值、提示词集成和标量置信度过滤都是必须比较的基线，但它们没有回答“这个文本对当前区域的深度误差是否具有正的条件价值”。

因此，候选创新点不能写成“增加一个鲁棒性模块”，而应是下面的**决策式、反事实式选择性融合**。

### 1.3 可证伪假设

> 对语言条件深度估计器，训练一个预测逐区域“语言相对纯视觉分支的条件误差收益”的路由器，并用错误文本的单边 regret 约束训练，可在保留正确文本收益的同时，显著降低错误、无关和不完整文本造成的最坏退化。

如果简单 caption dropout、CLIP gate 或文本集成已经达到相同的正确文本精度—错误文本鲁棒性 Pareto 前沿，则该假设被否证，不应包装成论文。

## 2. 算法草案

### 2.1 视觉安全分支与语言残差分支

给定图像 $I$ 和描述 $c$：

1. 纯视觉分支输出安全预测 $D_0=f_{img}(I)$；
2. 语言分支输出对 log-depth 或 TR2M scale/shift map 的候选修正 $\Delta=f_{txt}(I,c)$；
3. 路由器预测每个 patch 的语言价值 $\hat v_p=h(I,c,D_0,\Delta)_p$；
4. 用 $g_p=\sigma(\hat v_p/\tau)$ 选择性采用修正：

$$
\log \hat D_p=\log D_{0,p}+g_p\Delta_p.
$$

首轮 canary 建议以 TR2M/Depth Anything 小模型实现，因为单次前向和尺度残差更便宜；信号成立后再迁移到 Iris/Marigold 的 diffusion conditioning。

### 2.2 自动构造“语言价值”监督

训练时有深度真值 $D^*$。对 patch $p$，把语言专家完全开启后的预测记为 $D_1$，定义 stop-gradient 教师价值：

$$
v_p^*=\ell_p(D_0,D^*)-\ell_p(D_1,D^*).
$$

$v_p^*>0$ 表示语言在该区域确实减少误差，$v_p^*\leq0$ 表示应回退到视觉分支。路由器学习 $\hat v_p\approx v_p^*$，而不是学习没有任务含义的抽象置信度。

每张图自动生成四类文本干预：

- **语义不变：** 模板化同义改写、句序变化、删除冗余形容词；
- **信息删减：** 删除一个有标注实例或远处小目标；
- **局部冲突：** 把有标注实体替换成图中不存在或几何属性冲突的实体；
- **全局无关：** 匹配场景类别后交换另一张图的 caption，避免只靠“室内/室外”轻易识别。

实体存在性优先来自数据集类别、panoptic mask 或检测标注；深度真值是最终 oracle。LLM 可以生成表面文本，但不能充当正确性裁判。

### 2.3 核心优化目标

$$
\mathcal L=
\mathcal L_{depth}^{+}
+\lambda_v\mathcal L_{value}
+\lambda_r\mathcal L_{regret}^{-}
+\lambda_e\mathcal L_{equiv}
+\lambda_s\mathcal L_{sparse}.
$$

- $\mathcal L_{depth}^{+}$：正确描述下的标准深度损失，确保语言仍能提供收益；
- $\mathcal L_{value}$：$\hat v_p$ 对 $v_p^*$ 的带符号回归或排序损失；
- $\mathcal L_{regret}^{-}=\max(0,\ell(\hat D(I,c^-),D^*)-\ell(D_0,D^*)-\epsilon)$：错误文本相对视觉分支的单边遗憾；
- $\mathcal L_{equiv}$：语义等价改写应产生一致的预测与路由；
- $\mathcal L_{sparse}$：阻止所有区域默认依赖语言，同时避免“全部关闭语言”的平凡解。

最后一项必须与正确文本收益约束一起使用；否则 minimax 训练的最优解可能只是忽略全部语言。

## 3. 最小可证伪实验（先做这个）

### 3.1 Defect reproduction

1. 复现一个开源语言条件深度模型及其纯视觉版本；
2. 在 NYUv2 和 KITTI 各抽取固定验证子集；
3. 为每张图生成上述四种干预，每种至少 3 个变体；
4. 报告正确文本增益、错误文本退化、worst-of-N AbsRel，以及小区域/远距离目标误差；
5. 检查退化是否跨随机种子、文本生成器和数据集稳定存在。

只有当错误文本相对纯视觉模型造成显著且稳定退化，才进入方法开发。

### 3.2 Canary

冻结相对深度 backbone，只训练语言残差头和小型 value router。首轮不训练完整 diffusion，不追求 SOTA，只回答两个问题：

- 正确文本下，是否保留至少 80% 的原始语言增益？
- 错误/无关文本下，worst-of-N 退化是否至少降低 50%，且显著优于最强简单 gate？

若两个条件不能同时满足，则停止该方向或重新定义机制。

## 4. 正式实验矩阵

### 数据集与指标

- 室内：NYUv2、ScanNet；室外：KITTI、DIODE；零样本：ETH3D。
- 全图指标：AbsRel、RMSE、δ1。
- 鲁棒指标：corruption regret、worst-of-N AbsRel、CVaR@20%、正确文本—错误文本 Pareto 曲线。
- 区域指标：小目标 mask、被修改实体 mask、非目标区域误差泄漏。
- 校准指标：预测 $\hat v$ 与真实误差收益 $v^*$ 的 Spearman、ECE/选择性风险曲线。

### 必须击败的 killer baselines

- 纯视觉模型、原始 Iris/TR2M；
- caption dropout / classifier-free guidance strength；
- 多 caption 平均或多数集成；
- CLIP 图文相似度 gate；
- 标量 uncertainty / consistency filtering；
- 无 value supervision 的逐像素 sigmoid gate；
- 只做反事实数据增强、不做 regret 与 value routing。

### 必做消融

- 去掉 value teacher、regret、语义等价约束、稀疏约束；
- 全局 gate 对比 patch gate；
- 只路由 metric scale 对比同时路由局部 residual；
- 合成错误类型、错误强度、caption 生成器和 backbone 迁移；
- 路由器额外参数量/吞吐量等预算。

## 5. 结果解释与止损条件

- **最佳情况：** 正确文本继续提高小物体与尺度预测，错误文本下接近视觉分支下界，并且 value map 与真实收益区域对齐。这才支持“条件语言价值路由”主张。
- **普通情况：** 鲁棒性提升但正确文本收益明显下降；这可能只是保守正则化，只能算有限结果。
- **负结果：** 简单 caption dropout、CLIP gate 或 ensemble 达到相同 Pareto；或者 gate 最终几乎恒为 0。此时算法创新不足，应终止论文化。

最强反对意见是：**这只是一个鲁棒多模态 gate。** 回应它不能靠命名，而必须靠实验表明：带符号 value oracle、单边 regret 和区域化反事实干预三者缺一不可，并且能预测“何时语言真的降低深度误差”。

## 6. 算力与可复现性

- canary：冻结小型 backbone，仅缓存视觉/文本特征并训练 router，单张 A800 足够；
- 正式验证：先 TR2M/Depth Anything，再选一个 diffusion baseline；避免一开始完整重训所有模型；
- 所有 caption 干预保存为 JSONL，包含原句、变体、干预类型、实体 mask 来源和随机种子；
- 预先固定主指标、失败阈值和统计检验，不依据结果临时筛选文本。

## 7. 升级为 Paper Candidate 的必要条件

目前只能登记为 **Research Opportunity**。满足以下条件后再升级：

1. 在至少两个数据集、两个 backbone 上复现稳定的错误文本退化；
2. canary 同时保留正确文本收益并压低 worst-case regret；
3. 明显超过全部 killer baselines，而不是只超过原始模型；
4. 形成清晰伪代码和上述决策目标，且新近邻检索未发现同构方法；
5. 资源预算可在现有 A800 节点上复现。
