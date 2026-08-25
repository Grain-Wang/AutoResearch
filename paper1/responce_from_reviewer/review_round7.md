# Review Round 7

## 1. 🎯 强CCF-C达标判定

- **当前状态**：未达标；原始 `NYUv2 + KITTI` 双数据集算法主线已经进入 `STOPPED_CURRENT_DATA_BRANCH`，而不是普通的“继续实现中”状态。
- **核心差距**：Step 003 已用真实 official-training 数据证明当前冻结的 KITTI source 无法提供局部 mask/depth oracle，但仓库尚未冻结新的可执行研究范围，也没有 intervention corpus、公平 D0/D1、OOF cache、缺陷复现、Claim-F 或 Claim-M 结果。
- **C类顶流潜力**：否。真实负门禁、审计纪律与停止条件体现了较好的研究质量，但 Main-PR 剩余差异仍是 partial residual、clean constraint 与 CVaR 的任务化组合；在没有第二个真实 inferential dataset、完整 killer baselines 和跨 seed 稳定实证前，不具备 Best Paper Nomination 所需的独立机制突破。

## 2. 🔄 改进效果评估

本轮首次出现了可改变研究决策的真实数据证据。`paper1/results/covol/annotation_coverage.json` 与 `step003_feasibility_gate.json` 不再是 toy fixture：NYUv2 的局部 oracle coverage 通过，当前冻结的 KITTI source coverage 为零，调度器按合同阻断后续 detectability 与模型实验。该处理比为了推进论文而绕过负结果更可信。

### ✅ 有效改进

- **Step 003 真实门禁闭环成立**：只读取 official-training material，固定 500/500 图像，按不可拆分 cluster 划分，并记录 source manifest、pilot manifest、split audit、coverage 与 deterministic replay hash。NYUv2 获得 500 个 eligible images、105779 个 depth-separated pairs 和 156 个独立 eligible clusters；当前 KITTI source 为 0/0/0。
- **负结果没有被改写成正结果**：`STOP_TWO_DATASET_CLAIM`、`Claim-M STOPPED`、power 未运行、Step 005 未启动均被明确记录；A800 shared CUDA canary 也被限定为执行环境证据，而非算法证据。
- **VKITTI2 的角色得到正确收缩**：所有天气、相机与视角 clone 被归入 5 个基础 scene，且 `dataset_fallback_decision.yaml` 已禁止把 VKITTI2 当作第二个 inferential dataset 或用于挽救失败的 KITTI local gate。
- **Round 6 的统计合同已被准确写入规范**：full-crop weighting、cluster-balanced estimand、dev retention LCB、test-retention stop、per-seed threshold、seed×cluster inference 与实体级 artifact lineage均进入 Step 005/006/008/014 和 metrics spec，并明确标为未实现。
- **状态审计更诚实**：`steps/README.md` 已将指标层改成 `ROUND6-CODE-REVISION-PENDING`，没有继续用旧 scalar tests 冒充新统计协议已经落地。
- **结果可复核性优于上一轮**：远程 CPU 队列的 Ruff、Black、97 tests、coverage gate exit code 和逐字节 replay 被写入可移植结果文件；当前 GitHub commit 本身没有 CI status，但仓库至少保留了远端执行证据与哈希。

### ⚠️ 部分解决

