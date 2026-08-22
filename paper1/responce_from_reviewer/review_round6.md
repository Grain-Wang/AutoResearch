# Review Round 6

## 1. 🎯 强CCF-C达标判定

- **当前状态**：未达标
- **核心差距**：Round 5 指出的数据分支、风险聚合、Lagrangian 和 cluster bootstrap 矛盾已被代码级修正，但当前仍没有真实干预数据、冻结双候选、OOF cache、缺陷复现或 baseline 结果；同时现有 Main-PR 训练风险与全图主指标的像素权重仍不一致，dev 的 retention 可行性未提供统计保证，训练随机种子也没有进入主评测层级。
- **C类顶流潜力**：否。当前研究问题、审计纪律和失败门禁已经接近一篇严谨强 CCF-C 工作的设计水平，但 Main-PR 剩余差异仍是 partial residual、clean constraint 与 CVaR 的任务化组合。只有在真实数据上稳定击败 Risk-L2D-C、TIGER-style LOO、Regression-L2D、DR-PostHoc-L2D、Dense-Coherence-L2D、LOO-Uncertainty-Router 及 robust single-expert baselines 后，才具备普通强 CCF-C 算法论文资格；目前没有 Best Paper Nomination 所需的独立机制证据。

## 2. 🔄 改进效果评估

针对 `review_round5.md`，本轮 response 和实现属于实质修正，不是对原方案的文字重述。作者继续明确区分“本地合成代码测试通过”和“科学 claim 成立”，这一点应保留。

### ✅ 有效改进

- VKITTI2 已新增 source adapter、checksum/version/provenance 合同、RGB/depth/class/instance 解析与回归测试；formal power 的数据集集合不再被硬编码为 NYUv2+KITTI。
- `steps/004_defect_reproduction.md` 已改为读取冻结的 `claim_dataset_decision.local_claim_datasets`，避免在文字上继续硬编码 KITTI。
- Main-PR 风险已改为“完整 caption variant 先跨 region 聚合，再在 variants 上取最大值”，消除了不同 region 拼接不同 variant 的 Frankenstein risk。
- Eq. (9)–(10) 已统一为 signed Lagrangian 与 projected dual ascent；`beta`、Huber delta、region weighting 规则、batch、optimizer、`eta` 和 `lambda` 更新参数已进入机器可读合同。
- `bootstrap.py` 已统一使用冻结 `cluster_id`，并新增 dev-frozen operating point 下的 CVaR/WorstOf3 paired cluster bootstrap。
- `constrained_evaluation.py` 已实现 dev-only threshold selection，并能写出 hash-addressed operating-point artifact；internal-test 的风险代码不再重新选择 threshold。
- feature firewall 已从字段名 denylist 扩展到 source-function allowlist、raw-field allowlist 和 runtime sanitizer，显式 GT/loss/oracle 字段更难进入 router。
- D0 合同已从 zero text 改为 learned-null text path，并要求逐层 active-gradient parity，方向上比“形式参数量相同”更公平。
- `power_analysis.py` 已明确改称 conditional inferential detectability，不再把预设 score/loss 分布下的模拟外推为端到端研究 power。
- 本地 `paper1` 范围的 Ruff、Black 与 92 个单元测试被记录，旧的固定“22 tests”状态已删除。

### ⚠️ 部分解决

