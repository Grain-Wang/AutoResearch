# Review Round 3 [2026-09-01 06:31:43 UTC]

## 1. 🎯 强CCF-C达标判定
- **当前状态**：**未达标**。相较 Round 2，作者已经实质修复 target audit、baseline-family post-selection 区间和 claim scope，并正确停止了缺乏新颖性的 point-score + threshold + Top-K 方法；但这意味着当前版本不是“接近完成的方法”，而是退回到仅保留一个尚未定义和验证的 joint selected-set Research Opportunity。
- **核心差距**：当前唯一保留的“联合建模选中动作集合的 utility 分布，并据此做 selection-aware risk/utility 决策”既没有形成冻结算法，也尚未排除 2025–2026 年 decision-aware conformal selection、adaptive selective risk certificate 与 multivariate conformal selection 的直接覆盖；同时正式 exclusive accuracy–latency Pareto 仍未完成。
- **C类顶流潜力**：**否（当前版本）**。本轮最有价值的是研究纪律：发现旧目标失配后重定义、发现 point router 不新后主动 STOP、发现 GPU 污染后 fail-closed。这些是高质量研究过程，但 Best Paper Nomination 需要一个不可被通用风险控制直接替代的新算法、完整正式 Pareto、独立确认集及跨方法/跨数据证据，当前均不存在。

## 2. 🔄 改进效果评估

本轮核对了作者对 Round 2 的书面回应、更新后的 idea、`steps/027–031`、v2 配置、统计分析代码与已提交结果。Round 2 的最大轮次为 2，本文件因此为 Round 3。

- ✅ **有效改进**：
  1. **target mismatch 被实证发现并处理。** `utility_target_alignment_v1.json` 显示 K=3 时 `u_i/weight_sum` 的 Top-K Jaccard 为 `0.927`，但按 raw utility 计算的 oracle recovery 只有 `0.93696`，低于冻结阈值 `0.95`；另有 `32/2400` 个区域出现 `weight_sum=0`。作者没有解释性绕过，而是返回 `REDEFINE_RANK_PRESERVING_TARGET`，把 v2 标签改为同图恒定分母的 `u_i/E_0(x)`。
  2. **当前 point router 被正确判定为不新。** Step 028 明确给出 `STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER`，并阻止 W08 继续生成训练标签或在冻结 val 上跑 Ridge/MLP。相比“先跑出数字再包装”，这是有效回应 Round 2 的核心新颖性质疑。
  3. **baseline-family 选择不确定性得到实质修复。** `budget_baselines_v2` 在每个 scan-bootstrap replicate 内重新取 non-oracle baseline 最大值。K=3 时 oracle 相对 envelope 的 95% CI 为 `[1.6991, 4.0169]` 个百分点；10,000 次 replicate 中 RGB/base rank 与 base-gradient 分别获胜 5,035 和 4,964 次，证明固定 point winner 的旧分析确实低估了 family-selection 不确定性。
  4. **direct-resolution accuracy family 被扩展并按 replicate 重选。** 518–2030、步长56的28个尺寸均完成200图评测，共5,600行，OOM为0；point 最优仍为518，其他27个尺寸的 point improvement 均为负。对全部28个尺寸做 replicate-wise max 后，oracle-minus-direct-envelope 的95% CI仍为 `[1.4235, 11.9335]` 个百分点。这比只比较到1022更可信，但仍只是 accuracy-only 证据。
  5. **正式时延协议的设计明显提升。** v2 要求两次独立 exclusive A800 session、每方法20次 warm-up、20个跨 scan 图×10次重复、阶段计时、p50/p90/p95、显存、吞吐与每秒 PID/clock/power/pstate 监控。第一次 session 被外来 compute PID 污染后没有伪装为有效数据，而是按 fail-closed 规则进入重试。
  6. **claim scope 修正基本有效。** 活动文档已把任务收缩为 selective regional refinement 与 per-image scale-aligned relative-depth mechanism probe，并把 Boosting 比较准确称为 edge-density selector adaptation，把 patch control 结论收缩为 beyond two frozen controls，把 shared timing 固定为 provisional/not formal。
  7. **通用算法矩阵比上一轮完整。** 新矩阵覆盖 SelectiveNet、Learn then Test、Conformal Decision Theory、multi-expert deferral、LASNet、LookWhere、GFNet、AdaFocus、DynamicViT、SkipNet、FrugalML 与 SaccadeCam，并得出了对当前 point method 不利但正确的结论。
  8. **停止规则被真正执行。** DIODE-train manifest、patch labels 和 W08 没有在 novelty 与 formal Pareto 未通过时提前运行；这不是遗漏，而是遵守门禁。

