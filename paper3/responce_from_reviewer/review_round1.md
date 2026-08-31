# Review Round 1 [2026-08-31 08:49:01 UTC]

## 1. 🎯 强CCF-C达标判定
- **当前状态**：**未达标**。但作为 `Research Opportunity`，当前证据足以支持继续执行下一轮可路由性门禁，不应因尚无完整方法而立即归档。
- **核心差距**：现有结果只证明了“区域细化收益存在且集中”的 oracle 上限，尚未给出一个在推理时不读取 GT/patch 输出、并在等真实延迟下稳定超过 content-adaptive selection、base-depth gradient 与直接高分辨率前向的可投稿算法。
- **C类顶流潜力**：**否（当前版本）**。v1 失效审计、v2 单变量修复和证据绑定体现出高质量研究纪律，但 Best Paper Nomination 需要清晰的新决策机制、跨数据/模型的稳定收益及有说服力的 accuracy–latency Pareto；当前三项均未成立。

## 2. 🔄 改进效果评估

当前 `paper3/responce_from_reviewer/` 在本轮审查前不存在，因此没有可对照的历史 `review_round*.md`；以下将 `steps/018–021` 视为作者在 idea 形成后的首轮内部改进记录。

- ✅ **有效改进**：
  1. 研究问题已从“再设计一个 patch 融合模块”收缩为“严格区域预算下预测候选动作的边际收益”，问题边界明确，并主动把 Boosting MDE 2021、base-gradient 等列为 novelty killer。
  2. Step 019 没有把 v1 的 `STOP_INSUFFICIENT_HEADROOM` 当作科学结论，而是定位到 inverse-depth affine 输出非正及 epsilon clipping 导致的病态误差；原始输出被保留，修复原因可审计。
  3. Step 020 的 v2 只改为 positive median scale-only alignment 和预定义 `[0.1, 350]m` 范围，其余数据、动作、阈值、bootstrap 与 merge 合同保持不变。这种单变量修复比重新选数据或调门槛可信。
  4. v2 结果给出了 point estimate、scan-cluster 95% CI、indoor/outdoor slice、clipping 比例及明确 claim boundary。`10.42%` positive headroom、`92.72%` budget capture、`9.66%` primary reduction 足以证明动作空间具有研究价值，但作者没有据此宣称 router 已成立。
  5. config、manifest、源码 revision、权重 SHA256、实现哈希、raw CSV、bootstrap 和 summary 已形成绑定链，且已有几何、metric、manifest、gate 单元测试；这部分可复现意识高于一般早期 idea。

- ⚠️ **部分解决**：
  1. v2 证明的是 oracle feasibility，不是算法有效性。`base-depth gradient` 已捕获 `72.90%` 的正效用，距 oracle 的剩余空间可能不足以支撑新方法，必须通过 held-out router probe 决定。
  2. 当前 heuristic summary 主要报告“所选区域中的正效用占比”，会把所选负效用区域截为 0；它不能替代 signed net error reduction、harmful-selection rate 和 paired regret。Step 021 中的 heuristic 净收益还是未 bootstrap 的诊断量。
  3. DIODE validation 的 200 图与 20 scans 足以做 canary，但不足以证明高分辨率通用性；当前只有一个数据集、一个 DAV2-S backbone、一个固定 3×4 action space。
  4. `pyproject.toml` 只给版本范围，仓库没有 `paper3/README.md`、锁文件和一键复算命令；根 README 仍把 `paper1` 写成活动项目，第三方无法直接重建 paper3 结果。
  5. 普通 AbsRel 被作为 safety metric 是正确方向，但主结论仍依赖自定义 boundary-weighted AbsRel，边界分位数 `0.9` 和权重 `5` 尚无敏感性分析或标准 depth-boundary 指标佐证。

