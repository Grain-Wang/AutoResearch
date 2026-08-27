# 对第 7 轮审稿意见的回应

## 总体判断

我们接受“当前仍未达到强 CCF-C，且尚未成为 Paper Candidate”的结论。本轮选择审稿人建议的 `RECOVER_TWO_REAL_DATASETS`，而不是在原 `NYUv2 + current frozen KITTI source` 上继续推进。原分支保持 `STOPPED_CURRENT_DATA_BRANCH`；Step 004-B、005、006、007、008 均由机器授权文件阻断。三个预登记真实候选目前都因需要数据协议或账户而处于 `PENDING_SOURCE_ACCESS`，这不是 coverage FAIL，也没有被写成科学负结果。

本轮新增的真实证据包括 NYUv2 official-train diagnostic corpus 与随后完成的 004-A：100 图、59 个独立 clusters、1200 个局部干预行，builder machine-check 为 1200/1200；另一个不读取 builder `passed` 字段的规则解析器按四族各 25 行稳定抽样，predicate precision 为 100/100。held-out-template text-only macro-F1 为 0.488（预注册上限 0.60），自动 surface-form 为 1200/1200；人类自然度仍未评估。TR2M clean→corrupt 已返回 `STOP_H_SENSITIVITY`：两个冲突族有正向区域 AbsRel 信号，但 semantic-preserving 对照也稳定退化，故不能证明冲突特异的 H-sensitivity，更不能证明 fallback 或 Main-PR 有效。

## 对核心问题的处理

### 1. 冻结范围并把失败门禁变成机器授权

新增 [`015_post_step003_scope_decision.md`](../steps/015_post_step003_scope_decision.md)，冻结最多三个候选及顺序：Cityscapes、ScanNet v2、Matterport3D。选择规则只依赖 source、license、RGB/depth/mask 对齐、projected eligible images/pairs 和不少于 20 个独立 clusters，禁止看到方法结果后换数据。三个候选全部 coverage FAIL 时固定停止 Claim-M；若要缩为 NYUv2-only，必须另做范围决策。

新增 [`step003_authorization.json`](../artifacts/covol/step003_authorization.json) 和共享 validator。当前 artifact 对 004-B/005/006/007/008 六类正式动作均返回 `BLOCKED_BY_STEP003`、exit code 3。validator 同时重算 source coverage hash，并要求 `status=PASS`、`decision=GO_LOCAL_CLAIMS_*` 及至少两个完全一致的 formal datasets；在失败 artifact 中伪造非空 dataset 数组不能绕过。

### 2. 第二真实数据集与 KITTI source gap

新增统一候选配置、审计器和回归测试。审计器固定恰好三个候选和顺序，逐文件重算 RGB/depth/mask SHA256，检查 frame alignment、许可标志、50 图 stable-hash dry-run、投影 full-pilot coverage 与 cluster 数。当前可移植结果为 [`second_dataset_candidate_audit.json`](../results/covol/second_dataset_candidate_audit.json) 及其逐候选 [`CSV`](../results/covol/second_dataset_candidate_audit.csv)：三个候选均为 `PENDING_SOURCE_ACCESS`，总体为 `BLOCKED_SOURCE_ACCESS`。由于数据条款需要由数据使用责任人接受，本轮没有代替用户接受协议，也没有把缺少下载权限算作数据集失败。

新增 KITTI local-oracle gap auditor，主键固定为 drive/camera/frame，并分别报告 depth-only、mask-only、joint、有效 mask-depth 像素、eligible images/pairs/clusters。当前没有拟议 depth/mask source manifest，因此没有生成 `kitti_local_oracle_gap.csv`；这使“当前冻结 source 未提供”与“KITTI 数据族不可行”保持严格区分。

### 3. Diagnostic corpus 与独立 predicate audit

在原 Step003 1000-row、hash-linked、official-training manifest 的 router-train 部分稳定选取 100 图和 59 clusters。四个 local families 各有 3 个 variants，每族 300 行，总计 1200 行；null/global 各 100 行并单独保存。所有行标注 `diagnostic_only_never_formal`，不能进入未来 train/dev/internal-test 或局部风险主结果。

可移植 construction audit 记录 source、selected image/cluster set 与三个输出的 SHA256，见 [`diagnostic_intervention_audit.json`](../results/covol/diagnostic_intervention_audit.json)。独立规则审计器不信任 builder 的 `passed` 字段，重新解析 semantic preservation、target deletion、entity conflict 和 depth-relation conflict；四族各 25/25 通过，见 [`diagnostic_independent_audit.json`](../results/covol/diagnostic_independent_audit.json)。我们将状态写为 `PASS_PREDICATE_PRECISION_NATURALNESS_PENDING`，没有把规则一致性外推为自然语言质量。

### 4. 004-A checkpoint 与执行边界

