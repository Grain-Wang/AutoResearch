# Review Round 2 [2026-08-31 15:08:02 UTC]

## 1. 🎯 强CCF-C达标判定
- **当前状态**：**未达标**。相较 Round 1 已从“仅有 oracle 可行性”推进到 `PARTIAL_G0_PASS / W07_EXCLUSIVE_PENDING / NOT_PAPER_CANDIDATE`：问题空间、简单选择器余量和 patch 信息来源均得到更可信的控制实验支持，但尚未形成可投稿算法。
- **核心差距**：当前唯一可能构成论文贡献的“校准 signed utility 分布 + 预算条件选择/弃权 + harmful-action 风险约束”仍停留在协议层，且训练标签、集合决策和论文主指标之间存在尚未消除的目标错位；正式独占 GPU accuracy–latency Pareto 也未完成。
- **C类顶流潜力**：**否（当前版本）**。研究纪律、失败审计和预注册质量已经具备强 CCF-C 项目的雏形；但 Best Paper Nomination 需要一个非通用拼接的新决策机制、正式 Pareto、跨数据/模型稳定性和可复现论文包，当前均未达到。

## 2. 🔄 改进效果评估

本轮重点核对 `steps/022–026`、更新后的 idea、G0 控制实验代码/结果，以及 Round 1 工单的落实情况。

- ✅ **有效改进**：
  1. **修复了选择器评价语义。** `budget_baselines_v1` 已将 signed primary reduction、signed AbsRel reduction、harmful-selection rate、oracle regret 和实际选择数设为核心统计，positive-utility capture 降为诊断指标；旧 `uniform_primary_reduction_ratio` 被明确更正为 all-12，而不是预算匹配的 uniform Top-K。
  2. **简单 killer 后仍存在可路由余量。** K=3 时，RGB/base rank-combination 的 signed primary reduction 为 `6.62%`，oracle at-most-3 为 `9.66%`；oracle 相对当前最强简单方法保留 `3.04` 个百分点，paired scan-bootstrap 95% CI 为 `[1.81, 4.44]`，足以支持继续验证 routability，但不能直接支持新算法有效。
  3. **Boosting MDE 2021 的 selector 适配具有可审计性。** 官方 revision、脚本哈希和两张官方示例图上的逐区域 score/ranking exact match 均已记录；在同一 BAR action/merge 下，Boosting selector 的 K=3 signed reduction 为约 `5.10%`，未消除当前 oracle margin。
  4. **patch 信息来源得到更强控制。** high-pass residual 在固定 rank selector 下取得 `6.62%`，而冻结参数的 RGB bilateral 和 base unsharp controls 为负收益；high-pass 相对最佳无额外模型前向 control 的差值为 `7.22` 个百分点，paired CI 下界为正。`aligned_patch_replacement` 仍为正，而“只加 patch 高频、不减 base 高频”显著为负，说明收益并非普通锐化即可解释。
  5. **任务表述显著收缩。** idea 已明确当前是 `per-image median-scale-aligned depth refinement`，不是 absolute metric depth；非重叠 target cells 下删除了缺乏证据的 pairwise redundancy 项，并把 point regression + Top-K 降为 routability diagnostic。
  6. **router probe 协议比上一轮完整。** DIODE train/val 分离、scan-grouped five-fold、冻结 evaluation manifest、feature allowlist/forbidden list、exact-K 与 at-most-K 两条轨、五随机种子、10,000 次 paired scan-bootstrap 和停止规则均被机器可读合同约束。
  7. **直接分辨率 killer 已开始落地。** 同一 DAV2-S 在 10 个 whole-image input sizes 上生成了 2000 行精度记录；shared-GPU 时延被显式标为 diagnostic，默认分析路径拒绝将其当作 formal result，这一证据边界是正确的。
  8. **新颖性判断更加克制。** Step 026 已明确“generic point utility regressor + Top-K 不足以构成论文”，并把 Paper Candidate 升级条件压到校准分布、风险约束、真实 latency budget 和超过 point/heuristic killers 上。
  9. **工程审计覆盖面扩大。** 新增 selector fidelity、预算统计、merge variant、matched-latency config 和 shared-diagnostic opt-in 等单元测试；config、输入 CSV、实现和输出结果继续通过 SHA256 绑定。

