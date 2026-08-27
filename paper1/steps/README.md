# 研究步骤审计表

状态含义：

- `DONE-DESIGN`：范围、定义或门禁已写定，不代表实验完成。
- `DONE-CODE`：实现与单元测试已完成，但不代表真实数据或科学结果已经生成。
- `IN-PROGRESS`：已有部分可运行产物，仍缺少该步骤的必要数据、模型或结果。
- `READY`：输入与实现依赖齐全，可执行。
- `SPECIFIED`：协议已写定，但数据/代码/产物尚未生成。
- `BLOCKED`：存在已确认的外部或实现依赖。
- `PENDING`：前置步骤未通过。
- `PARKED`：备用方向，不允许占用当前资源。
- `STOP`：对应假设已被证据否定。

| 步骤 | 状态 | 本轮证据 | 下一出口 |
| --- | --- | --- | --- |
| 001 主线范围 | DONE-DESIGN / STOPPED-CURRENT-DATA-BRANCH | `RECOVER_TWO_REAL_DATASETS` 已冻结；原 NYUv2+current KITTI source 停止；Q-GeoRoute 停放 | 按 015 顺序完成第二真实数据集审计；三个全失败即 STOP Claim-M |
| 002 最近邻审计 | DONE-DESIGN | 增补 MRUF、DeferredSeg、Regression Deferral、Density-Ratio Post-Hoc L2D；覆盖机制已撤回新颖性 | 首次 GPU 实验前再检索一次最新近邻 |
| 003 干预数据 | STOPPED-CURRENT-DATA-BRANCH / DIAGNOSTIC-PREDICATE-PASS | NYUv2 500/500 eligible；从原 manifest 的 router-train 固定 100 图/59 clusters，生成 1200 local rows、四类各 300、machine-check 100%；独立规则分层样本 100/100 predicate pass，自然性 pending。第二候选因协议/下载访问 `BLOCKED_SOURCE_ACCESS` | 完成 naturalness 审计；合法获取候选 source 后按冻结顺序 dry-run |
| 004 缺陷复现 | 004-A-PENDING-MODEL-EXECUTION / 004-B-BLOCKED | TR2M core 与 relative-depth checkpoint 已锁定 SHA；尚缺 DINOv2/CLIP、批量 runner 和 clean→corrupt 结果；正式 fallback 仍缺授权与公平 experts | 完成 training-only H-sensitivity；失败即停止问题主张 |
| 005 冻结专家 | BLOCKED-BY-STEP003 / VALIDATOR-DONE-CODE | cluster-OOF v2 plan与实体 cache validator 已实现；打开 checkpoint/config/training/cache 重算哈希，三 seed×D0/D1×controls 合成覆盖测试通过 | authorization PASS 后运行 32-sample smoke 和真实 cache；合成测试不是模型证据 |
| 006 语义增量 | BLOCKED-BY-STEP003-AND-005 | 三类真实 extractor callable、sanitized-input firewall 和 constrained policy合同已落代码/规范；真实 controls/results 缺失 | 公平 cache/corpus 后执行；AUROC 与 constrained CVaR/Worst 门通过，HV 仅 secondary |
| 007 公平基线 | SPECIFIED | 合同加入四个 published direct baselines、artifact controls 与 robust experts | 实现全部方法；缺一项不得判 Claim-M |
| 008 最终 canary | STOPPED-CURRENT-DATA-BRANCH / BLOCKED-NEW-AUTH | Claim-M 要求 cluster-balanced constrained risk、test-retention stop，以及三个固定 seed 各自 cluster CI 同向；不再做 3-seed population bootstrap | 先恢复合规数据分支，再完成全部 direct/robust killers |
| 009 组件消融 | SPECIFIED | granularity 与 hard/soft boundary 协议已写定 | 删除无独立增益或产生边界伪影的组件 |
| 010 复现环境 | PENDING | 依赖方法代码 | 锁依赖、硬件、运行时与一键命令 |
| 指标/审计代码 | ROUND7-HELPERS-DONE-CODE / FORMAL-RESULTS-BLOCKED | full-crop weights、cluster-balanced weighted CVaR、retention LCB/test stop、per-seed schema、operating artifact lineage、feature callables与实体 cache validator有合成/手算测试 | 仍缺训练器和真实 outcome；不得把 helper QA 写成科学结果 |
| 015 范围恢复 | DONE-DESIGN / SOURCE-ACCESS-BLOCKED | 固定三候选、首个 PASS 选择规则、阈值与机器审计器；当前三者都需用户账户/协议后才能下载 | 合法获取 source archives 并固定实际 hash；不得把 pending 当 FAIL |
| A800 GPU 执行基础 | SHARED-CANARY-PASS / EXCLUSIVE-PAUSED | shared 模式在 GPU 2 与既有任务共存时完成极小 CUDA 张量测试；exclusive scheduler 已 graceful drain，PENDING state 保留 | 仅在科学门禁恢复后重启；该结果不是算法证据 |
| 011 主张语言 | DONE-DESIGN | 因果/安全 overclaim 已移除；Claim-F/Claim-M 分开 | 结果出现后逐条更新 claim status |
| 012 Q-GeoRoute | PARKED | 仅保留 Phase-0 Go/No-Go | CoVoL Gate-0 否定且更新 001 后才能启动 |

## 当前不能声称的内容

- 已有 Step003 真实 training-only source/pilot/coverage 负门禁与 diagnostic-only intervention JSONL；独立规则 predicate precision 为 100/100，但 naturalness 与 H-sensitivity 未完成。已有锁定的 released core checkpoint 文件不等于模型执行证据；仍无缺陷复现、方法结果表、科学置信区间或 latency。
- 尚未证明文本语义有超出普通专家选择的预测力。
- 尚未实现冻结公平 `D0/D1` 或最终 router。
- 尚未达到强 CCF-C，也未进入 Paper Build。

## 每步记录要求

每个步骤完成后必须在对应文件中记录：commit/model revision、数据 manifest/hash、命令、随机种子、硬件、开始/结束时间、产物路径、主要指标与 CI、失败日志、`GO/ITERATE/STOP` 决策。失败结果不得删除。
