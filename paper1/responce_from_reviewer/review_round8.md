# Review Round 8

## 1. 🎯 强CCF-C达标判定

- **当前状态**：未达标；本轮没有检测到 Round 7 之后的作者回应或 `paper1/steps/` 增量，因此无法认定 Round 7 审稿意见已经在远程 `paper1` 分支中落实。
- **核心差距**：远程 `paper1` 分支在本轮审查开始时仍停留在提交 `16aa4ce99cc5ed838d92b60124c67fe06ac749c9`（`review: add round 7 strong CCF-C assessment`），响应目录中不存在 `response_round7.md` 或 `responce_round7.md`；科学层面则仍停留在 `STOP_TWO_DATASET_CLAIM`、无 intervention corpus、无公平 D0/D1、无 OOF cache、无缺陷复现和无方法结果的状态。
- **C类顶流潜力**：否。当前问题定义和审计纪律较成熟，但尚未形成可运行方法和核心实验。即使后续结果为正，Main-PR 仍需通过同输入、同风险目标的直接 defer baselines 才能达到普通强 CCF-C；现阶段不具备 Best Paper Nomination 所需的独立机制与实证强度。

### CCF-C 基线距离量化

下表是按仓库当前可验证产物给出的**论文成熟度审稿估计**，不是录用概率。普通 CCF-C 基线指“问题清楚、方法可运行、实验完整且可复现，创新不必达到 CCF-B”。

| 维度 | 当前成熟度 | 普通 CCF-C 基线 | 差距 | 审稿依据 |
| --- | ---: | ---: | ---: | --- |
| 问题定义与动机 | 80/100 | 75/100 | 已过基线约 5 分 | 任务已收缩为局部 caption error 下的冻结候选替换，overclaim 已大量移除；但 Step003 后的最终范围尚未冻结 |
| 方法完整性 | 30/100 | 65/100 | 35 分 | 有数学规范和失败门禁，但没有 PyTorch D0/D1、Main-PR、Risk-L2D-C、训练 manifest 或可微端到端实现 |
| 实验证据 | 10/100 | 70/100 | 60 分 | 仅有数据可行性负门禁；没有 intervention validity、H-sensitivity、H-fallback、Claim-F、Claim-M、baseline 或消融结果 |
| 可复现性 | 45/100 | 65/100 | 20 分 | source/split/provenance/replay 审计较强，但没有模型 checkpoint、环境 lock、训练命令和一键复现主表 |
| 写作与论文产物 | 35/100 | 65/100 | 30 分 | claim language 克制，但没有完整论文稿、结果表、图、limitations 与实验叙事闭环 |

按“问题 15% / 方法 25% / 实验 35% / 可复现性 15% / 写作 10%”加权，当前约为 **34/100**；普通 CCF-C 可投稿基线约为 **69–70/100**，尚差约 **35–36 个成熟度点**。从关键工作量看，仍缺约 **60%–70% 的论文核心闭环**，其中绝大部分不是继续写协议，而是生成 corpus、训练候选、运行公平基线和获得稳定结果。距离“强 CCF-C”约 **45 分以上**。

## 2. 🔄 改进效果评估

本轮无法针对 Round 7 的最新修改做内容级验收，因为远程分支不存在相应 response 或增量 commit。以下只审计可见状态。

### ✅ 有效改进

- **本轮无新增可验证改进。** Round 7 已审过的 Step003 真实负门禁、NYUv2 coverage、KITTI 当前 source 失败、VKITTI2 auxiliary-only 定位和统计合同仍保留，但它们均早于 `review_round7.md`，不能重复计为本轮回应。
- 现有仓库继续明确区分数据可行性证据与算法证据，没有把 A800 CUDA canary、toy tests 或 coverage pass 写成 Claim-F/Claim-M 结果；这一研究纪律仍然正确。

### ⚠️ 部分解决

