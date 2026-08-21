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

## 由原始论文确认的覆盖边界

1. `arXiv:2404.08540` 已系统研究描述粒度、定向攻击和分布偏移；“语言可能损害深度”只能作为动机。
2. `arXiv:2601.01457` 已在冻结相对深度 backbone 与冻结 CLIP text encoder 下，用语言预测校准参数包络、视觉选择校准，并以闭式最小二乘 oracle 监督；“冻结视觉+语言校准”不能作为新颖性。
3. CapDepth 已使用详细长 caption、progressive masked attention 和 text-adaptive decoder；“语义原子/细粒度文本筛选”不能作为新颖性。
4. TR2M 已输出 pixel-wise scale/shift maps；“局部语言校准”本身不能作为新颖性。
5. Learning-to-defer 与 SelectiveNet 使 `D0/D1 + advantage + gate/coverage` 成为必须击败的范式，而不是默认贡献。

## 当前唯一可测试的差异

| 待验证主张 | 必要实验 | 失败后处理 |
| --- | --- | --- |
| 文本—区域语义有超出视觉难度和候选差异的增量预测力 | A/B/C nested probe；匹配分箱；C-B AUROC 与 paired CI | 删除语义机制主张 |
| 交叉拟合 nuisance-residual 比普通 advantage gate 更可靠 | 与 B predictor、standard L2D 同缓存同容量对比 | 删除 cross-fitting 贡献 |
| clean-gain 约束的 CVaR 优化形成更优 Pareto | retention–CVaR Pareto、3 seeds、两数据集 CI | 降级为普通正则化或停止 |
| region replacement 有必要 | global vs 8×8/16×16/32×32；局部错误 mask | 若 global 相同则删除区域机制 |

## 实现可用性审计

- TR2M 研究代码版本锁为 [`a45925862bcd76c84ac38c6fc98da1e187f1146e`](https://github.com/BeileiCui/TR2M/commit/a45925862bcd76c84ac38c6fc98da1e187f1146e)。
- 当前上游 README 提供评测脚本、数据 split、文本和 checkpoint，但写明训练代码尚待发布。因此发布版可用于缺陷复现，不能直接满足公平独立训练 `D0/D1` 的要求。
- H-semantic 开始前必须完成自有 calibration-head 复现与 sanity check，或将基线替换为能够独立训练两个候选的公开实现。

## 审计决策

- 主线保留为 Research Opportunity。
- 不主张“首次发现错误文本危害”“首次细粒度 caption 深度”“首次冻结视觉语言校准”或“首次 advantage gate”。
- 最近邻审计在第一次 GPU 实验前、Paper Candidate Gate 前各重跑一次；发现同构方法时立即更新 `001_primary_scope_lock.md` 并重新判定。