- ⚠️ **部分解决**：
  1. **`u_i/E_0(x)` 只证明了同图 exact-K 保序，没有证明跨图 abstention 自洽。** 同一图内分母恒定，因此 Top-K 排序与 raw `u_i` 一致；但全局 score threshold 会比较不同图像的预测值。图像依赖的 `E_0(x)` 缩放会改变跨图选择、总 raw utility 权重和 action-count 分配。当前 audit 没有验证 at-most-K 轨是否仍优化论文的 micro-aggregated signed reduction。
  2. **generic novelty audit 正确杀死了旧方法，但没有真正审完新保留方向。** `joint selected-set utility distribution + selection-aware LCB` 只是一句研究假设，没有 frozen inputs、distribution family、dependence parameterization、solver、calibration split、finite-sample claim 或 killer implementation。
  3. **风险合同从“只报 harmful rate”前进到了可执行字段，但还不是有效证书。** 当前对101个 train-OOF threshold 分别计算 one-sided Clopper–Pearson UCB，再在同一批 OOF 数据中选 utility 最大的可行 threshold。单阈值区间不自动覆盖自适应选择后的 winner；需要独立 certification split 或 family-wise/selective-valid correction。
  4. **时延数据采集协议更扎实，但正式证据仍为零。** Step 029 当前明示 session 1 attempt 1 被污染，session 2 与 joint analysis 尚未完成。任何 `GO_REGIONAL_ORACLE_PARETO` 仍只能写 provisional accuracy-only 或 shared diagnostic。
  5. **28尺寸 accuracy sweep 是强控制，但不是完整 nearest-neighbor baseline。** 对一个主要在518输入上使用的 DAV2-S 简单增大输入，回答的是“naive direct scaling 是否有效”，不能替代 Depth Pro、PRO、PatchRefiner V2 或完整 Boosting-MDE pipeline 的系统级 Pareto。
  6. **DIODE 200-val 已不再是 untouched final evaluation。** 它已经用于 oracle feasibility、metric repair、selector筛选、merge controls、target重定义、direct candidate分析和算法方向收缩。即便未来 router 权重不在其上训练，方法设计已反复读取该集合；最终论文必须另设未查看的确认集。
  7. **自定义指标、单一 backbone 和单一数据来源仍未变化。** P1 的标准指标、完整近邻、跨 backbone、外部数据与复现包被合理推迟，但因此当前距离强 CCF-C 完整证据仍很远。

- ❌ **无效/偏离**：
  1. **“统一使用 `u_i`”尚未落实到全文。** 当前 idea 与 Step 027 的公式仍出现 `\nu_i`，随后又使用未在同一公式链中一致定义的 `u_i`。状态文本声称符号已统一，但写作事实不一致。
  2. **当前 Clopper–Pearson threshold 规则不能被表述为95% selection-valid harm guarantee。** 101个 threshold 的可行性与 utility winner 都由同一 OOF样本决定，现有合同没有 multiplicity correction、独立 certificate set 或 joint event。若直接写“风险上界≤0.10”，统计主张会被审稿人否定。
  3. **保留的 joint-set 新颖性受新近工作直接威胁。** 2026年6月公开的 *A Joint Finite-Sample Certificate for Adaptive Selective Conformal Risk Control*（arXiv:2606.08517）已经处理有限网格上的自适应 threshold selection，并联合给出 selected risk、acceptance 与 deployment utility 证书；2026年的 *Risk-Controlled Post-Processing of Decision Policies*（arXiv:2605.06479）也覆盖 chance-constrained threshold post-processing。它们未必覆盖“12动作条件联合分布”本身，但已经消除了“selection-aware certificate/LCB”作为独立贡献的空间。
  4. **当前 additive action contract 尚不能支撑“集合交互”叙事。** target cells 不重叠且 merge 只写回各自 cell，所以真实集合 utility 被定义为 `U(S)=Σu_i`。能够保留的新问题只能是动作 utility 的统计依赖与 post-selection tail risk，而不是非加性 action interaction；现有文档没有清楚区分这两者。
  5. **formal latency v2 的 bootstrap 把 `(session,image,repeat)` 400个单位平铺为近似 IID。** 同一图像10次重复共享输入难度，同一 session 共享时钟/功耗状态；直接平铺重采样会低估 p50/p95 feasible-set 的层级不确定性。应按 session→image/scan→repeat 做 paired hierarchical resampling，并要求两次 session 单独得到同向结论。
  6. **candidate range closure 实现只要任意两个连续尺寸同时超过 regional p50/p95 就立即返回 closed。** GPU kernel latency可能随 shape 非单调；若后续更大尺寸重新变为 feasible，该规则仍会错误关闭范围。有效规则应要求以2030结尾的连续 infeasible/OOM suffix，或显式证明后续无 re-entry。
  7. **formal analyzer主要信任 runner 写出的 COMPLETE 状态。** 它检查状态与哈希，却没有从 raw rows、monitor samples 和 stage fields独立重建每个 session 的行数、foreign PID、stage-sum、OOM suffix 与完整性 verdict。强可复现性要求独立 validator，而不是生成器自证。