- `main_pr_objective.py` 目前只是 Python scalar helper，没有 PyTorch/autograd router、cluster batch sampler、`eta` 参数更新、dual update 与 checkpoint；因此“目标已实现”只能解释为公式单元测试完成，不能解释为训练过程可运行。
- `constrained_evaluation.py` 用 dev retention **点估计**判断 `>=0.80`。当前测试甚至选择恰好 `0.80` 的 threshold，没有 one-sided lower confidence bound 或安全余量；在 20 个左右独立 cluster 上，该 threshold 很可能在 internal-test 违反 clean utility。
- internal-test bootstrap 只比较风险，不检查冻结 threshold 在 internal-test 的 retention 是否仍满足 0.80。此时结果不能命名为 `CVaR@Ret>=0.80`，最多只能称为 `CVaR@dev-feasible-threshold`。
- operating-point artifact 仅绑定 dev manifest 与 method config，没有绑定 expert cache、raw outcome table、coverage grid、metric-spec version、minimum-clean-gain artifact、seed 和代码 commit；同一个 threshold index 可被错误套用到另一份结果表。
- feature allowlist 中登记的 `candidate_features`、`caption_region_features`、`image_features` 当前只是字符串合同，`features.py` 并未定义这些实际 extractor callable；因此 schema 可以引用一个不存在的函数并通过验证。
- learned-null D0、active-gradient parity、same-width B/C controls 和两类 permutation 仍停留在配置与步骤文件，尚无模型、forward/backward smoke 或 grounding 结果。
- 92 个本地测试覆盖大量 toy fixtures，但没有 GitHub Actions/远端 CI artifact、依赖 lock 或真实数据 fixture；测试不能证明官方 archive 上的 adapter 与统计链路可运行。

### ❌ 无效/偏离

- **Main-PR 的 region 权重仍与正式全图指标不一致。** Step 014 将 `w_ir` 定义为“eligible regions 内有效深度像素占比”，权重和固定为 1；`metrics_spec.md` 的主风险却在 official crop 的全部有效像素上计算。若只有一半有效像素属于 eligible regions，当前训练风险会把局部 regret 放大约两倍。要与全图 AbsRel regret 等价，region 权重分母必须是整张 official crop 的全部有效深度像素，未路由区域以固定 D0、零 regret 进入总和。
- **VKITTI2 分支虽然可以解析数据，但仍不能支撑正式两数据集推断。** adapter 正确地把所有 clone/weather/camera 归入 5 个基础 scene，而 annotation coverage 与 detectability 合同要求至少 20 个独立 cluster。因此 VKITTI2 在当前正式门禁下必然只能是 structured auxiliary/descriptive set，不能成为 NYUv2+VKITTI2 的第二个 inferential dataset。当前 `dataset_fallback_decision.yaml` 仍把它写成可进入正式 local claim 的分支。
- **VKITTI2 source provenance 仍允许事前挑帧。** adapter 接受外部 `frame_index_path`，而 provenance 只验证该列表具有一个 SHA256，并未确认它是对官方解压目录的完整、规范枚举。调用者可以先观察数据，再生成一个有利子集并得到自洽 hash；这与 `validate_trusted_training_source` 所声称的 canonical full training source 不一致。
- **训练随机种子没有进入统计对象。** baseline contract 要求 seeds `17/29/43`，但 `PolicyImageOutcome`、operating-point artifact 和 constrained bootstrap 都没有 seed 字段。当前代码无法区分“一个 seed 上显著”与“三个训练重复稳定”，也无法传播训练随机性。
- **Step 005 的实体级 OOF 审计仍未完成。** 文档正文仍保留 scene-group 旧描述，现有 plan/cache schema 没有 `(seed,candidate_id,control_type,checkpoint_sha,training_manifest_sha,config_sha,code_commit)`，也没有真实文件存在性与内容 hash 校验。
- **核心干预数据仍没有构建器和产物。** 当前新增的是 source/provenance/coverage infrastructure；`build_interventions.py`、predicate-clean captions、local error JSONL、mask references 和 natural-error audit 仍不存在。研究问题本身尚未进入可运行状态。

## 3. 🔍 强CCF-C维度深度审查

### 问题与动机

问题定义已经足够清楚：自动 caption 含局部可验证错误时，在冻结的纯视觉候选与图文候选之间做区域选择，并在 clean utility 约束下控制尾部退化。该问题比早期“安全语言深度”叙事具体得多，也具备自动化否证路径。

但真实动机仍未成立。当前没有任何自然 caption error prevalence、predicate precision 或 D0-relative severity 结果；VKITTI2 只能提供合成场景和结构化压力测试，不能替代真实 captioner 错误证据。若最终 natural-error slice 欠功效，论文标题、摘要和结论必须限定为 **controlled local-caption stress testing**。

### 技术完备性

1. **统一全图风险与局部训练权重。** 对 official crop 全部有效像素，定义每个 eligible region 的权重为 `valid_pixels(region)/valid_pixels(full_crop)`；不满足 eligibility 的区域固定使用 D0，其 regret 为 0。只有这样，region-wise loss 求和才等于主表的 full-image AbsRel difference。

