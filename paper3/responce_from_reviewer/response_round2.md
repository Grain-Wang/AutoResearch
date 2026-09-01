# Response to Review Round 2

感谢审稿人指出目标错位、post-selection 区间、时延功效与通用算法新颖性四个
决定性问题。本轮没有把协议修订写成算法结果，也没有在门禁失败后继续执行 W08。
当前总状态为：

`RESEARCH_OPPORTUNITY_JOINT_SET_PROBE_ONLY /
STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER /
FORMAL_W07_V2_PENDING / NOT_PAPER_CANDIDATE`。

## P0-1：训练目标与评价目标对齐 — DONE

新增逐图、K={1,3,6} 的 raw-vs-normalized target 审计及 10,000 次 scan
bootstrap。K=3 的 mean set Jaccard 为 0.927，但 normalized target 的 raw-oracle
recovery 只有 0.93696，低于冻结阈值 0.95；14% 图像的 Top-3 集合不同。另有
32/2400 个区域 `weight_sum=0`，使 v1 标签出现 0/0。自动决策为
`REDEFINE_RANK_PRESERVING_TARGET`。

v2 标签现为 `u_i/E_0(x)`，其中 `E_0(x)` 在同一图内恒定，因而与 raw `u_i`
严格保序。v1 合同和历史产物未覆盖。

## P0-2：utility、risk 与 threshold 合同 — DONE-CODE / NOT-EXECUTED

新合同统一使用 `u_i`，定义 unit action cost、集合 raw utility、negative-utility
mass、图像级 harm event `1[sum selected u_i < 0]` 与 harm CVaR90。at-most-K 轨固定
101 个 train-OOF score quantile thresholds；所有 score baseline 使用相同稳定 tie
rule、one-sided 95% Clopper--Pearson UCB≤0.10 条件和 `abstain_all` fallback。
validator 会拒绝缺少上述字段或放宽 feature firewall 的合同。

这只是可执行诊断合同；没有产生 router 训练或评价结果。

## P0-3：通用算法最近邻 — DONE / CURRENT METHOD STOPPED

新矩阵包含 13 项工作和 10 个算法轴，覆盖 selective regression、learning to
defer、conformal risk control、cost-aware routing 与 spatial adaptive inference。
结论是现有 `point score + train threshold + Top-K/abstention` 只是已有方法的应用性
组合，固定决策为 `STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER`，因此当前 W08 已
停止。

仅保留一个尚未授权训练的 Research Opportunity：联合建模 adaptively selected set
的总 utility 分布，并构造 selection-aware lower confidence bound。它必须在相同
features/folds 下超过 point Top-K、Learn-then-Test 和直接 conformal decision
calibration，并证明 within-image dependence 改变集合风险；否则最终 `STOP_NOVELTY`。

## P0-4：replicate-wise max envelope — DONE

预算 baseline v2 在每个 scan-bootstrap replicate 内重新选择最大 non-oracle
baseline。K=3 的 oracle-minus-envelope point margin 仍为 3.0364 个百分点，95% CI
为 `[1.6991, 4.0169]` 个百分点。10,000 次 replicate 中，point winner 并不固定：
RGB/base combination 胜 5,035 次，base gradient 胜 4,964 次，random 胜 1 次。
因此该修正确实改变了不确定性计算，而不是只更换状态名。

matched-latency v2 同时重采样 scan accuracy 与 timing units，在每个 replicate 内
重建 feasible set 并重选精度最优候选。对旧 shared 数据的修正结果仍仅为
`PROVISIONAL / NOT_FORMAL`：oracle-minus-replicate-best direct 的 95% joint CI 是
`[4.2063, 12.3771]` 个百分点。该结果不能完成正式门禁。

## P0-5/P0-6：正式时延与 direct range — ACCURACY-DONE / LATENCY-RUNNING

已冻结 518--2030、步长 56 的 28 个整图候选。accuracy v2 runner 对每个候选输出
200 图结果，并将重试后 OOM 记录为候选状态。range 只有在两个连续尺寸同时满足
p50/p95 超过 regional K=3，或出现直到 2030 的连续 OOM 后才闭合。

