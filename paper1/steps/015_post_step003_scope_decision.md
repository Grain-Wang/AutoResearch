# 015 Post-Step003 Scope Decision

## Frozen decision

历史冻结选择为 `RECOVER_TWO_REAL_DATASETS`，但 004-A 已在更上游的问题真实性/特异性门禁返回 `STOP_H_SENSITIVITY`。因此 CoVoL 当前最终状态为 `STOPPED_BY_H_SENSITIVITY_CONTROL`，新的 Step003 authorization 也不能自动恢复 Claim-F、Claim-M 或 Main-PR。

“第二个真实数据集”不再无条件要求 outdoor；跨室内/室外泛化也不作为当前贡献前提。选择标准只看真实采集、RGB 与 metric depth/local mask 可对齐、至少 20 个独立 clusters、许可可复现和固定 source revision。为保留更强跨环境证据，候选顺序仍优先检查 outdoor Cityscapes，但不能为此放宽任何门槛。

## Preregistered candidate limit and order

最多审计以下三个真实数据集，顺序在读取任何 Main-PR、router 或 D0/D1 方法结果前冻结：

1. [`Cityscapes`](https://www.cityscapes-dataset.com/dataset-overview/)：真实 outdoor stereo；只接受 official-train fine annotations、官方 disparity 和 camera calibration 可共同解析的帧；cluster 为 city，不把 30-frame snippet 当独立 cluster。
2. [`ScanNet v2`](https://www.scan-net.org/ScanNet/)：真实 indoor RGB-D sequences；只接受 official train scans 中 RGB、metric depth 与 filtered 2D instance/semantic projections 对齐的帧；cluster 为 physical space，不把同一空间的 rescans 当独立 cluster。
3. [`Matterport3D`](https://github.com/matterport/3d-dataset-tools)：真实 indoor building-scale RGB-D；只接受 official academic release 中 RGB/depth 与 instance/semantic region labels 可对齐的 views；cluster 为 building。

每个候选先固定官方 source revision/terms 和 training-only pool，再用稳定 hash 选择 50 图 dry-run。选择规则是“按上述顺序取第一个同时满足 projected full pilot `>=150` eligible images、`>=300` eligible pairs、`>=20` independent clusters 且 license/provenance PASS 的候选”。禁止看到模型或方法结果后更换数据集。三个候选全部 FAIL 时，Claim-M 正式 `STOPPED_NO_SECOND_REAL_DATASET`，不得继续无限搜索；届时只能另行提交 `RESCOPE_NYUV2_ANALYSIS_ONLY` 范围变更。

## Work completed before the H-sensitivity stop

- 读取公开论文与官方数据说明，冻结三个候选的 source/provenance/许可合同；
- 对三个候选运行 metadata/source dry-run 和 training-only coverage audit；
- 对当前 KITTI 500 个 image IDs 审计拟议 depth/mask source 的 drive/camera/frame 交集，区分“当前 source 未提供”与“KITTI 数据族不可行”；
- 在 NYUv2 official-train 的 `train` split 固定 100 图，构建不进入论文主结果的 diagnostic-only intervention corpus；
- 用 released checkpoint 运行 004-A H-sensitivity diagnostic；该项已完成并返回 `STOP_H_SENSITIVITY`；
- 实现并测试 full-crop risk、cluster-balanced metrics、retention LCB、test-retention stop、feature firewall 和 artifact validator；
- 运行 CPU QA 与合成/手算回归测试。

diagnostic corpus 与 H-sensitivity 只能回答“caption intervention 是否有效、问题是否真实”，不能回答 D0-relative fallback、Claim-F 或 Claim-M。实际结果显示 semantic-preserving 对照也有稳定退化，故不支持冲突特异的问题主张。其 image/caption/template hashes 不得被后续 dev/internal-test 使用。

## Forbidden CoVoL work after the H-sensitivity stop

- Step 004-B H-fallback-defect；
- Step 005 公平 D0/D1 正式训练或任何 OOF/final checkpoint；
- Step 006 Claim-F、Step 007 killer baselines、Step 008 Claim-M；
- official benchmark test、dev/internal-test 方法读取或阈值选择；
- 把 NYUv2 diagnostic、VKITTI2 或 shared CUDA canary 写成第二数据集或算法证据；
- 恢复 CoVoL exclusive GPU queue，或启动任何新的 CoVoL 科学 GPU 任务。

机器执行入口必须读取 [`step003_authorization.json`](../artifacts/covol/step003_authorization.json)。仅 `status=PASS`、`decision=GO_LOCAL_CLAIMS_*`、两个及以上 formal datasets 与 source coverage artifact 全部一致时，正式 downstream action 才能返回 0；当前固定返回 `BLOCKED_BY_STEP003` 和 exit code 3。非空 `local_claim_datasets` 数组本身不构成授权。

## Exit conditions

1. 某个候选通过 50-image dry-run 后，先完成 500-image training-only pilot 与 deterministic replay；只有完整 coverage PASS 才生成新的 Step003 authorization。
2. 三候选全部失败时，Claim-M 正式停止。是否转为 `RESCOPE_NYUV2_ANALYSIS_ONLY` 需要新的范围决策，并同步删除算法 Paper Candidate gate。
3. NYUv2 diagnostic 的固定 H-sensitivity 判据要求 machine-check/independent precision `>=0.95`、至少一个冲突族的 region AbsRel degradation cluster CI 下界大于 0，并且 semantic-preserving CI 包含 0。实际结果中 semantic-preserving CI 为 `[0.000579, 0.001777]`，不包含 0，因此此退出条件已经触发；即使第二数据集可用也不进入 Main-PR。
4. 任何范围恢复都不自动支持算法 novelty；仍须通过公平 D0/D1、Claim-F、direct killers 与逐 seed 稳定性门禁。
