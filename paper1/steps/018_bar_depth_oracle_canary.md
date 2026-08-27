# 018 BAR-Depth Oracle Patch-Utility Canary

## Frozen decision

本步骤只回答：高分辨率深度的区域细化收益是否足够大且足够集中，从而值得研究
预算化选择算法。配置以
[`oracle_canary_v1.json`](../configs/bar_depth/oracle_canary_v1.json) 为唯一机器可读
定义；结果生成后不得修改阈值或主 merge variant。

## Execution order

1. 下载官方 DIODE validation archive，核对 MD5 `5c895d09201b88973c8fe4552a67dd85`；
2. 枚举 20 scans，每 scan 固定哈希选择 10 张并写入逐文件 SHA256 manifest；
3. 锁定 Depth Anything V2 官方源码 revision 和 V2-S 权重 SHA256；
4. 每图执行一次 base 与 12 次 patch 前向，记录逐 cell utility 和便宜启发式；
5. 用 scan-cluster bootstrap 汇总并执行冻结 GO/STOP；
6. 无论结果正负，保存完整逐 cell CSV、summary、命令、版本和失败切片。

## Interpretation boundary

- `GO_ORACLE`：仅表示有足够且集中的 oracle headroom；router 可学习性仍未验证。
- `STOP_INSUFFICIENT_HEADROOM`：局部细化没有实际收益空间。
- `STOP_DIFFUSE_UTILITY`：收益存在但必须接近全量执行，不支持预算选择。
- `STOP_GLOBAL_SAFETY`：细节指标改善以普通 AbsRel 明显恶化为代价。
- 数据、模型或 200 图合同不满足时为 `INVALID_CANARY`，不能判科学 STOP。

共享 GPU 下的耗时只作运行诊断，不作为论文 latency；正式计时必须在 exclusive
条件下同步测量。

## v1 outcome

v1 完成数据与模型合同并生成 2400 region rows，但 metric-domain 审计发现 outdoor
存在 affine-aligned inverse depth 非正并被 epsilon clipping。原始 gate STOP 因此是
`INVALID_METRIC_ALIGNMENT`，不能判方向失败；证据与唯一允许的 v2 repair 见
[Step 019](019_bar_depth_v1_metric_audit.md)。