- **当前结果只能否定“冻结的 KITTI source”，不能否定 KITTI 数据族本身**。结果文件的原因是当前 RGB source 没有可信的 local instance-mask/depth oracle；仓库尚未给出当前 500 个 image IDs 与任何可对齐 depth/mask annotation source 的交集审计。因此，“KITTI 分支失败”成立，“KITTI 不可能支持本任务”尚未成立。
- **NYUv2 coverage 只证明局部 mask/depth 条件充足，不证明 intervention corpus 有效**。当前没有 predicate-clean captions、结构化语言编辑、machine-check JSONL、自然错误 prevalence 或 independent precision audit；105779 个实体对不能直接转换成 105779 个自然、语言正确且无模板伪影的干预样本。
- **两数据集要求缺少科学必要性说明**。当前任务本身要求跨数据集可信度，但不天然要求“一室内一室外”。若算法 claim 只写成通用选择性路由，另一个具有独立场景、metric depth 和局部 mask 的真实数据集即可；若坚持 outdoor，则必须把 outdoor generalization 写入问题定义和贡献边界。
- **Round 6 的数学修正仍主要停留在 Markdown**。`main_pr_objective.py`、`constrained_evaluation.py` 与 `bootstrap.py` 仍是旧 image-weighted/point-retention/无 seed schema 的实现；full-crop 50% coverage test、weighted CVaR、retention LCB、test-retention stop 与 hierarchical result schema尚未存在。
- **Claim-F 的政策效用门禁仍强制使用 hypervolume**，而 Step 008 已将 hypervolume 降为 secondary。若全文主张转向固定 clean utility 下的风险，Claim-F 也应使用 dev-frozen constrained operating point，而不是重新把 HV 作为必过主门。
- **三 seed 的 hierarchical bootstrap 统计解释不足**。只有三个训练 seed 时，对 seed 进行非参数重采样不能稳定估计训练随机性分布；当前更可信的做法是逐 seed 报告、要求三者同向，并分别给出 cluster CI，或把训练 seed 增加到至少 5 个后再做 seed-level bootstrap。
- **当前分支含大量与 paper1 无关的 `tools/` 删除和重写**。这不会改变本轮科学判断，但会污染代码审查、复现包和未来合并；论文 artifact 应从干净分支生成。

### ❌ 无效/偏离

- **`001_primary_scope_lock.md` 仍把 Claim-M 写成活跃的 `UNVERIFIED METHOD HYPOTHESIS`，但真实 Step 003 已把当前双数据集分支 STOP**。范围锁、Idea、README 和状态表没有形成一个唯一机器可读的“当前主线已停止、待范围决策”状态。
- **FAIL coverage artifact 中仍保留 `local_claim_datasets: [NYUv2]`**。如果下游只读取该数组而忽略 `status=FAIL` 与 `decision=STOP_TWO_DATASET_CLAIM`，会错误启动单数据集实验。所有 Step 004–008 入口必须验证显式授权字段，而不能靠人工阅读文档。
- **GPU 调度与 shared canary 虽实现正确，但不触及当前核心科学阻塞**。继续投入 queue、exclusive scheduler 或 CUDA canary 不会恢复数据分支，也不会验证 caption intervention、D0/D1 clean gain 或路由价值。
- **当前严格阻断了所有 corpus 工作，形成新的证据死锁**。双数据集 Claim-M 不应启动，但完全可以在 NYUv2 official-train 的小型 diagnostic split 上构建一个不进入论文主结果的 corpus，先否证 caption 编辑自然性、machine-check precision 和 H-sensitivity；这些风险与第二数据集选择相互独立。
- **尚未执行正式范围变更**。当前既没有选择“恢复第二个真实数据集”，也没有选择“收缩为 NYUv2 单数据集 controlled stress test”；继续仅增加协议文件会让项目长期停留在高质量但不可投稿的审计工程状态。

## 3. 🔍 强CCF-C维度深度审查

### 问题与动机

CoVoL-Depth 的细分问题已经清楚：自动 caption 出现局部可验证错误时，在两个冻结 metric-depth candidates 间逐区域选择，并在 clean utility 约束下控制尾部退化。Step 003 的负结果没有否定这个问题，而是证明原定 `NYUv2 + 当前 KITTI source` 的实验实例不可执行。

现在必须区分三个不同命题：

1. **数据可用性命题**：当前 KITTI source 缺少可用 local oracle；该命题已有证据。
2. **问题真实性命题**：真实或受控 caption errors 是否会使 D1 相对 D0 退化；尚无结果。
3. **方法有效性命题**：Main-PR 是否优于 direct defer 与 robust expert；尚无模型或结果。

仓库当前只完成第 1 项。强 CCF-C 不能把第 1 项的严谨负结果当作论文主体，也不能在第 2 项尚未验证时继续扩张第 3 项的算法和统计框架。

对于强 CCF-C 算法目标，优先建议恢复一个第二个真实数据集，但不必把“outdoor”当作无条件硬要求。候选数据必须在方法结果出现前，按固定规则审计对齐 RGB、metric depth、local instance/semantic mask、至少 20 个独立 clusters、许可与可复现 source revision。若固定预算内没有候选通过，应正式停止算法型 Claim-M，而不是无限搜索数据集。