## 3. 🔍 强CCF-C维度深度审查

- **问题与动机**：
  - 当前问题已经从宽泛的“预算自适应高分辨率深度”收缩为：在一次低成本 base pass 后，对12个等成本、可选、可能有害的局部细化动作进行选择或全弃权。这一问题定义是清楚的。
  - 当前经验事实也足够明确：K=3 oracle为9.66%，简单选择器 envelope约6.62%，且约四成被简单方法选中的区域是有害动作。因此“是否能预测净收益并限制伤害”是真问题。
  - 但本轮主动停止 point router 后，论文问题不能直接等同于论文贡献。剩余 research question 应写成：“在 additive actions 下，条件相关性是否会使独立 action uncertainty 对 selected-set tail risk产生系统性误校准，以及一个 dependence-aware set model能否在相同有限样本风险控制下提高 raw utility？”只有这个命题被验证，joint-set 才不是 generic conformal wrapper。
  - 当前 DIODE val 应重新命名为 development canary。继续称其为 one-time final evaluation 会掩盖多轮研究决策已使用该集合的事实。

- **技术完备性**：
  - 目前没有论文级方法。joint-set方向缺少至少以下定义：条件联合分布族、边际/相关参数、训练目标、选集算子、风险损失、校准与认证分割、有限样本或经验保证、复杂度及失败回退。
  - `u_i/E_0(x)` 适合做同图 ranking target，但未必适合跨图 score calibration。建议把“ranking score”与“set utility/risk prediction”拆为两个明确 estimand，而不是让一个归一化标量同时承担排序、跨图弃权和 raw utility 最大化。
  - 若使用101个 policy threshold，必须明确哪一份数据用于训练 score、哪一份用于选择 threshold/模型、哪一份用于最终风险认证。`fit/tune/certify` 三分或 Learn-then-Test式 family-wise控制均可作为 baseline；同一 OOF集合同时调参与认证不能产生所声称保证。
  - 因为 `U(S)` 可加，joint model的必要性只能来自条件协方差/尾部依赖。方法必须包含 independent-marginal ablation；若 full joint 与 independent convolution 在 harm calibration和utility上无显著差异，应停止该方向。
  - risk量也需公式化：应定义 `M^-(S)=Σ_{i∈S}max(-u_i,0)`，以及 `L(S)=max(-U(S)/E_0(x),0)` 后的 CVaR90。当前配置字符串不足以确定符号、归一化和无伤害样本如何进入 tail estimator。

- **实验可信度**：
  - target audit、replicate-wise baseline envelope、28-size direct envelope和污染 session fail-closed都提高了可信度；这些改进是真实有效的。
  - baseline-envelope结果仍只回答 oracle空间，不回答可学习性。当前不能把1.70个百分点的 CI下界写成方法预期增益；真实方法最多只能争取3.04个百分点 point gap，而且还要支付 selector、校准与泛化损失。
  - direct accuracy sweep显示增大 DAV2-S输入反而普遍恶化，这是有价值的负结果，但可能反映其训练/位置编码/resize protocol，而不是高分辨率整图推理一般无效。必须把完整高分辨率近邻列入最终 baseline。
  - 时延分析应同时报告两次 session各自的 Pareto verdict、层级 pooled verdict与range suffix状态。仅在 pooled 400 rows上得到GO不能抵消某一session的相反结论。
  - 当前200张图已经承担过多次模型/指标/动作空间决策。强 CCF-C至少需要一个在 joint-set方法与阈值冻结后才首次解封的外部确认集。
  - 主指标仍是自定义 boundary-weighted AbsRel。最终证据必须包含标准 AbsRel、RMSE、δ1、SILog、DBE accuracy/completeness及权重敏感性；否则算法可能只学到当前metric的边界偏好。