- ⚠️ **部分解决**：
  1. **W07 仍未形成正式证据。** shared diagnostic 中 regional K=3 的 p50/p95 约为 `2566/3419 ms`，而 1022 whole-image 约为 `320/680 ms`；这提示区域管线仍有很大的等时延对手搜索空间。作者正确地没有把 shared run 当正式结论，但当前 formal gate 仍为空。
  2. **当前时延协议统计功效不足。** 每种方法只有 20 个 timed images，p95 基本由一个极端样本决定；5 个 warm-up images、单次 session、无峰值显存/吞吐/阶段分解，尚不足以支撑强 CCF-C 的系统效率结论。
  3. **Boosting 对比是 selector adaptation，不是完整 Boosting MDE pipeline。** 它公平回答“官方 edge-density score 在 BAR action space 中能否消除余量”，但不能替代论文级的完整最近邻方法对比。
  4. **cheap controls 只使用一组冻结参数。** 当前结论只能写成“两个预注册 control 未复现收益”，不能写成“任何无额外前向的 sharpening 均无法复现收益”。
  5. **router 仍未执行。** 尚无 DIODE train manifest、训练期 patch labels、feature extraction、Ridge/MLP out-of-sample prediction、five-seed 结果或 inference firewall 的真实运行证据。
  6. **最近邻矩阵仍偏深度专用。** 现有矩阵覆盖 patch/high-resolution depth 方法，但没有系统审计 selective regression、learning-to-defer、conformal risk control、cost-aware routing 和 spatially adaptive inference；因此 surviving mechanism 是否只是通用方法迁移仍未回答。
  7. **标准指标和外部有效性仍为空。** 当前主要证据依赖自定义 boundary-weighted AbsRel、单一 DIODE 200-val、单一 DAV2-S 和 scale-aligned protocol；Round 1 要求的 DBE/δ1/RMSE、跨 backbone、外部高分辨率数据尚未执行。
  8. **可复现入口仍缺失。** `paper3/pyproject.toml` 继续使用宽版本范围，尚无 `paper3/README.md`、lockfile、一键重分析脚本和 CI artifact reanalysis；未来 Ridge/GroupKFold 所需依赖也尚未声明。

- ❌ **无效/偏离**：
  1. **训练目标与最终决策目标尚不一致。** 协议令模型预测 `primary_utility_sum / weight_sum`，随后按预测值求和选区域；论文主指标却按原始 `primary_utility_sum` 聚合。由于 `weight_sum` 受 valid mask 和 GT boundary weights 影响且测试时不可见，normalized utility 的排序不保证最大化最终 signed error reduction。该问题若不先量化并修正，router 即使“预测准确”也可能在优化错误目标。
  2. **数学符号仍存在 `ν_i/u_i` 混用。** idea 先定义 `ν_i`，随后以未重新定义的 `u_i` 构造 `\tilde u_i` 和集合目标；这会使实现合同、论文公式和 CSV 字段无法一一映射。
  3. **harmful-action risk 仍是口号而非约束。** config 要求报告 harmful-selection rate，但没有定义主要 risk event、允许风险水平、置信上界、threshold calibration 算法和违反约束时的决策。仅有 AbsRel safety gate 不能替代区域动作伤害约束。
  4. **“最强 baseline”区间没有计入选择过程。** 当前代码先在同一 frozen val 上按 point estimate 选出 strongest non-oracle method，再对该固定方法计算 paired CI；matched-latency 也先按 point estimate 选 best feasible resolution。对“优于 baseline family 的最大值”这一主张，bootstrap replicate 内必须重新取 max，或使用等价的多重比较控制。
  5. **whole-image candidate range 尚未闭合。** shared diagnostic 下 518–1022 的全部 whole-image 点都远快于 regional K=3，说明 `1022` 上限并非由 latency budget 决定；在未扩展到不再 feasible、OOM 或预注册硬上限之前，不能称为“best matched-latency direct baseline”。
  6. **“预算自适应”仍可能 overclaim。** 当前 12 个动作成本相同，主结果固定 K=3，集合求解退化为按分数取 Top-K/正分数弃权。若最终方法既不处理异质 action cost，也不能用单一模型稳定覆盖多个 K/latency operating points，题目应收缩为“selective regional refinement”。
  7. **部分状态名过宽。** `GO_PATCH_INFORMATION_NECESSARY` 容易被理解为 patch inference 对所有可行 control 都“必要”；现有证据只支持 `GO_PATCH_INFORMATION_BEYOND_TWO_FROZEN_CONTROLS`。同理，Boosting 表格应明确标注为 edge-density selector adaptation，而非完整方法。