- Round 7 已要求在 `STOP_TWO_DATASET_CLAIM` 后冻结新范围，但当前 `001_primary_scope_lock.md` 仍把 Claim-M 写成活跃的 `UNVERIFIED METHOD HYPOTHESIS`；没有 `015_post_step003_scope_decision.md` 或等价机器可读决策。
- Round 6 冻结的 full-crop weighting、cluster-balanced estimand、retention LCB、test-retention stop、seed-aware artifact lineage 和实体级 OOF 合同仍只存在于步骤文档，当前代码实现状态没有新增证据。
- NYUv2 已证明局部 mask/depth coverage 足够，但 diagnostic intervention corpus、predicate precision 和 H-sensitivity 仍未生成，因此“问题真实性”未被验证。

### ❌ 无效/偏离

- 用户所称“Round 7 的回应以及做出的改变”没有出现在远程 `paper1` 分支。审稿流程无法从本地未 push 内容、其他未声明分支或口头说明推断已完成工作。
- 响应目录仍只有 `responce_round6.md`，没有 Round 7 response；分支 HEAD 在本轮评审前正是审稿人创建 `review_round7.md` 的提交。缺少“审稿意见—作者回应—代码/步骤变更—验证产物”的可审计链路。
- 在当前状态下继续提交新的方法规范、GPU 调度或 provenance 代码，不能弥补 corpus、模型和实验结果缺失，也不会提高 CCF-C 的实验评分。

## 3. 🔍 强CCF-C维度深度审查

### 问题与动机

问题本身已经达到 CCF-C 所需的清晰度：自动 caption 含局部、可验证错误时，在冻结的 D0/D1 之间做区域替换，并约束 clean utility、控制尾部 regret。真正未解决的是**研究范围已经因真实数据门禁停止，却没有选择新主线**。

当前必须在以下两条路线中冻结一条：

1. `RECOVER_TWO_REAL_DATASETS`：引入第二个真实数据集，满足 RGB、metric depth、local mask、至少 20 个独立 clusters、可复现 source revision 与许可；恢复算法型 Claim-M。
2. `RESCOPE_NYUV2_CONTROLLED_ANALYSIS`：只在 NYUv2 official-train 上做 controlled local-caption stress test，把 Claim-M 降为分析性探索，重点验证 Claim-F、caption intervention validity 和强 direct baselines。

若继续保持当前双数据集 Claim-M 又不提供第二数据集，论文逻辑上没有可执行实验路径。若直接用单个 NYUv2 支撑通用算法论文，实验广度又明显低于普通 CCF-C 基线。

### 技术完备性

- 当前没有可训练的双候选。数学目标、OOF 合同和缓存 schema不能替代 `dual_candidate_depth.py`、训练脚本、checkpoint、forward/backward smoke 和实际 cache。
- Main-PR 与 Risk-L2D-C 的唯一差异仍未通过 executable contract test 固定。若两者在网络、batch、risk、constraint、threshold 或搜索预算上存在其他差异，Claim-M 无法归因。
- full-crop risk 权重必须进入代码：eligible region 权重分母是整张 official crop 的有效像素数，未覆盖部分固定走 D0。旧 scalar helper 若继续要求 region weights 和为 1，会与主指标不一致。
- cluster-balanced estimand、dev retention LCB、test-retention stop 和 per-seed artifact 必须形成同一 evaluator；不能让 Markdown 使用新口径、代码继续使用旧 image-weighted 点估计。
- feature firewall 中登记的 extractor 必须是真实可 import callable，且运行时只接收 sanitizer 输出。字符串 allowlist 不能证明训练代码没有读取 GT 派生信息。

### 实验可信度

当前唯一真实实验结论是：**当前冻结 KITTI source 无法支持局部 oracle，NYUv2 可支持局部 oracle 构造。** 这是一项有价值的 feasibility 结果，但不足以进入论文主结果。

普通 CCF-C 最少还需要以下证据链：

1. diagnostic intervention validity：machine-check、人工独立 precision、text-only artifact test；
2. H-sensitivity：错误 caption 相对 predicate-clean caption 的配对退化；
3. 公平 D0/D1 clean gain 与 H-fallback-defect；
4. B-direct/C-direct/two C-permuted Claim-F controls；
5. Main-PR 相对 Risk-L2D-C 和直接 published adaptations；
6. 三个以上训练重复、cluster CI、消融、边界伪影和延迟；
7. 至少一个独立数据集或明确的单域限定与第二 backbone/captioner 泛化。

