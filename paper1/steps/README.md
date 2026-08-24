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
| 001 主线范围 | DONE-DESIGN | 唯一主线锁为 CoVoL；Q-GeoRoute 停放 | 只有正式范围变更才能切主线 |
| 002 最近邻审计 | DONE-DESIGN | 增补 MRUF、DeferredSeg、Regression Deferral、Density-Ratio Post-Hoc L2D；覆盖机制已撤回新颖性 | 首次 GPU 实验前再检索一次最新近邻 |
| 003 干预数据 | FEASIBILITY-CODE-READY / REMOTE-DATA-GATE-PENDING | 本地 96 项回归通过；NYUv2+KITTI 是唯一 inferential 组合，VKITTI2 固定为 synthetic auxiliary 且 source adapter 强制 canonical full-directory enumeration；完整 intervention builder 尚未实现 | 仅在远程 `whr` 准备 NYUv2/KITTI official-training 数据并跑 CPU coverage/detectability；任一失败即 STOP，不进 005 |
| 004 缺陷复现 | PENDING | 已拆为 004-A H-sensitivity 与 004-B H-fallback-defect；前者依赖 003，后者依赖 005 | 不再用 TR2M 单 checkpoint 声称 H-defect |
| 005 冻结专家 | IN-PROGRESS | OOF stacking plan/cache 审计代码完成；同构 D0/D1、负控制和真实 cache 未完成 | 实现 PyTorch 模型并产出 OOF/final checkpoints/cache |
| 006 语义增量 | PENDING | Claim-F 改为 B-direct/C-direct/C-permuted；Main 使用 outer-5/inner-4 nested OOF | 两个 direct/permuted AUROC/HV cluster-CI 下界均 >0 |
| 007 公平基线 | SPECIFIED | 合同加入四个 published direct baselines、artifact controls 与 robust experts | 实现全部方法；缺一项不得判 Claim-M |
| 008 最终 canary | PENDING | Claim-M 要求击败全部 direct/robust killers；Claim-F-only 降级路径已写定 | 两数据集的全部 Claim-M 差值 cluster-CI 下界 >0 |
| 009 组件消融 | SPECIFIED | granularity 与 hard/soft boundary 协议已写定 | 删除无独立增益或产生边界伪影的组件 |
| 010 复现环境 | PENDING | 依赖方法代码 | 锁依赖、硬件、运行时与一键命令 |
| 指标/审计代码 | DONE-CODE | feature extractor allowlist/runtime sanitization、`cluster_id` bootstrap、dev-frozen CVaR/WorstOf3 主比较与 fixed-HV sensitivity 均有本地单测 | official metric adapter、真实结果与远端复验仍待生成 |
| 011 主张语言 | DONE-DESIGN | 因果/安全 overclaim 已移除；Claim-F/Claim-M 分开 | 结果出现后逐条更新 claim status |
| 012 Q-GeoRoute | PARKED | 仅保留 Phase-0 Go/No-Go | CoVoL Gate-0 否定且更新 001 后才能启动 |

## 当前不能声称的内容

- 已有 split/OOF/features/metrics/bootstrap 基础代码及单元测试，但尚无真实数据 JSONL、checkpoint、缺陷复现、结果表、置信区间或 latency。
- 尚未证明文本语义有超出普通专家选择的预测力。
- 尚未实现冻结公平 `D0/D1` 或最终 router。
- 尚未达到强 CCF-C，也未进入 Paper Build。

## 每步记录要求

每个步骤完成后必须在对应文件中记录：commit/model revision、数据 manifest/hash、命令、随机种子、硬件、开始/结束时间、产物路径、主要指标与 CI、失败日志、`GO/ITERATE/STOP` 决策。失败结果不得删除。
