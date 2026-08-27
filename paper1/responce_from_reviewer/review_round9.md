# Review Round 9

## 1. 🎯 强CCF-C达标判定

- **当前状态**：未达标；CoVoL-Depth 已按预注册的 004-A 控制门禁进入 `STOPPED_BY_H_SENSITIVITY_CONTROL`，不再是活跃 Paper Candidate，也不应继续按算法论文路径投入 D0/D1、router 或 killer baselines。
- **核心差距**：本轮首次完成了真正可审计的语言敏感性实验，但该实验使用的是由 NYUv2 GT 实体与深度关系生成的确定性短模板，而不是原任务定义中的自动图像 caption；结果能够停止当前模板化 probe 和 Main-PR 贡献路径，却不能被解释为“自动 caption 局部错误问题整体被否定”。
- **C类顶流潜力**：否。作者执行负门禁、保留失败结果和禁止选择性推进的研究纪律值得肯定，但当前没有可投稿的算法贡献；若将现有材料改写成负结果分析，也仍缺自动 caption、人工自然度、跨模型复现和冲突相对等价改写的直接对照。

### 距离 CCF-C 基线

若只评价当前可复核资产，问题定义约 `70/100`、方法完整性约 `15/100`、实验事实约 `35/100`、可复现性约 `80/100`、写作与论文产物约 `50/100`。按问题 15%、方法 25%、实验 35%、复现 15%、写作 10% 加权，约为 **44/100**；普通 CCF-C 可投稿基线约为 **70/100**，表面差距约 **26 分**。

但该差距不是线性的：原算法主张已被停止，不能通过补齐剩余代码把 44 分直接推到 70 分。要重新达到普通 CCF-C，必须先形成一个新的、未被当前负结果否定的论文问题，再重建方法与主实验链路。按“强 CCF-C”而非普通基线衡量，当前至少还差一个完整研究周期和约 **40 个以上的论文成熟度点**。

## 2. 🔄 改进效果评估

### ✅ 有效改进

- Round 7、Round 8 的回应和对应增量已经同步到远程 `paper1` 分支，修复了上一轮无法审计作者回应的问题。
- 作者在 NYUv2 official-train 上稳定选择 100 图、59 个独立 clusters，构建 1200 条 diagnostic-only local interventions；四个 family 各 300 行，另存 null/global diagnostics，没有读取 official benchmark test。
- 004-A 使用锁定的 TR2M、Depth Anything、DINOv2 和 CLIP 权重执行真实 A800 推理，逐行 CSV、summary、运行环境和模型哈希均已保存；10,000 次 paired cluster bootstrap 的统计单位与预注册一致。
- 结果没有被选择性包装。`local_entity_conflict` 和 `depth_relation_conflict` 虽然有正向区域 AbsRel 信号，但 `semantic_preserving` 也显著退化，作者按原门禁返回 `STOP_H_SENSITIVITY`，没有删除控制组、改阈值或继续训练 Main-PR。
- `001_primary_scope_lock.md`、Idea、Step 004、Step 005–008 和步骤状态表已经把 Claim-F、Claim-M 与 CoVoL 主线同步标为 STOP；真实 D0/D1、OOF cache 和 router artifact 有意不存在，符合停止规则。
- full-crop residual mass、cluster-balanced metrics、weighted CVaR、dev retention LCB、test-retention stop、feature callables、实体级 cache validator 和 operating-point lineage 已进入代码与回归测试。虽然这些代码不再支撑 CoVoL 论文，但实现边界比前几轮清楚。
- VKITTI2 已被固定为 `synthetic_structured_auxiliary_only`，没有用天气、视角或相机 clone 冒充独立场景，也没有用合成数据挽救失败的真实双数据集门禁。

### ⚠️ 部分解决

