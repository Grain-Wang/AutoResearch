# 对第 6 轮审稿意见的回应

## 总体判断

我们接受“当前未达到强 CCF-C，也尚未成为 Paper Candidate”的结论。第 6 轮之后新增的唯一真实科学证据仍是 Step003 的 official-training feasibility gate：NYUv2 local-oracle coverage 通过，而当前冻结的 KITTI source 不具备可信的 local instance-mask/depth oracle，因此正式两数据集分支返回 `STOP_TWO_DATASET_CLAIM`。Claim-F 仍为 `UNVERIFIED`，Claim-M 在当前 NYUv2+KITTI 分支上为 `STOPPED`。

本轮没有把协议文字、合成单元测试或 CUDA canary 写成算法结果。我们完成的是三件边界明确的工作：保留已通过的 Step003 数据修正；冻结 Round6 指出的统计与实验合同；确认 A800 shared-GPU 执行链可用并暂停 exclusive 排队。后两项只降低未来实验的执行风险，不增加 Claim-F 或 Claim-M 的证据。

## 已完成的数据分支修正与真实结果

1. 删除 inferential `GO_LOCAL_CLAIMS_NYUV2_VKITTI2` 分支。只有 NYUv2+KITTI 可以通过当前 two-dataset gate；VKITTI2 永久固定为 `synthetic_structured_auxiliary_only`，五个基础场景不能通过天气、视角或相机 clone 扩充独立样本数。
2. VKITTI2 adapter 不再接受外部 frame index。它只扫描官方解压后的 RGB/depth/class/instance/textgt 目录，检查完整 scene/variation/camera/frame 对齐，并将 pilot selection 绑定到 canonical full-source count 和 SHA256。
3. Step003 使用可导入的 `python -m` 入口；clean-deployment pytest 临时目录位于调度器创建的 `.local-deps` 下。

上述数据修正对应 commit `435240e18fd4fbcc4685b2a5ef43e9824f5d4636`。远程 CPU 队列通过 Ruff、Black 和 97 个 paper1 tests。

真实 pilot 只读取 official-training material，未读取 official benchmark test。每个数据集固定 500 图，并按不可拆分 scene/drive-connected cluster 划分为 300/100/100：

| Dataset | Images | Eligible images | Eligible depth-separated pairs | Independent eligible clusters | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| NYUv2 | 500 | 500 | 105779 | 156 | PASS |
| KITTI | 500 | 0 | 0 | 0 | FAIL |

因此冻结决策为 `STOP_TWO_DATASET_CLAIM`，KITTI 只保留 `image_level_sensitivity_only`。调度器按预注册合同阻断 conditional detectability，没有生成 power artifact、intervention corpus、Step005 checkpoint 或算法结果。独立 replay 的 source/pilot manifest、split audit 和 coverage CSV/JSON 均逐字节同哈希。

可移植证据为 [`annotation_coverage.json`](../results/covol/annotation_coverage.json)、[`annotation_coverage.csv`](../results/covol/annotation_coverage.csv) 和 [`step003_feasibility_gate.json`](../results/covol/step003_feasibility_gate.json)。

## Round6 逐项回应

下表区分 `DONE-CODE`、`FROZEN-DESIGN`、`OPEN` 与 `BLOCKED-BY-STEP003`。`FROZEN-DESIGN` 只表示我们接受意见并消除了协议歧义，不表示相应实现或实验已经完成。

