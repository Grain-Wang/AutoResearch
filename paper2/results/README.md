# Results

在此保存可由命令行重建的实验结果、统计汇总和绘图输入。大型原始数据与模型产物需另行制定存储策略。

`blockstamp/ring_producer_canary.json` 保留 smooth-NMOS ring 的逐步 producer、tube、
checker 与事后 reference 诊断；`blockstamp/diode_rc_producer_sweep.csv` 及 manifest
保留完整 precision × tolerance × radius 网格。两者的 Decimal-160 reference 均为
non-rigorous high-precision test reference，不是 checker oracle。

`blockstamp/component_ladder_parts/` 是本地可重建的 120 个逐配置 transient checkpoint，
默认不进入 Git。正式 Git 证据是 `component_ladder.csv`、manifest 与
`component_ladder.summary.json`。其中 summary 是 2026-09-02 component-ladder 阶段的
冻结历史快照，内嵌的旧 gate/M2 状态不得覆盖独立的当前 `next_round_gate.json`。该
component round 为 `COMPLETE-CANARY / HOLD`：覆盖与 matched hashes 通过，但仅含
`steps=100`、`replicate=0`，不能替代五 replicate 的 nonlinear M2。
`b2_fairness.json` 已更新为 component-matched schema 2 证据。

`blockstamp/minimal_probe.csv` 及 manifest 保存完整冻结 M2：2,250/2,250 measured
rows 和 450 warm-ups。注册规则给出 `W=PASS`、`D=E=STOP`，但全部整轨 verdict 为
`UNKNOWN`，且 whole-run strict fallback 没有恢复任何 `ACCEPT`。

`blockstamp/interface_contraction_canary.json` 保存随接受 Krawczyk image 传播接口的强
pointwise/slab baseline。六个 100-step 实例中，contractive pointwise 全部改善旧 B2
prefix；没有 fixed slab 或 largest-first adaptive policy 得到更长 prefix。因此当前 W
为 `FAIL-CANARY / ITERATE`，不能用原 M2 的正信号升级论文候选。

`blockstamp/operator_stress.json` 是当前 gate 以 hash 绑定的 M1 operator stress canary。
`experiments/summarize_round5.py` 保留为历史聚合工具；它默认读取的 `integrity_replay/`
是未进入 Git 的本地审计输入，不是解释当前 gate 所必需的正式证据，也不授权在已关闭
的 Round 5 中重新执行。

Git 只归档正式 aggregate、manifest、gate 和必要 canary。以下目录属于本地执行状态并
被 `.gitignore` 排除：`minimal_probe_parts/`、`component_ladder_parts/`、
`integrity_replay/` 和 `minimal_probe_invalidated/`。前两者是 resumability checkpoint，
第三者重复正式 CSV，最后一项只含已判无效的 bug runs；它们都不是当前正式证据。