若改为 NYUv2 单数据集 controlled stress test，则论文可以继续验证 Claim-F，但需要同步降低算法主张：至少增加第二 backbone、多个 captioner、held-out error family 和强 direct baselines，标题和摘要不得声称跨域或普适 robustness。以当前窄方法差异，单数据集结果即使为正，也较难达到“强 CCF-C 算法论文”门槛。

### 技术完备性

- **范围决策是当前最高优先级技术依赖**。在 `STOP_TWO_DATASET_CLAIM` 未被正式替换前，Step 005–008 的实现不应被视为主线工作。
- **full-crop risk 合同必须进入代码**：eligible region 权重的分母是 official crop 全部 valid-depth pixels，未覆盖质量固定走 D0；旧 helper 要求权重和为 1，仍与新规范相反。
- **cluster-balanced estimand 必须贯穿训练和评测**：cluster 等权、cluster 内图像等权，不能只在文档中定义而在 scalar metrics 中继续使用 image mean。
- **Claim-F 与 Claim-M 的 policy metric 应统一**：C-direct 相对 B/permuted 的“任务有效增量”应在相同 dev-retention LCB 约束下比较 CVaR/WorstOf3；HV 留作 secondary，避免两个 claim 使用不同成功定义。
- **三 seed 不足以支撑 seed-population bootstrap**：在资源有限时，将 seed 作为固定重复，逐 seed 给 cluster CI、报告均值±标准差并要求同向；若要对 seed 随机性做 CI，则把正式 seed 数增至至少 5。
- **实体级 OOF 合同仍未实现**：必须绑定真实 checkpoint、训练 manifest、config、code commit、cache path 与实际 SHA，而不是继续扩写旧 scene-level plan。
- **intervention corpus 是当前缺失的核心对象**：没有它，predicate-clean、local conflict、relation reversal、held-out family、captioner isolation 和自然错误审计都只是文字。

### 实验可信度

- Step 003 结果本身可信度较高：official-training only、固定 seed、cluster split、source hash、replay hash 和预注册 exit code均有记录。
- 但 `annotation_coverage PASS` 不是 `intervention validity PASS`。NYUv2 需要先生成有限 diagnostic corpus，验证 caption edit 是否只改变目标语义、是否保持其余实体/关系、是否产生可被 text-only classifier 识别的模板伪影。
- 当前 KITTI 失败原因应拆成 depth availability、mask availability、frame alignment、independent cluster 和 license 五列；只有逐项审计后，才能决定补充 annotation source还是放弃当前分支。
- 双数据集分支停止后，不应打开 official benchmark test，也不应训练完整 Main-PR；但使用 official-train 的 100-image diagnostic corpus运行 H-sensitivity 不会污染未来 test，并能快速判定研究问题是否值得恢复。
- 如果重新选择第二数据集，选择规则必须预注册，例如：依次审计 3 个候选，按“coverage pass → cluster 数 →可复现许可”的固定字典序选第一个通过者，禁止看到方法结果后选择更有利的数据集。
- 论文主结果分支应与当前包含大量 `tools/` 变化的分支隔离，确保 artifact diff 只包含 paper1 代码、配置和结果 manifest。

### 叙事克制性

本轮最值得肯定的是，作者没有把真实负结果隐藏，也没有用 VKITTI2 clone 数伪装独立样本。后续叙事需要进一步做到：

- 将“**KITTI 不具备 local oracle**”统一改为“**当前冻结的 KITTI source 不具备本研究要求的 local oracle**”；
- 将 `Claim-M UNVERIFIED` 改成 `STOPPED_CURRENT_DATA_BRANCH`，直到范围锁被明确更新；
- 将 NYUv2 coverage 表述为“local-oracle feasibility”，不得写成 intervention corpus 或语言鲁棒性已经建立；
- shared GPU canary 只放在 reproducibility appendix，不进入方法或实验贡献；
- 如果最终采用 NYUv2 单数据集，标题必须包含 controlled/indoor/single-domain 限定词。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“作者自己的预注册 Gate 已经停止了论文主线，当前没有一个处于运行状态的投稿问题。”**
   - 攻击依据：`STOP_TWO_DATASET_CLAIM`、Claim-M stopped、corpus 未构建、Step 005–008 全部 blocked，但 `001_primary_scope_lock.md` 仍保留原 Claim-M。
   - 现有内容能否扛住：**不能。** 必须先提交范围变更或恢复第二数据集，不能用后续协议修订替代。