2. **约束必须针对同一总体。** 训练 batch 目前按 cluster 等概率抽样、每 cluster 最多 4 图，而评测的 retention/CVaR 是 image-weighted。若不做 inverse-probability weighting，batch constraint 与最终 estimand 不同。作者必须在 cluster-balanced 与 image-weighted 两种 estimand 中冻结一个主定义，并让训练采样、dev threshold、internal-test risk 使用同一权重。

3. **dev 可行性不能只用点估计。** 从 21 个 thresholds 中筛选 retention 时，应使用 dev cluster bootstrap 的 one-sided lower bound，或预注册可验证的 margin。否则 threshold search 会系统性偏向“刚好达到 0.80”的噪声点。

4. **test utility 必须显式判定。** 冻结 threshold 后，internal-test 必须同时报告 retention 及 cluster CI。若 Main-PR 的 internal-test retention 点估计低于 0.80，应输出 `STOP_TEST_RETENTION_VIOLATION`；不得仍把风险称为 `@Ret>=0.80`。

5. **训练随机性必须进入结果层。** 三个 seeds 需要各自的 expert cache、router、dev threshold 和 test outcome；最终比较应使用 seed×cluster 的分层 paired bootstrap，或至少报告每 seed 的风险差并要求方向一致。

6. **Main-PR 与 Risk-L2D-C 需要真正可执行的唯一差异。** 两者应共享 network、input schema、batch sampler、CVaR、constraint、dual schedule、trial budget 和 threshold calibration；唯一差异只能是 direct advantage target 与 inner-OOF partial-residual target。该条件必须由自动 contract test 检查，而不是只在 Markdown 中声明。

### 实验可信度

- 当前没有真实 JSONL、checkpoint、OOF cache、defect reproduction、Claim-F control、baseline 或 latency，所有科学结论仍为零。
- VKITTI2 只有 5 个独立基础场景；可以进入定性图、结构化错误覆盖和跨域 stress test，但不能被 bootstrap 复制成 20 个独立单位。正式两数据集 claim 在 KITTI local coverage 失败时应停止，除非另一个 outdoor dataset 通过相同独立性门禁。
- CVaR@20% 的 point estimator 当前在 image 层计算。即使 bootstrap 按 cluster 重采样，图像更多的长 sequence 仍对 point risk 权重更高。主表应报告 cluster-balanced CVaR，并把 image-weighted CVaR 作为 sensitivity，或反向明确其应用含义。
- 每个方法独立在 dev 选择 threshold 是合理的，但 artifact 必须绑定其 seed、score table、coverage grid、expert cache、metric spec 和 config；internal-test evaluator必须拒绝手工传入裸 `threshold_index`。
- conditional detectability 只可用于决定样本规模，不能替代真实 pilot。下一步必须运行一个单 seed、20–50 independent clusters 的端到端链路，优先暴露数据、显存、梯度和统计接口问题。

### 叙事克制性

本轮继续保持了较好的克制：Main-PR 不再声称 causal/orthogonal guarantee，hypervolume 被降为 secondary，VKITTI2 的 5-scene 局限也在 response 中被承认。

下一轮需要进一步统一术语：在 internal-test retention 尚未验证前，结果列名使用 `CVaR@Dev-Ret≥0.80`，而不是 `CVaR@Ret≥0.80`；VKITTI2 使用“synthetic structured auxiliary set”，而不是“第二个跨场景验证数据集”。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“仓库已经成为复杂的数据审计框架，但论文核心实验仍不存在。”**
   - 攻击依据：没有干预 JSONL、PyTorch D0/D1、真实 OOF cache、fallback defect、Claim-F controls 或直接 baselines。
   - 现有内容能否扛住：**不能。** 92 个 toy tests 只能证明若干输入合同和标量函数，没有证明方法可训练或问题真实存在。