- ❌ **无效/偏离**：
  1. v1→v2 的 metric 修复是实验正确性修复，不能计入论文贡献，也不能弥补当前没有 learned router 的核心缺口。
  2. 分析代码中的 `uniform_primary_reduction_ratio` 实际为 12 个区域效用之和，即“执行全部区域”，不是与 3-region budget 匹配的 uniform/random Top-3；若把它写成预算基线会构成不公平对比。
  3. 当前 canary 对 DAV2-S 使用逐图 GT median scale，因此结果属于 **per-image scale-aligned relative depth evaluation**，不能支持“绝对 metric depth”主张。现有命名若不收缩，会形成明显 overclaim。
  4. post-canary 目标中的 pairwise redundancy `rho_ij` 尚未被当前非重叠 target-cell 动作或交互实验支持；在没有实测非加性之前加入该项，会让方法看起来先有公式、后找证据。

## 3. 🔍 强CCF-C维度深度审查

- **问题与动机**：
  - “在固定局部推理预算下，选择最值得细化的区域”是清楚且有实际价值的细分问题，尤其适合高分辨率 dense prediction 的 accuracy–cost trade-off。
  - 当前实验分辨率为 `1024×768`。base 前向约处理 `518×686`，再执行 3 个 `518×518` patch 后，总 resized pixels 已约为 116 万，而原图约为 79 万；Transformer 的 attention 成本并非按像素线性增长，因此这不直接否定方案，但它使“比直接原分辨率前向更省”成为必须实测、不能默认成立的命题。
  - 动机应从“所有高分辨率方法都浪费大部分计算”收缩为“对给定 backbone、candidate action 和 latency budget，局部收益呈非均匀分布；学习式选择能否优于廉价启发式仍待验证”。
  - 若继续使用 GT median scale，任务名称必须写成 scale-aligned depth refinement；只有换用原生 metric backbone 并在无 GT 对齐条件下评测，才可恢复 metric depth 表述。

- **技术完备性**：
  - 当前没有可投稿方法，只有一个 post-canary optimization sketch。尚缺：router 输入张量、utility label 归一化、训练损失、预算条件编码、允许少选/不选的 abstention 规则、训练/验证切分、selection solver、成本测量方式及推理伪代码。
  - `u_i` 是基于执行 patch 后的 GT utility，作为训练标签可以接受；但所有 patch 必须只在训练期生成标签，测试期 router 不能接触 patch prediction。该隔离需要在代码级断言和 provenance 中体现。
  - 当前动作的中心 target cells 不重叠，单 patch utility 基本可加。`rho_ij` 只有在引入重叠候选、共享 batch 成本或组合 merge 交互后才有依据；下一轮应先检验 `u(S)` 与 `sum_i u_i` 的差异，再决定是否保留二阶项。
  - learned score 若只是用 base-depth gradient 的 MLP 替代手工排序，很可能被评价为常规 ranking head。要形成强 CCF-C 方法，最终算法必须明确改变预算条件下的集合决策或训练目标，而不只是“换一个更复杂的打分器”。

- **实验可信度**：
  - canary 的 manifest、哈希、固定阈值和 scan-cluster bootstrap 是可信基础；v2 的 indoor/outdoor 同方向也降低了单域偶然性风险。
  - 现有结论仍是同一批 200 张 validation 图上的 oracle/heuristic 诊断。router 的超参数若在这 200 图上选择，再在同一批图上报告结果，会产生选择偏差；应使用 DIODE train 建标签和调参，把现有 200-val manifest 作为一次性冻结评测集。
  - 需要比较的 killer 不只包括 random、RGB edge、base edge 和 Boosting 2021 selector，还包括：直接提高全图输入分辨率、等延迟 global multi-scale、全部 tile、廉价 RGB/base sharpening，以及当前高分辨率方法的效率点。
  - `positive-utility capture` 忽略了被选中负效用 patch，不能作为主要 baseline 指标。主要比较应使用 signed end-to-end error reduction，并给出 paired scan-bootstrap 差值、负效用选择率、oracle regret、实际选择数及普通 AbsRel/边界指标。
  - shared-GPU timing 只能证明程序运行，不足以支撑效率 claim。动态 patch 数、batch size 和预处理会改变延迟，必须报告 exclusive GPU 下的端到端 p50/p90、吞吐、峰值显存和 selector overhead。
  - 自定义 boundary-weighted AbsRel 可能放大 DIODE 深度噪声或特定阈值效果。强 CCF-C 需要标准指标、边界指标、阈值敏感性和至少一个更高分辨率外部数据集。