2. **“NYUv2 的 mask/depth coverage 只说明可取区域，并不说明 caption 干预正确、自然或与部署错误相关。”**
   - 攻击依据：没有 predicate-clean caption、machine-check corpus、独立 precision audit、text-only artifact baseline、natural-error prevalence 或 H-sensitivity。
   - 现有内容能否扛住：**不能。** 105779 个实体对是候选原材料，不是语言实验数据。

3. **“即使恢复数据，Main-PR 仍可能只是标准 defer 加 partial residual 和 CVaR；作者尚未运行任何公平模型或直接 baseline。”**
   - 攻击依据：没有 D0/D1、clean gain、OOF cache、Risk-L2D-C、TIGER-style LOO、regression/DR/dense baselines或 robust expert。
   - 现有内容能否扛住：**不能。** 只有真实端到端结果能回答，继续增加审计代码不会改变该判断。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 叙事修正 | 新建 post-Step003 范围决策文件，只允许二选一：`RECOVER_TWO_REAL_DATASETS` 或 `RESCOPE_NYUV2_ANALYSIS_ONLY`；以强 CCF-C 算法目标为默认时选择前者，并写明最多审计 3 个真实候选数据集，全部失败即正式 STOP Claim-M | 强CCF-C要求唯一活跃问题和可执行实验范围；当前主线已被 Gate 停止但 001 仍显示活跃 | 生成 `015_post_step003_scope_decision.md`，包含选择、允许任务、禁止任务、退出条件；`001`、README、Idea 和状态表四处状态逐字一致 | `paper1/steps/015_post_step003_scope_decision.md`, `paper1/steps/001_primary_scope_lock.md`, `paper1/README.md`, `paper1/ideas/01_counterfactual_value_of_language_depth.md` |