- **叙事克制性**：
  - `STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER`、`NOT_PAPER_CANDIDATE` 与 shared/not-formal 标签均准确，应保留。
  - 不应把“joint-set”直接写成新算法名称。当前只能写“尚待证伪的机制假设”，直到它超过 independent marginals、Learn-then-Test、adaptive selective certificate和direct conformal decision baselines。
  - `PASS_OBJECTIVE_CONTRACT_V2` 应收缩为 `PASS_EXACT_K_RANK_TARGET_CONTRACT / CROSS_IMAGE_ABSTENTION_ALIGNMENT_PENDING`，因为跨图 threshold问题尚未关闭。
  - `CONTINUE_GENERIC_NOVELTY` 已经对当前方法失败，因此 `router_probe_v2.json` 只能作为历史诊断合同。不要通过改 prerequisite名称恢复它；应另建 joint-set v1合同。
  - 论文贡献列表在当前阶段只能陈述经验发现和研究边界，不能陈述“提出风险可控路由算法”。

## 4. ⚔️ 模拟评审攻击 (Top 3 Rejection Risks for Strong C-C)

1. **“作者已经承认当前 router 不新；剩下的 joint selected-set certificate 又被 adaptive selective conformal risk-control工作覆盖，因此没有算法贡献。”**  
   - **当前能否扛住：不能。** 新矩阵尚未纳入 arXiv:2606.08517、arXiv:2605.06479、AISTATS 2026 Adaptive Coverage Policies、ICML 2025 Multivariate Conformal Selection、ICML 2025 decision-theoretic risk calibration及UAI 2026 interaction-aware conformal retrieval。现有一句 joint-set差异不足以排除通用方法迁移。

2. **“风险上界是看过101个threshold后挑出来的单阈值Clopper–Pearson区间，覆盖率并不对自适应winner成立；而新标签只对同图排序保序，跨图弃权目标仍错位。”**  
   - **当前能否扛住：不能。** 现有合同没有独立certificate split或多重选择修正，也没有跨图target audit。该攻击会同时否定方法的安全性和objective consistency。

3. **“Pareto仍无两次有效exclusive session，timing bootstrap忽略层级依赖，range closure允许后续shape重新feasible；此外最终证据只来自反复使用的DIODE canary与自定义指标。”**  
   - **当前能否扛住：不能。** 数据采集协议已经明显改进，污染处理也正确，但正式结果尚未产生，分析规则仍有可修复的统计/实现缺口，且没有 untouched confirmation set。

## 5. 🛠️ 下一轮原子化改进工单 (Atomic Action Items)