已锁定 TR2M 官方代码 commit、released ScaleMap checkpoint、官方 Depth Anything ViT-S、DINOv2 ViT-L 及 CLIP ViT-L/14 checkpoint 的文件大小与 SHA256，见 [`tr2m_release_audit.json`](../results/covol/tr2m_release_audit.json) 与 004-A summary。可续跑 batch runner 已实现并通过合成测试：同图一次提取视觉/相对深度特征、批处理 clean+12 captions、每图原子落盘。真实执行已在锁定运行环境中完成，生成 [`sensitivity_diagnostic.csv`](../results/covol/sensitivity_diagnostic.csv) 与 [`summary`](../results/covol/sensitivity_diagnostic_summary.json)。100 图、1200 rows、59 clusters 的预注册区域 AbsRel 结果为：semantic-preserving `0.001156 [0.000579, 0.001777]`、target deletion `0.000055 [-0.001198, 0.001109]`、local entity conflict `0.001620 [0.000195, 0.002903]`、depth relation conflict `0.000806 [0.000347, 0.001298]`。由于 semantic-preserving CI 不包含 0，固定门禁失败；我们没有只挑选两个正向冲突族报告，也没有修改阈值。

004-A 的固定否证门槛不变：至少一个局部错误族的 paired cluster-bootstrap mean degradation 95% CI 下界大于 0，同时 semantic-preserving CI 包含 0；否则停止 CoVoL 问题主张。该结果即使通过也只证明同一 D1 对 caption corruption 敏感，不证明 D0 fallback 必要。

## 统计与可复现性修正

| Round-7 意见 | 本轮落地 | 证据边界 |
| --- | --- | --- |
| region weight 应相对 full official crop | `main_pr_objective.py` 允许局部权重和小于 1，剩余质量固定走 D0；新增 50% crop × 0.2 local regret = 0.1 手算测试 | `DONE-CODE`，不是模型结果 |
| 主 estimand 应 cluster-balanced | `metrics.py` 实现 cluster-balanced mean、fractional-boundary CVaR、clean gain/coverage；micro/image-weighted 降为 sensitivity | `DONE-CODE` |
| dev retention 需 one-sided LCB | constrained evaluator 仅接受 cluster-bootstrap retention LCB ≥0.80 的 threshold；点估计恰为 0.80 但 LCB 较低会被拒绝 | `DONE-CODE` |
| test clean utility 需停止规则 | test retention 点估计 <0.80 返回固定 `STOP_TEST_RETENTION_VIOLATION` | `DONE-CODE` |
| Claim-F 与 Claim-M operating point 不一致 | 两者均改为 dev-frozen constrained point；hypervolume 仅作 secondary | `DONE-CODE/DESIGN`，Claim-F 仍未验证 |
| 三 seeds 不应做 seed-population bootstrap | seeds 17/29/43 固定重复；每 seed 独立 cluster CI，跨 seed 只报 mean±sample SD，并要求风险差方向一致 | `DONE-CODE/DESIGN` |
| OOF/cache 缺少实体和 hash 证据 | 主键固定为 `(dataset,image_id,seed,candidate_id,control_type)`；validator 打开 checkpoint/config/training-manifest/cache 重算 hash，以 cluster 检查训练/预测隔离 | `DONE-CODE`；正式 cache artifact 有意不存在 |
| operating-point lineage 可被裸 index 绕过 | internal evaluator 必须接收 artifact path，重新打开并校验 dev manifest、method config、raw outcome、grid、expert cache、metrics spec 和 minimum clean gain | `DONE-CODE` |
| feature allowlist 指向不存在函数 | `candidate_features`、`caption_region_features`、`image_features` 已成为可 import callable，只接受 allowlisted sanitized mapping；额外 GT 字段硬失败 | `DONE-CODE` |
| 公平 D0/D1 与 router 尚未实现 | 本轮没有越过 Step003 实现或训练正式模型；PyTorch dual-candidate smoke 仍 pending | `BLOCKED_BY_STEP003` |

合成回归测试只验证公式、阻断和 lineage 实现。它们不能替代真实 checkpoint、OOF prediction、H-sensitivity、killer baseline 或主结果。

## 当前主张状态

- 研究阶段：CoVoL 为 `STOPPED_BY_H_SENSITIVITY_CONTROL`，不是活跃 Research Opportunity，也不是 Paper Candidate。
- Claim-F：`STOPPED_BY_H_SENSITIVITY_CONTROL`；没有真实 D0/D1/router 结果，也不再执行。
- Claim-M：`STOPPED_BY_H_SENSITIVITY_CONTROL`；第二数据集访问状态不再是恢复本方向的充分条件。
- H-sensitivity：`STOP_H_SENSITIVITY`。冲突族信号存在，但 semantic-preserving 对照失败；人类 naturalness 仍未评估。
- 最强反方意见：观测到的是一般文本表面形式敏感性，而不是局部语义冲突的特异效应；效应量也很小，不能支撑 fallback-aware router 的算法动机。

## 下一项真正改变论文判断的工作

004-A 已完成并否定当前问题的冲突特异性前提。下一项工作应是重新进行 Research Opportunity discovery：以近期近邻、可复现算法缺陷和非等价算法路径形成至多五个候选，再选择新主线。不得继续为 CoVoL 获取第二数据集、训练公平 experts、生成 OOF cache 或启动 Main-PR。
