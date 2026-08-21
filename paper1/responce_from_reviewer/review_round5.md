# Review Round 5

## 1. 🎯 强CCF-C达标判定

- **当前状态**：未达标
- **核心差距**：本轮已把 Main-PR 的方法边界、training-only 数据切分、provenance、防泄漏和功效审计推进到接近可执行的协议，但正式数据退路、训练目标与评测指标、主统计实现仍未闭合，且仓库仍没有真实 checkpoint、OOF cache、缺陷复现或直接 baseline 结果。
- **C类顶流潜力**：否。当前研究纪律和审计强度已经具备形成一篇严谨强 CCF-C 工作的基础，但 TIGER、MRUF、DeferredSeg、Regression-L2D 与 Density-Ratio Post-Hoc L2D 已覆盖语言条件冻结专家路由、贡献教师、dense defer、连续回归 defer 和 post-hoc scorer。Main-PR 剩余差异是“固定 clean utility 下的局部尾部 regret 决策”，属于需要由明显且稳定实验优势证明的窄组合差异，尚不具备 Best Paper Nomination 所需的独立机制突破。

## 2. 🔄 改进效果评估

针对 `review_20260821_153624.md`，本轮 response 与代码修改是实质性推进。尤其值得肯定的是，作者没有把新增审计代码或协议文字冒充科学结论，并继续维持 Research Opportunity 状态。

### ✅ 有效改进

- TIGER 已被加入直接近邻矩阵，且“语言条件 + 冻结专家 + dense contribution routing”已从新颖性主张中撤回。Main 被重命名为 Main-PR，`orthogonalized`、`causal` 和理论风险保证等不成立术语已删除。
- 新增 `steps/014_objective_and_algorithm_spec.md`，明确了变量、固定宽度 B/C 输入、partial residual、clean retention constraint、Rockafellar–Uryasev CVaR、dual update、dev threshold 冻结和推理流程。相比上一轮只用组件名称描述方法，本轮已出现可检查的数学算法规范。
- Step 003 新增 training-only pilot builder，并把 official benchmark test 读取锁到 Step 008。scene 与 sequence 通过二部图连通分量形成冻结 `cluster_id`，能够覆盖“同一物理序列使用不同 scene ID”的泄漏风险。
- NYUv2/KITTI source adapters、RGB 内容 SHA、split provenance、frozen crop、annotation coverage 和 formal power audit 已进入代码；provenance verifier 不再只相信调用者自报的 manifest 字段。
- feature firewall 已增加 GT、label、advantage、D0/D1 loss、oracle 与 test metric 等禁用字段，并从仓库相对源码重新计算 SHA256。
- B-direct/C-direct 已改为固定宽度输入；global-match 与 local-relation 两类 permutation 被预注册，不再使用同一视频邻帧 cyclic permutation 作为唯一负控制。
- hypervolume 已降为 secondary sensitivity。Claim-M 主判据改为：dev 在 retention ≥0.80 的 operating points 中选择最低 CVaR threshold，冻结后在 internal-test 比较 CVaR 与 WorstOf3。这个判据比“全曲线面积更大”更贴近论文实际主张。
- bootstrap 已删除 `math.inf` 绕过路径，并开始记录 clean-gain denominator 不稳定的 replicate 数与 STOP 状态。
- published adaptation 已区分 faithful 与 capacity-matched 两版，避免为了参数量匹配而破坏先行方法公式。

### ⚠️ 部分解决