- **原任务与 004-A 输入不一致。** Idea 和范围锁仍把输入定义为自动 caption；实际 `build_interventions.py` 用 GT class、instance mask 和 median depth 直接生成 `The image shows A closer ... than B` 等短关系模板。该结果测量的是 released TR2M 对 annotation-derived relation prompts 的表面形式敏感性，不是自动 caption 中局部错误的自然分布。
- **semantic-preserving 控制不是独立自然 caption。** variant 0 与 clean caption 完全相同，variant 1/2 是固定句式改写；family 均值混合一个机械零值和两个改写值。控制失败可以停止当前 probe，但不能据此推断所有语义等价自动 caption 都会同样失败。
- **独立 predicate audit 只验证规则实现。** 100/100 的 parser audit 能确认模板包含预期实体与关系，不能确认句子在人类看来语义等价、自然、无歧义；仓库也明确记录 `human_naturalness=NOT_ASSESSED`。
- **text-artifact gate 的 aggregate 口径掩盖了单 family 泄漏。** 总 macro-F1 为 0.488，低于预设上限 0.60；但 `local_entity_conflict` 的单族 F1 约为 0.664，`target_deletion` 为 1.0。尤其 local-entity 是获得正向敏感性信号的 family，不能再写成“所有局部冲突均未被表面模板识别”。
- **控制门禁是显著性检验，不是等价性或冲突特异性检验。** “semantic-preserving CI 包含 0”会在样本量足够时因极小、无实践意义的表面形式效应而失败；真正的冲突特异性应比较 `conflict - semantic_preserving` 的 paired difference，并预先定义 smallest effect size of interest 或等价区间。
- 004-A 报告了区域 AbsRel 的显著性，但尚未系统报告 clean region AbsRel 分布、目标区域占 full crop 的像素比例、相对百分比变化、leave-one-cluster-out 影响和多 family multiplicity。当前效应量约为 `8e-4–1.6e-3`，是否具有任务意义仍不清楚。
- 三个第二数据集候选均为 `PENDING_SOURCE_ACCESS`，该结果处理正确；但 004-A 已停止 CoVoL 后，候选审计和 `RECOVER_TWO_REAL_DATASETS` 不应继续出现在活跃执行出口中，只能作为历史记录。

### ❌ 无效/偏离

- **“停止整个 CoVoL 问题主张”是过宽表述。** 当前实验没有使用 automatic caption，也没有自然错误 slice、人工语义等价审核或第二个语言深度模型。严谨表述应是：`当前 GT-template minimal probe 与 Main-PR 贡献路径停止`；原自动-caption问题尚未被本实验直接检验。
- **机器授权没有编码最终科学 STOP。** `step003_authorization.json` 仍为 `BLOCKED_CURRENT_DATA_BRANCH`，`nyuv2_h_sensitivity=true`，scientific status 也没有绑定 `sensitivity_diagnostic_summary.json`。`step003_authorization.py` 只审计 Step003；未来若生成新的 PASS coverage artifact，形式上仍可能授权 Step 004-B–008，而不读取 004-A 的 `STOP_H_SENSITIVITY`。
- `diagnostic_intervention_audit.json` 仍写 `independent_precision_status=PENDING` 和 `PENDING_INDEPENDENT_PRECISION_AND_H_SENSITIVITY`，与已经完成的 validity audit 和 004-A summary 不一致。多个“当前状态”artifact 没有一个最终 closure manifest 统一解析。
- text-artifact 的通过条件只看 aggregate macro-F1，使一个强可识别 family 被整体平均掩盖。该 gate 不足以支撑“正向 local-entity 信号来自语义冲突而非模板”的解释。
- 现有代码、方法规范、第二数据集恢复和 GPU 队列状态仍散布在活跃阅读路径中，容易让后续 Agent 把已经停止的方法当成待继续实现的主线。

## 3. 🔍 强CCF-C维度深度审查

### 问题与动机

原问题定义本身清楚：自动 caption 含局部语义错误时，选择性回退到纯视觉候选。但 004-A 实际回答的是另一个更窄的问题：

> 当输入为由 GT 实体和深度关系构造的短句时，released TR2M 是否对语义冲突模板比对语义等价模板更敏感？

现有结果没有通过该窄问题的预注册门禁，因此停止 Main-PR 是合理的资源决策。它不等于证明真实自动 caption 错误不存在，也不等于证明任何 fallback 路由均无价值。论文和 closure 文档必须把“项目停止决策”与“科学普遍否定”分开。

另一方面，结果确实揭示了一个可复核现象：TR2M 对语义等价表面改写也有小幅但稳定的区域误差变化。这个现象最多可作为下一轮 Research Opportunity discovery 的候选线索；在完成近期近邻检索、多模型复现和自然 caption 对照前，不应直接命名为“paraphrase-invariant depth”新主线。

