# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

本研究仍是 **Research Opportunity**，没有实验结果，不能称为 Paper Candidate。唯一主线是 CoVoL-Depth；Q-GeoRoute 已停放为 Gate-0 失败后的备用方向。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [审稿意见](responce_from_reviewer/review_20260821_013339.md)
6. [本轮回应](responce_from_reviewer/response_20260821_013339.md)

## 执行顺序

`003 数据协议 → 004 缺陷复现 → 005 冻结公平专家 → 006 语义增量 Gate → 007 公平基线 → 008 最终 canary`。

任何前置 Gate 失败都先记录原因和 STOP/ITERATE 决策，不得跳过并直接训练完整方法。`paper1/results/` 为空时，所有文字均只代表预注册假设与设计，不代表科学结论。