- Main-PR 虽然有唯一文档，但仍缺少会改变实验结果的冻结参数：`β`、Huber `δ`、region 权重 `w_ir`、image/cluster batch 组成、`η` 初始化与更新方式、dual update 频率。这些内容没有进入 `baseline_contract.yaml`。
- Step 003 已有大量 adapters 和 audit code，但 response 明确说明 Linux 远端测试、真实数据下载、coverage 与 power gate 尚未运行。`steps/README.md` 仍写“全套 22 个测试通过”，这与本轮新增大量测试及“REMOTE VERIFICATION PENDING”不一致。
- `power_analysis.py` 模拟的是在预设 AUC、预设增量和预设损失分布下，固定测试设计能否检测差异。它没有模拟 expert/router 的训练误差、超参数选择、tie band、held-out captioner 或训练集规模，因此更接近 **conditional inferential detectability**，不能独立证明端到端实验具有 0.80 power。
- `features.py` 的字段名 denylist 与源码 SHA 检查能阻止显式泄漏，但不能阻止把 GT 派生量改名为 `empirical_error`、`teacher_score` 或 `reference_signal` 后声明成 `candidate` 特征；`source_function` 也尚未通过 allowlist 与运行时 sanitized input 约束。
- D0/D1 参数结构形式相同，但 D0 的 zero text input 可能令 text adapter 的输入权重长期零梯度。若不使用 learned null token 并检查 active-gradient parameter ratio，“相同参数量”仍不等于“相同有效容量”。
- faithful/matched baseline 目前只是配置中的方法名称和 objective 标签，尚无原论文公式到 CoVoL 变量的 adaptation card、代码或 sanity check。

### ❌ 无效/偏离

- **VKITTI2 fallback 目前是无法执行的死分支。** `dataset_fallback_decision.yaml` 允许 NYUv2+Virtual KITTI 2，但 `validate_trusted_training_source` 只接受 NYUv2/KITTI，`power_analysis.py` 又把 formal datasets 硬编码为 `{KITTI, NYUv2}`，仓库也没有 VKITTI2 source adapter。即使 KITTI local coverage 失败，正式 provenance/power 流程也不能合法切换到 VKITTI2。
- `steps/004_defect_reproduction.md` 前文允许 NYUv2+VKITTI2，后文 H-fallback-defect 通过条件仍写成“NYUv2/KITTI internal-test 均通过”，与冻结数据分支直接矛盾。
- **Main-PR 的训练风险与正式指标不是同一随机变量。** Eq. (7) 先在每个 region 内对三个 caption variants 取最大值，再跨 region 求和；`metrics_spec.md` 则先形成每个完整 caption variant 的整图 regret，再对三个完整变体取最大值。前者可能把 region A 的 variant 1 与 region B 的 variant 2 拼成现实中不存在的“Frankenstein worst caption”，从而优化一个比报告指标更保守但不同的目标。
- **Eq. (9) 与 Eq. (10) 不是同一个 primal-dual 问题。** Eq. (9) 使用 `λ[κG1-Gg]_+`，而 Eq. (10) 用带符号的原始 constraint 更新 λ，使约束满足时 λ 可以下降。若使用 hinge，λ 对满足约束的样本没有对应梯度；若使用标准 Lagrangian，则目标中不应再加 hinge。当前混合写法无法唯一复现。
- `bootstrap.py` 的数据类和重采样仍使用 `scene_id`，而最新数据协议把 scene–sequence connected component 的 `cluster_id` 定义为唯一独立单位。同一 cluster 含多个 scene ID 时，现有 bootstrap 仍会拆开相关帧。
- 当前 bootstrap 只实现 hypervolume difference；新的 primary claim 所需的“dev 冻结 constrained threshold + internal-test CVaR/WorstOf3 paired cluster CI”尚未实现。因此 primary claim 的正式统计路径仍不存在。
- Step 005 文档仍保留 scene-group stacking 描述，现有 `cache_oof_experts.py` 也尚未升级为 `(dataset,image_id,seed,candidate_id,control_type)` 与真实 checkpoint/cache 文件绑定。上一轮明确要求的实体级 OOF 审计尚未完成。

## 3. 🔍 强CCF-C维度深度审查

### 问题与动机

问题定义已经收缩为一个清楚的细分任务：自动 caption 含局部可验证错误时，在两个冻结、同任务 metric-depth candidates 之间做局部替换，并在 clean utility 约束下控制尾部 regret。该定义具备强 CCF-C 所需的具体性和可证伪性。