### 技术完备性

CoVoL 已被停止，因此继续补 PyTorch D0/D1 或 Main-PR 不再属于技术完备性要求。当前应完成的是**停止状态的技术闭环**：

1. 用一个全局 scientific gate 将 004-A summary 的 SHA、status 和 exit code 绑定到所有下游入口；
2. 生成唯一 closure manifest，统一解释 Step003、intervention validity、TR2M release、004-A CSV/summary 和当前 claim status；
3. 把未执行的 Main-PR、baseline 和数据恢复合同标为 archived preregistration，而不是 active pending work；
4. 提供一条从锁定 corpus、checkpoint 和环境重放 004-A summary 的命令。

若作者想把当前负结果写成分析论文，则必须重新定义问题、重新做相关工作审计，并至少加入真实自动 caption、多模型、人工自然度与冲突相对等价改写的直接差值；这属于新论文，不是 CoVoL 的剩余消融。

### 实验可信度

004-A 的 paired design、cluster bootstrap、模型权重哈希和停止规则执行是可信的。当前最主要的实验限制不是运行错误，而是**构造有效性**：

- clean 与 corrupt 文本来自固定 GT 模板，不来自自动 caption；
- semantic-preserving 没有人类等价性与自然度证据；
- local entity distractor 来自固定小词表，容易产生 family-specific 表面线索；
- aggregate artifact score 掩盖了单 family 的高可分类性；
- “任一冲突族 CI 下界大于 0”涉及三个 family，却未给 family-wise error correction；
- region effect 尚未转换为相对 clean error、full-image impact 和目标区域质量占比。

这些问题不要求恢复 CoVoL 正式实验，但必须决定负结果能被写到什么程度。现阶段最稳妥的结论是：

> 在该确定性 GT 关系模板 corpus 上，released TR2M 的误差变化不具备预注册的冲突特异性；因此当前 Main-PR 研究路径停止。

### 叙事克制性

作者在“不挑正结果”和“不越过门禁”方面表现良好。下一步需要收紧以下词句：

- `CoVoL problem falsified` → `current GT-template CoVoL probe and contribution path stopped`；
- `automatic caption error control failed` → `annotation-derived relation-template control failed`；
- `text artifact control passed` → `aggregate control passed, local-entity and deletion families remained individually identifiable`；
- `semantic-preserving` 首次出现时注明“规则定义的等价改写，human equivalence/naturalness 未评估”；
- 当前方法规范只称 `archived preregistration`，不得继续用“候选算法”或“下一实现步骤”措辞。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“你声称研究自动 caption 错误，但实验使用的是 GT 关系模板。”**
   - 攻击依据：clean caption 和四类 intervention 均由 class、instance 和 median depth 直接生成，没有自动 captioner 输出。
   - 现有内容能否扛住：**不能。** 只能把结论收缩为模板化 diagnostic；不能外推原任务。

2. **“控制失败并没有证明冲突不特异，因为你没有直接比较 conflict 与 matched paraphrase control。”**
   - 攻击依据：门禁只检验各 family 相对 0；没有 conflict-minus-control paired contrast、等价区间或 smallest effect size；同时 local-entity family 的 text-only F1 已超过 aggregate 阈值。
   - 现有内容能否扛住：**不能。** 停止项目是合规的，但科学解释必须降级，探索性差值只能用于 postmortem，不能反向恢复 confirmatory claim。

3. **“这是一份执行严谨的负 probe，不是一篇 CCF-C 论文。”**
   - 攻击依据：没有活跃方法、D0-relative defect、Claim-F、Claim-M、跨模型或跨数据集结果；当前唯一模型结论来自一个 released checkpoint 和 100 张 training-only 图。
   - 现有内容能否扛住：**不能。** 现有材料适合作为内部研究淘汰记录或更大 robustness study 的一部分，不满足强 CCF-C 主论文门槛。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 叙事修正 | 新建 CoVoL closure 文档，逐项写明“原任务、实际 diagnostic 输入、预注册判据、观测结果、可支持结论、不可支持结论、停止动作、可复用资产”；将最终科学表述固定为“current GT-template probe and Main-PR path stopped”，删除“自动 caption 问题整体被否定”含义 | 强CCF-C要求贡献与证据严格匹配；当前任务输入与 diagnostic 输入不一致 | `016_covol_closure.md` 含上述 8 节；全文搜索不再出现把单模型模板 probe 外推为自动-caption普遍结论的句子 | `paper1/steps/016_covol_closure.md`, `paper1/steps/001_primary_scope_lock.md`, `paper1/ideas/01_counterfactual_value_of_language_depth.md`, `paper1/README.md` |