- **叙事克制性**：
  - `GO_ORACLE_ROUTABILITY_UNVERIFIED / NOT_PAPER_CANDIDATE` 的状态标注准确，Step 021 也主动指出 base-gradient 和 Boosting 2021 可能消除新意，这一点应保留。
  - “25% budget capture 92.72%”必须写成“oracle 在每图至多选择 3 个区域时捕获 92.72% 的正效用”，不能省略 oracle、正效用和“至多”；否则读者会误解为真实 router 已取得该结果。
  - “uniform”指标名、“metric depth”任务名以及 `ν_i/u_i` 符号不一致会削弱专业性；在进入方法开发前应先修正定义。
  - 在 learned router、等延迟 Pareto 和跨数据验证通过之前，贡献只能写成“发现并量化一个候选缺陷”，不能写“提出高效 BAR-Depth 方法”。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“这是一份 oracle measurement，不是一篇算法论文；而且 2021 年已有 content-adaptive patch selection。”**  
   - **当前能否扛住：不能。** 目前没有测试期可运行的 router，base-gradient 已恢复 `72.90%` 正效用，Boosting 2021 尚未做预算匹配复现。即使 oracle 数字很高，也只说明上限存在。

2. **“所谓预算效率没有与直接全图高分辨率前向做等延迟比较；1MP DIODE 上 base+3 patches 未必更便宜。”**  
   - **当前能否扛住：不能。** 现有 timing 来自共享 GPU，仅记录 base/12-patch forward 总时长，没有 selector、I/O、merge、batch 策略，也没有直接 `770` short-side 或其他等延迟全图点。

3. **“论文声称 metric/high-resolution depth，但实验使用逐图 GT scale、自定义边界加权指标、单一 DAV2-S 和单一 DIODE 子集。”**  
   - **当前能否扛住：部分能。** 普通 AbsRel safety、clipping 审计和 indoor/outdoor slice 提供了透明度；但它们无法消除任务定义不一致、指标依赖和外部有效性不足。若不收缩 claim 或补无 GT 对齐实验，该攻击足以拒稿。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 实验补充 | 新建 router probe 预注册协议与 JSON 合同，固定允许输入、训练标签、数据切分、`K∈{1,3,6}`、全部 killer、paired scan-bootstrap 10,000 次及升级门槛；主门槛写为：K=3 时相对最强预算匹配非学习 baseline 的 signed primary reduction 提升点估计≥1.0 个百分点且 95% CI 下界>0，恢复≥80% oracle signed gain，普通 AbsRel 相对恶化的 95% CI 上界≤1%，selector p50 overhead≤端到端延迟的5% | 对应“问题定义清晰度、预注册、Baseline公平性、贡献证据匹配”；防止看到结果后改阈值 | 生成可解析的 `router_probe_v1.json` 与 Step 022；所有阈值、停止条件和允许输入均有唯一字段，`pytest` 校验配置完整 | `paper3/configs/bar_depth/router_probe_v1.json`; `paper3/steps/022_bar_depth_router_probe_protocol.md`; `paper3/tests/test_bar_depth_router_config.py` |
