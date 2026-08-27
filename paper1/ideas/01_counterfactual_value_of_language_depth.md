# 想法 1：CoVoL-Depth——受控描述干预下的选择性区域候选路由

## 当前结论

- **`STOPPED_BY_H_SENSITIVITY_CONTROL`，不是活跃 Research Opportunity，更不是 Paper Candidate。**
- **停止证据：** 004-A 的两个冲突族有正向 region AbsRel sensitivity，但 semantic-preserving 对照也稳定退化，95% CI `[0.000579, 0.001777]` 不包含 0；预注册的冲突特异性 Gate-0 因此失败。
- **不再继续本方向。** 第二数据集审计、正式 D0/D1、Claim-F、Claim-M 与 Main-PR 均停止。Q-GeoRoute 仍为 PARKED，只有另行更新范围锁、最近邻和 Research Opportunity Gate 后才能成为新主线。
- 任务限定为：自动图像描述出现局部、可机器验证的语义错误时，在冻结的纯视觉候选 `D0` 与图文候选 `D1` 之间逐区域选择，无收益时回退到 `D0`。
- “错误语言会损害深度”“长描述/细粒度文本”“冻结视觉骨干+语言校准”“通用 gate”均已被近邻覆盖，不作为贡献。
- 研究主张拆成两层：Claim-F 用固定宽度 direct/两类 permuted controls 检验语义是否有增量信息；Claim-M 检验固定 clean utility 下的局部 tail-regret router 是否优于获得相同 OOF experts 与合法 zC 特征的 direct defer baselines。
- cross-fitting、partial residualization、CVaR 与 clean constraint 都是标准组件，不能单独作为创新；TIGER 也已覆盖语言指令、冻结专家、dense routing 与 expert-exclusion contribution target。只有 Claim-M 的 same-feature、faithful/matched 对比通过，任务专属决策差异才可能成为算法贡献。

术语统一：`counterfactual` 改为 **controlled caption intervention**；`value` 仅指两个冻结候选间的 **empirical advantage**，无因果含义；`safe` 改为 **selective/fallback-aware**，不声称分布外安全保证。

## 1. 可证伪假设

1. **H-sensitivity（诊断）：`STOP_H_SENSITIVITY`。** local entity conflict 与 depth relation conflict 的 region AbsRel degradation CI 下界大于 0，但 semantic-preserving 对照 CI 不含 0，故结果不具冲突特异性，也不证明 fallback 必要。
2. **H-fallback-defect（正式缺陷）：** OOF 公平训练并冻结的 D1 在至少一个局部错误族上比同一设置的 D0 更差；原 NYUv2+当前 KITTI source 分支已 STOP，只有新的两个真实数据集 Step003 authorization PASS 后才能判定。Virtual KITTI 2 只作 synthetic structured auxiliary stress test。
3. **H-semantic / Claim-F：** `C-direct−B-direct` 与 `C-direct−C-permuted-global/local` 在同一 dev-retention LCB constrained operating point 上的 CVaR/WorstOf3 逐 seed cluster-CI 均通过；Main-PR 不参与，hypervolume 只作 secondary。
4. **H-method / Claim-M：** 每 seed 在 dev 只从 clean-gain retention one-sided 95% LCB ≥80% 的 thresholds 中选最低 cluster-balanced CVaR；internal-test 上 Main-PR 相对全部 direct killers 的 `CVaR/WorstOf3@Dev-Ret≥0.80` 风险差逐 seed cluster-CI 均同向为负；HV 仅作 secondary。