2. **“你声称在相同 clean utility 下更低风险，但训练和评测的 utility/risk 不是同一个 estimand。”**
   - 攻击依据：eligible-region 权重归一化与 full-image AbsRel 不一致；cluster-balanced batch 与 image-weighted test 不一致；dev retention 只看点估计；test retention 不进入 stop rule。
   - 现有内容能否扛住：**不能。** 这些差异足以让 Main-PR 通过门禁却在真实全图和 test utility 上不成立。

3. **“结果只来自一个幸运 seed 或人工选择的 synthetic frames/outdoor branch。”**
   - 攻击依据：结果数据结构不含 seed；OOF manifest 未绑定真实 checkpoint；VKITTI2 frame index 可由外部提供且只有 5 个独立场景。
   - 现有内容能否扛住：**不能。** 必须建立 seed×cluster 统计、canonical source enumeration 和不可后验选择的数据分支。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 可复现性 | 将 region 权重改为 `valid_pixels(region)/valid_pixels(full_official_crop)`，为所有非 eligible 像素增加固定 D0、零 regret 的 residual mass；在两区域 toy case 中让 eligible 区只覆盖 50% 有效像素 | 技术自洽性；当前训练局部风险与主表 full-image AbsRel regret 不等价 | 新单测中局部 regret=0.2、覆盖50%时 full-image regret 必须等于0.1；`main_pr_objective` 与从像素直接计算的结果绝对差 `<1e-8` | `paper1/experiments/covol/main_pr_objective.py`, `paper1/steps/014_objective_and_algorithm_spec.md`, `paper1/steps/metrics_spec.md`, `paper1/tests/test_main_pr_objective.py` |
