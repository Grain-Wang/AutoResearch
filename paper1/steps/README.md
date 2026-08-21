# 研究步骤审计表

状态含义：

- `DONE-DESIGN`：范围、定义或门禁已写定，不代表实验完成。
- `READY`：输入与实现依赖齐全，可执行。
- `SPECIFIED`：协议已写定，但数据/代码/产物尚未生成。
- `BLOCKED`：存在已确认的外部或实现依赖。
- `PENDING`：前置步骤未通过。
- `PARKED`：备用方向，不允许占用当前资源。
- `STOP`：对应假设已被证据否定。

| 步骤 | 状态 | 本轮证据 | 下一出口 |
| --- | --- | --- | --- |
| 001 主线范围 | DONE-DESIGN | 唯一主线锁为 CoVoL；Q-GeoRoute 停放 | 只有正式范围变更才能切主线 |
| 002 最近邻审计 | DONE-DESIGN | 8 项矩阵补齐 2024/2026 关键近邻 | 实验前再检索一次最新近邻 |
| 003 干预数据 | SPECIFIED | 数量、schema、泄漏规则、机器检查已预注册 | 生成脚本与 12,000 条 JSONL |
| 004 缺陷复现 | BLOCKED | TR2M eval 权重可用；原始数据与 caption 产物未就绪 | 两数据集至少一局部错误族 regret CI 下界 >0 |
| 005 冻结专家 | BLOCKED | 上游 TR2M 尚未释放训练代码 | 自行复现公平 heads 或切换可训练基线 |
| 006 语义增量 | PENDING | A/B/C nested probe 与阈值已定义 | C-B AUROC ≥0.03 且 CI 下界 >0 |
| 007 公平基线 | PENDING | baseline 清单与公平约束已定义 | 同缓存、参数量 ±10%、3 seeds |
| 008 最终 canary | PENDING | 80% retention / 50% regret 阈值已预注册 | 两数据集显著超过最强简单基线 |
| 009 组件消融 | PENDING | 依赖 008 | 每个贡献对应独立消融 |
| 010 复现环境 | PENDING | 依赖方法代码 | 锁依赖、硬件、运行时与一键命令 |
| 011 主张语言 | DONE-DESIGN | 因果/安全 overclaim 已移除 | 结果出现后逐条更新 claim status |
| 012 Q-GeoRoute | PARKED | 仅保留 Phase-0 Go/No-Go | CoVoL Gate-0 否定且更新 001 后才能启动 |

## 当前不能声称的内容

- 尚无缺陷复现、数据 JSONL、checkpoint、结果表、置信区间或 latency。
- 尚未证明文本语义有超出普通专家选择的预测力。
- 尚未实现冻结公平 `D0/D1` 或最终 router。
- 尚未达到强 CCF-C，也未进入 Paper Build。

## 每步记录要求

每个步骤完成后必须在对应文件中记录：commit/model revision、数据 manifest/hash、命令、随机种子、硬件、开始/结束时间、产物路径、主要指标与 CI、失败日志、`GO/ITERATE/STOP` 决策。失败结果不得删除。