| P0 | 可复现性 | 枚举 DIODE train 的全部 scans，按 seed `271828` 对每个 scan 固定哈希选取至多20帧，生成训练 manifest；router 的模型选择只使用 train scans，现有 200 张 validation manifest 保持冻结并只执行一次最终评测 | 对应“数据隔离、可复现性”；避免在同一 200-val 集上调参和报结果 | 生成 train manifest、audit 与 SHA256；train/val 的 `scan_id` 交集为0，重复生成字节级一致 | `paper3/artifacts/bar_depth/diode_train_router_manifest_v1.jsonl`; `paper3/artifacts/bar_depth/diode_train_router_audit_v1.json`; `paper3/experiments/bar_depth/build_router_train_manifest.py` |
| P0 | 实验补充 | 新增预算匹配 baseline 分析器，对 RGB-gradient、base-gradient、rank-combination、true uniform Top-K、random Top-K 与 all-12 分别计算 **signed** primary reduction、普通 AbsRel reduction、负效用选择率、oracle regret 和实际选择数；random 使用100个固定种子，统计使用10,000次 scan-cluster paired bootstrap；保留旧 v2 summary，不改写历史文件 | 对应“Baseline公平性、统计可信度”；当前 positive capture 会忽略被选负效用区域，`uniform` 又不是 K=3 基线 | 生成 CSV/JSON；K=3 基线都恰好选择3个区域，另设 `all_12_regions` 键；每个方法均含 point、CI 和逐 scan 差值 | `paper3/experiments/bar_depth/analyze_budget_baselines.py`; `paper3/results/bar_depth/budget_baselines_v1.csv`; `paper3/results/bar_depth/budget_baselines_v1.json`; `paper3/tests/test_budget_baseline_metrics.py` |
| P0 | 实验补充 | 从 Boosting MDE 2021 官方实现提取 content-adaptive patch score，在 BAR 的同一12个候选 cell 上选 K=3；固定相同 patch prediction、alignment、merge、数据和指标，仅替换 selector，并单独记录 score 计算时间 | 对应“最近邻公平复现、novelty killer”；不允许因候选动作或 merge 不同而制造优势 | 生成逐区域 score 与逐图选择 CSV；官方示例图上的 patch 排序与官方实现一致；在冻结 200-val 上给出 signed reduction±paired 95% CI | `paper3/experiments/bar_depth/selectors/boosting2021_selector.py`; `paper3/results/bar_depth/boosting2021_budget3_v1.csv`; `paper3/steps/023_bar_depth_killer_selector_result.md` |
| P0 | 实验补充 | 实现最小可路由性 probe：输入仅含每 cell 的 8-bin RGB/base-gradient 直方图、base disparity 的 mean/std/四分位数、归一化位置及 base encoder pooled feature；分别训练 Ridge 与两层 MLP（hidden=256、GELU、dropout=0.1），目标为 `primary_utility_sum/weight_sum`，使用 Huber loss；train scans 内5折 GroupKFold调参，固定 seeds `[11,23,37,53,71]`，最终在冻结 val 上输出预测 | 对应“技术完备性、无泄漏、稳定复现”；先回答 utility 是否可从便宜信息预测，再决定是否值得设计论文级 selector | 生成每个 val region 的 out-of-sample score、每 seed 结果和汇总；测试期代码路径断言禁止读取 GT、mask、patch prediction、文件名与 dataset ID；按 Step 022 门槛给出 GO/STOP | `paper3/experiments/bar_depth/train_router_probe.py`; `paper3/experiments/bar_depth/selectors/router_probe.py`; `paper3/results/bar_depth/router_probe_v1_predictions.csv`; `paper3/results/bar_depth/router_probe_v1_summary.json`; `paper3/steps/024_bar_depth_router_probe_result.md` |
| P0 | 实验补充 | 在相同 DAV2-S 权重上运行全图 short-side `[518,672,770,896]` 四个点，并运行 BAR 的 `K=[0,1,3,6,12]`；所有点使用同一 scale-aligned metric 和数据 manifest，禁止根据精度结果追加输入尺寸 | 对应“等成本公平性”；直接高分辨率前向是最强简单 killer，当前未比较 | 生成 accuracy–latency 原始表；每个点包含 AbsRel、primary metric、输入 token/pixel 数、forward/端到端时间和显存；图中标出 BAR K=3 与最近延迟的全图点 | `paper3/experiments/bar_depth/run_direct_resolution_baselines.py`; `paper3/results/bar_depth/direct_resolution_pareto_v1.csv`; `paper3/results/bar_depth/direct_resolution_pareto_v1.pdf` |
| P0 | 可复现性 | 在独占 A800 上对每个全图/BAR 配置执行50次 warm-up 和200次计时，分别测 batch=1 latency 与 batch=4 throughput；每次使用 CUDA synchronize，端到端计时包含预处理、router、patch forward、alignment、merge 和输出 resize，并记录 p50/p90、峰值显存、GPU/驱动/CUDA、功耗模式 | 对应“真实效率、可复现性”；共享 GPU forward 诊断不能支撑论文效率结论 | 生成原始200次 timing 与汇总 JSON；同一配置重复两轮的 p50 相对差≤5%；不存在未计入的 selector/merge 时间 | `paper3/experiments/bar_depth/benchmark_latency.py`; `paper3/results/bar_depth/latency_a800_v1.csv`; `paper3/results/bar_depth/latency_a800_v1.json` |
| P0 | 叙事修正 | 将 current canary 的任务表述统一改为“per-image median-scale-aligned depth refinement”，在状态段明确写入“GT scale 仅用于评测，v2 不验证 absolute metric depth”；只有新增无 GT 对齐的 metric-backbone 结果后才使用 metric depth claim | 对应“贡献克制性、任务定义一致性”；当前 GT median scale 与 metric claim 冲突 | idea 中所有 v2 结论均带 `scale-aligned` 限定；不存在把 v2 oracle 数字描述为 absolute metric performance 的句子 | `paper3/ideas/candidates/01_budget_adaptive_regional_depth.md` |
| P0 | 写作规范 | 统一 `ν_i` 与 `u_i` 为单一符号，逐项定义 `E_i` 的像素集合、权重、分母、正负号及“至多 K 个正效用区域”的 oracle 规则；在未提交组合交互证据前删除目标式中的 `rho_ij`，改为可加 Top-K 目标 | 对应“问题定义清晰度、数学可复现性”；避免公式与代码语义不一致 | 文档中的 utility 定义可直接映射到 CSV 字段；全文无 `ν_i/u_i` 混用；目标函数与当前非重叠动作一致 | `paper3/ideas/candidates/01_budget_adaptive_regional_depth.md`; `paper3/steps/022_bar_depth_router_probe_protocol.md` |
| P1 | 消融补全 | 在冻结 200-val 上对 boundary quantile `[0.85,0.90,0.95]` × weight `[2,5,10]` 的9组设置复算 base、all-12、oracle-K3、base-gradient-K3 和 learned-router-K3，并同时报告 AbsRel、RMSE、δ1、DBE-accuracy、DBE-completeness；所有设置在运行前写入单一 config | 对应“指标稳健性、消融覆盖”；排除结果只在 quantile=0.9、weight=5 下成立 | 生成9组完整结果与 CI，无隐藏设置；若≥3组中 oracle primary reduction 的95% CI下界≤0，则删除“边界细化收益稳定”主张 | `paper3/configs/bar_depth/metric_robustness_v1.json`; `paper3/experiments/bar_depth/run_metric_robustness.py`; `paper3/results/bar_depth/metric_robustness_v1.csv` |
| P1 | 消融补全 | 固定 K=3 和相同 selector，比较 `highpass_residual`、直接 aligned patch replacement、patch high-frequency without base subtraction、RGB-guided bilateral sharpening（无额外模型前向）和 base-depth unsharp mask（无额外模型前向）；每个变体使用预注册参数，不按 val 结果调参 | 对应“核心组件有效性、替代解释排除”；验证收益来自 patch 模型信息而不是普通锐化 | 生成每个 merge/control 的 signed reduction、AbsRel、DBE 与 latency；若最佳无额外前向 control 与 highpass 的 paired 差值95% CI包含0，则不得把 patch inference 写成必要机制 | `paper3/configs/bar_depth/merge_ablation_v1.json`; `paper3/experiments/bar_depth/run_merge_ablation.py`; `paper3/results/bar_depth/merge_ablation_v1.csv` |
| P1 | 实验补充 | 在 DAV2-B 与 Depth Pro 上复用同一 3×4/1.5×/K=3 动作定义，分别运行 base、all-12、oracle、base-gradient 和 direct-full-resolution；Depth Pro 使用其原生 metric 输出时禁止 GT scale alignment，DAV2-B 沿用明确标注的 scale-aligned protocol | 对应“跨模型有效性、任务边界”；排除 oracle signal 只来自 DAV2-S 特定分辨率与输出域 | 生成两 backbone 的 point+scan-bootstrap CI；每个 backbone 单独标注 relative/metric protocol，未混合汇总 | `paper3/configs/bar_depth/backbone_transfer_v1.json`; `paper3/experiments/bar_depth/run_backbone_transfer.py`; `paper3/results/bar_depth/backbone_transfer_v1.csv` |
| P1 | 实验补充 | 在 ETH3D 与 Middlebury 2014 的公开高分辨率 GT 子集上运行冻结 selector、K=3、merge 参数和 direct-resolution baselines；不使用目标数据标签调阈值，按 scene 聚类统计 | 对应“外部有效性、高分辨率真实性”；DIODE 1MP 子集不足以支撑通用 high-resolution claim | 生成数据 manifest/checksum、逐图结果和 scene-cluster 95% CI；两个数据集均报告失败样例，不以筛图方式删除负结果 | `paper3/artifacts/bar_depth/external_eval_manifests/`; `paper3/experiments/bar_depth/run_external_eval.py`; `paper3/results/bar_depth/external_eval_v1.csv`; `paper3/steps/025_bar_depth_external_validity.md` |
| P1 | 可复现性 | 新建 paper3 专用 README、`uv.lock` 和 `scripts/reproduce_oracle_v2.sh`；脚本按顺序校验 DIODE MD5、clone DAV2 指定 revision、校验权重 SHA256、安装锁定依赖、运行测试、复算 raw analysis 与 summary；README 同时给出仅复算已提交 CSV 的 CPU 命令 | 对应“环境与结果可复现性”；当前依赖为范围声明且根 README 指向 paper1 | 在全新 Python 3.12 环境执行 CPU 复算命令后，gate decision 与所有 estimate/CI 在 `1e-12` 容差内匹配 committed v2 summary；README 不含机器绝对路径或凭据 | `paper3/README.md`; `paper3/uv.lock`; `paper3/scripts/reproduce_oracle_v2.sh` |
| P1 | 可复现性 | 添加 committed-artifact integration test：从 `oracle_patch_utility_v2.csv` 与 provenance 在临时目录重跑 analyzer，逐字段比较 estimates、CI、gate、bindings；另添加 safety gate 测试，要求下一版 gate 使用 degradation CI 上界而非仅 point estimate | 对应“自动化审计、统计门禁正确性”；防止分析代码变更静默改变历史结论 | `pytest paper3/tests -q` 全部通过；任意 raw CSV/config 字节变更都会触发 hash mismatch；safety CI 超阈值时测试返回 STOP | `paper3/tests/test_oracle_v2_reanalysis.py`; `paper3/tests/test_router_gate_statistics.py` |
| P2 | 文献增补 | 新建 nearest-neighbor matrix，逐列记录 Boosting MDE、PatchFusion、PatchRefiner V2、PRO、Depth Pro、InfiniDepth、URGT、SaccadeCam 的 candidate generation、selection policy、budget definition、merge、监督、分辨率、metric/relative 协议与真实 latency；每个差异必须指向论文页码或官方代码位置 | 对应“最近邻覆盖、贡献定位”；当前缺少 PatchRefiner V2、Depth Pro、URGT 与更广义 adaptive-resolution depth 先例的结构化对照 | 生成至少8行×8列矩阵；BAR 的剩余差异能用一句可证伪陈述表达；无法形成差异时在文档中记录 STOP_NOVELTY | `paper3/ideas/bar_depth_nearest_neighbor_matrix.md`; `paper3/steps/026_bar_depth_novelty_audit.md` |