当前完成的是上述链路之前的数据可用性筛查，因此实验成熟度约为 CCF-C 基线的六分之一以下。

### 叙事克制性

现有 claim language 总体克制，但状态命名需同步真实门禁：

- 当前 Claim-M 应写为 `STOPPED_CURRENT_DATA_BRANCH`，而不是继续写活跃 `UNVERIFIED`；
- NYUv2 结果只能称 `local-oracle feasibility PASS`，不能称 intervention 或 robustness 已建立；
- KITTI 结论必须限定为“当前冻结 source 失败”；
- 若采用 NYUv2 单数据集，标题、摘要和贡献必须包含 `controlled`、`indoor`、`single-domain` 等限定；
- CUDA canary 和 scheduler 只进入复现附录，不进入贡献。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“作者声称已回应审稿，但远程分支没有 response 或任何新 commit。”**
   - 攻击依据：`paper1` HEAD 在本轮开始时仍为 `16aa4ce…`，响应目录没有 Round 7 文件。
   - 现有内容能否扛住：**不能。** 这是版本管理和可审计性问题；必须先同步远程内容。

2. **“当前研究分支已经被数据门禁停止，论文却仍把算法 Claim-M 当活跃主张。”**
   - 攻击依据：`STOP_TWO_DATASET_CLAIM` 与 `001_primary_scope_lock.md` 的活跃 Claim-M 并存，没有后 Step003 范围决策。
   - 现有内容能否扛住：**不能。** 审稿人无法判断论文究竟是双数据集算法论文还是 NYUv2 单域分析。

3. **“没有论文核心实验，只有数据审计和方法规范。”**
   - 攻击依据：无 corpus、D0/D1、OOF cache、H-defect、Claim-F、baseline、消融或结果表。
   - 现有内容能否扛住：**不能。** 这是距离 CCF-C 基线最大的实质差距，任何写作包装都无法替代。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 可复现性 | 将 Round 7 作者回应新建为 `response_round7.md`，把每项回应链接到实际 commit、文件和验证产物；将本地修改 push 到 `paper1` 分支，并确认分支 HEAD 严格晚于 `16aa4ce99cc5ed838d92b60124c67fe06ac749c9` | 强CCF-C要求改进闭环可审计；当前远程没有本轮回应或增量 | GitHub 上能读取 `response_round7.md`；`compare_commits(16aa4ce, paper1)` 至少返回 1 个新增 commit 和对应 paper1 文件 diff | `paper1/responce_from_reviewer/response_round7.md` |