| P0 | 可复现性 | 在 dev threshold 筛选中对 retention 执行 10,000 次 cluster bootstrap，只有 one-sided 95% lower bound `>=0.80` 的 threshold 才进入 CVaR 排序；删除只看点估计的可行性判定 | clean-utility 公平性；threshold search 会偏向噪声可行点 | 新测试构造 point retention=0.81、LCB=0.76，函数必须返回 `STOP_NO_FEASIBLE_DEV_THRESHOLD` | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/tests/test_constrained_evaluation.py` |
| P0 | 可复现性 | 在 internal-test evaluator 中计算冻结 threshold 的 retention、95% cluster CI 和 constraint status；Main-PR retention 点估计 `<0.80` 时返回 `STOP_TEST_RETENTION_VIOLATION`，并将正式列名改为 `CVaR@Dev-Ret>=0.80` | 贡献匹配性；风险比较必须证明 test utility 没有坍塌 | 生成结果行包含 test retention/CI/status；toy test 中 test retention=0.78 时不输出 Claim-M PASS | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/steps/008_canary_decision.md`, `paper1/tests/test_constrained_evaluation.py` |
| P0 | 可复现性 | 为 `PolicyImageOutcome`、operating-point artifact 和 OOF cache 增加 `seed`；每个 seed 独立冻结 threshold，并实现 seed×cluster 两级 paired bootstrap | 结果稳定性；当前统计完全忽略训练随机性 | 三个 seeds 每个图恰有一行；缺失或重复 seed 硬失败；输出 per-seed 风险差和 pooled hierarchical CI，三个 seed 方向必须一致 | `paper1/experiments/covol/bootstrap.py`, `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/cache_oof_experts.py`, `paper1/tests/test_cluster_bootstrap.py` |
| P0 | 可复现性 | 扩展 expert manifest 主键为 `(dataset,image_id,seed,candidate_id,control_type)`，逐行记录 checkpoint/config/training-manifest/code-commit/cache 文件路径与实际 SHA256；validator 打开文件重新计算 hash | OOF 可审计性；自洽 JSON 不能证明真实模型未见 prediction cluster | 篡改任一 checkpoint/cache 字节后 validator 非零退出；D0/D1/twins/shuffled 三 seeds 行数完整 | `paper1/experiments/covol/cache_oof_experts.py`, `paper1/tests/test_expert_cache_no_leakage.py`, `paper1/steps/005_frozen_experts.md` |
| P0 | 实验补充 | 新建 `build_expert_training_manifest.py`，冻结每个 OOF/final expert 的训练 cluster、图像、predicate-clean caption、captioner revision/hash 和 valid-depth target；禁止使用没有 caption 的 D1 训练行 | 数据合同完整性；当前 expert 使用哪些 official-training 图像与 caption 尚未闭合 | `expert_training_manifest.jsonl` 中 D1 caption 缺失率=0、prediction cluster overlap=0，D0/D1 每对训练图像集合完全相同 | `paper1/experiments/covol/build_expert_training_manifest.py`, `paper1/artifacts/covol/expert_training_manifest.jsonl`, `paper1/steps/005_frozen_experts.md` |
| P0 | 实验补充 | 实现 PyTorch `dual_candidate_depth.py` 与 32-sample smoke，D0 使用 learned-null token，D1 使用 caption embedding，两个路径逐层同构；连续 10 个 batch 记录 active-gradient 参数 | 技术完备性；learned-null 公平合同目前仅存在于 YAML | D0/D1 trainable 参数名与 shape 完全一致；两者至少95% trainable 参数在10个 batch 内出现非零有限梯度；保存重载误差 `<1e-6` | `paper1/experiments/covol/models/dual_candidate_depth.py`, `paper1/experiments/covol/train_expert.py`, `paper1/tests/test_dual_candidates.py` |
| P0 | 可复现性 | 实现可微 Main-PR 与 Risk-L2D-C 训练 step，使用同一 router architecture、batch indices、CVaR、constraint、dual schedule 和 optimizer；仅 target construction 不同 | Baseline 公平性；scalar helper 不能证明实际训练差异唯一 | `test_main_vs_risk_contract.py` 自动断言参数、输入列、batch、risk、threshold budget相同；两种 target 的 SHA 不同；所有梯度有限 | `paper1/experiments/covol/train_router.py`, `paper1/experiments/covol/main_pr_objective.py`, `paper1/tests/test_main_vs_risk_contract.py` |
| P0 | 可复现性 | 在 `features.py` 中定义并导出 allowlist 中的三个 extractor callable，validator 用 `importlib` 验证函数存在；extractor 只能接收 sanitizer 返回的 mapping | 特征防泄漏；当前 allowlist 可引用不存在的函数 | 未注册/不存在 callable 硬失败；向原始 record 添加 GT、loss、error metadata 后 extractor 输出逐元素不变 | `paper1/experiments/covol/features.py`, `paper1/tests/test_feature_schema_no_intervention_metadata.py` |
| P0 | 实验补充 | 实现 `build_interventions.py`，从冻结 manifest 生成 predicate-clean、四类 local families、null diagnostic、target mask 引用和 machine-check；按 cluster/template/captioner/error-family 执行泄漏审计 | 问题真实性与可执行性；当前只有 source infrastructure，没有核心 caption 数据 | pilot 行数与 Step 003 公式完全一致；local machine-check pass=100%；null 不进入 local CVaR；所有泄漏计数为0 | `paper1/experiments/covol/build_interventions.py`, `paper1/data/covol/intervention_manifest.json`, `paper1/steps/003_intervention_dataset.md` |
| P0 | 叙事修正 | 将 VKITTI2 在 dataset decision 中固定为 `synthetic_structured_auxiliary_only`；只有 outdoor dataset 的独立 cluster 数 `>=20` 且通过相同 coverage/provenance 门禁时才可进入第二个 inferential local dataset，否则 two-dataset Claim-M 返回 STOP | 贡献克制性；VKITTI2 只有5个基础场景，不能支撑跨场景推断 | 配置中不存在 `GO_LOCAL_CLAIMS_NYUV2_VKITTI2` 的 inferential PASS；测试确认5 clusters只能生成 descriptive status | `paper1/configs/covol/dataset_fallback_decision.yaml`, `paper1/steps/003_intervention_dataset.md`, `paper1/steps/004_defect_reproduction.md`, `paper1/steps/008_canary_decision.md` |
| P0 | 可复现性 | 删除 VKITTI2 adapter 对任意外部 frame subset 的信任；扫描官方解压目录生成 canonical full-source manifest，校验每个 scene/variation/camera 的 frame index 集，再由固定 hash 从 full manifest 选择 pilot | 数据不可后验选择；当前 `frame_index_path` 可承载观察结果后的挑帧 | full-source manifest 的文件集合由目录内容唯一决定；删除/添加一行自定义 frame index 均使 provenance audit 失败 | `paper1/experiments/covol/build_vkitti2_source_manifest.py`, `paper1/experiments/covol/audit_provenance.py`, `paper1/tests/test_build_vkitti2_source_manifest.py` |
| P1 | 实验补充 | 同时实现 cluster-balanced 与 image-weighted CVaR；冻结 cluster-balanced CVaR 为 Claim-M 主指标，先在 cluster 内平均 image risk，再对 clusters 取上尾20% | 统计单位一致性；长 sequence 不应因图像更多而控制 point estimate | 结果表包含两种 CVaR、tail cluster count、最大单 cluster tail mass；复制同一 cluster 图像不改变 cluster-balanced CVaR | `paper1/experiments/covol/metrics.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/steps/metrics_spec.md`, `paper1/tests/test_cluster_bootstrap.py` |
| P1 | 可复现性 | 扩展 operating-point artifact，绑定 seed、expert-cache SHA、raw-dev-outcomes SHA、threshold-grid values/SHA、metric-spec SHA、minimum-clean-gain artifact与代码 commit；新增 read/verify 函数，internal-test 只接受验证后的 artifact | 可复现性；裸 threshold index 可被套用到另一方法或结果表 | 修改任一 lineage 文件后 evaluator 拒绝运行；artifact 可唯一恢复 method/seed/threshold | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/tests/test_constrained_evaluation.py` |
| P1 | 消融补全 | 对同一 expert cache 运行 soft expected-risk、straight-through hard 和 train/infer hard 三个版本，固定 seeds/trials，报告 test retention、CVaR、WorstOf3、边界误差与 latency | 方法有效性；训练 surrogate 必须转化为 deterministic hard routing 收益 | 生成 `ablation_relaxation_gap.csv`；若 hard Main-PR 不优于 Risk-L2D-C，则 Claim-M 不成立 | `paper1/experiments/covol/run_ablation.py`, `paper1/results/covol/ablation_relaxation_gap.csv`, `paper1/steps/009_component_ablation.md` |
| P1 | 实验补充 | 为 TIGER-style LOO、Regression-L2D、DR-PostHoc-L2D、Dense-Coherence-L2D、LOO-Uncertainty 各新增一份 adaptation card，列出原公式、CoVoL 变量映射、faithful 参数、matched 参数和 sanity test | Baseline 忠实性；方法名和 objective 标签不足以证明公平复现 | 五份 card 均含可执行 config 与至少一个原论文性质回归测试；缺任一项时 Claim-M 状态保持 PENDING | `paper1/baselines/adaptation_cards/`, `paper1/configs/covol/baseline_contract.yaml`, `paper1/steps/007_fair_gate_baselines.md` |
| P1 | 可复现性 | 生成 Python/CUDA/PyTorch lock、CPU GitHub Actions 和 A800 environment manifest；CI 执行 Ruff、Black、Pytest，GPU manifest记录driver/CUDA/cuDNN/torch与checkpoint SHA | 强CCF-C可复现性；当前只有本机下界依赖和口头测试结果 | CPU CI 在当前 commit 上绿色；远端环境文件可重建依赖；`pip/conda` 解算不使用浮动版本 | `paper1/environment/`, `.github/workflows/paper1-ci.yml`, `paper1/pyproject.toml`, `paper1/README.md` |
| P0 | 实验补充 | 在真实数据门禁通过后运行一个 seed、20–50 independent clusters 的端到端 pilot：source→split→caption/intervention→D0/D1→OOF cache→fallback defect→Risk-L2D-C/Main-PR constrained comparison | 最小科学闭环；继续增加审计代码不能替代可运行证据 | 生成 `pilot_manifest.json`、两个 checkpoint、OOF cache、`fallback_defect_pilot.csv`、`constrained_risk_pilot.csv` 和完整运行日志；任一步失败记录 STOP/ITERATE | `paper1/scripts/run_end_to_end_pilot.sh`, `paper1/results/covol/pilot/`, `paper1/steps/004_defect_reproduction.md`, `paper1/steps/008_canary_decision.md` |
