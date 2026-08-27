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
| 001 主线范围 | STOPPED-BY-H-SENSITIVITY-CONTROL | 004-A 的 semantic-preserving region AbsRel degradation 95% CI `[0.000579, 0.001777]` 不含 0；冲突特异性门禁失败 | 归档 CoVoL；新方向须另做范围变更和 Research Opportunity Gate |
| 002 最近邻审计 | DONE-DESIGN | 增补 MRUF、DeferredSeg、Regression Deferral、Density-Ratio Post-Hoc L2D；覆盖机制已撤回新颖性 | 首次 GPU 实验前再检索一次最新近邻 |
| 003 干预数据 | STOPPED-CURRENT-DATA-BRANCH / DIAGNOSTIC-PREDICATE-PASS | NYUv2 500/500 eligible；从原 manifest 的 router-train 固定 100 图/59 clusters，生成 1200 local rows、四类各 300、machine-check 100%；独立规则分层样本 100/100 predicate pass，自然性 pending。第二候选因协议/下载访问 `BLOCKED_SOURCE_ACCESS` | 完成 naturalness 审计；合法获取候选 source 后按冻结顺序 dry-run |
| 004 缺陷复现 | 004-A-STOP-H-SENSITIVITY / 004-B-STOPPED | 100 图、1200 rows、59 clusters、10,000 bootstrap；两个冲突族为正，但 semantic-preserving 对照也稳定退化；逐行 CSV 与 summary 已锁定 | 不运行 004-B，不事后修改判据 |
| 005 冻结专家 | STOPPED-BY-004-A / VALIDATOR-DONE-CODE | cluster-OOF v2 plan与实体 cache validator 已实现并通过合成测试；真实 checkpoint/cache 有意不存在 | 不训练 CoVoL D0/D1 |
| 006 语义增量 | STOPPED-BY-004-A | feature firewall 与 constrained policy 合同保留；真实 controls/results 有意不存在 | 不执行 Claim-F |
| 007 公平基线 | STOPPED-BY-004-A | baseline 合同保留，未实现模型实验 | 不执行 CoVoL killers |
| 008 最终 canary | STOPPED-BY-004-A | Claim-M 结果有意不存在 | 不执行 Main-PR |
| 009 组件消融 | SPECIFIED | granularity 与 hard/soft boundary 协议已写定 | 删除无独立增益或产生边界伪影的组件 |
| 010 复现环境 | PENDING | 依赖方法代码 | 锁依赖、硬件、运行时与一键命令 |
| 指标/审计代码 | ROUND7-HELPERS-DONE-CODE / FORMAL-RESULTS-BLOCKED | full-crop weights、cluster-balanced weighted CVaR、retention LCB/test stop、per-seed schema、operating artifact lineage、feature callables与实体 cache validator有合成/手算测试 | 仍缺训练器和真实 outcome；不得把 helper QA 写成科学结果 |
| 015 范围恢复 | SUPERSEDED-BY-004-A-STOP | 固定三候选均为 `PENDING_SOURCE_ACCESS`，不是 coverage FAIL；但上游 H-sensitivity 控制条件已停止问题主张 | 不再为 CoVoL 获取数据；审计仅作历史记录 |
| A800 GPU 执行基础 | 004-A-COMPLETED / COVOL-QUEUE-STOPPED | GPU 2 上完成正式 004-A；Python 3.12.13、torch 2.5.0+cu121、A800 80GB；返回科学 STOP | 不为 CoVoL 重启 queue |
| 011 主张语言 | DONE-DESIGN | 因果/安全 overclaim 已移除；Claim-F/Claim-M 分开 | 结果出现后逐条更新 claim status |
| 012 Q-GeoRoute | PARKED | CoVoL Gate-0 已否定，但尚未完成范围变更与新的机会/近邻门禁 | 不自动启动；先与其他机会共同审计 |

## 当前不能声称的内容

- 已有 Step003 真实 training-only source/pilot/coverage 负门禁、diagnostic-only intervention JSONL、独立规则 predicate precision 100/100 和正式 H-sensitivity 诊断；人类 naturalness 未评估。H-sensitivity 触发负门禁，仍无 D0-relative defect、方法结果表或 latency。
- 尚未证明文本语义有超出普通专家选择的预测力。
- 尚未实现冻结公平 `D0/D1` 或最终 router。
- 尚未达到强 CCF-C，也未进入 Paper Build。

## 每步记录要求

每个步骤完成后必须在对应文件中记录：commit/model revision、数据 manifest/hash、命令、随机种子、硬件、开始/结束时间、产物路径、主要指标与 CI、失败日志、`GO/ITERATE/STOP` 决策。失败结果不得删除。