| P0 | 可复现性 | 新建全局 scientific-gate artifact，绑定 `sensitivity_diagnostic_summary.json` 和逐行 CSV 的实际 SHA256，将 `step004_b/step005/step006/step007/step008/official_test/second_dataset_recovery` 全部设为 false；新增 validator，任何 CoVoL 下游入口必须同时通过 Step003 gate 与 scientific gate | 可复现性和失败门禁；当前 Step003 authorization 未编码 004-A STOP，未来 coverage PASS 可能绕过科学停止 | 在当前 artifact 上所有下游 action 均返回 `STOPPED_BY_H_SENSITIVITY` 和固定 exit code 4；伪造 PASS Step003 artifact仍不能授权；对应 pytest 全部通过 | `paper1/artifacts/covol/covol_scientific_gate.json`, `paper1/experiments/covol/scientific_gate.py`, `paper1/tests/test_scientific_gate.py` |
| P0 | 可复现性 | 生成唯一 closure manifest，重算并登记 source manifest、diagnostic corpus、independent audit、intervention validity、TR2M release audit、004-A CSV/summary、代码 commit 和环境 lock 的 SHA256；把旧 `diagnostic_intervention_audit.json` 的 PENDING 状态标记为被 closure manifest supersede，而不覆盖历史文件 | 强CCF-C要求结果 lineage 唯一；当前多个 artifact 状态相互不一致 | `covol_closure.json` 校验所有文件存在且 hash 一致，状态唯一为 `STOPPED_BY_H_SENSITIVITY_CONTROL`；删除或篡改任一文件时 validator 非零退出 | `paper1/artifacts/covol/covol_closure.json`, `paper1/experiments/covol/validate_covol_closure.py`, `paper1/tests/test_covol_closure.py` |
| P0 | 实验补充 | 对 stable-hash 选取的 100 条 intervention 进行双人盲审；每条分别标注语法自然度、与 clean 的语义等价性、是否只改变目标实体/关系和是否含歧义，保存原始 200 份评分及分歧裁决 | 构造有效性；规则 parser 不能替代 human semantic/naturalness audit | 生成逐行评分 CSV、每 family 接受率、weighted kappa 和 95% 区间；若 semantic-preserving 等价率低于 0.95，则 closure 解释改为 `STOP_INVALID_CONTROL_CONSTRUCTION`，不得写成模型语义不变性失败 | `paper1/results/covol/intervention_human_audit.csv`, `paper1/results/covol/intervention_human_audit_summary.json`, `paper1/steps/016_covol_closure.md` |
| P0 | 实验补充 | 基于已冻结 1200-row CSV 运行一次明确标为 `EXPLORATORY_POSTMORTEM` 的 paired cluster analysis：分别计算三个 conflict family 与 semantic-preserving family 的 mean degradation 差值、10,000 次 paired cluster bootstrap CI、Holm 校正 p 值和标准化效应；同时按 template variant 分层报告 | 实验解释性；当前只比较各 family 与 0，不能判断冲突相对表面改写的额外效应 | 生成 `sensitivity_difference_in_difference.csv/json`；文件头包含 `cannot_reverse_preregistered_stop=true`；每个 family 含 point、CI、Holm p、standardized effect 和 per-template rows | `paper1/experiments/covol/analyze_sensitivity_postmortem.py`, `paper1/results/covol/sensitivity_difference_in_difference.csv`, `paper1/results/covol/sensitivity_difference_in_difference.json` |
| P0 | 实验补充 | 将 text-only artifact 审计改为逐 family 门禁：对每个 family 分别运行 leave-one-template-out binary classifier，报告 F1、AUROC、caption length、token count和 edit-distance 分布；不得再用 aggregate macro-F1 单独判 PASS | Baseline/控制可信度；local-entity 与 target-deletion 的表面可识别性被总体平均掩盖 | 生成 `text_artifact_control_per_family.csv`；任何 family F1 >0.60 时状态标为 `FAMILY_ARTIFACT_DETECTED`，并在 closure 中限制对应模型效应解释 | `paper1/experiments/covol/audit_intervention_validity.py`, `paper1/results/covol/text_artifact_control_per_family.csv`, `paper1/results/covol/intervention_validity.json` |
| P0 | 实验补充 | 从 004-A 逐行结果计算每图 target-region valid-pixel fraction、clean region AbsRel、absolute/relative degradation、full-image degradation和 leave-one-cluster-out influence；按 family 报告 median、IQR、95th percentile 与最大单 cluster 贡献 | 强CCF-C要求报告实践效应而非只报告显著性；当前 `1e-3` 量级是否有任务意义未知 | 生成 `sensitivity_practical_effect.csv/json`；每 family 同时包含 absolute effect、relative effect、target mass 和 influence diagnostics，不得只给 p/CI | `paper1/experiments/covol/analyze_sensitivity_postmortem.py`, `paper1/results/covol/sensitivity_practical_effect.csv`, `paper1/results/covol/sensitivity_practical_effect.json` |
| P1 | 写作规范 | 将 Step 005–014 的标题或首段统一加上 `ARCHIVED_PREREGISTRATION_NOT_AUTHORIZED`，将“下一出口/下一实现”改为“历史预注册记录”；将第二数据集候选审计状态改由 closure manifest解释为 `SUPERSEDED_BY_H_STOP` | 写作规范和执行安全；停止后的方法合同仍像活跃路线，容易被后续 Agent误启动 | `steps/README.md` 中所有 CoVoL 下游步骤均无 active next action；搜索 `PENDING REAL OOF CACHE`、`下一原子动作.*CoVoL` 返回 0 个活跃命中 | `paper1/steps/005_frozen_experts.md`, `paper1/steps/006_semantic_incrementality_gate.md`, `paper1/steps/007_fair_gate_baselines.md`, `paper1/steps/008_canary_decision.md`, `paper1/steps/014_objective_and_algorithm_spec.md`, `paper1/steps/README.md` |
| P1 | 可复现性 | 新增只重放 004-A 的锁定环境与命令：固定 Python/PyTorch/CUDA及依赖 hash，验证输入 corpus/checkpoint SHA，运行 runner 和 summary，再逐字节比较 CSV/JSON hash；添加 CPU dry-run 和不下载权重的 CI | 可复现性；当前只有远端执行记录，没有一键重放入口和 GitHub status | `reproduce_h_sensitivity.sh` 在已准备权重的数据环境中重建同 hash summary；GitHub Actions 对 parser、metrics、gate 和 dry-run tests 出现绿色 workflow run | `paper1/environment/h_sensitivity.lock`, `paper1/scripts/reproduce_h_sensitivity.sh`, `.github/workflows/paper1-qa.yml`, `paper1/README.md` |
| P1 | 文献增补 | 新建下一轮 Research Opportunity Gate，最多登记 5 个非等价候选；每个候选逐项写出 2024–2026 最近邻、可复现算法缺陷、与现有方法不同的决策变量、公开数据、单张 A800 可运行的最小 probe和明确 STOP 条件；Q-GeoRoute 只能作为五个候选之一参加同一门禁 | 强CCF-C要求新主线先有清楚差异与低成本否证；当前 CoVoL 已停止，不能自动切到备用方向 | 生成不超过 5 行的候选矩阵；每行至少 5 篇最近邻、1 个公开数据源、1 个单-seed canary和1 个量化 STOP；只有一行被标记 `SELECTED` | `paper1/steps/017_research_opportunity_gate.md`, `paper1/ideas/candidates/` |
| P2 | 写作规范 | 将当前 CoVoL 材料整理为内部 negative-result technical note，正文只包含问题、模板化 diagnostic、构造限制、004-A 结果、停止规则和可迁移教训，不包含未执行 Main-PR 的算法贡献 | 负结果资产管理；现有材料不足以作为 CCF-C 主论文，但可避免研究经验丢失 | 形成 4–6 页等价内容的 Markdown，标题含 `Diagnostic Negative Result`，摘要明确“automatic captions were not directly tested”；不将其放入 Paper Candidate 目录 | `paper1/archive/covol_negative_result.md` |
