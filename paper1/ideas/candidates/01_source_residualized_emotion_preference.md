# Candidate 01: Source-Residualized Video-Grounded Emotion Preference (SR-VEP)

状态：`SELECTED_RESEARCH_OPPORTUNITY / DEFECT_CANARY_PENDING / NOT_PAPER_CANDIDATE`。

## 问题

EmoPrefer/MER-Prefer 以“视频与两条情绪描述”为输入，预测人类偏好。但 2026 shortcut audit 报告：只用描述长度和生成器身份的逻辑回归在 EmoPrefer-V2 上达到 65.8 WAF，接近 LoRA 7B text/audio-visual judge 的 66.8；描述文本以 99.5% 准确率泄漏生成器身份，每个 pair 又恰好来自不同生成器。于是普通 Bradley–Terry/DPO 可能通过生成器风格先验获得高分，而没有核对描述与视频中的情绪证据。

该缺陷必须先在官方 annotation tables 上独立复现。现阶段不声称仓库已证实这些外部数字，也不把 benchmark confound 写成算法贡献。

## 最近邻与未覆盖边界

- EmoPrefer (ICLR 2026) 定义数据与 MLLM judge，但没有消除 generator-source confounding。
- Style over Substance (2026-07) 提供 content-blind、ODIN 与 counter-stereotypical 审计；其结论是普通 decorrelation 后 content head 接近 chance，主要给出数据侧建议，没有提供下述 same-generator video-matching 识别机制。
- EAPO (2026-08) 用 emotion-aware 错误增强、多 judge 与 margin-calibrated fusion 改善偏好可靠性，但没有显式隔离生成器风格先验。
- MJ1 (2026) 用 grounded verification chain 与位置反事实奖励训练通用 multimodal judge；它针对 position/visual grounding，不识别 EmoPrefer 的 generator-pair confound。
- Perception-Judge (2026) 用 perceptual perturbation 与 GRPO 纠正 fluent-text anchoring，但没有 source-residualized pairwise emotion preference estimand。
- AVERE/AVEm-DPO 与 ACPO 分别改善 audiovisual emotion reasoning 和 audio grounding；它们不解决人类 preference label 与 generator identity 的共变。

最近邻可能迅速变化，尤其 EAPO 只早于本门禁两天。任何直接实现“same-generator matched video negatives + cross-fitted source residual + worst-source-pair preference optimization”的新工作都会使本方向停止或重新定义。

## 可证伪算法路径

对视频 `v_i`、候选描述 `d_i`、可审计 source `g_i` 与偏好 `y_i`，先在每个训练 fold 内估计 source/length nuisance propensity `b(g, length, style)`，不让验证样本参与 nuisance 拟合。核心 evidence scorer `a_theta(v,d)` 不直接靠 cross-generator preference label 识别，而用 **same-generator、coarse-emotion-matched 的 cross-video negatives** 训练：同一生成器的原视频—描述 pair 为正，保持生成器与粗情绪近似不变但替换视频的 pair 为负。这样最直接的生成器风格信号在 matched pair 内抵消。

最终 pairwise margin 为：

$$
m_i = [a_\theta(v_i,d_{i1})-a_\theta(v_i,d_{i2})]
      + [q_\phi(d_{i1})-q_\phi(d_{i2})]
      - \widehat b_{-fold(i)}(g_{i1},g_{i2},\ell_{i1},\ell_{i2}).
$$

训练目标同时包含：cross-fitted residualized Bradley–Terry loss、same-generator video-match contrastive loss、candidate-order consistency，以及按 generator-pair × prior-agreement 环境定义的 group-DRO worst-group loss。`q_phi` 只允许学习 source-adversarial 的描述质量残差。该路径的算法差异是“用同生成器跨视频反事实识别 AV evidence margin，再对 source nuisance 做折外残差化和 worst-group 决策”，不是普通 DPO、ODIN 正交头或数据增广。

这里的 `video-grounded` 是操作性定义：分数应区分原视频与 coarse-emotion-matched swapped video；不声称恢复人类偏好的因果真值。

## 最小 probe 与门禁

公开资源：EmoPrefer V1/V2 annotation tables、MER2025/2026 对应 audio/video（需接受非商业研究条款）、Qwen2.5-Omni-7B；所有派生数据只保存在仓库内且不再分发受限媒体。算力上限为一张 A800。

1. CPU defect canary：五折重跑 length、source、combined 与 fold-exclusive source-prior probes；若 generator recovery <95%，或 content-blind WAF 与对称 Omni LoRA 相差 >5 pp，则 `STOP_DEFECT_NOT_REPRODUCED`。
2. Signal canary：在训练 fold 生成 same-generator、coarse-emotion-matched video swaps；冻结 Omni scorer 的 correct-match AUROC 必须 >0.65，否则 `STOP_NO_RECOVERABLE_GROUNDED_SIGNAL`。
3. 两折 500-pair LoRA prototype：相对对称 Omni LoRA，counter-stereotypical WAF 至少 +8 pp、原视频相对 matched-swap 的平均 margin 至少 +0.10、aggregate WAF 下降不超过 3 pp；任一不满足则不升级。
4. Killer gate：在相同 split/预算下必须超过 Style-audit ODIN、MJ1-style grounded verifier 与 EAPO augmentation。增益若仅来自 source name 字段、长度、candidate order 或额外模型集成，方向停止。

## 当前判断

该方向通过 Research Opportunity Gate 的理由是：问题重要、缺陷有近期公开可复现实验、方法改变了 pairwise utility 的识别与 worst-group 决策过程、无需新增人工标签，并可用一张 A800 做小规模否证。它尚未通过仓库自己的 defect canary，更没有稳定增益、killer baseline 或跨版本证据，因此不是 Paper Candidate。
