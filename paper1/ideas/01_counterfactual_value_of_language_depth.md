# 想法 1：CoVoL-Depth——受控描述干预下的选择性区域候选路由

## 当前结论

- **Research Opportunity，不是 Paper Candidate。**
- **这是仓库唯一主线。** Q-GeoRoute 仅在 Gate-0 否定本方向后启动。
- 任务限定为：自动图像描述出现局部、可机器验证的语义错误时，在冻结的纯视觉候选 `D0` 与图文候选 `D1` 之间逐区域选择，无收益时回退到 `D0`。
- “错误语言会损害深度”“长描述/细粒度文本”“冻结视觉骨干+语言校准”“通用 gate”均已被近邻覆盖，不作为贡献。
- 研究主张拆成两层：Claim-F 检验控制混杂后语义是否仍有增量信息；Claim-M 检验 orthogonalized、clean-constrained tail-risk router 是否优于获得相同 zC 特征和相同风险目标的 Risk-L2D-C。
- cross-fitting、orthogonal residualization、CVaR 与 clean constraint 都是标准组件，不能单独作为创新；只有 Claim-M 的 same-feature 对比通过，组合决策差异才可能成为算法贡献。

术语统一：`counterfactual` 改为 **controlled caption intervention**；`value` 仅指两个冻结候选间的 **empirical advantage**，无因果含义；`safe` 改为 **selective/fallback-aware**，不声称分布外安全保证。

## 1. 可证伪假设

1. **H-sensitivity（诊断）：** 同一 D1 的 corrupted caption 相对 clean caption 显著退化；可用 TR2M checkpoint，但不证明 fallback 必要。
2. **H-fallback-defect（正式缺陷）：** 公平独立训练并冻结的 D1 在至少一个局部错误族上比同一设置的 D0 更差，且 NYUv2/KITTI image-level regret 95% CI 下界均 >0。
3. **H-semantic / Claim-F：** C-B advantage AUROC 增量 ≥0.03 且 CI 下界 >0，同时 C-B retention–CVaR Pareto hypervolume 增量 CI 下界 >0。
4. **H-method / Claim-M：** clean gain retention ≥80%、worst-of-3 regret 降低 ≥50%，且 Main 相对 same-feature Risk-L2D-C 的 Pareto hypervolume 增量在两数据集 CI 下界均 >0。

正式依赖按 `003 → 005 → H-fallback-defect → H-semantic → H-method` 执行。H-sensitivity 可提前诊断，但不能替代公平 D0-relative defect。

## 2. 最近邻矩阵

