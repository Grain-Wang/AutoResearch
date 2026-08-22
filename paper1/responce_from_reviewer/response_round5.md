# Response to Review Round 5

更新日期：2026-08-22。感谢审稿人指出 formal dataset branch、训练风险、主统计量和独立重采样单位之间的内部矛盾。本轮先修正会改变算法定义或结论有效性的 P0 问题，再补充可执行审计。研究状态仍为 **Research Opportunity**；本地合成测试通过不等于真实科学 claim 成立。

## 主要修正

| 审稿意见 | 本轮回应 | 状态与证据 |
| --- | --- | --- |
| VKITTI2 是不可执行的死分支 | 新增官方 Virtual KITTI 2 `2.0.3` adapter，校验官方 RGB/depth/class/instance/textgt archive MD5、逐文件 SHA256、scene/variation/camera/frame identity、全图深度/实例协议和 license；provenance 正式接受该合同。power 不再硬编码数据集，而是读取与 manifest hash 绑定的 coverage decision，只接受 NYUv2+KITTI 或 NYUv2+VKITTI2。 | `build_vkitti2_source_manifest.py`, `audit_provenance.py`, `power_analysis.py`；6 个新增回归测试覆盖合法源、伪造版本、伪造 checksum、RGB alias、跨 split clone 和 fallback decision。官方格式与 checksum 来源：[NAVER LABS Europe](https://europe.naverlabs.com/proxy-virtual-worlds-vkitti-2/)。 |
| fallback 可能把相关 clone 当独立场景 | `scene_id` 固定为基础 `SceneXX`，所有天气、视角和双相机序列经 scene–sequence connected component 合并为同一 `cluster_id`。VKITTI2 只有 5 个基础场景，不能用 clone 数量冒充 20 个独立场景；像素/实体 coverage 即使充足，正式独立聚类门禁仍会 STOP/仅作描述统计。 | adapter、pilot selector 测试与 Step 003 合同已同步；真实数据审计待 Linux 恢复。 |
| Step 004 仍硬编码 NYUv2/KITTI | H-fallback-defect 改为读取冻结的 `claim_dataset_decision.local_claim_datasets`；Step 008 要求结果表保存 coverage-decision SHA256 和 dataset role。 | `steps/004_defect_reproduction.md`, `steps/008_canary_decision.md`；IMPLEMENTED-DESIGN。 |
| Eq. (7) 训练了不存在的 Frankenstein caption | 正式风险改为“每个完整 caption variant 先跨 region 加权求和，再对 3 个完整 variant 取最大值”，与 WorstOf3 报告指标使用同一随机变量。新增两 region/两 variant 反例测试，旧写法风险为 2、正确写法为 1。 | `main_pr_objective.py`, `test_main_pr_objective.py`, `steps/014_objective_and_algorithm_spec.md`；IMPLEMENTED/TESTED。 |
| Eq. (9)/(10) 的 hinge Lagrangian 与 signed dual update 不一致 | 统一为标准 signed Lagrangian `L + lambda(retention_target-retention)`，`lambda>=0` 用 projected signed dual ascent；新增 20 步可行/不可行方向测试。 | 同上；IMPLEMENTED/TESTED。 |
| beta、Huber delta、region weights、batch、eta/lambda 未冻结 | 固定 `beta=1`、Huber delta `1`（outer-train median/MAD 后）、region 权重为图内 valid-depth pixel fraction、8 clusters/batch、每 cluster 最多 4 图、AdamW `1e-3/1e-4`、eta 外层训练 0.8 分位且每步 `1e-3` 更新、lambda `0/.01/[0,100]` 每步更新。 | `baseline_contract.yaml`, Step 014；SPECIFIED，真实训练未运行。 |
| soft gate 的风险解释不清 | 明确 soft loss 是 Bernoulli hard route 的期望风险，不是混合深度图 AbsRel；预注册 deterministic hard route、straight-through 与 relaxation-gap 消融。 | Step 014；SPECIFIED。 |
| bootstrap 错用 `scene_id` | `PolicyImageOutcome` 和所有重采样路径统一改用冻结的 `cluster_id`，同一 connected component 永不拆分。 | `bootstrap.py`, `test_cluster_bootstrap.py`；IMPLEMENTED/TESTED。 |
| 主 claim 缺 dev-frozen threshold + internal-test CI | 新增 dev-only constrained operating-point selector；每个方法独立选择 retention `>=0.80` 的最低 CVaR threshold，冻结 artifact 后只在 internal-test 比较 CVaR/WorstOf3。新增 paired cluster bootstrap，记录 clean-gain 无效 replicate 并在比例 `>5%` 时 STOP。 | `constrained_evaluation.py`, `bootstrap.py` 及对应测试；IMPLEMENTED/TESTED。 |
| feature denylist 可被重命名绕过 | 在 denylist 之外增加 source-function allowlist、每个 extractor 的 raw-field allowlist和 runtime sanitizer；未注册函数、`empirical_error` 等改名字段不能进入 extractor，额外 GT 字段不会传入运行时输入。 | `features.py`, `test_feature_schema_no_intervention_metadata.py`；IMPLEMENTED/TESTED。 |
| D0 zero text 会降低有效容量 | 合同改为 D0 使用 trainable shared learned-null token，并经过与 D1 完全相同的 adapter/FiLM 路径；要求逐层 active-gradient parameter parity。 | `baseline_contract.yaml`, `steps/005_frozen_experts.md`；SPECIFIED，模型/smoke 尚未实现。 |
| power 名称过度声称 | 模块、artifact 和文档明确标记为 `CONDITIONAL_INFERENTIAL_DETECTABILITY_NOT_END_TO_END_POWER`：它不模拟训练、搜索、captioner 或 threshold estimation，不能单独证明完整实验有 0.80 power。 | `power_analysis.py`, Step 003；IMPLEMENTED。 |
| 状态表仍写 22 tests / 本机完全不测试 | 删除过期固定测试数，区分“本地微型代码 QA”和“远端真实数据科学门禁”。 | `steps/README.md`, `paper1/README.md`；UPDATED。 |

## 本地验证

按用户本轮授权，仅在本机使用微型/合成数据验证代码，未连接校内 Linux、未下载真实数据、未训练模型：

- `python -m ruff check paper1`：通过；
- `python -m black --check paper1`：通过；
- `python -m pytest paper1/tests -q`：`92 passed`；
- 上一轮涉及的 47 个文件已被上述完整 `paper1` 回归重新覆盖，不再保留“尚未验证”的代码状态。

仓库级 `ruff check .` 与 `black --check .` 仍会被 `tools/` 中既存、与本论文轮次无关的 lint/format debt 阻断；本轮没有批量改写这些用户既有文件。

## 尚未完成且不冒充解决

- 尚无真实 NYUv2/KITTI/VKITTI2 manifest、coverage/detectability 结果、checkpoint、natural-error prevalence 或主结果表。
- VKITTI2 在正确的独立性定义下只有 5 个基础 scene；若不能补充独立 outdoor 数据，不能支撑跨场景尾部风险 claim。
- OOF cache 尚未完成 `(dataset,image_id,seed,candidate_id,control_type)` 与真实 checkpoint/cache 文件的实体绑定。
- learned-null D0/D1、active-gradient parity、faithful/matched published baselines 和 20–50 scene GPU pilot 尚未实现。
- 主方法仍需稳定击败 Risk-L2D-C、TIGER-style LOO 与 faithful/matched direct baselines，才能升级为 Paper Candidate。

## 当前结论

本轮消除了审稿人指出的三个直接内部矛盾：数据 fallback 死分支、训练/评估风险不一致、以及 scene/cluster 重采样不一致。它提高了协议的可执行性和可证伪性，但没有新增真实实验事实。因此 Claim-F、Claim-M 均仍为 `UNVERIFIED`，当前不进入完整 Paper Build。