| P0 | 可复现性 | 新增机器可读 `step003_authorization.json` 和共享 validator；仅当 `status=PASS` 且 `decision=GO_LOCAL_CLAIMS_*` 时允许 Step 004-B/005/006/007/008，当前 STOP artifact 必须使所有入口以固定退出码 3 终止 | 强CCF-C要求失败门禁不能靠人工阅读；当前 FAIL artifact 仍含非空 `local_claim_datasets` | 添加 6 个入口测试，当前 `annotation_coverage.json` 对全部下游返回 `BLOCKED_BY_STEP003/exit 3`；伪造非空数据集数组不能绕过 | `paper1/experiments/covol/step003_authorization.py`, `paper1/tests/test_step003_authorization.py`, `paper1/artifacts/covol/step003_authorization.json` |
| P0 | 实验补充 | 对恰好 3 个预先登记的真实候选数据集运行统一 source/coverage dry-run；每个候选先固定 source revision 和随机 50 图，再检查 RGB、metric depth、local mask、frame alignment、许可及独立 cluster 数 | 强CCF-C要求跨数据集证据可复现且不能按方法结果择优选择 | 生成 `second_dataset_candidate_audit.csv/json`；候选通过标准为 projected full pilot 中 ≥150 eligible images、≥300 pairs、≥20 clusters；按预注册字典序选择第一个 PASS，三个全 FAIL 则 STOP Claim-M | `paper1/experiments/covol/audit_second_dataset_candidates.py`, `paper1/configs/covol/second_dataset_candidates.yaml`, `paper1/results/covol/second_dataset_candidate_audit.json` |
| P0 | 实验补充 | 对当前 KITTI 500 个 `image_id` 分别计算与每个拟议 depth source、instance/semantic-mask source的可对齐交集，主键固定为 drive/camera/frame；逐项报告 depth-only、mask-only、joint 和 ≥32 valid-depth-mask pixels 的数量 | 当前门禁只证明冻结 RGB source 不足；Baseline公平性和数据可信度要求区分“源未下载”与“确实无可对齐标注” | 生成 `kitti_local_oracle_gap.csv`；若 joint eligible ≥150 images 且 ≥20 drives，则更新 adapter 并重跑 Step003；否则写 `CLOSED_CURRENT_KITTI_BRANCH` | `paper1/experiments/covol/audit_kitti_local_oracle_sources.py`, `paper1/results/covol/kitti_local_oracle_gap.csv`, `paper1/steps/003_intervention_dataset.md` |
| P0 | 叙事修正 | 将所有“KITTI 不具备 local oracle”替换为“当前冻结 KITTI source 未提供满足合同的 local oracle”，并把 Claim-M 状态改为 `STOPPED_CURRENT_DATA_BRANCH` | 强CCF-C要求贡献和负结论严格匹配证据；当前措辞可能把 source failure 过度外推为 dataset failure | 全仓搜索不再出现无来源限定的“KITTI 不具备/无法提供”；001、003、005、008 和 response 状态一致 | `paper1/steps/001_primary_scope_lock.md`, `paper1/steps/003_intervention_dataset.md`, `paper1/steps/005_frozen_experts.md`, `paper1/steps/008_canary_decision.md` |
| P0 | 实验补充 | 在 NYUv2 的 official-train `train` split 固定 100 图构建 diagnostic-only corpus：4 个 local families×3 variants，共 1200 rows；null/global 另存，不训练 router、不读取 dev/internal-test | 问题真实性与数据有效性尚未验证；该诊断与第二数据集选择独立且不会污染 test | 生成 `diagnostic_interventions.jsonl` 1200 rows；machine-check 通过率 100%，scene/template 无泄漏；随机 100 条独立人工/规则复核 precision ≥0.95，否则 STOP corpus design | `paper1/experiments/covol/build_interventions.py`, `paper1/data/covol/diagnostic_interventions.jsonl`, `paper1/results/covol/diagnostic_intervention_audit.csv` |
| P0 | 实验补充 | 使用锁定 TR2M released checkpoint 在上述 100 图上运行 004-A：同图 predicate-clean 与四类 corrupted captions 配对，按 frozen cluster 报告 clean→corrupt AbsRel、δ1 和局部区域差值 | 强CCF-C要求先证明定义的问题真实存在；该诊断不依赖公平 D0 | 生成 `sensitivity_diagnostic.csv`；至少一个局部 family 的 paired cluster-bootstrap mean degradation 95% CI 下界 >0，且 semantic-preserving CI 包含 0；否则停止 CoVoL 问题主张 | `paper1/experiments/covol/run_defect_reproduction.py`, `paper1/results/covol/sensitivity_diagnostic.csv`, `paper1/steps/004_defect_reproduction.md` |
| P0 | 可复现性 | 修改 region-risk helper：region weight 使用 `valid_pixels(region)/valid_pixels(full_official_crop)`，允许权重和 <1；未覆盖质量固定为 D0；同时实现 cluster-balanced weighted MeanRegret/WorstOf3/CVaR | 强CCF-C要求训练目标与主评测 estimand 完全一致 | 新增 50% coverage 手算测试得到 full-image regret=0.1；cluster size 不同的手算测试与公式误差 <1e-8；旧权重和必须等于1的检查被删除 | `paper1/experiments/covol/main_pr_objective.py`, `paper1/experiments/covol/metrics.py`, `paper1/tests/test_main_pr_objective.py`, `paper1/tests/test_metrics.py` |
| P0 | 可复现性 | 实现 dev retention one-sided 95% cluster-bootstrap LCB、internal-test retention CI 和 `STOP_TEST_RETENTION_VIOLATION`；Claim-F 与 Claim-M 都使用 dev-frozen constrained operating point，HV 统一降为 secondary | 强CCF-C要求预注册 clean utility 约束在选择和测试阶段均可审计；当前 Claim-F/HV 与 Claim-M 指标不一致 | threshold 恰好 point retention=0.80 但 LCB<0.80 的测试必须被拒绝；test retention<0.80 返回固定 STOP；Step006 不再把 HV 作为必过主门 | `paper1/experiments/covol/constrained_evaluation.py`, `paper1/experiments/covol/bootstrap.py`, `paper1/tests/test_constrained_evaluation.py`, `paper1/steps/006_semantic_incrementality_gate.md` |
| P0 | 可复现性 | 重写 OOF cache schema，主键固定为 `(dataset,image_id,seed,candidate_id,control_type)`；validator 打开 checkpoint/config/training-manifest/cache 文件重算 SHA256，并以 `cluster_id` 检查训练/预测交集 | 强CCF-C要求 stacking 无泄漏且结果可追溯；当前旧 scene-level plan 不满足合同 | 三 seeds×D0/D1/twins/shuffled 的覆盖测试通过；缺文件、假 SHA、跨 cluster、跨 seed threshold 任一情况硬失败 | `paper1/experiments/covol/cache_oof_experts.py`, `paper1/tests/test_expert_cache_no_leakage.py`, `paper1/artifacts/covol/expert_cache_manifest.json` |
| P1 | 实验补充 | 在数据分支恢复后实现 32-sample PyTorch D0/D1 smoke：learned-null D0 与 caption D1 使用同路径，逐层统计 active-gradient parameter count，并验证保存/重载和 caption permutation | 强CCF-C要求专家公平性与实现完整性；当前只有 CUDA 张量 canary | D0/D1 对应层参数量完全相同，active-gradient ratio 差绝对值 ≤0.01；D0 permutation 不变、D1 至少一例变化；重载误差 <1e-6 | `paper1/experiments/covol/models/dual_candidate_depth.py`, `paper1/tests/test_dual_candidates.py`, `paper1/results/covol/dual_candidate_smoke.json` |
| P1 | 可复现性 | 三个训练 seeds 作为固定重复而非 seed-population bootstrap：每 seed 独立冻结 expert/router/threshold，分别报告 cluster CI，主结论要求三 seed 风险差同向；只报告跨 seed mean±SD | 仅三个 seed 时外层非参数 bootstrap不稳定；强CCF-C要求统计解释与重复数匹配 | 删除“seed bootstrap CI”主张；结果表包含 3 个 seed 行、mean、SD 和 direction_pass；任一 seed 反向即 Claim-M FAIL | `paper1/steps/metrics_spec.md`, `paper1/steps/006_semantic_incrementality_gate.md`, `paper1/steps/008_canary_decision.md` |
| P1 | 可复现性 | 为 `candidate_features`、`caption_region_features`、`image_features` 定义真实可 import callable，只接受 sanitized mapping，并为每个输出列记录数值范围、shape 与 source hash | feature firewall 目前仍可引用不存在的字符串函数；强CCF-C要求实现可执行 | `importlib` 可解析三函数；传入额外 GT 字段不进入 callable；输出 schema 与 runtime schema SHA 一致 | `paper1/experiments/covol/features.py`, `paper1/tests/test_feature_schema_no_intervention_metadata.py` |
| P1 | 可复现性 | 从干净基线创建只包含 paper1 研究变化的 release 分支，不携带当前大量 `tools/` 删除；添加 GitHub Actions 仅运行 `ruff check paper1`、`black --check paper1` 和 `pytest paper1/tests` | 强CCF-C代码复现要求审稿 diff 可审计；当前分支存在大量无关变化且 commit 无 CI status | PR diff 中 `tools/` 变更为 0；CI 三项均 green，并保存 Python/依赖版本 artifact | `.github/workflows/paper1-ci.yml`, `paper1/pyproject.toml` |
| P2 | 叙事修正 | 若三个第二数据集候选全部失败，正式切换 `RESCOPE_NYUV2_ANALYSIS_ONLY`：删除 Claim-M Paper Candidate gate，把目标改为 Claim-F 与受控 stress-test 分析；固定两个 backbone、三个 captioner和一个 held-out error family | 单数据集无法支撑当前广泛算法 claim，但仍可能形成普通 CCF-C 分析论文；需要贡献克制性 | 新 scope 文档只保留 Claim-F；标题含 `indoor/controlled`；不得出现跨域、部署安全或通用算法 superiority；重新运行近邻审计 | `paper1/steps/015_post_step003_scope_decision.md`, `paper1/steps/001_primary_scope_lock.md`, `paper1/steps/011_claim_language_revision.md` |

## 本轮结论

本轮最重要的进展不是 Main-PR 更接近完成，而是作者第一次获得了足以停止原实验分支的真实负证据。对强 CCF-C 研究而言，这是正确结果，但它要求立即进行范围决策。下一轮不应继续扩写 queue、provenance 或未授权的 Main-PR 规范；应优先完成“恢复第二个真实数据集”或“正式缩题”中的一个，并用 NYUv2 小型 diagnostic corpus验证研究问题本身。