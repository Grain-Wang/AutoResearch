# 019 BAR-Depth v1 Metric-Domain Audit

## Verdict

`INVALID_METRIC_ALIGNMENT / NO_SCIENTIFIC_GO_OR_STOP`。

冻结的 v1 runner 完成了 200 张图、20 scans、2400 个 region rows，并按原门禁输出
`STOP_INSUFFICIENT_HEADROOM`。该 STOP **不能解释为研究方向失败**，因为随后针对异常
domain slice 的 base-only 审计证明：v1 把 unconstrained affine-aligned inverse depth
直接求倒数计算 AbsRel；当 affine 输出非正值时，`1e-6` clipping 会制造极大的伪深度
误差。

## Evidence

绑定审计文件为
[`v1_metric_pathology_audit.json`](../results/bar_depth/v1_metric_pathology_audit.json)：

- indoor：78,155,273 个 valid pixels 中无 clipping，mean AbsRel 为 `0.06958`；
- outdoor：60,504,062 个 valid pixels 中 157,380 个被 clipping，占 `0.2601%`；
- 100 张 outdoor 图中 15 张发生 clipping，单图最高 `7.4796%`；
- clipping 后 outdoor mean AbsRel 达 `766.05`，使 outdoor 占全局 base primary error 的
  `99.9877%`；
- 因此 v1 全局 point estimate 与 bootstrap 均被少数 metric-domain violations 主导。

原始 v1 输出、bootstrap 和 summary 保留为失败审计，不删除、不改写：

- `oracle_patch_utility.csv`；
- `oracle_raw_provenance.json`；
- `oracle_cluster_bootstrap.csv`；
- `oracle_canary_summary.json`。

## Repair rule

允许且必须执行一个 v2 repair canary：数据、200 图 manifest、模型、3×4 grid、patch
merge、25% budget、主指标权重、bootstrap 和全部 GO/STOP 阈值保持不变；唯一变化是把
image-level metric alignment 改为正值保持的 median scale-only alignment，并在运行时
要求所有 base valid pixels 在 clipping 前均为正。该修复消除非法数值域，不利用 v1
结果选择阈值、数据子集、grid、模型或 merge。

v2 结果之前，BAR-Depth 仍是 `RESEARCH_OPPORTUNITY / NOT_PAPER_CANDIDATE`，oracle
headroom 和可路由性均未验证。