正式时延 runner 要求两次独立 exclusive A800 session；每次每方法 20 warm-ups、
20 个跨 scan 图×10 repetitions，共 200 raw rows。它持续每秒采样 compute PID、
clock、power、pstate，记录 p50/p90/p95、模型预处理/base forward/selector/patch
forward/merge/output resize/orchestration、峰值显存和吞吐。外来 PID、monitor error、
stage sum error>2% 或行数不足都会使 session 失效。合并分析还要求两 session 的
p50 相对差≤5%、p95≤10%。

审稿前等待的 W07-v1 任务从未获得 GPU（`PENDING/attempt=0`），已 graceful drain；
没有终止任何 GPU 作业。远程 CPU 合同测试为 15 passed；四任务 fail-closed 队列已
在用户级 tmux 中启动并保持运行。

其中 28 尺寸 accuracy task 已在首次 exclusive 尝试中完成：28×200=5,600 行，
518--2030 全部 `OK`、没有 OOM。点估计上最强整图候选仍是 518（改善 0%），其余
27 个尺寸均为负改善，次强 574 为 -0.4214%。新增 accuracy-only 分析在每个
scan-bootstrap replicate 内对全部 28 个尺寸取最大值，不借助时延先筛选候选。
regional K=3 oracle 相对这一 all-size envelope 的 point margin 为 9.6600 个百分点，
10,000 次 paired bootstrap 95% CI 为 `[1.4235, 11.9335]` 个百分点。因此 direct
accuracy killer 尚未消除 oracle 空间；该结论对任何未来 latency-feasible 子集是保守
的，但不等于正式 Pareto PASS。

latency session 1 当前为 `RUNNING/attempt=1`。它在干净分配后启动，但一秒监控随后
观察到外来 compute process 进入同卡，所以本次尝试受污染、不能作为 exclusive
证据。runner 将 fail-closed，队列配置了一次重试；重试仍会等待 4×30 秒完整独占
窗口，不终止或抢占其他进程。session 2 与 CPU formal analysis 继续依赖有效的
session 1，当前均为 `PENDING/attempt=0`。故 Step 029 仍明确记录
`TWO_VALID_EXCLUSIVE_SESSIONS_PENDING / NOT_FORMAL`。

## P0-7：train manifest 与 W08 — NOT-EXECUTED BY GATE

工单要求 objective、generic novelty 与 formal W07 全部 PASS 后才生成 DIODE-train
manifest 和 patch labels。generic novelty 已对当前方法返回 STOP，formal W07-v2
尚未完成，因此没有下载/生成 train labels，也没有运行 Ridge/MLP 或读取冻结 val。
这是预注册停止规则的执行，不是遗漏实验。

## P0-8：claim scope — DONE

活动文档统一使用：

- `Boosting-MDE edge-density selector adapted to frozen BAR actions`，不再冒充完整
  Boosting-MDE pipeline；
- `GO_PATCH_INFORMATION_BEYOND_TWO_FROZEN_CONTROLS`，只覆盖两类冻结 control 与
  各一组参数；
- shared latency 一律带 `PROVISIONAL / NOT_FORMAL`；
- 题目与贡献收缩为 selective regional refinement，不声称异质成本预算分配；
- 只陈述 per-image scale-aligned relative-depth mechanism probe。

历史机器产物和旧状态名保留用于 hash/provenance 审计，映射集中记录于 Step 031。

## P1 与当前结论

P1 control grid、标准指标、完整近邻、跨 backbone/dataset 和论文复现包没有在 P0
门禁未闭合时提前扩张。现阶段新增的科学事实是：现象余量在更严格的 selector
envelope 和完整 518--2030 direct-accuracy envelope 下仍存在，但当前 router 的算法
新颖性不成立。最强反方意见仍是：联合集合机制可能最终退化为 generic conformal
calibration；两次有效 exclusive session 尚未证明同等时延 Pareto 和范围闭合。因此
当前不是 Paper Candidate。
