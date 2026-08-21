# 002 Related Work Audit

审计日期：2026-08-21。该文件记录“哪些主张已被近邻覆盖”和“剩余差异必须由什么实验支持”，不把文献差异直接等同于方法新颖性。

## 最近邻矩阵

| 工作 | 任务 | 候选专家 | 决策变量 | 训练监督 | 本研究剩余差异 |
| --- | --- | --- | --- | --- | --- |
| [On the Robustness of Language Guidance for Low-Level Vision Tasks](https://arxiv.org/abs/2404.08540) | 测量语言引导 MDE 的泛化、描述粒度与攻击鲁棒性 | 多个语言深度模型/描述条件 | 受控改变描述，无候选路由 | 深度 GT 与鲁棒性评估 | 错误语言危害已知；需学习冻结候选间的局部替换并控制 regret |
| [Language as Prior, Vision as Calibration](https://arxiv.org/abs/2601.01457) | 冻结相对深度模型的 metric scale recovery | 文本给出校准包络，视觉选择包络内参数 | image-specific inverse-depth affine calibration | closed-form least-squares oracle | 冻结视觉和语言校准已知；需对局部错误选择性回退 |
| [CapDepth](https://arxiv.org/abs/2607.28285) | 长 caption 引导非朗伯表面/恶劣天气 MDE | 单一图文深度模型 | progressive masked text attention 与 text-adaptive decoder | 深度 GT | 细粒度 caption 编码已知；需经验优势预测而非更强文本融合 |
| [Iris: Integrating Language into Diffusion MDE](../reference_papers_processed/Zeng_Iris_Integrating_Language_into_Diffusion-based_Monocular_Depth_Estimation_CVPR_2026_paper.md) | 文本条件扩散深度 | image-only 与 text-conditioned 变体 | 文本条件注入 | diffusion depth loss | 论文已展示 wrong-text 误导；需冻结候选与可审计 fallback |
| [TR2M](https://arxiv.org/abs/2506.13387) | 相对深度到 metric depth | relative-depth backbone 与图文 scale/shift maps | pixel-wise rescale maps | metric/pseudo metric depth、对比损失 | pixel-wise 图文校准已知；需公平 D0/D1、区域选择与 regret |
| [WorDepth](https://arxiv.org/abs/2404.03635) | 文图联合消除 metric scale 歧义 | 文本变分先验、图像条件 sampler | 从语言先验选深度 | alternating variational training | 语言先验已知；需错误 caption 下的候选替换 |
| [Predict Responsibly / Learning to Defer](https://arxiv.org/abs/1711.06664) | 模型向外部专家 defer | 自动模型与外部专家 | 每样本预测或 defer | GT 与专家行为 | 两专家 advantage gate 是已知范式；必须证明语义增量与新风险 Pareto |
| [SelectiveNet](https://arxiv.org/abs/1901.09192) | coverage 约束的选择性预测 | 模型输出与 reject | accept/reject | selective risk 与 coverage | 拒绝已知；本方向需证明 dense region candidate replacement 的额外价值 |

## 直接算法近邻

| 工作 | 任务 | 预测粒度 | 专家是否冻结 | 贡献/优势教师 | 损失类型 | 本研究剩余边界 |
| --- | --- | --- | --- | --- | --- | --- |
| [TIGER](https://arxiv.org/abs/2606.15765) | 多任务 dense prediction 的异构 VFM 协作 | shared token grid 上的 token-level expert weights | 是，CLIP/DINOv2/SAM/OWLv2 均冻结 | 移除每个 expert 后的 task-loss 变化 | task loss + counterfactual contribution alignment | language task instruction、frozen experts、dense routing 与 expert-exclusion target 均已覆盖；本研究只能检验同任务双候选在固定 clean utility 下的局部尾部 regret 决策 |
| [MRUF](https://arxiv.org/abs/2607.10599) | 鲁棒多模态情感分析 | subspace 与 modality/utterance 多粒度 | 非冻结候选后处理设定 | leave-one-out error increase + modality uncertainty | routing、inverse-variance calibration、contrastive alignment | leave-one-out 经验贡献教师和多粒度可靠性路由已知；只能作为直接 baseline |
| [DeferredSeg](https://arxiv.org/abs/2604.12411) | 模型与人类专家的医学分割 defer | pixel-wise dense regions | 不是本研究的冻结双模型设定 | base/expert discrepancy | pixel-wise collaboration surrogate + spatial-coherence + load balance | dense defer、空间一致性与多专家路由已知；区域 gate 不构成创新 |
| [Regression with Multi-Expert Deferral](https://arxiv.org/abs/2403.19494) | 连续回归向多个专家 defer | instance-level continuous regression | two-stage 支持 pre-trained predictor | bounded regression loss 与 expert cost | single/two-stage H-consistent surrogate | 连续 advantage/defer 已知；必须实现其 two-stage surrogate 对照 |
| [Density-Ratio Losses for Post-Hoc L2D](https://arxiv.org/abs/2605.19557) | 冻结 model/expert 的 post-hoc defer | instance-level thresholded scorer | 是，post-hoc | model/expert ideal-distribution density ratio | DR class-probability-estimation loss | 冻结候选后处理与可调 threshold 已知；必须实现 density-ratio 对照 |

## 六个直接机制的八维对照

`✓` 表示原方法核心或本方案预注册组件；`—` 表示不是其主要机制。Main-PR 各组件仍为 `UNVERIFIED`，不能由矩阵直接推出新颖性。

| 工作 | 冻结 experts | 语言指令/条件 | token/region routing | expert-exclusion target | clean utility 约束 | 上尾 regret | 同任务候选替换 | 本研究角色 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| TIGER | ✓ | task instruction | token | ✓ | — | — | —；异构 feature fusion | faithful/matched direct baseline |
| MRUF | 部分 | modality context | utterance/subspace | ✓ | — | uncertainty-weighted | — | LOO-uncertainty baseline |
| DeferredSeg | model+human | — | pixel | discrepancy | load balance | — | segmentation defer | dense-coherence baseline |
| Regression-L2D | 可 two-stage 冻结 | — | instance | bounded expert cost | — | — | continuous prediction/expert | faithful/matched regression baseline |
| DR-PostHoc-L2D | ✓ | — | instance threshold | density ratio | — | — | frozen model/expert | faithful/matched post-hoc baseline |
| Main-PR | ✓ | caption-region content | region | empirical D1-D0 advantage；非新颖 | retention `>=0.80` | CVaR@20% | 同任务 D0/D1 | 待否证候选 |

## 组件级先行工作

下表专门审计本方案所用统计和风险优化组件。`直接复用` 表示不得单独作为新颖性；`任务化改写` 表示只改变了数据单位、约束或评测对象；`本研究新增` 仅表示仍待实验否证的组合差异，不表示已经成立。

| 组件级工作 | 已覆盖内容 | 本研究使用方式 | 边界判定 |
| --- | --- | --- | --- |
| [Double/Debiased Machine Learning](https://arxiv.org/abs/1608.00060) | orthogonal score、sample splitting 与 K-fold cross-fitting | 仅借用 sample splitting/cross-fitting 形成场景分组 OOF partial residual | cross-fitting 直接复用；本研究没有 Neyman-orthogonal score，不继承 DML 理论 |
| [Orthogonal Statistical Learning](https://arxiv.org/abs/1901.09036) | 两阶段 nuisance estimation 与正交损失下的泛化分析 | 仅作为“为何要隔离 nuisance 拟合”的启发来源 | 当前损失不是正交损失；不得把 Main-PR 称为 orthogonal learning |
| [Optimization of Conditional Value-at-Risk](https://doi.org/10.21314/JOR.2000.038) | CVaR 的尾部风险定义与优化形式 | 在先按 caption variants 聚合得到的图像级风险上优化 CVaR@20% | CVaR 直接复用；image-level 聚合和 clean-gain 约束是任务化改写 |
| [Learn then Test](https://arxiv.org/abs/2110.01052) | 对候选规则进行有限样本风险控制和多重检验 | 用固定 coverage 网格审计选择策略，而不声称逐样本安全保证 | 风险控制思想直接复用；当前方案尚未提供其同等级有限样本保证 |
| [Conformal Selective Prediction with General Risk Control](https://arxiv.org/abs/2603.24704) | 一般风险下的选择性预测与校准 | 作为 risk-aware selective prediction 的近期强对照边界 | 选择性风险控制不是本研究新颖性；若采用其保证，必须单列实现与假设 |

## 由原始论文确认的覆盖边界

1. `arXiv:2404.08540` 已系统研究描述粒度、定向攻击和分布偏移；“语言可能损害深度”只能作为动机。
2. `arXiv:2601.01457` 已在冻结相对深度 backbone 与冻结 CLIP text encoder 下，用语言预测校准参数包络、视觉选择校准，并以闭式最小二乘 oracle 监督；“冻结视觉+语言校准”不能作为新颖性。
3. CapDepth 已使用详细长 caption、progressive masked attention 和 text-adaptive decoder；“语义原子/细粒度文本筛选”不能作为新颖性。
4. TR2M 已输出 pixel-wise scale/shift maps；“局部语言校准”本身不能作为新颖性。
5. Learning-to-defer 与 SelectiveNet 使 `D0/D1 + advantage + gate/coverage` 成为必须击败的范式，而不是默认贡献。
6. MRUF 已用 leave-one-out error increase 监督 modality routing，并以 uncertainty 校准 gate；“经验贡献教师”不能作为新颖性。
7. DeferredSeg 已实现 pixel-wise dense defer 与 spatial-coherence routing；“区域 defer”不能作为新颖性。
8. Regression with Multi-Expert Deferral 已覆盖 bounded continuous loss 下的 single/two-stage defer；“连续 advantage defer”不能作为新颖性。
9. Density-Ratio Post-Hoc L2D 已覆盖冻结 model/expert 的 scorer 与可调 threshold；“冻结专家后处理”不能作为新颖性。
10. TIGER 已覆盖自然语言 task instruction、冻结异构 VFM、token-level dense routing 与 expert-exclusion contribution alignment；这些机制全部不能作为本研究新颖性。

## 当前仅剩的可测试差异

| 待验证主张 | 必要实验 | 失败后处理 |
| --- | --- | --- |
| Claim-F：文本—区域语义在控制视觉难度和候选差异后仍有任务有效的增量预测力 | 同模型/同目标 `C-direct−B-direct` 与 `C-direct−C-permuted`；AUROC/HV scene-cluster CI | 任一门禁失败即删除语义增量主张 |
| Claim-M：固定 clean utility 下的局部尾部 regret 决策优于相同输入和风险目标的标准方法 | Main-PR 必须同时击败 Risk-L2D-C、TIGER-style LOO、regression surrogate、density-ratio、dense-coherence 和 LOO-uncertainty；主判据为 dev-frozen `CVaR/WorstOf3@Retention>=0.80` | 任一直接方法差值 CI 下界不大于 0 时删除算法贡献，仅保留 Claim-F（若成立） |
| region replacement 有必要 | global vs 8×8/16×16/32×32；局部错误 mask | 若 global 相同则删除区域机制 |

cross-fitting、partial residualization、CVaR、coverage control、dense defer、leave-one-out contribution teacher、language-guided frozen-expert routing、continuous regression defer 和 frozen-expert post-hoc scoring 均不再作为独立贡献。唯一可能的方法贡献是固定 clean utility 下的同任务双候选局部尾部 regret 决策同时击败全部 faithful/matched direct baselines；这必须由步骤 007/008 支持。

## 实现可用性审计

- TR2M 研究代码版本锁为 [`a45925862bcd76c84ac38c6fc98da1e187f1146e`](https://github.com/BeileiCui/TR2M/commit/a45925862bcd76c84ac38c6fc98da1e187f1146e)。
- 当前上游 README 提供评测脚本、数据 split、文本和 checkpoint，但写明训练代码尚待发布。因此发布版只用于 `H-sensitivity` 诊断，不能满足正式 `H-fallback-defect` 所需的公平独立 `D0/D1`。
- 不再等待 TR2M 训练代码。步骤 005 已锁定仓库自有 shared-backbone dual-head 路线；完成两个候选的训练、哈希和 smoke test 后，才允许运行 `H-fallback-defect` 与 H-semantic。

## 审计决策

- 主线保留为 Research Opportunity。
- 不主张“首次发现错误文本危害”“首次细粒度 caption 深度”“首次冻结视觉语言校准”或“首次 advantage gate”。
- 不把 cross-fitting、partial residualization、CVaR 或 selective risk control 单独列为贡献，也不使用未定义的 orthogonalization 表述。
- TIGER 已使“语言条件 + 冻结 experts + dense contribution routing”失去新颖空间；若 `014_objective_and_algorithm_spec.md` 的 clean-utility/tail-regret 差异不能在 direct baselines 上得到证据，Claim-M 降为 `ANALYSIS-ONLY`。
- 不把区域 defer、经验误差贡献教师、连续 advantage defer 或冻结专家 post-hoc routing 列为贡献。
- Claim-F 与 Claim-M 必须分开判定；H-semantic 通过不自动支持算法新颖性。
- 最近邻审计在第一次 GPU 实验前、Paper Candidate Gate 前各重跑一次；发现同构方法时立即更新 `001_primary_scope_lock.md` 并重新判定。