原正式依赖链已被 H-sensitivity 上游门禁停止。以下方法、基线和统计设计只作为预注册记录保留，不授权继续执行。

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
| [MRUF](https://arxiv.org/abs/2607.10599) | 多模态可靠性路由 | modality/subspace 分支 | leave-one-out contribution + uncertainty gate | error increase、uncertainty、alignment | 经验贡献教师与多粒度路由已覆盖，必须作为 direct baseline |
| [DeferredSeg](https://arxiv.org/abs/2604.12411) | dense segmentation defer | base model/人类及多专家 | pixel-wise route + spatial coherence | collaboration surrogate | 区域 defer 与空间一致性已覆盖，不能作为 novelty |
| [Regression Multi-Expert Deferral](https://arxiv.org/abs/2403.19494) | 连续回归 defer | predictor/multiple experts | single/two-stage defer | H-consistent bounded-loss surrogate | 连续 advantage/defer 已覆盖，必须实现 two-stage baseline |
| [Density-Ratio Post-Hoc L2D](https://arxiv.org/abs/2605.19557) | 冻结专家 post-hoc defer | frozen model/expert | density-ratio scorer + threshold | DR CPE loss | 冻结候选后处理已覆盖，必须实现 post-hoc baseline |
| [TIGER](https://arxiv.org/abs/2606.15765) | 异构冻结 VFM 的多任务 dense prediction | CLIP/DINOv2/SAM/OWLv2 features | natural-language task instruction + token routing | expert-exclusion loss change | 语言条件、冻结专家、dense contribution routing 已覆盖；剩余边界只能是同任务双候选的 clean-utility/tail-regret 决策 |

**审计结论：** 当前最强反对意见是“direct regression/dense/post-hoc/LOO routers 与 robust single-expert training 已解释全部收益”。若 H-semantic 失败，删除“语言价值预测”主张；若 Claim-M 未击败这些 killers，撤回算法论文路径，而不是换名包装。

组件级先行工作已补入 [002 related-work audit](../steps/002_related_work_audit.md)。本研究对 cross-fitting、partial residualization、CVaR 和 risk control 的使用一律标为直接复用或任务化改写；不存在可复核的正交 score，故不使用 orthogonalized 表述。

## 3. OOF 冻结协议

### 3.1 公平候选

- `D0`：冻结 DepthAnything ViT-S 骨干，读取 frozen image-global/multi-scale features；text channel 使用固定非零 learned-null embedding，并经过与 D1 完全相同的 adapter 路径。
- `D1`：读取完全相同的 frozen image-global/multi-scale features；唯一变化是 text channel 读取冻结 caption embedding。
- 两个 head 独立训练、独立保存、无共享可训练参数；数据、mask、优化器、步数和种子相同。
- 对应层、初始化 seed、参数量和 FiLM 位置逐项一致；`D1` 只看 predicate-clean 自动 caption，`D0` 对 caption permutation 逐元素不变。
- 先冻结并记录两个 checkpoint 的 SHA256，再缓存 `D0/D1/Delta/mask/features`；router 只能读取缓存。测试必须确认 expert 梯度均为 `None` 且重复缓存逐元素一致。
- router-train 使用 5-fold sequence/drive-cluster OOF experts；每个 fold 的 experts 排除该 fold 全部近邻帧后训练。dev/internal-test 由只在非 dev/internal-test clusters 上训练的 final experts 预测。
- 两个 image-only twin heads 与 shuffled-caption D1 作为负控制，排除随机 expert diversity。

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

Claim-F 固定四个同算法 controls：固定宽度 `B-direct([zB,0,mask=0])`、`C-direct([zB,semantic,mask=1])`、跨 cluster length/scene 匹配的 `C-permuted-global` 和只错配局部实体/关系的 `C-permuted-local`。四者第一层、模型、参数量、standard objective 和 trials 完全相同，只改变语义信息。Main-PR 不参加 Claim-F。

Main-PR 唯一实现固定为 outer 5-fold + inner 4-fold sequence/drive-cluster cross-fitting，详见 [Step 006](../steps/006_semantic_incrementality_gate.md) 与 [唯一目标规范](../steps/014_objective_and_algorithm_spec.md)。inner folds 为每个 outer-train 样本产生未见本样本的 nuisance OOF prediction；trial 以跨 outer-validation 平均 rank 最小选择。最小算法：

1. 在折外样本估计 nuisance advantage `m_p=E[a_p|z_B]`；
2. 形成不参与自身拟合的残差 `r_p=a_p-m_p`；
3. semantic branch 只用新增语义特征预测 `r_p`；
4. 最终分数 `s_p=m_p+ŝ_p`，在 dev 集校准 gate。

这不是已成立的贡献，也不是正交学习。只有 C-direct 同时超过 B-direct 与两类 C-permuted，才能支持 Claim-F；只有 Main-PR 进一步超过全部 direct baselines，才能支持 Claim-M。

删除用 `L_sparse` 防止全关门的设计。预注册 clean gain retention：

$$
G_{clean}=
\frac{R(D_0)-R(\hat D_{clean})}
{R(D_0)-R(D_{1,clean})}\ge\kappa,\quad\kappa=0.80.
$$

用 primal-dual 优化 partial-residual loss 与 corrupted regret 的 `CVaR@20%`，并满足上式约束。`κ` 不得看测试结果后修改。只有 paired clean D1-D0 gain 的 bootstrap 95% CI 下界 >0 且超过预注册 `δ_clean` 才计算 retention；invalid bootstrap replicate 比例超过 5% 输出 `STOP_UNSTABLE_CLEAN_GAIN`。唯一聚合与更新公式见 [objective spec](../steps/014_objective_and_algorithm_spec.md) 和 [metrics spec](../steps/metrics_spec.md)。

## 6. 数据、基线与统计

- NYUv2/KITTI 各从 **official training pool** 按 scene–sequence connected component 固定 500 张，并各分 300 train / 100 dev / 100 internal-test；Step 003 不读取 official benchmark test，完整 test integrity audit 只允许 Step 008 显式解锁。
- 同图像配对 predicate-clean、未经编辑但机器检查失败的 natural error 与 structured local error；null_diagnostic 和随机/全局错配只作独立诊断，不进入 local CVaR。
- scene/image 不跨 split；template、captioner、替换词表和至少一个 error family 在 test 留出；自然错误与合成干预分开报告。
- natural `entity_absence` 只对 declared-exhaustive classes 启用，并要求两个独立 detector/segmenter 都未检出；否则标为 `unverified_mention`。predicate precision <0.95 自动禁用。
- 详细协议见 [003_intervention_dataset.md](../steps/003_intervention_dataset.md)。

heuristic baselines（always-D0/D1、oracle、CLIP、uncertainty、`|D1-D0|`）保留原始零参数实现，不做参数匹配。learned published gates 同时报告 faithful 与 capacity-matched 两版；±10% 只约束 matched 版，不能裁剪 faithful 公式。所有 learned gates 共享训练步数、3 seeds 和 20-trial 搜索预算。必须新增：

- L2D-B：读取 zB；
- L2D-C：读取与 Main 完全相同的 zC；
- Risk-L2D-C：读取相同 zC，并使用相同 clean constraint + CVaR objective，但不做 cross-fitted partial residual routing；
- Regression-L2D、DR-PostHoc-L2D、Dense-Coherence-L2D、LOO-Uncertainty-Router：分别对应连续回归 defer、density-ratio post-hoc、dense spatial coherence 和 leave-one-out contribution routing；
- robust expert killers：caption dropout、corruption augmentation、three-caption ensemble、image-caption consistency filtering；
- artifact controls：text-only classifier 与 frozen VLM grounding scorer。

机器可读公平契约见 [baseline contract](../configs/covol/baseline_contract.yaml)。

专家/router 主实验种子为 `17/29/43`，predictability probe 为 `17/29/43/71/101`。所有风险先在每图内部聚合 caption variants，再按 scene/drive 做 10,000 次 paired cluster bootstrap；每个 replicate 重算 clean denominator、retention、CVaR、Pareto 与 HV。报告独立 cluster 数，不能用 patch/image 数夸大显著性。

## 7. 决策门禁

### 升级为 Paper Candidate

当前不能升级。H-sensitivity 的 semantic-preserving 控制条件已经失败，因此不再执行 H-fallback-defect、Claim-F 或 Claim-M。

### 停止或降级

- 缺陷不能跨两数据集稳定复现；
- B 已解释全部优势；
- 任一 direct defer 或 robust single-expert baseline 达到/支配相同 Pareto；
- gate 近乎恒为 0，clean gain 约束无法满足；
- 收益仅来自模板化错误，在未见 captioner/error family 上消失。

## 8. Assumptions

1. D0/D1 可在相同视觉输入、同构 text channel 和 OOF stacking 下稳定训练。
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

## 10. 停止后的动作边界

保留 004-A 的逐行负结果、权重哈希和协议，停止 CoVoL 的数据恢复与模型实验。下一研究动作不是调参或删除失败对照，而是重新做至多五个 Research Opportunities 的文献缺口、最小缺陷 probe 与算法路径审计；选择新主线前必须更新 [001 范围锁](../steps/001_primary_scope_lock.md)。