仍未验证的关键前提是：自然自动 caption 中可机器确认的局部错误，是否在足够多独立 cluster 上产生相对 D0 的实际深度损害。若最终只有程序化 structured errors 上成立，应把论文定位为 **controlled caption stress test**；不能把 Virtual KITTI 2 合成错误或模板干预外推为真实 captioner 部署风险。

当前数据与审计工程已经明显重于模型和科学验证。强 CCF-C 评审不会因 provenance 代码规模而提高算法评分。下一阶段应停止扩张审计框架，优先获得一个最小但完整的“真实数据 → 公平 experts → OOF cache → defect → direct baseline → Main-PR”证据链。

### 技术完备性

1. **风险聚合必须唯一化。** 正式目标应直接对应报告指标，例如：

   $$
   Q_i(\theta)=\left[\max_v\sum_r w_{ir}
   \bigl(L^g_{irv}-L^0_{ir}\bigr)\right]_+,
   $$

   而不是先对每个 region 独立取 `max_v`。除非作者明确把 region-wise adversarial caption composition 定义为另一个任务，并为其构造真实输入，否则不能用不同随机变量训练与评测。

2. **Lagrangian 必须重写为一个数学一致的版本。** 可选方案是标准形式 `L + λ(κG1-Gg)`、`λ≥0`、projected dual ascent；或者固定 penalty coefficient 的 hinge constraint。当前 `λ×hinge + signed dual update` 不成立。

3. **soft gate 必须说明概率解释。** Eq. (4) 是固定候选损失的凸组合，它等价于 Bernoulli 随机 hard route 的期望风险，但不等于对混合深度图计算 AbsRel。训练使用 soft expected risk、推理使用 deterministic binary gate 时，应增加 straight-through/hard-routing 对照，并报告 relaxation gap。

4. **D0/D1 的有效容量仍需验证。** D0 text channel 应使用可训练且与 D1 同路径的 learned null token；需要逐层报告 active-gradient parameter count，而不是只报告总参数量。

5. **Main-PR 与 Risk-L2D-C 的差异需要精确到 score 公式。** 两者必须共享 gate architecture、semantic inputs、risk term、threshold calibration 和 search budget；唯一差异只能是 direct advantage target 与 inner-OOF partial residual target。配置和 adaptation card 应能自动检查这一点。

### 实验可信度

- 当前没有真实 manifest、coverage/power 结果、checkpoint、OOF prediction、regret、AUROC 或 baseline 表，因此没有一项科学 claim 得到支持。
- 正式 fallback branch 必须在任何实验结果出现前冻结。若 KITTI local coverage 失败，必须先让 VKITTI2 adapter、provenance、power 和 metric contract全部可执行，再切换；不能在结果出现后人工选择更有利的 outdoor dataset。
- `power_analysis.py` 的输出不能命名为完整 study power，除非模拟过程包含训练样本量、模型拟合、inner/outer trial selection 和 threshold calibration。当前版本可作为“在假定 score 分布成立时的条件检测能力”诊断。
- cluster bootstrap 必须使用 manifest 的 `cluster_id`；NYUv2 同 sequence/scene 连通分量和 KITTI drive 的所有图像必须始终共同重采样。
- primary comparison 应在 dev 为每个方法独立冻结一个满足 retention≥0.80 的 threshold，然后在相同 internal-test clusters 上比较风险。不得在 internal-test 重新选 threshold，也不得用 hypervolume 代替已预注册的 constrained operating point。
- CVaR@20% 需要报告 tail 中独立 cluster 数、最大单 cluster tail mass 和 `α∈{0.10,0.20,0.30}` 的预注册敏感性。若尾部几乎由一个 drive/sequence 构成，只能报告描述统计，不能声称跨场景尾部风险改善。
- faithful/matched adaptations 必须分别忠实实现。参数量匹配版不能代替 faithful 版，faithful 版的负结果也不能因“容量不公平”被删除。