| 最近邻 | 任务 | 候选专家 | 决策变量 | 训练监督 | 剩余差异 |
| --- | --- | --- | --- | --- | --- |
| [Language Guidance Robustness](https://arxiv.org/abs/2404.08540) | 语言引导深度鲁棒性 | 多个语言深度模型/描述 | 改变描述，无选择器 | 深度 GT | 不再贡献“错误语言有害”；需冻结候选的区域选择与尾部风险控制 |
| [Language as Prior, Vision as Calibration](https://arxiv.org/abs/2601.01457) | metric scale recovery | 文本校准包络、视觉选择 | 每图 affine calibration | inverse-depth LS oracle | 不再贡献“冻结视觉+语言校准”；需局部错误回退 |
| [CapDepth](https://arxiv.org/abs/2607.28285) | 长描述引导困难 MDE | 单个图文模型 | 动态文本编码/解码 | 深度 GT | 不再贡献长描述、语义原子或细文本筛选 |
| [Iris](../reference_papers_processed/Zeng_Iris_Integrating_Language_into_Diffusion-based_Monocular_Depth_Estimation_CVPR_2026_paper.md) | 文本条件扩散深度 | image-only/text-conditioned 变体 | 注入文本条件 | 扩散深度损失 | 已展示错误文本误导；剩余问题是可审计 fallback |
| [TR2M](../reference_papers_processed/Cui_TR2M_Transferring_Monocular_Relative_Depth_to_Metric_Depth_with_Language_CVPR_2026_paper.md) | 相对深度转 metric depth | 相对骨干、图文 scale/shift 头 | 逐像素校准图 | metric/pseudo-metric GT | 不再贡献 pixel-wise 校准；需公平冻结 D0/D1 |
| [WorDepth](https://arxiv.org/abs/2404.03635) | 文图消除尺度歧义 | 文本变分先验、图像采样器 | 选择深度样本 | 交替变分训练 | 不再贡献语言先验；需错误描述下的选择性替换 |
| [Learning to Defer](https://arxiv.org/abs/1711.06664) | 模型向专家 defer | 模型、外部专家 | 每样本预测/defer | 标签与专家行为 | `D0/D1 + advantage + gate` 已属通用范式；必须证明语义增量 |
| [SelectiveNet](https://arxiv.org/abs/1901.09192) | 覆盖率约束的选择性预测 | 预测/拒绝 | accept/reject | selective risk/coverage | 本方向是两个 dense 候选间的区域替换，仍须公平实验证明必要性 |

**审计结论：** 当前最强反对意见是“普通 two-expert learning-to-defer 已解释全部收益”。若 H-semantic 失败，删除“语言价值预测”主张，将方向降级或停止，而不是换名包装。

组件级先行工作已补入 [002 related-work audit](../steps/002_related_work_audit.md)。本研究对 cross-fitting、orthogonalization、CVaR 和 risk control 的使用一律标为直接复用或任务化改写。

## 3. 两阶段冻结协议

### 3.1 公平候选

- `D0`：冻结 DepthAnything ViT-S 相对深度骨干，加 image-only metric calibration head。
- `D1`：同一冻结骨干、相同输出分辨率和同结构 calibration head，额外读取冻结的 caption 特征。
- 两个 head 独立训练、独立保存、无共享可训练参数；数据、mask、优化器、步数和种子相同。
- image/fusion adapters 的可训练参数量控制在 ±10%；`D1` 只看 clean 自动 caption 和正式训练集，不能看 router 数据或结构化错误；`D0` 永不读 caption。
- 先冻结并记录两个 checkpoint 的 SHA256，再缓存 `D0/D1/Delta/mask/features`；router 只能读取缓存。测试必须确认 expert 梯度均为 `None` 且重复缓存逐元素一致。

### 3.2 仓库自有实现路线

上游固定为 `BeileiCui/TR2M@a45925862bcd76c84ac38c6fc98da1e187f1146e`。截至 2026-08-21，该仓库只释放评测代码和权重，README 仍声明训练代码待发布。因此：

- 发布 checkpoint 只用于 H-sensitivity；
- 禁止用替换/置空文本冒充独立训练的 `D0`；
- 不再等待上游训练代码；Step 005 直接实现 shared frozen DepthAnything backbone 与两个独立同构 metric heads；
- H-fallback-defect 前必须完成 checkpoint/cache SHA、参数匹配和冻结梯度测试；
- 本地环境尚无 PyTorch，因此 GPU 模型实现是下一原子动作，但研究路线不再依赖外部发布日期。

## 4. 唯一区域 oracle

图像按归一化坐标划分为 `16×16` 不重叠网格。第 `(i,j)` 个 cell 使用半开边界
`[floor(iH/16),floor((i+1)H/16)) × [floor(jW/16),floor((j+1)W/16))`，末行/列吸收余数。先应用官方 crop 和有效深度 mask；cell 至少有 32 个有效像素且有效率 ≥50% 才参与训练。

区域损失固定为有效像素 mean AbsRel：

$$
\ell_p(D,D^*)=\frac{1}{|M_p|}\sum_{u\in M_p}
\frac{|D_u-D_u^*|}{\max(D_u^*,10^{-3})},
\qquad
a_p=\ell_p(D_0,D^*)-\ell_p(D_1,D^*).
$$

`a_p>0` 表示采用 `D1` 更好。测试期 gate 在 dev 集预注册阈值后二值化，以 nearest-neighbor 上采样：

$$
\log \hat D_u=(1-g_u)\log D_{0,u}+g_u\log D_{1,u}.
$$

统计单位只能是图像/场景，不能把 patch 当独立样本。`a_p≈0` 不直接二值化：tie band 由重复 cache 数值差与有效 mask 1-pixel erosion 的 95 分位共同确定；连续 advantage regression 是主诊断。

16×16 hard-nearest 只作为 canary。正式保留 region claim 前必须比较 global、8×8、16×16、32×32 以及 hard-nearest/soft-bilinear，并报告 target mask、5-pixel boundary band、非目标区域 AbsRel 与 depth-gradient discontinuity。

## 5. 候选算法：交叉拟合的语义增量优势

设置三个嵌套预测器：

- A：视觉难度与 D0 uncertainty；
- B：A 加 `D0-D1`、residual norm 和候选置信度；
- C：B 加文本—区域语义特征。

唯一实现固定为 5-fold scene-group cross-fitting，详见 [Step 006](../steps/006_semantic_incrementality_gate.md)。每个 outer fold 内再按 scene hash 分 fold-fit/fold-validation；scaler、feature selection 和 20 个 trial 不能读取 fold-test。最小算法：

1. 在折外样本估计 nuisance advantage `m_p=E[a_p|z_B]`；
2. 形成不参与自身拟合的残差 `r_p=a_p-m_p`；
3. semantic branch 只用新增语义特征预测 `r_p`；
4. 最终分数 `s_p=m_p+ŝ_p`，在 dev 集校准 gate。

这不是已成立的贡献。只有 C-B 同时通过分类增量与策略 hypervolume 增量，才能支持 Claim-F；只有 Main 进一步优于 same-feature Risk-L2D-C，才能支持 Claim-M。

删除用 `L_sparse` 防止全关门的设计。预注册 clean gain retention：

$$
G_{clean}=
\frac{R(D_0)-R(\hat D_{clean})}
{\max(R(D_0)-R(D_{1,clean}),10^{-6})}\ge\kappa,\quad\kappa=0.80.
$$

用 primal-dual 优化 advantage loss 与 corrupted regret 的 `CVaR@20%`，并满足上式约束。`κ` 不得看测试结果后修改。只有 paired clean D1-D0 gain 的 bootstrap 95% CI 下界 >0 才计算 retention，否则输出 `STOP_NO_CLEAN_GAIN`。唯一聚合公式见 [metrics spec](../steps/metrics_spec.md)。

## 6. 数据、基线与统计

- NYUv2/KITTI 各从 **official training pool** 按 scene hash 固定 500 张，并各分 300 train / 100 dev / 100 internal-test；构建器必须断言与 official benchmark test 的 image/scene 交集为 0。
- 同图像配对 verified-clean、未经编辑但机器检查失败的 natural error、structured local error、deletion/null；随机/全局错配仅作诊断。
- scene/image 不跨 split；template、captioner、替换词表和至少一个 error family 在 test 留出；自然错误与合成干预分开报告。
- natural `entity_absence` 只对 declared-exhaustive classes 启用，并要求两个独立 detector/segmenter 都未检出；否则标为 `unverified_mention`。predicate precision <0.95 自动禁用。
- 详细协议见 [003_intervention_dataset.md](../steps/003_intervention_dataset.md)。

heuristic baselines（always-D0/D1、oracle、CLIP、uncertainty、`|D1-D0|`）保留原始零参数实现，不做参数匹配。learned gates 才匹配 Main 的参数量 ±10%、训练步数、3 seeds 和 20-trial 搜索预算。必须新增：

- L2D-B：读取 zB；
- L2D-C：读取与 Main 完全相同的 zC；
- Risk-L2D-C：读取相同 zC，并使用相同 clean constraint + CVaR objective，但不做 orthogonalized residual routing。

机器可读公平契约见 [baseline contract](../configs/covol/baseline_contract.yaml)。

专家/router 主实验种子为 `17/29/43`，predictability probe 为 `17/29/43/71/101`。所有风险先在每图内部聚合 caption variants，再跨图像统计；报告 image-level 10,000 次 paired bootstrap 95% CI、AbsRel、δ1、region AbsRel、clean gain retention、mean regret、worst-of-3、CVaR@20%、coverage、Pareto hypervolume、AUROC/AUPRC/Spearman、参数量、显存与分模块 latency。

## 7. 决策门禁

### 升级为 Paper Candidate

必须同时满足 H-fallback-defect、Claim-F、Claim-M；第二个 backbone 复现结论；natural-error predicate 有足够 verified 样本；最新近邻未发现同构方法。

### 停止或降级

- 缺陷不能跨两数据集稳定复现；
- B 已解释全部优势；
- L2D-C 或 Risk-L2D-C 达到相同 Pareto；
- gate 近乎恒为 0，clean gain 约束无法满足；
- 收益仅来自模板化错误，在未见 captioner/error family 上消失。

## 8. Assumptions

1. D0/D1 可公平独立训练并在冻结后稳定。
2. caption 的实体/远近错误能程序化验证。
3. clean D1 相对 D0 有非平凡正增益。
4. 16×16 网格能近似局部收益。
5. held-out captioner/error family 能检验模板外泛化。
6. captioner 成本可离线摊销，但必须单列报告。

## 9. Threats to Validity

1. 机器规则无法覆盖全部自然 hallucination。
2. GT depth 只在训练/分析可用，部署时不可得。
3. 候选质量/容量差异可能伪装成语义价值。
4. 网格尺度与 hard upsampling 会改变 label 噪声并制造边界断裂，必须做 granularity/upsampling/boundary ablation。
5. NYUv2/KITTI 不能支持普适安全结论。
6. 分布外错误无逐样本非退化保证。
7. 双候选会增加延迟，本方向不应伪称效率方法。

## 10. 下一步唯一动作

先用已实现的 `build_image_manifest.py` 生成 official-train 内部 split/audit，再执行 `005 → 004-B → 006 → 007 → 008`。在 Claim-F 和 Claim-M 分别得到证据前，不扩展 Iris/Marigold、不启动 Q-GeoRoute，也不进入 Paper Build。