| 审稿意见 | 本轮回应 | 当前状态 |
| --- | --- | --- |
| full-image metric 与 eligible-region 权重不一致 | region 权重分母改为 official crop 的全部 valid-depth pixels；非 eligible residual mass 固定走 D0、regret 为 0；权重和允许小于 1 | `FROZEN-DESIGN`；现有 scalar helper 仍要求和为 1，待代码与 50% coverage toy test 落地 |
| cluster-balanced training 与 image-weighted evaluation estimand 不一致 | 主 estimand 冻结为 cluster-balanced：每图权重为 `1/(S n_s)`；训练均匀抽 cluster、再均匀抽 cluster 内图；dev/test 使用相同权重；image-weighted 只作 sensitivity | `FROZEN-DESIGN` |
| dev retention 只看点估计 | 21 个 threshold 均运行 10,000 次 cluster bootstrap；只有 one-sided 95% retention LCB `>=0.80` 才可进入 dev CVaR 排序 | `FROZEN-DESIGN`；当前 evaluator 尚未实现 |
| internal-test 未审计 utility | 冻结 threshold 后必须报告 test retention 点估计和 95% CI；点估计 `<0.80` 返回 `STOP_TEST_RETENTION_VIOLATION`；风险列统一命名为 `CVaR@Dev-Ret>=0.80` | `FROZEN-DESIGN`；当前 evaluator 尚未实现 |
| seed 未进入结果层 | seeds `17/29/43` 各自产生 expert cache、router、dev threshold 和 test outcome；主比较使用 paired seed×cluster hierarchical bootstrap，同时逐 seed 报告并要求方向一致 | `FROZEN-DESIGN`；现有 outcome/artifact schema 尚无 seed |
| Main-PR 与 Risk-L2D-C 的唯一差异不可执行审计 | 两者共享网络、输入、batch indices、CVaR、clean constraint、dual/optimizer、trial 与 threshold budget；唯一差异冻结为 direct advantage target 与 inner-OOF partial-residual target | `FROZEN-DESIGN`；PyTorch contract test 未实现 |
| VKITTI2 不能挽救正式推断 | 接受；其角色固定为 synthetic structured auxiliary set，不能替代第二个真实 inferential dataset | `DONE-CODE` |
| VKITTI2 可由外部 frame list 事后挑帧 | 已删除该入口，改为扫描完整官方目录并绑定 canonical full-source hash | `DONE-CODE` |
| OOF cache 实体、seed 与文件哈希不完整 | 主键冻结为 `(dataset,image_id,seed,candidate_id,control_type)`；逐行必须绑定 checkpoint/config/training-manifest/code-commit/cache path 与重算 SHA256；D0/D1/twins/shuffled 均需覆盖三 seeds | `FROZEN-DESIGN`；现有 plan/cache validator 仍不满足该合同 |
| expert training manifest 缺失 | 每个 OOF/final expert 必须冻结 cluster、image、predicate-clean caption、captioner revision/hash 和 valid-depth target；D1 caption 缺失硬失败，成对 D0/D1 训练图集合必须相同 | `FROZEN-DESIGN`；builder 尚未实现 |
| core intervention builder 缺失 | 该意见成立；当前只有 source/provenance/coverage infrastructure，没有可用于研究主张的 intervention JSONL | `BLOCKED-BY-STEP003` |
| feature allowlist 指向不存在的 callable | 该意见成立；在三个 extractor 真正定义、可 import 且只接受 sanitizer mapping 前，feature firewall 只能标为部分实现 | `OPEN` |
| D0/D1、router 与可微目标未实现 | 该意见成立；scalar formula tests 不等于可训练模型，也没有梯度、checkpoint 或算法结果 | `BLOCKED-BY-STEP003` |
| operating-point lineage 不完整 | artifact 必须绑定 seed、raw outcome table、coverage grid、expert cache、metric-spec、minimum-clean-gain、method config 和 code commit 的实际哈希；internal-test 不接受裸 threshold index | `FROZEN-DESIGN`；实现待补 |
| cluster-balanced CVaR 应为主指标 | 接受并冻结为主 estimand；image-weighted CVaR 降为 sensitivity，cluster bootstrap 仍以 sequence/drive cluster 为独立抽样单位 | `FROZEN-DESIGN` |

## Shared GPU 结果及 exclusive 队列状态

A800 shared canary 已在 GPU 2 与一个既有 compute process 共存时完成：启动前空闲显存约 47,577 MiB，PyTorch `2.4.1+cu121` / CUDA 12.1，张量校验和 1024.0，用时约 2.85 s，peak allocated/reserved 分别约 0.0044/2.0 MiB。该结果只证明“按剩余显存启动、记录模式与共存进程数”的调度和 CUDA 环境可运行；它不是 D0/D1、router、数据门禁或性能结果。

按当前指令，exclusive queue 已 graceful drain 并停止后台 scheduler；exclusive job 保持 `PENDING`、attempt 为 0，shared job 保持 `PASSED`、attempt 为 1，SQLite state、配置与结果均保留。后续收到明确指令后可从同一状态恢复，不会重复 shared job。

## 当前决策与下一步

Round6 提出的统计问题已经转化为无歧义的实现验收合同，但尚未被代码或真实实验关闭。shared GPU 可用并不解除 Step003 的科学依赖，因此当前不启动 Step005、intervention builder 或 router 训练。

恢复 Claim-M 有且只有两个合规入口：其一，明确引入另一个满足相同 provenance/local-oracle coverage 且至少有 20 个独立 clusters 的真实 outdoor dataset，并重新执行 Step003；其二，正式缩窄为 NYUv2 单数据集、controlled local-caption stress-testing 的研究范围，然后重新做 novelty/power/Candidate Gate 判断。在其中一个方向被明确选择前，增加 GPU 实验不会改变论文判断。