### 叙事克制性

本轮叙事继续保持克制：TIGER 等近邻已被正面承认，Main-PR 不再使用 causal/orthogonal/safe 等过度术语，hypervolume 也被降为 secondary。这是明确优点。

但论文仍需防止另一种 overclaim：把大量审计、manifest、power 和 provenance 工程包装成算法贡献。当前能够被允许的最强方法主张只有：

> 在两个冻结、同任务深度候选之间，Main-PR 在预注册 clean-retention operating point 上，比相同输入、相同风险目标和忠实直接近邻获得更低的受控 caption-error 尾部 regret。

若 Main-PR 不能稳定击败 Risk-L2D-C 或 TIGER-style LOO，方法贡献应删除；即使 Claim-F 成立，也只能转为语义增量分析工作。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

### 1. “你的正式数据分支根本不能运行，outdoor 结论可在 KITTI 与 VKITTI2 之间事后选择。”

- **攻击依据**：fallback YAML 允许 VKITTI2，但 provenance、power、adapter 和 Step 004 通过条件仍硬编码 KITTI。
- **现有内容能否扛住**：**不能。** 这是 formal experiment contract 的直接内部矛盾，会使两数据集结论不可审计。

### 2. “你训练的不是论文报告的风险，而且 primal-dual 公式自身不一致。”

- **攻击依据**：region-wise variant max 与 image-wise worst-of-3 不同；hinge Lagrangian 与 signed λ update 不匹配；β、Huber δ、region weights 和 batch policy 未冻结。
- **现有内容能否扛住**：**不能。** 即使未来结果为正，审稿人也无法判断究竟实现了哪个算法，复现者也无法从文档重建相同目标。

### 3. “仓库证明了许多 JSON 能互相校验，但没有证明方法有效；主统计代码甚至仍按 scene_id 重采样。”