> ⚠️ **输出禁令**：严禁使用“加强”、“完善”、“优化”、“考虑”等模糊动词。每一项必须是可验证、可执行的原子任务。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-C对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 文献增补 | 新建算法矩阵v3，至少加入 `A Joint Finite-Sample Certificate for Adaptive Selective Conformal Risk Control`（arXiv:2606.08517）、`Risk-Controlled Post-Processing of Decision Policies`（arXiv:2605.06479）、`Adaptive Coverage Policies in Conformal Prediction`（AISTATS 2026）、`Multivariate Conformal Selection`（ICML 2025）、`Decision Theoretic Foundations for Conformal Prediction`（ICML 2025）、`Learning Polyhedral Conformal Sets for Robust Optimization`（arXiv:2605.08506）和 `IDCR: Information-Directed Conformal Retrieval`（UAI 2026）；逐篇填写 adaptive selection、joint response、utility LCB、risk guarantee、subset interaction、calibration split、solver和复杂度，并逐项标记 BAR 仍新增的组件 | 对应“最近邻覆盖、算法新颖性”；最新公开工作已直接覆盖自适应policy选择后的risk/utility certificate | 生成不少于20行×12列矩阵；结尾仅允许两个机器可读结论：`STOP_NOVELTY_JOINT_SET`，或一条不含“用于depth”措辞、可写出伪代码的算法差异；找不到差异时禁止创建joint-set训练合同 | `paper3/ideas/bar_depth_algorithmic_nearest_neighbor_matrix_v3.md`; `paper3/steps/032_bar_depth_joint_set_novelty_gate.md` |
| P0 | 实验补充 | 使用冻结的2400行 utility，在 `K∈{1,3,6}` 和 fixed/rank/oracle selection下建立 dependence canary：在每个 `(domain, region_id)` 内跨图独立置换 utility 以保持边际分布并破坏图内相关性，执行100个固定置换×10,000次scan-cluster bootstrap；比较真实与独立null的 `P[U(S)<0]`、`Var[U(S)]`、VaR90和CVaR90 | 对应“方法动机可证伪性”；当前 action utility可加，joint model只有在统计依赖改变集合尾部风险时才有必要 | 生成逐selector/K的 observed-null差值和CI；K=3必须满足 harm-event绝对差≥0.03且CI不含0，或CVaR90相对差≥20%且CI不含0，否则写入 `STOP_NO_DEPENDENCE_MECHANISM` | `paper3/experiments/bar_depth/analyze_set_dependence_canary.py`; `paper3/results/bar_depth/set_dependence_canary_v1.csv`; `paper3/results/bar_depth/set_dependence_canary_v1.json`; `paper3/tests/test_set_dependence_canary.py`; `paper3/steps/033_bar_depth_set_dependence_canary.md` |
| P0 | 实验补充 | 对 `u_i`、`u_i/E_0(x)` 两个oracle score执行5-fold scan-held-out at-most-K threshold审计；每fold只在4/5 scans上从101个quantile中选threshold，再在剩余1/5 scans上计算micro raw reduction、macro relative reduction、action count、image-harm rate和negative mass；同时报告两个target产生的跨图selection disagreement | 对应“训练目标与最终评价一致性”；同图保序不能保证跨图threshold决策一致 | 生成 `cross_image_target_alignment_v1.json`；若 `u/E0` 相对raw-u的micro utility恢复率<0.95或harm rate高出>0.02，则未来joint-set合同必须拆分 `within_image_rank_head` 与 `set_raw_utility_head`，不得复用单一point target | `paper3/experiments/bar_depth/audit_cross_image_target_alignment.py`; `paper3/results/bar_depth/cross_image_target_alignment_v1.csv`; `paper3/results/bar_depth/cross_image_target_alignment_v1.json`; `paper3/tests/test_cross_image_target_alignment.py`; `paper3/steps/034_bar_depth_cross_image_objective.md` |
| P0 | 写作规范 | 在活动idea、Step027及后续文档中统一只使用 `u_i`，把 `ν_i` 全部替换；显式写出 `U(S)=Σu_i`、`M^-(S)=Σmax(-u_i,0)` 和 `L(S)=max(-U(S)/E_0(x),0)`，并规定CVaR90对 `L(S)` 的经验估计；把状态改为 `PASS_EXACT_K_RANK_TARGET / CROSS_IMAGE_ABSTENTION_ALIGNMENT_PENDING` | 对应“数学定义准确性、叙事克制性”；当前状态与公式不一致，negative mass/CVaR字符串不可复现 | 新增文本测试扫描 `paper3/ideas/` 与 `steps/027+`：不存在 `\nu_i`，三个风险量公式各只保留一个权威定义，状态不再声称整个objective已关闭 | `paper3/ideas/candidates/01_budget_adaptive_regional_depth.md`; `paper3/steps/027_bar_depth_objective_contract.md`; `paper3/tests/test_bar_depth_objective_notation.py` |
| P0 | 实验补充 | 废止v2中“同一OOF集合选101阈值并用单阈值CP上界认证”的保证；为未来joint-set probe冻结三分协议：按scan把train划分为60% fit、20% policy-selection、20% untouched certification，fit训练分布模型，selection只选模型/threshold，certification只计算最终one-sided risk bound；另实现Learn-then-Test family-wise baseline。用10,000次synthetic重复检验nominal 10%风险下的实际违规频率 | 对应“有限样本风险有效性、post-selection正确性”；单阈值区间不能覆盖自适应winner | synthetic中naive规则应显示其实际违规频率，三分/Family-wise方法的违规频率95%二项CI上界≤0.05；生成前不得把风险结果称为certificate | `paper3/configs/bar_depth/selection_valid_risk_protocol_v1.json`; `paper3/experiments/bar_depth/calibrate_selection_valid_risk.py`; `paper3/tests/test_selection_valid_risk_control.py`; `paper3/steps/035_bar_depth_selection_valid_risk_contract.md` |
| P0 | 实验补充 | 保留正在采集的两次exclusive raw session，不改写数据；新增独立validator，从 `raw_measurements` 与 `gpu_monitor.samples` 重新计算每方法200行、stage-sum误差、foreign PID、OOM集合、p50/p95和session verdict，禁止读取runner顶层status作为判定输入 | 对应“可复现性、生成器与验证器独立性”；当前formal analyzer主要依赖runner自报COMPLETE状态 | 对每个session生成独立audit JSON；任意删除1行、注入foreign PID、stage error>2%或OOM集合不一致都返回INVALID；原始artifact字节不变 | `paper3/experiments/bar_depth/validate_latency_session_v2.py`; `paper3/results/bar_depth/matched_latency_exclusive_v2_run1_audit.json`; `paper3/results/bar_depth/matched_latency_exclusive_v2_run2_audit.json`; `paper3/tests/test_latency_session_validator.py` |
| P0 | 实验补充 | 新建formal analyzer v3：对两session分别计算一次Pareto gate；pooled不确定性按session→sample_index→repeat_index做paired hierarchical bootstrap；range closure只在“以2030结尾且长度≥2的所有尺寸均同时p50/p95 infeasible”或“以2030结尾的连续OOM suffix”时PASS，禁止任意中间连续pair提前关闭 | 对应“时延统计可信度、candidate family闭合”；平铺400 rows与非终端closure会低估不确定性或漏掉latency re-entry | 两个session各自GO、pooled CI下界>0、session reproducibility PASS和terminal suffix closure四项同时成立才输出 `GO_REGIONAL_ORACLE_PARETO_FORMAL_V3`；任一失败输出明确STOP/INVALID | `paper3/experiments/bar_depth/analyze_matched_latency_v3.py`; `paper3/results/bar_depth/matched_latency_analysis_v3.csv`; `paper3/results/bar_depth/matched_latency_analysis_v3.json`; `paper3/tests/test_hierarchical_latency_bootstrap.py`; `paper3/tests/test_terminal_range_closure.py`; `paper3/steps/036_bar_depth_formal_latency_v3_result.md` |
| P0 | 可复现性 | 将现有DIODE 200-val在活动文档中改名为 `development_canary`；在任何joint-set模型代码提交前，冻结ETH3D与Middlebury 2014确认集的文件列表、SHA256、裁剪、scale-alignment、指标和一次性解封规则，并创建仓库测试，要求在method config hash未写入前confirmation result文件不存在 | 对应“独立确认、避免研究者自由度”；DIODE val已经驱动多轮方法决策，不能再充当最终未见测试 | 生成两个只含协议/manifest的确认集合同；manifest可字节级重建；joint-set方法、超参和阈值commit SHA写入后才允许首次生成结果 | `paper3/configs/bar_depth/confirmation_protocol_v1.json`; `paper3/artifacts/bar_depth/confirmation_manifests/`; `paper3/tests/test_confirmation_set_lock.py`; `paper3/steps/037_bar_depth_confirmation_lock.md` |
| P0 | 实验补充 | 仅在Step032、033、035和036全部PASS后新建joint-set probe合同；在完全相同features/folds下实现 independent marginal quantiles、low-rank multivariate Gaussian、conditional copula或等价joint model、Learn-then-Test、arXiv:2606.08517式adaptive selective certificate和direct conformal decision baseline；所有方法使用同一fit/selection/certification scans | 对应“方法完整性、killer baseline公平性”；必须证明joint dependence而非通用certificate带来收益 | K=3主门槛：joint方法相对replicate-wise generic-baseline envelope的micro reduction高≥1.0个百分点且paired CI下界>0；certified harm≤0.10；oracle raw gain recovery≥0.80；移除dependence后的paired差值CI下界>0。任一失败记录 `STOP_NOVELTY_JOINT_SET` | `paper3/configs/bar_depth/joint_set_probe_v1.json`; `paper3/experiments/bar_depth/train_joint_set_probe.py`; `paper3/experiments/bar_depth/evaluate_joint_set_probe.py`; `paper3/results/bar_depth/joint_set_probe_v1.json`; `paper3/steps/038_bar_depth_joint_set_probe_result.md` |
| P1 | 实验补充 | 在joint-set probe通过后运行完整Boosting-MDE pipeline与PRO、PatchRefiner V2、Depth Pro中至少两项；固定官方revision/weights，分别报告官方默认指标与BAR统一scale-aligned指标，并在同一独占A800协议下测端到端p50/p95/显存 | 对应“完整最近邻、公平Pareto”；naive DAV2输入放大不能代替高分辨率专用方法 | 每个方法生成逐图结果、版本/权重哈希、400条两session timing；若任一完整近邻在相同或更低p95下同时支配BAR主指标，输出 `STOP_NO_PARETO_SPACE` | `paper3/configs/bar_depth/full_neighbor_baselines_v1.json`; `paper3/experiments/bar_depth/run_full_neighbor_baselines.py`; `paper3/results/bar_depth/full_neighbor_baselines_v1.csv`; `paper3/steps/039_bar_depth_full_neighbor_result.md` |
| P1 | 消融补全 | 使用冻结predictions计算 boundary quantile `[0.85,0.90,0.95]` × weight `[2,5,10]` 九组指标，并同时输出AbsRel、RMSE、δ1、SILog、DBE-accuracy、DBE-completeness；对heuristic、generic-risk baseline、joint model、all-12和oracle执行同一scan-bootstrap | 对应“指标稳健性、贡献证据匹配”；当前主信号可能依赖单一自定义边界权重 | 生成9组point+CI；若joint-vs-killer方向在≥3组翻转，正文只允许metric-specific claim，不得写普遍深度改善 | `paper3/configs/bar_depth/metric_robustness_v1.json`; `paper3/experiments/bar_depth/run_metric_robustness.py`; `paper3/results/bar_depth/metric_robustness_v1.csv`; `paper3/steps/040_bar_depth_metric_robustness.md` |
| P1 | 消融补全 | 在DIODE train-only上执行 bilateral 81组和unsharp 16组参数网格，按train raw signed reduction为每类选择唯一winner，再一次性评测development canary；使用replicate-wise control envelope比较high-pass | 对应“替代解释排除、control公平性”；当前两组冻结control不能代表各自方法族 | 输出97组train score、两组冻结winner、val signed reduction/latency及paired envelope CI；若high-pass差值CI下界≤0，撤回patch-information claim | `paper3/configs/bar_depth/no_forward_control_grid_v1.json`; `paper3/experiments/bar_depth/tune_no_forward_controls.py`; `paper3/results/bar_depth/no_forward_control_train_grid_v1.csv`; `paper3/results/bar_depth/no_forward_control_val_v1.json` |
| P1 | 实验补充 | 在DAV2-B与Depth Pro上复用冻结action/selection规则；DAV2-B使用scale-aligned协议，Depth Pro禁止GT scale alignment；随后在已锁定ETH3D/Middlebury确认集上只运行一次冻结joint model与threshold | 对应“跨backbone、跨数据和metric边界”；单一DAV2-S/DIODE不足以支撑强CCF-C | 每个backbone×dataset输出base、heuristic、generic certificate、joint、oracle、标准指标、risk与latency；不允许目标域调参，任何失败slice完整保留 | `paper3/configs/bar_depth/backbone_external_eval_v1.json`; `paper3/experiments/bar_depth/run_backbone_external_eval.py`; `paper3/results/bar_depth/backbone_external_eval_v1.csv`; `paper3/steps/041_bar_depth_external_validity.md` |
| P1 | 可复现性 | 新建paper3 README、锁文件和CPU reanalysis脚本；声明所有scikit-learn/训练依赖、数据下载校验、模型revision、GPU命令与仅从已提交CSV重算所有gate的命令；添加CI测试重算target audit、baseline envelope、direct accuracy envelope和最终risk/Pareto summary | 对应“可复现性、独立重分析”；当前只有宽版本pyproject和散落命令 | 全新Python3.12环境按README执行后，所有已提交point/CI/status在 `1e-10` 容差内一致；任意config/CSV字节变化触发hash mismatch | `paper3/README.md`; `paper3/uv.lock`; `paper3/scripts/reproduce_all_analysis.sh`; `paper3/tests/test_committed_artifact_reanalysis.py` |