## 3. 🔍 强CCF-C维度深度审查

- **问题与动机**：
  - 当前细分问题已经清楚：给定一次低成本全图前向和有限区域动作预算，预测每个局部前向对最终深度误差的 signed marginal utility，并在可能有害时弃权。相较 Round 1，这是实质性进步。
  - 但“校准 + 弃权 + 风险控制”并非天然新颖。至少需要与 [SelectiveNet](https://proceedings.mlr.press/v97/geifman19a.html)、[Learn then Test](https://arxiv.org/abs/2110.01052)、[Conformal Decision Theory](https://arxiv.org/abs/2310.05921)、[Regression with Multi-Expert Deferral](https://proceedings.mlr.press/v235/mao24d.html) 和 [Post-hoc Estimators for Learning to Defer](https://proceedings.neurips.cc/paper_files/paper/2022/hash/bc8f76d9caadd48f77025b1c889d2e2d-Abstract-Conference.html) 区分；“低分辨率 selector 决定高分辨率计算位置”还需要与 [LASNet](https://proceedings.neurips.cc/paper_files/paper/2022/hash/ef472869c217bf693f2d9bbde66a6b07-Abstract-Conference.html) 和 [LookWhere?](https://papers.nips.cc/paper_files/paper/2025/hash/7dd74dcef03c8f88a58d18a9d49d7a10-Abstract-Conference.html) 对照。若最终差异只剩“把通用风险控制用于深度 patch”，强 CCF-C 新颖性不足。
  - 当前 G0 结果证明的是“有害动作很多、oracle 余量存在、两个简单 controls 不能解释 patch gain”，并未证明必须采用预测分布、conformal calibration 或新的集合决策。method motivation 应由后续 probe/error slices 驱动，而不是先确定复杂公式再寻找收益。
  - `K∈{1,3,6}` 是合理的 probe 轴，但要支撑“budget-adaptive”，最终模型应接收 budget/latency 条件，并在未重新训练的情况下生成多个 operating points；否则固定 K=3 只是 selective ranking。

- **技术完备性**：
  - 尚缺论文级方法的核心定义：预测分布族或 quantile 参数化、训练损失、校准集划分、risk event、置信界、budget-conditioned solver、tie/zero-score 规则、校准失败回退、复杂度和推理伪代码。
  - `utility/weight_sum` 的标签看似消除区域有效像素数差异，却改变了与主指标一致的区域排序；而 `weight_sum` 本身来自 GT depth boundary 和 mask。必须先完成 target-alignment audit，再生成训练标签，否则后续全部 probe 可能建立在错误 target 上。
  - at-most-K 轨的 baseline 公平性仍未冻结到算法级：每一种 score 的 threshold grid、校准目标、risk bound 和 tie rule 必须完全相同，不能只写“thresholds fit on train”。
  - harmful-selection rate 只计负 utility 区域的数量，不反映负 utility 幅度。风险约束至少需要同时报告 negative-utility mass、每图净退化概率和 tail harm；否则方法可通过选择大量“轻微负收益”区域获得较低表面风险。
  - config validator 目前验证的是声明，而非实际 tensor provenance。真实 feature builder 必须拒绝含 GT/mask/patch outputs/path identifiers 的列，并在序列化 feature artifact 中保存 schema/hash；测试阶段应在 patch backend 未实例化的情况下完成 router scoring。
  - 若所有 action cost 恒等，solver 不需要 knapsack 或复杂分配。此时算法贡献必须来自可靠的 signed-utility/risk estimation，而不能把普通 Top-K 写成新的 budget allocation algorithm。

- **实验可信度**：
  - signed metric、paired scan bootstrap、100 random seeds、官方 selector fidelity 和 no-forward controls 已使 G0 现象证据明显更可信。
  - 当前 `oracle - strongest` 和 `oracle - best direct` 的 CI 仍受 post-selection bias 影响。尤其 rank-combination 与 base-gradient point estimates 接近，固定 point winner 后再 bootstrap 会低估 baseline envelope 的不确定性。
  - shared latency 的区域管线比最高测试 whole-image resolution 慢约一个数量级；这并非自动否定方法，但意味着直接分辨率 sweep 必须扩展，且需要加入等时延 global multi-scale/ensemble 或可执行高分辨率近邻，而不是只比较 DAV2-S 的 out-of-training-resolution resize。
  - 20 个 timing samples 不足以稳定估计 p95；GPU exclusivity 仅在 pre/post 检查也无法发现运行中短暂进入后退出的 foreign process。正式 runner 应持续采样 GPU compute PIDs，并输出原始重复测量。
  - cheap-control 参数在 val 结果已知后不能直接继续手调。下一次 control search 必须只在 DIODE train/folds 上选择参数，再一次性应用于 frozen val。
  - DIODE train/val 的 `scan_id` 不重叠仍不足以排除同 scene 或近重复帧泄漏；manifest audit 应增加 scene overlap 和程序化近重复检测。
  - 自定义 boundary-weighted AbsRel 可以作为主机制 probe，但正式论文必须给标准 AbsRel、RMSE、δ1、SILog 和 depth-boundary 指标，并报告 metric quantile/weight sensitivity。
  - 单一相对深度 backbone 与 per-image GT scale alignment 不能支撑 metric-depth 或通用高分辨率 claim；至少需要一个原生 metric backbone 的无 GT 对齐结果，以及一个外部高分辨率数据集。

- **叙事克制性**：
  - `NOT_PAPER_CANDIDATE`、shared diagnostic 非正式、point probe 非算法等边界写得准确，应继续保留。
  - 可以声称：“在冻结 DAV2-S/DIODE/action/merge 合同下，signed oracle 相对当前简单 selector family 保留显著余量。”不能声称：“BAR-Depth 已学会分配预算”或“已建立高效 Pareto”。
  - `Boosting MDE 2021` 应改写为“Boosting-MDE official edge-density selector adapted to the frozen BAR 3×4 actions”；完整方法没有被复现时，表格不能省略 `selector adaptation`。
  - `GO_PATCH_INFORMATION_NECESSARY` 应改成证据覆盖范围内的名字，且正文必须说明 no-forward controls 只有两类和一组参数。
  - 在通用算法邻居审计、target-alignment audit、formal W07 和 W08 probe 完成前，不应写“首次提出 calibrated risk-aware regional refinement”。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“你们的方法只是 selective regression / learning-to-defer / conformal risk control 与已有 spatial adaptive inference 的组合，深度任务本身不构成算法新颖性。”**  
   - **当前能否扛住：不能。** Step 026 正确否定了 point regression + Top-K，但还没有覆盖通用算法邻居，也没有实现 surviving mechanism。必须给出一条超过通用风险控制迁移的、可由消融验证的算法差异。

2. **“训练标签优化平均区域 utility，论文却评价总 signed utility；风险约束也没有正式定义，所以算法目标并不自洽。”**  
   - **当前能否扛住：不能。** `primary_utility_sum/weight_sum` 与 raw aggregate objective 的排序一致性未经验证，`ν_i/u_i` 仍混用，harmful-selection 只有 metric 没有约束。该攻击会直接否定后续 router 结果的解释。

3. **“Pareto 和显著性结论经过候选选择但没有校正，而且时延对手范围被截断、formal exclusive run 未完成。”**  
   - **当前能否扛住：部分不能。** 作者已正确隔离 shared diagnostic，并提供 paired cluster bootstrap；但 replicate 内未重选 strongest method，20-sample p95 不稳定，1022 上限仍远低于 regional latency budget。当前只能称为 provisional engineering diagnostic。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

> ⚠️ **输出禁令**：严禁使用“加强”、“完善”、“优化”、“考虑”等模糊动词。每一项必须是可验证、可执行的原子任务。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 实验补充 | 读取冻结的 `oracle_patch_utility_v2.csv`，对每张图和 `K∈{1,3,6}` 分别按 `primary_utility_sum` 与 `primary_utility_sum/weight_sum` 排序；计算 Top-K set Jaccard、Kendall tau-b、按 raw utility 计的 signed reduction、raw-oracle recovery 和 selected-set disagreement。若 K=3 的 mean Jaccard `<0.90` 或 normalized-target recovery `<0.95`，在新合同中把标签改为 `primary_utility_sum / image_base_primary_error_sum`，不得覆盖 v1 合同 | 对应“目标函数与评价一致性”；当前 normalized label 可能训练出错误排序 | 生成 `utility_target_alignment_v1.csv/json`；JSON 含逐 K point+scan-bootstrap CI 和自动 PASS/REDEFINE；新增 synthetic test 证明分母变化可改变排序 | `paper3/experiments/bar_depth/audit_router_target_alignment.py`; `paper3/results/bar_depth/utility_target_alignment_v1.csv`; `paper3/results/bar_depth/utility_target_alignment_v1.json`; `paper3/tests/test_router_target_alignment.py`; `paper3/steps/027_bar_depth_objective_contract.md` |
| P0 | 写作规范 | 在新 objective contract 中统一使用 `u_i`，逐项定义 raw utility、rank-preserving training target、action cost、集合 utility、negative-utility mass 和 per-image harm event `1[Σ_{i∈S}u_i<0]`；为 at-most-K 轨固定 101 个 train-score quantile thresholds，并规定“在 train-fold 上使 harm-event 95% 上置信界≤0.10时选 signed utility 最大的 threshold”，所有 score-based baseline 使用同一规则 | 对应“技术完备性、风险约束可验证性、baseline公平性”；当前只有 harmful metric，没有 calibration algorithm | 新建 `router_probe_v2.json`，validator 能拒绝缺少 risk level、threshold grid、tie rule 或 fallback 的合同；全文无 `ν_i/u_i` 混用 | `paper3/configs/bar_depth/router_probe_v2.json`; `paper3/experiments/bar_depth/router_contract_v2.py`; `paper3/tests/test_bar_depth_router_config_v2.py`; `paper3/steps/027_bar_depth_objective_contract.md` |
| P0 | 文献增补 | 新建算法级 nearest-neighbor matrix，至少纳入 SelectiveNet、Learn then Test、Conformal Decision Theory、Regression with Multi-Expert Deferral、Post-hoc Estimators for Learning to Defer、LASNet、LookWhere、GFNet 及4篇 cost-aware routing/selective regression 工作；逐篇记录 action/expert、cost、utility/risk、abstention、校准保证、训练目标、solver、真实 latency 和与 BAR 的差异，并给出论文页码/公式号或官方代码位置 | 对应“最近邻覆盖、贡献克制性”；现有矩阵无法排除通用算法迁移 | 生成不少于12行×10列矩阵；结尾写一条可证伪算法差异；若差异只剩“应用于 depth patches”，记录 `STOP_NOVELTY` 并停止 W08 | `paper3/ideas/bar_depth_algorithmic_nearest_neighbor_matrix_v2.md`; `paper3/steps/028_bar_depth_generic_novelty_audit.md` |
| P0 | 实验补充 | 新建 v2 统计分析器：在每个 10,000 次 scan-bootstrap replicate 内重新选择 signed reduction 最大的 non-oracle baseline；matched-latency 分析中同时对 timing rows 重采样、重建 feasible set，并在 replicate 内重新选择精度最大的 feasible whole-image candidate。保留全部 v1 结果，不覆盖旧文件 | 对应“多候选比较、置信区间有效性”；固定 point winner 后计算 CI 会低估 max-envelope 不确定性 | 生成 `budget_baselines_v2.json` 和 `matched_latency_analysis_v2.json`，均含 `replicate_wise_max_envelope=true`；新增 crossing-baseline synthetic test，v1 固定 winner 会 PASS 而 v2 envelope 会按构造返回 STOP | `paper3/experiments/bar_depth/analyze_budget_baselines_v2.py`; `paper3/experiments/bar_depth/analyze_matched_latency_v2.py`; `paper3/results/bar_depth/budget_baselines_v2.csv`; `paper3/results/bar_depth/budget_baselines_v2.json`; `paper3/tests/test_max_envelope_bootstrap.py` |
| P0 | 实验补充 | 在执行正式 W07 前新建 `matched_latency_v2.json`：每种方法按20个跨 scan 图循环10次得到200个 timed samples，逐 shape 先运行20次 warm-up；在两次独立 exclusive A800 session 中重复。每秒采样 compute PIDs，并记录 model preprocess、base forward、selector、patch forward、merge、output resize 的阶段时长、p50/p90/p95、峰值显存、吞吐、GPU clock/power mode | 对应“真实效率、稳定复现”；20个样本和 pre/post PID 检查不足以支撑 p95 | 两个 session 的 p50 相对差≤5%、p95相对差≤10%，全过程 foreign PID 数为0；输出每方法400条 raw timing，所有阶段之和与端到端时间误差≤2% | `paper3/configs/bar_depth/matched_latency_v2.json`; `paper3/experiments/bar_depth/benchmark_matched_latency_v2.py`; `paper3/results/bar_depth/matched_latency_exclusive_v2_run1.json`; `paper3/results/bar_depth/matched_latency_exclusive_v2_run2.json`; `paper3/steps/029_bar_depth_formal_latency_result.md` |
| P0 | 实验补充 | 将 whole-image input-size 列表冻结为从 `518` 到 `2030`、步长 `56` 的全部尺寸；对每个尺寸运行同一200图 accuracy sweep 和 formal timing，OOM 按预注册状态写入结果而不是删除。只有出现至少两个连续 p50/p95 均高于 regional K=3 的尺寸，或后续全部尺寸 OOM，才宣布 direct candidate range 闭合 | 对应“Baseline公平性、Pareto可信度”；当前最高1022仍远快于区域管线 | 生成28个候选的逐图 accuracy、formal latency 和 OOM 状态；best direct 由 replicate-wise feasible max envelope 得出，不允许人工截断候选 | `paper3/configs/bar_depth/direct_resolution_v2.json`; `paper3/experiments/bar_depth/run_direct_resolution_v2.py`; `paper3/results/bar_depth/direct_resolution_raw_v2.csv`; `paper3/results/bar_depth/direct_resolution_raw_provenance_v2.json`; `paper3/results/bar_depth/direct_resolution_pareto_v2.csv` |
| P0 | 可复现性 | 枚举 DIODE train 全部 scans，使用 seed `271828` 对每个 scan 固定哈希抽取至多20帧；生成逐文件 SHA256 manifest，并审计 train 与冻结 val 的 `scan_id`、`scene_id` 交集及 RGB perceptual-hash 近重复。将 pHash Hamming distance≤4 的 train 样本从训练 manifest 排除并记录原因 | 对应“数据隔离、可复现性”；仅 scan-level split 不能排除同 scene/近重复泄漏 | manifest 重建字节级一致；train/val scan 和 scene 交集均为0；保留所有排除项及 pHash distance；测试自动校验三个条件 | `paper3/experiments/bar_depth/build_router_train_manifest.py`; `paper3/artifacts/bar_depth/diode_train_router_manifest_v1.jsonl`; `paper3/artifacts/bar_depth/diode_train_router_audit_v1.json`; `paper3/tests/test_router_train_manifest.py` |
| P0 | 实验补充 | 仅在 objective contract、generic novelty audit 和 formal W07 均 PASS 后执行 W08：在 train manifest 上生成12-action patch labels和 allowlist features，使用5-fold GroupKFold选择 Ridge alpha 与 MLP epoch，运行 seeds `[11,23,37,53,71]`；测试期进程不实例化 patch backend，并对 feature artifact schema 执行 forbidden-field assertion；最后一次性读取冻结 val | 对应“无泄漏、稳定性、routability 机制验证”；当前只有协议没有真实预测 | 对 K=1/3/6、exact-K/at-most-K、每 seed 输出 signed reduction、harm event、negative mass、oracle recovery、actual count 和 selector overhead；自动给出既有 gate 的 GO/STOP，缺任一 seed 即 INVALID | `paper3/experiments/bar_depth/build_router_features.py`; `paper3/experiments/bar_depth/train_router_probe.py`; `paper3/experiments/bar_depth/evaluate_router_probe.py`; `paper3/results/bar_depth/router_probe_v2_predictions.csv`; `paper3/results/bar_depth/router_probe_v2_summary.json`; `paper3/steps/030_bar_depth_router_probe_result.md` |
| P0 | 叙事修正 | 在 current idea 和后续结果中把 `Boosting MDE 2021` 统一写为 `Boosting-MDE edge-density selector adapted to frozen BAR actions`；把 `GO_PATCH_INFORMATION_NECESSARY` 改写为 `GO_PATCH_INFORMATION_BEYOND_TWO_FROZEN_CONTROLS`；把 shared latency 结果统一加 `PROVISIONAL/NOT_FORMAL` 前缀，并删除任何 absolute metric depth 表述 | 对应“贡献克制性、Baseline身份准确性、证据边界” | 对 `paper3/ideas/` 与 `paper3/steps/022–030` 执行文本检查；除历史状态引用外不存在三类过宽表述，新 correction step 列出旧名与新名映射 | `paper3/ideas/candidates/01_budget_adaptive_regional_depth.md`; `paper3/steps/031_bar_depth_claim_scope_corrections.md`; `paper3/tests/test_bar_depth_claim_scope.py` |
| P1 | 消融补全 | 在 DIODE train folds 上搜索 RGB bilateral 的 `radius∈{1,2,3}`、`spatial_sigma∈{0.5,1,2}`、`color_sigma∈{0.05,0.1,0.2}`、`amount∈{0.25,0.5,1.0}` 共81组，以及 unsharp 的 `sigma∈{0.5,1,2,4}`、`amount∈{0.25,0.5,1,1.5}` 共16组；按 train signed reduction 选每类唯一参数，再一次性评测 frozen val，并用 replicate-wise control max envelope 与 high-pass 比较 | 对应“替代解释排除、消融公平性”；单组 cheap-control 参数可能构成 strawman | 输出97组 train score、两组冻结 winner、val signed metrics/latency 和 max-envelope paired CI；若 high-pass 差值 CI 下界≤0，撤回 patch-information claim | `paper3/configs/bar_depth/no_forward_control_grid_v1.json`; `paper3/experiments/bar_depth/tune_no_forward_controls.py`; `paper3/results/bar_depth/no_forward_control_train_grid_v1.csv`; `paper3/results/bar_depth/no_forward_control_val_v1.json` |
| P1 | 消融补全 | 对 boundary quantile `[0.85,0.90,0.95]` × weight `[2,5,10]` 的9组设置重算 base、最强 heuristic、Boosting selector adaptation、learned router、all-12 和 oracle；同时报告标准 AbsRel、RMSE、δ1、SILog、DBE-accuracy 与 DBE-completeness，所有设置使用同一冻结 predictions | 对应“指标稳健性、贡献证据匹配”；当前结论可能依赖单一自定义边界权重 | 生成9组 point+scan-bootstrap CI；若 learned-vs-killer 的方向在≥3组中翻转，正文只保留预注册 metric-specific claim，不写 metric-agnostic robustness | `paper3/configs/bar_depth/metric_robustness_v1.json`; `paper3/experiments/bar_depth/run_metric_robustness.py`; `paper3/results/bar_depth/metric_robustness_v1.csv`; `paper3/steps/032_bar_depth_metric_robustness.md` |
| P1 | 实验补充 | 在相同 DIODE manifest 上运行至少两个可执行完整近邻：完整 Boosting MDE pipeline 与 PRO/PatchRefiner V2 中一个；使用各自官方 revision/weights，报告官方默认输出和与 BAR 相同 scale-aligned指标，并在独占 A800 上测相同端到端 latency。不得把 selector adaptation 代替完整方法 | 对应“最近邻公平性、系统级 Pareto”；当前 G0 只比较 selector score | 生成每方法逐图结果、官方版本/权重哈希、200次 timing 和 Pareto 表；若完整近邻在相同或更低 latency 上同时支配 learned BAR，则记录 `STOP_NO_PARETO_SPACE` | `paper3/configs/bar_depth/full_neighbor_baselines_v1.json`; `paper3/experiments/bar_depth/run_full_neighbor_baselines.py`; `paper3/results/bar_depth/full_neighbor_baselines_v1.csv`; `paper3/steps/033_bar_depth_full_neighbor_result.md` |
| P1 | 实验补充 | 在 DAV2-B 和一个原生 metric backbone（Depth Pro）上复用冻结 action/selector 规则；DAV2-B 使用明确标注的 scale-aligned protocol，Depth Pro 禁止 GT scale alignment。随后在 ETH3D 与 Middlebury 2014 公开高分辨率 GT 子集上直接应用 DIODE-train 得到的 router/threshold，不进行目标域调参 | 对应“跨模型、跨数据有效性、metric claim 边界” | 每个 backbone×dataset 输出 base、heuristic、learned、oracle、all-region 和 direct/full-neighbor结果及 scene-cluster CI；Depth Pro 结果中不存在 per-image GT alignment | `paper3/configs/bar_depth/transfer_eval_v1.json`; `paper3/experiments/bar_depth/run_transfer_eval.py`; `paper3/results/bar_depth/transfer_eval_v1.csv`; `paper3/steps/034_bar_depth_external_validity.md` |
| P1 | 可复现性 | 新建 paper3 专用 README、`uv.lock`、CPU reanalysis 脚本、GPU G0/W08 脚本和 GitHub Actions；在依赖中显式加入实际使用的 `scikit-learn` 版本。CPU 脚本从 committed CSV/provenance 重算所有 G0 summaries，GPU 脚本校验数据/权重哈希后执行指定阶段 | 对应“可复现性、写作规范性”；当前宽版本范围和根 README 无法重建 paper3 | 全新 Python 3.12 环境中，CPU reanalysis 的所有 point estimates/CI 与 committed v2 summary 在 `1e-12` 内一致；CI 执行 Ruff、Black、全部 tests 和 artifact reanalysis 成功 | `paper3/README.md`; `paper3/uv.lock`; `paper3/scripts/reanalyze_g0.sh`; `paper3/scripts/run_router_probe.sh`; `.github/workflows/paper3-ci.yml`; `paper3/pyproject.toml` |
