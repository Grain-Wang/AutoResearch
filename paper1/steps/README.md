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
| 002 最近邻审计 | DONE-DESIGN | 增补 DML/cross-fitting、orthogonal learning、CVaR、risk control；标准组件不列为贡献 | 首次 GPU 实验前再检索一次最新近邻 |
| 003 干预数据 | IN-PROGRESS | official-train-only scene split builder 与泄漏单测完成；真实 manifest/干预未生成 | 导入真实 official-train/test manifests 并生成审计产物 |
| 004 缺陷复现 | PENDING | 已拆为 004-A H-sensitivity 与 004-B H-fallback-defect；前者依赖 003，后者依赖 005 | 不再用 TR2M 单 checkpoint 声称 H-defect |
| 005 冻结专家 | SPECIFIED | 仓库自有 shared-backbone dual-head 协议已锁定，不再等待 TR2M 训练代码 | 实现模型/训练脚本并产出双 checkpoint、SHA256 与 smoke test |
| 006 语义增量 | PENDING | 5-fold scene-group cross-fitting、tie band 与双门禁已唯一化 | C-B AUROC 与 Pareto hypervolume 的 CI 下界均 >0 |
| 007 公平基线 | SPECIFIED | `L2D-B`、same-feature `L2D-C`、same-objective `Risk-L2D-C` 合同已写定 | 实现同缓存、同容量、同预算的 learned gates |
| 008 最终 canary | PENDING | Claim-F/Claim-M 已分离；Claim-M 只对 `Risk-L2D-C` 判定 | 两数据集的 Claim-M 差值 CI 下界 >0 |
| 009 组件消融 | SPECIFIED | granularity 与 hard/soft boundary 协议已写定 | 删除无独立增益或产生边界伪影的组件 |
| 010 复现环境 | PENDING | 依赖方法代码 | 锁依赖、硬件、运行时与一键命令 |
| 指标实现 | DONE-CODE | 唯一指标公式与 5 个手算单测完成；全套 7 个测试通过 | 真实缓存生成后锁定版本并产出结果表 |
| 011 主张语言 | DONE-DESIGN | 因果/安全 overclaim 已移除；Claim-F/Claim-M 分开 | 结果出现后逐条更新 claim status |
| 012 Q-GeoRoute | PARKED | 仅保留 Phase-0 Go/No-Go | CoVoL Gate-0 否定且更新 001 后才能启动 |

## 当前不能声称的内容

- 已有 split/metrics 基础代码及单元测试，但尚无真实数据 JSONL、checkpoint、缺陷复现、结果表、置信区间或 latency。
- 尚未证明文本语义有超出普通专家选择的预测力。
- 尚未实现冻结公平 `D0/D1` 或最终 router。
- 尚未达到强 CCF-C，也未进入 Paper Build。

## 每步记录要求

每个步骤完成后必须在对应文件中记录：commit/model revision、数据 manifest/hash、命令、随机种子、硬件、开始/结束时间、产物路径、主要指标与 CI、失败日志、`GO/ITERATE/STOP` 决策。失败结果不得删除。