- **攻击依据**：无真实 checkpoint/results；OOF entity binding 未完成；primary constrained-risk CI 未实现；direct baselines 只有名称；远端测试延期且状态表仍声称旧的 22 tests passed。
- **现有内容能否扛住**：**不能。** 目前最有说服力的产物是研究协议基础设施，而不是强 CCF-C 所需的科学证据闭环。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 可复现性 | 新增 `build_vkitti2_source_manifest.py`，冻结 VKITTI2 下载版本、scene/clone/frame identity、RGB/depth/mask SHA 与 metric crop；在 `validate_trusted_training_source` 中加入 VKITTI2 contract，并让 formal power datasets 从 `dataset_fallback_decision.yaml` 的冻结输出读取，而非硬编码 `{KITTI,NYUv2}` | 数据分支闭合性；当前 fallback 是不可执行死分支 | 增加至少 6 个测试：合法 VKITTI2、伪造 revision、跨 split clone 泄漏、RGB alias、coverage fallback、formal power fallback；两条 outdoor 分支均可从 source manifest 跑到 coverage/power audit | `paper1/experiments/covol/build_vkitti2_source_manifest.py`, `paper1/experiments/covol/audit_provenance.py`, `paper1/experiments/covol/power_analysis.py`, `paper1/tests/test_build_vkitti2_source_manifest.py` |
| P0 | 叙事修正 | 将 H-fallback-defect 的通过条件改为读取冻结 `claim_dataset_decision.local_claim_datasets`，删除固定“NYUv2/KITTI 均通过”表述；把最终结果表的数据集顺序和 dataset role 写入一个哈希化 decision artifact | 问题定义一致性；禁止结果后择优数据集 | 生成 `paper1/artifacts/covol/dataset_decision.json`；Step 004/008/README 中不存在与该 artifact 冲突的硬编码数据集组合 | `paper1/steps/004_defect_reproduction.md`, `paper1/steps/008_canary_decision.md`, `paper1/configs/covol/dataset_fallback_decision.yaml` |
| P0 | 消融补全 | 将 Eq. (7) 重写为“每个完整 caption variant 先跨 region 聚合，再在 variant 上取最大值”，同步修改训练 objective、metrics 与 power simulator；添加一个两 region/两 variant 反例，保证 region-wise max 与 image-wise max 不被混用 | 方法—指标一致性；当前训练目标与主结果不是同一风险 | `test_objective_matches_reported_worst_variant` 手算通过，训练 `Q_i` 与评测 image-level worst regret 的绝对差 `<1e-10` | `paper1/steps/014_objective_and_algorithm_spec.md`, `paper1/experiments/covol/metrics.py`, `paper1/experiments/covol/power_analysis.py`, `paper1/tests/test_main_pr_objective.py` |
| P0 | 可复现性 | 在 Eq. (9) 中改用标准 Lagrangian `L_PR + βCVaR + λ(κG1-Gg)` 并保留 projected dual ascent，或删除 dual update 改用固定 hinge penalty；在 YAML 中固定 `β`、Huber `δ`、`w_ir` 公式、cluster batch size、每 batch image 数、`η/λ` 初始化和更新频率 | 技术完备性与唯一可实现性；当前 hinge 与 dual update 不属于同一优化问题 | 新增一个 feasible 和一个 infeasible toy batch：约束违反时 λ 上升、满足时 λ 不为负；固定 seed 下 20 次 update 的 loss/λ 序列逐元素一致 | `paper1/steps/014_objective_and_algorithm_spec.md`, `paper1/configs/covol/baseline_contract.yaml`, `paper1/tests/test_main_pr_objective.py` |
| P0 | 实验补充 | 实现 `select_constrained_operating_point`：每个方法只在 dev 从 retention≥0.80 的 21 个 threshold 中选最低 CVaR 点并保存 threshold ID；实现 `cluster_bootstrap_constrained_risk_difference`，internal-test 只对冻结 threshold 计算 CVaR/WorstOf3 paired CI | 主结果预注册一致性；当前 primary metric 尚无代码路径 | 生成 dev threshold artifact；测试中改变 internal-test score 排序不会改变 threshold ID；输出 CVaR 和 WorstOf3 的 estimate/CI/cluster count/invalid fraction | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/tests/test_constrained_evaluation.py` |
| P0 | 可复现性 | 将 `PolicyImageOutcome.scene_id` 替换为 `cluster_id`，bootstrap 只读取 manifest 冻结 cluster；添加一个 cluster 内含两个 scene ID 的测试，验证二者在所有 replicate 中共同出现 | 统计独立性；当前代码违反最新 connected-component 定义 | `test_bootstrap_uses_frozen_cluster_id` 通过；任何传入空 cluster_id 或同 image 多 cluster 的输入均非零失败 | `paper1/experiments/covol/bootstrap.py`, `paper1/tests/test_cluster_bootstrap.py`, `paper1/steps/metrics_spec.md` |
| P0 | 可复现性 | 扩展 expert plan/cache 主键为 `(dataset,image_id,seed,candidate_id,control_type)`；逐行记录真实 checkpoint path/SHA、cache path/SHA、training manifest SHA、config SHA、code commit 和 training cluster set，并读取文件重新计算 hash | OOF 与模型实体绑定；防止自洽但虚假的 manifest | 三个 seeds × D0/D1/twins/shuffled controls 均可唯一定位；篡改任一 checkpoint/cache byte 后 validator 必须失败；prediction cluster 与 training cluster 交集为 0 | `paper1/experiments/covol/cache_oof_experts.py`, `paper1/tests/test_expert_cache_no_leakage.py`, `paper1/steps/005_frozen_experts.md` |
| P0 | 可复现性 | 新增 expert-training manifest builder，只允许带 predicate-clean caption revision/hash 的 D1 训练行；D0 与 D1 读取完全相同 image rows；禁止 dev/internal-test cluster；将每个 OOF fold 的 caption coverage 写入 audit | 公平专家训练；当前 OOF plan 可使用未定义 caption 的 official-training rows | 每个 D1 training row 的 caption coverage 为 100%，D0/D1 image key 集完全相同，dev/internal-test cluster overlap 为 0 | `paper1/experiments/covol/build_expert_training_manifest.py`, `paper1/tests/test_expert_training_manifest.py`, `paper1/artifacts/covol/expert_training_manifest.jsonl` |
| P0 | 实验补充 | 在 20–50 个独立 cluster、单 seed 上执行一次端到端 pilot：source adapter→pilot manifest→caption→D0/D1→OOF cache→H-fallback→B-direct/C-direct→Risk-L2D-C/Main-PR→dev frozen threshold→internal risk table；不运行完整 baseline 矩阵 | 尽早验证证据链可执行；当前工程规模已远超实证进度 | 生成 `pilot_run_manifest.json`，所有输入/输出有 SHA；命令退出码为 0；结果允许为负，但不得有手工复制文件或缺失 lineage | `paper1/scripts/run_end_to_end_pilot.sh`, `paper1/results/covol/pilot/`, `paper1/steps/005_frozen_experts.md`, `paper1/steps/014_objective_and_algorithm_spec.md` |
| P0 | 可复现性 | 在授权 Linux 工作区对当前 commit 执行 `ruff check paper1`、`black --check paper1`、`pytest paper1/tests -q`，保存 Python/依赖/OS/commit/命令/退出码/测试数量；按真实结果更新状态表，删除未复验的“22 tests passed” | 可复现性与状态真实性 | 生成 `paper1/artifacts/covol/round5_verification.json` 和原始日志；三条命令退出码均为 0；状态表测试数与日志完全一致 | `paper1/pyproject.toml`, `paper1/steps/README.md`, `paper1/artifacts/covol/round5_verification.json` |
| P1 | 实验补充 | 将当前 `power_analysis.py` 输出明确命名为 `conditional_detectability`；另增含 train/dev 样本数、模型拟合、20-trial selection 和 dev threshold calibration 的学习过程 simulation，或取消其作为进入 Step 005 的硬门禁 | 功效解释准确性；当前模拟直接假定 score AUC，未覆盖学习不确定性 | 两份结果分开输出；文档不得把 conditional detectability 写成 end-to-end power；扩样规则明确是增加 train、dev、internal-test 中的哪一项 | `paper1/experiments/covol/power_analysis.py`, `paper1/configs/covol/power_grid_v1.json`, `paper1/steps/003_intervention_dataset.md` |
| P1 | 可复现性 | 用 feature extractor allowlist 替代仅靠名称 denylist：登记允许的函数全限定名、合法原始输入键和输出维度；运行时给 extractor 传入不含 GT/loss/label 的 sanitized mapping；测试 `empirical_error/reference_depth/teacher_score` 三个别名均被拒绝 | 特征无标签泄漏；名称黑名单可被改名绕过 | 生成 `feature_allowlist.yaml`；任何 extractor 请求未登记字段、未登记函数或维度不符时非零失败 | `paper1/configs/covol/feature_allowlist.yaml`, `paper1/experiments/covol/features.py`, `paper1/tests/test_feature_schema_no_intervention_metadata.py` |
| P1 | 消融补全 | 增加 learned-null D0、zero-null D0 和 shared-head modality-dropout 三个 expert control；逐层记录 active-gradient parameter count，并在相同 seed/updates 上比较 clean gain 与随机 twin advantage | 候选容量公平性；zero text 可能让 D0 adapter 大量参数失活 | 生成 `expert_capacity_controls.csv`；D0/D1 active-gradient parameter ratio 差异≤1%，否则正式双候选合同失败 | `paper1/experiments/covol/models/dual_candidate_depth.py`, `paper1/experiments/covol/run_expert_controls.py`, `paper1/tests/test_dual_candidates.py` |
| P1 | 文献增补 | 为 TIGER、MRUF、DeferredSeg、Regression-L2D、DR-PostHoc-L2D 各新增一张 adaptation card，逐项写原论文公式、CoVoL 变量映射、faithful 超参数、capacity-matched 改动和不可复现细节；每张卡绑定实现文件与单元测试 | Baseline 忠实性；当前配置只有方法标签 | 五张卡均含公式与 deviation table；主结果中每个方法同时出现 faithful/matched 行，缺任一行时 Claim-M 自动标记未完成 | `paper1/baselines/cards/`, `paper1/experiments/covol/baselines/`, `paper1/steps/007_fair_gate_baselines.md` |
| P1 | 消融补全 | 对 Main-PR 比较 soft expected-risk gate、straight-through hard gate 和训练/推理均 hard gate；所有版本复用 experts、features、trial 数和 dev threshold 规则 | 训练—推理一致性；Eq. (4) 是随机 hard route 的期望而非混合深度真实损失 | 生成 `ablation_gate_relaxation.csv`，报告 relaxation gap、clean retention、CVaR、WorstOf3 和训练稳定性；若 soft 版优势在 hard 版消失，不列为方法贡献 | `paper1/experiments/covol/run_gate_relaxation_ablation.py`, `paper1/results/covol/ablation_gate_relaxation.csv`, `paper1/steps/009_component_ablation.md` |
| P1 | 实验补充 | 对 CVaR 主结果固定报告 `α=0.20`，并预注册 `α=0.10/0.30` 敏感性；为每个结果记录 tail image 数、tail unique cluster 数、最大单 cluster tail mass；tail unique cluster <5 时只报描述统计 | 尾部风险可信度；少量 cluster 可主导 CVaR | 主结果表包含四个 tail composition 字段；不允许用 image 数代替独立 cluster 数 | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/steps/metrics_spec.md`, `paper1/results/covol/tail_composition.csv` |
| P1 | 叙事修正 | 在 contribution ledger 中为 Claim-F、Claim-M、natural-error relevance 和 structured-only stress test 分别设置状态；若 natural predicate precision/power 未通过，自动将摘要和标题中的自然部署表述替换为 controlled intervention | 贡献克制性；合成证据不能外推真实部署 | 生成 `claim_ledger.json`；每条 claim 链接唯一结果文件和 CI；无证据 claim 不得出现在 contribution list | `paper1/steps/011_claim_language_revision.md`, `paper1/artifacts/covol/claim_ledger.json`, `paper1/ideas/01_counterfactual_value_of_language_depth.md` |
| P2 | 可复现性 | 新增 GPU 环境锁，固定 Python、PyTorch、CUDA、transformers、DepthAnything checkpoint revision 和 caption encoder revision；提供 CPU audit 环境与 GPU training 环境两个 lockfile及一键 smoke 命令 | 复现环境完整性；当前 `pyproject.toml` 没有 PyTorch/模型依赖 | CPU audit 与 GPU smoke 均能从空环境运行；模型保存/重载输出误差 `<1e-6` | `paper1/environment/audit.lock`, `paper1/environment/gpu.lock`, `paper1/scripts/smoke_gpu.sh`, `paper1/README.md` |

## 本轮结论

本轮修改使研究方案从“严谨但未闭合的协议集合”进一步接近可执行 canary，尤其是 Main-PR 目标、training-only provenance 和 constrained operating point 的方向是正确的。现在不应继续增加新的审计层或 baseline 名称，而应先完成四个不可替代的闭环：

1. 让正式数据 fallback 可执行；
2. 让训练目标与主评测指标完全一致；
3. 让 OOF plan 绑定真实模型文件与 cluster；
4. 跑通一个小型端到端 pilot。

在这四项完成前，当前版本仍是高质量 Research Opportunity，而不是强 CCF-C Paper Candidate。
