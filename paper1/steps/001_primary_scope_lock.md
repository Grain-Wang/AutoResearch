# 001 Primary Scope Lock

## Current state

当前唯一选择的 Research Opportunity 是 **SR-VEP：Source-Residualized Video-Grounded Emotion Preference**，状态为 `SELECTED_RESEARCH_OPPORTUNITY / DEFECT_CANARY_PENDING / NOT_PAPER_CANDIDATE`。它研究 EmoPrefer/MER-Prefer judge 是否通过生成器风格先验而非音视频情绪证据做偏好判断，以及能否用 same-generator video matching、折外 source residualization 和 worst-group pairwise optimization 改善 grounded preference。

该选择只授权 CPU defect canary：获取官方公开 annotation tables 与许可文本、固定 hash、重跑五折 content-blind/source-prior probe。CPU gate 通过前不下载受限媒体、不启动 GPU、不实现完整训练器。量化门禁和最近邻见 [017 Research Opportunity Gate](017_research_opportunity_gate.md)，算法假设见 [SR-VEP candidate](../ideas/candidates/01_source_residualized_emotion_preference.md)。

## CoVoL archive boundary

CoVoL 的最终状态是 `ARCHIVED_GT_TEMPLATE_PROBE_STOPPED_BY_H_SENSITIVITY_CONTROL`。004-A 实际使用 NYUv2 GT class/instance/median-depth 构造的确定性关系短模板，而不是 automatic captions。semantic-preserving 控制也稳定变化，违反预注册停止条件。因此只停止当前 GT-template probe 和 Main-PR 贡献路径；它不证明自然 automatic-caption 错误整体不存在或无害。

CoVoL 的 Step004-B、Step005–008、official test 与第二数据集恢复全部禁止。历史 Step003 authorization 不能恢复它；所有入口还必须通过绑定 sensitivity CSV/summary SHA 的最终 scientific gate。完整证据边界见 [016 CoVoL Closure](016_covol_closure.md)。

## SR-VEP task

输入为视频/音频 `v` 与两条开放式 emotion descriptions `(d1,d2)`，目标是预测人类偏好，同时验证决策是否依赖与原视频匹配的情绪证据，而不是 generator identity、长度、candidate order 或 source-pair win-rate。

当前唯一待复现缺陷来自近期外部报告：content-blind source/length probe 接近 LoRA audio-visual judge，generator identity 又高度可从描述文本恢复。仓库尚未独立产生该事实。若 source recovery <95%，content-blind 与对称 Omni LoRA 相差 >5 pp，或官方数据/许可无法稳定获得，则方向停止。

## Candidate algorithm difference

候选方法不把普通 DPO、LoRA、对抗去偏或 group-DRO 单独当贡献。其可证伪差异是：

1. 在同一 generator 内，用 coarse-emotion-matched 的 cross-video negatives 识别 `video-description` evidence margin，使 generator style 在配对内抵消；
2. 用严格 cross-fitted nuisance model 残差化 generator-pair/length/style propensity，验证 fold 不参与 nuisance 拟合；
3. 在 generator-pair × prior-agreement 环境上优化 worst-group pairwise risk，并保持 candidate-order consistency；
4. 只把原视频相对 matched video-swap 的 margin 当操作性 grounding，不声称恢复人类偏好的因果真值。

## Upgrade gate

SR-VEP 只有在下列条件同时满足时才能成为 Paper Candidate：

- CPU defect canary 独立复现；
- 冻结 Omni correct-match AUROC >0.65，说明存在可恢复的音视频—描述匹配信号；
- 500-pair、两折 prototype 的 counter-stereotypical WAF 相对对称 Omni LoRA 至少 +8 pp，matched video-swap margin 至少 +0.10，aggregate WAF 下降不超过 3 pp；
- 在相同 split/预算下超过 Style-audit ODIN、MJ1-style grounded verifier 与 EAPO augmentation；
- 改进不依赖 source name、长度、candidate order、额外模型数量或读取 test label。

当前这些条件均未验证，算法 claim 不成立。
