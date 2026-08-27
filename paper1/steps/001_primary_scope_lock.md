# 001 Primary Scope Lock

## Current branch state

`RECOVER_TWO_REAL_DATASETS / STOPPED_CURRENT_DATA_BRANCH`。原 `NYUv2 + current frozen KITTI source` 已被真实 Step003 门禁停止；当前没有处于正式模型实验阶段的 Claim-M。唯一恢复路径由 [015 post-Step003 scope decision](015_post_step003_scope_decision.md) 冻结：最多按预注册顺序审计 Cityscapes、ScanNet v2、Matterport3D，选择第一个通过相同 provenance/coverage 门禁的真实数据集；三个全部失败即正式停止 Claim-M。

## Task

自动图像 caption 含局部、可机器验证的语义错误时，在两个冻结 metric-depth 候选之间逐区域选择，并在语言候选无经验收益的区域回退到纯视觉候选。

## Input

RGB 图像 `I`、自动 caption `c`、冻结纯视觉候选 `D0(I)`、冻结图文候选 `D1(I,c)`；训练期可用 metric-depth GT 构造区域经验优势，推理期不可用 GT。

## Primary Claim

| Claim | 状态 | 唯一证据 | 支持条件 |
| --- | --- | --- | --- |
| Claim-F：控制视觉难度与候选差异后，原始文本—区域语义仍有增量 advantage 预测力 | BLOCKED_CURRENT_DATA_BRANCH | Step 006 的固定宽度 B-direct/C-direct/两类 C-permuted cluster-OOF controls | 数据授权 PASS 后，C-direct 相对 B-direct/两类 C-permuted 在同一 dev-retention LCB constrained operating point 上的 CVaR/WorstOf3 逐 seed cluster-CI 均通过；Main-PR 不参与 |
| Claim-M：固定 clean utility 下的局部尾部 regret router 优于获得相同 OOF experts 与合法 zC 特征的直接 defer 方法 | STOPPED_CURRENT_DATA_BRANCH | Step 007/008 与 Risk-L2D-C、TIGER-style LOO、regression、density-ratio、dense-coherence、LOO-uncertainty faithful/matched baselines 比较 | 新 Step003 authorization PASS 后才恢复为 UNVERIFIED；每 seed dev retention LCB 冻结 threshold，internal-test 风险逐 seed cluster-CI 同向优于全部 baselines；HV 仅作 secondary |

cross-fitting、partial residualization、CVaR、clean constraint、dense defer、language-guided frozen-expert routing、leave-one-out contribution teacher、continuous regression defer 和 frozen-expert post-hoc scoring 均已被先行工作覆盖，不能单独列为创新。唯一待否证差异由 [014 objective spec](014_objective_and_algorithm_spec.md) 定义。

## Falsification

若 OOF 公平冻结 `D0/D1` 下的 fallback defect 不能稳定复现，则整个主线停止。若 Claim-F 任一 direct/permuted 门禁失败，撤回语义增量发现。若 Claim-M 不能显著优于任一 direct killer baseline，则撤回算法贡献，即使 Claim-F 成立也不得按 AGENTS.md 升级为算法 Paper Candidate；最多另行评估分析型普通 CCF-C 路径。Q-GeoRoute 只能在记录正式范围变更后作为新主线启动。