| P0 | 叙事修正 | 新建 Step003 后范围决策文件，`decision` 字段只能取 `RECOVER_TWO_REAL_DATASETS` 或 `RESCOPE_NYUV2_CONTROLLED_ANALYSIS`；同步修改 `001_primary_scope_lock.md`、Idea、README 和 Step 008，使 Claim-M 状态与该 decision 一致 | 强CCF-C要求唯一、可执行的问题范围；当前 STOP 与活跃 Claim-M 矛盾 | 四个入口文件读取到同一 decision；仓库全文不再同时出现 `STOP_TWO_DATASET_CLAIM` 和活跃双数据集 Claim-M | `paper1/steps/015_post_step003_scope_decision.md`, `paper1/steps/001_primary_scope_lock.md`, `paper1/ideas/01_counterfactual_value_of_language_depth.md`, `paper1/steps/008_canary_decision.md` |
| P0 | 实验补充 | 若选择 `RECOVER_TWO_REAL_DATASETS`，预注册最多 3 个真实候选数据集，按固定顺序审计 RGB、metric depth、local mask、许可、source revision、独立 cluster 数和 coverage；选择第一个全部通过者，禁止读取方法结果后择优 | Baseline 外部有效性与数据可复现性；当前第二数据集缺失 | 生成候选审计 CSV；被选数据集有 ≥150 eligible images、≥300 eligible pairs、≥20 independent clusters，并记录 source/hash/license | `paper1/configs/covol/second_dataset_candidates.yaml`, `paper1/results/covol/second_dataset_candidate_audit.csv`, `paper1/steps/015_post_step003_scope_decision.md` |
| P0 | 叙事修正 | 若选择 `RESCOPE_NYUV2_CONTROLLED_ANALYSIS`，将 Claim-M 标为 `ANALYSIS_ONLY_UNVERIFIED`，删除双数据集 Paper Candidate 门禁，并把允许的最强结论限定为 NYUv2 indoor controlled stress testing | 贡献克制性；单数据集不能支撑当前通用算法主张 | `001/008/011` 不含跨域、outdoor 或 two-dataset 算法录用主张；标题候选包含 `Controlled` 与 `Indoor` | `paper1/steps/001_primary_scope_lock.md`, `paper1/steps/008_canary_decision.md`, `paper1/steps/011_claim_language_revision.md` |
| P0 | 实验补充 | 从 NYUv2 official-train 固定 100 张图生成 diagnostic corpus：每图 4 families×3 variants，共 1,200 行；只使用 train split，不进入 router 训练或论文主结果 | 问题真实性和 intervention validity 是后续方法实验前提 | `diagnostic_interventions.jsonl` 恰有 1,200 行、主键唯一、machine-check 100% PASS、scene/template 泄漏为 0 | `paper1/experiments/covol/build_interventions.py`, `paper1/data/covol/diagnostic_interventions.jsonl`, `paper1/results/covol/diagnostic_intervention_audit.json` |
| P0 | 实验补充 | 对 diagnostic corpus 随机抽取 100 条，由与生成规则独立的 parser/grounding revision 验证 target change、non-target preservation 和 relation correctness；同时训练 text-only family classifier | 强CCF-C要求数据标签可信且排除模板伪影 | predicate precision 下界 ≥0.95；text-only held-out-template macro-F1 ≤0.60，否则重写模板并重新生成全 corpus | `paper1/experiments/covol/audit_intervention_validity.py`, `paper1/results/covol/intervention_precision.csv`, `paper1/results/covol/text_artifact_control.csv` |
| P0 | 实验补充 | 使用锁定 TR2M checkpoint 在 100-image corpus 上运行 predicate-clean 与 12 个 local variants，按 cluster 做 10,000 次 paired bootstrap；单独报告 semantic-preserving | 问题真实性门禁；没有 caption-induced degradation 就不应训练 router | 至少一个 conflict family 的 `D1_corrupt-D1_clean` region AbsRel CI 下界 >0，且 semantic-preserving CI 包含 0；否则记录 `STOP_H_SENSITIVITY` | `paper1/experiments/covol/run_sensitivity_diagnostic.py`, `paper1/results/covol/sensitivity_diagnostic.csv`, `paper1/steps/004_defect_reproduction.md` |
| P0 | 消融补全 | 修改 full-crop risk helper，使 region weight 和允许小于 1；新增“50% eligible coverage、局部 regret 0.2、全图 regret 0.1”单元测试 | 指标一致性；训练风险必须与主表 full-image AbsRel 同尺度 | 测试输出严格为 0.1，旧权重归一化行为触发失败；Ruff/Black/Pytest 通过 | `paper1/experiments/covol/main_pr_objective.py`, `paper1/tests/test_main_pr_objective.py`, `paper1/steps/metrics_spec.md` |
| P0 | 可复现性 | 为 Step 004–008 增加统一 authorization loader，只有 `status=PASS` 且 `decision` 匹配当前 scope 才允许运行；FAIL artifact 中即使含 NYUv2 数组也必须硬失败 | 防止下游绕过停止门禁；强CCF-C要求执行协议可审计 | 对当前 `STOP_TWO_DATASET_CLAIM` artifact 调用 Step005/006/008 均退出非零；对合法新 scope artifact 才返回授权 | `paper1/experiments/covol/scope_authorization.py`, `paper1/tests/test_scope_authorization.py` |
| P1 | 可复现性 | 实现实体级 expert training/cache manifest，主键固定为 `(dataset,image_id,seed,candidate_id,control_type)`，打开实际文件重算 checkpoint/config/data/code/cache SHA | OOF 公平性和复现性；当前旧 validator 不能证明真实模型未见 prediction cluster | 缺行、重复、cluster overlap、路径越界或任一实际 hash 不符均硬失败；三个 seeds×formal/twins/shuffled 覆盖完整 | `paper1/experiments/covol/build_expert_training_manifest.py`, `paper1/experiments/covol/cache_oof_experts.py`, `paper1/tests/test_expert_cache_no_leakage.py` |
| P1 | 实验补充 | 在数据范围重新 GO 后，实现 shared-backbone D0/D1 和 learned-null token，运行 32 样本 forward/backward smoke；逐层比较 active-gradient parameter mask | 方法完整性与候选公平性；当前只有合同没有模型 | D0/D1 层名、shape、参数量、active-gradient mask 完全相同；D0 caption permutation 不变，D1 至少一例改变；保存重载误差 <1e-6 | `paper1/experiments/covol/models/dual_candidate_depth.py`, `paper1/experiments/covol/train_expert.py`, `paper1/tests/test_dual_candidates.py` |
| P1 | 消融补全 | 实现 cluster-balanced weighted CVaR、dev retention one-sided LCB、test-retention stop 和逐 seed结果；三个 seeds 作为固定重复分别报告 cluster CI，不对 3 个 seeds 声称稳定 seed-population bootstrap | 统计可信度；当前规范与实现不一致且 seed 数过少 | 单测覆盖不等 cluster size、LCB 筛选、test retention <0.80 STOP；结果表含每 seed point/CI 和三 seed 同向字段 | `paper1/experiments/covol/metrics.py`, `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/tests/test_constrained_evaluation.py` |
| P1 | 实验补充 | 为 Main-PR 与 Risk-L2D-C 建立 executable contract，逐项比较 network、features、batch indices、optimizer、CVaR、constraint、dual、trial 和 threshold config，只允许 target-construction 字段不同 | Baseline 公平性；Claim-M 必须归因于 partial-residual target | 自动测试确认除 `target_construction` 外所有字段逐项相等；任一额外差异使训练启动失败 | `paper1/configs/covol/baseline_contract.yaml`, `paper1/experiments/covol/train_router.py`, `paper1/tests/test_main_vs_risk_l2d_contract.py` |
| P1 | 文献增补 | 在第一次真实模型训练前重新检索 2026 年最新的 dense defer、multimodal reliability routing、post-hoc expert selection 和 language-guided depth robustness工作，并更新重叠矩阵 | CCF-C贡献边界必须基于最新直接近邻 | 审计日期更新；每个 Claim-M 主张对应至少一个 direct baseline 或明确差异；发现同构方法时触发范围重判 | `paper1/steps/002_related_work_audit.md` |
| P1 | 可复现性 | 从干净的 `paper1` 基线新建 artifact 分支，只 cherry-pick paper1 相关 commit，不包含无关 `tools/` 大规模删除；添加 paper1 CI 执行 Ruff、Black、Pytest | 复现包应最小、可审；当前分支 diff 被无关文件污染 | `git diff` 仅含 paper1 与必要根配置；CI 对最新 commit 显示 PASS；失败日志可下载 | `.github/workflows/paper1-ci.yml`, `paper1/README.md` |
| P2 | 写作规范 | 在获得 H-sensitivity 和公平 D0/D1 结果后再建立论文骨架，Intro 中每个动机句链接到对应结果，禁止使用 feasibility coverage 替代语言鲁棒性证据 | 写作规范与证据匹配；当前尚不适合进入 Paper Build | 论文骨架含 Problem/Method/Experiment/Limitations；所有量化主张能追溯到结果文件和 CI | `paper1/paper/outline.md`, `paper1/paper/evidence_map.md` |
