# 006 Semantic Incrementality Gate

## Status

`STOPPED-BY-004-A`。004-A 的 semantic-preserving 控制条件失败已停止 CoVoL，Claim-F 不再执行。三类 extractor callables、seed-aware entity-cache validator 与统计合同仅作为预注册实现记录保留；真实 checkpoint/cache、controls 和 outcome 有意不存在。

## Frozen inputs

- router-train 只读取 Step 005 的 sequence/drive-cluster OOF expert cache；dev/internal-test 只读取 final-expert cache；
- 每行 cache 必须先通过 `validate_expert_cache_manifest`，训练内 expert prediction 一律拒绝；
- official-train 的 train/dev/internal-test scene splits 已由 Step 003 冻结；
- 同一 image 的 predicate-clean、natural、structured、null-diagnostic captions 与所有 regions 必须在同一 fold；
- official benchmark test 不进入任何 fold、scaler、trial、threshold 或结果选择。

## Nested sequence/drive-cluster cross-fitting

仅在 router `train` split 上执行；NYUv2 `sequence_id` 与 KITTI `drive_id` 是不可拆分 cluster，`scene_id` 只作统计字段。

### Outer 5-fold

outer fold-k 只产生最终 OOF score。其余 outer-train scenes 按固定 hash 划分 outer-fit/outer-validation；所有 scaler、缺失处理、feature selection 和 trial state 只能读取 outer-fit。20 个 trial 在 outer-validation 上排名，不读取 outer-test。

### Inner 4-fold nuisance OOF

对每个 outer-train：

1. 把 outer-fit scenes 固定为 inner 4 folds；
2. 第 j 个 nuisance `m_B^{(-j)}` 只在其余 3 folds 拟合，并只预测 inner-j；
3. 拼接后每个 outer-fit 样本恰有一个 inner-OOF nuisance prediction；
4. 用 `r_p=a_p-m_B^{OOF}(z_B)` 训练 semantic residual branch；
5. 将 nuisance 在全部 outer-fit 上重拟合，仅用于 outer-validation/outer-test score；residual target 永不来自看过本样本的 nuisance model；
6. 选定 trial 后，在 outer-train 上按同一 inner-OOF 流程重建 residual branch，再对 outer-test 输出唯一 score。

每个样本记录 outer fold、inner fold、scaler SHA、trial SHA、nuisance OOF SHA 和最终 score SHA。同 scene 跨 fold、预处理读取 test、trial 读取 test 或 target 来自 in-sample nuisance 均为硬失败。

### Trial aggregation and final refit

- 每个 outer fold 对 20 个 trial 按 outer-validation 主目标排序；
- 选择“跨 5 个 outer folds 平均 rank 最小”的 trial；并列时取预注册 trial ID 最小者；
- final direct models 用该 trial 在全部 router-train scenes 重拟合；
- final Main 先在全部 router-train 上运行 5-fold nuisance OOF 形成 residual targets，再拟合 semantic branch，最后将 nuisance 在全部 router-train 上重拟合；
- dev 只校准 coverage threshold；internal-test 不参与模型、trial 或 preprocessing refit。

## Tie band and targets

连续 advantage `a_p` 是主诊断 target。tie band：

$$
\delta_{tie}=\max(q_{0.95}^{repeat},q_{0.95}^{mask}),
$$

其中 `q^{repeat}` 来自相同 checkpoint/cache 配置独立运行两次的 `|a_p^{(1)}-a_p^{(2)}|`；`q^{mask}` 来自有效 mask 向内腐蚀 1 pixel 后的 `|a_p-a_p^{eroded}|`。二者只在 train split 估计一次。

- `a_p>\delta_{tie}`：D1-positive；
- `a_p<-\delta_{tie}`：D0-positive；
- `|a_p|\le\delta_{tie}`：tie。

tie 不进入 AUROC/AUPRC 的二元标签，但保留在连续回归、Spearman 和所有策略效用计算中。

## Claim-F controls and Main

固定五个模型：

| 模型 | 输入 | 训练算法/目标 | 进入哪个 claim |
| --- | --- | --- | --- |
| `B-direct` | 固定宽度 `[z_B, 0, mask=0]` | standard direct advantage objective | Claim-F |
| `C-direct` | 同宽度 `[z_B, semantic, mask=1]` | 与 B-direct 完全相同的第一层、模型、参数量、目标和 trials | Claim-F |
| `C-permuted-global` | 跨 cluster 且 caption length/scene category 匹配的 semantic block | 与 C-direct 完全相同 | Claim-F negative control |
| `C-permuted-local` | 只置换 target entity/local relation，保留全局场景与文风 | 与 C-direct 完全相同 | Claim-F negative control |
| `Main-PR` | 原始 `z_C` | inner-OOF partial residual + clean/CVaR objective | Claim-M only |

置换必须报告 caption length、全局 image-text similarity 与 target-region grounding 的 paired 差异；前两者标准化差异绝对值必须 `<0.1`，target grounding 必须显著下降。无法构造有效错配的 cluster 不静默保留，必须在 power gate 中处理。Main-PR 不参与 Claim-F 的语义信息判定。

所有模型的最终列必须通过 `features.py`：除 intervention metadata 外，`ground_truth/depth_gt/target/label/advantage/a_p/d0_loss/d1_loss/oracle/test_metric` 及其 one-hot/embedding 派生列全部禁止。每列记录 source fields、source function、source kind 和仓库相对 source path；SHA256 必须由本地文件重算。allowlist 中的 `candidate_features`、`caption_region_features` 与 `image_features` 已定义为可 import 的真实 callable，只接受 allowlisted/sanitized mapping，额外 GT 字段会硬失败；真实 runtime schema 尚待正式 cache 生成。

## Threshold calibration and policy utility

- 使用平均-rank 冻结的 trial 按上节 final-refit 规则拟合最终模型；
- seeds `17/29/43` 各自独立拟合模型，并只在独立 dev split 上把 score quantiles 冻结成 21 个 coverage thresholds（0%,5%,…,100%）；
- 每个 seed 只有 one-sided 95% cluster-bootstrap retention LCB `>=0.80` 的 threshold 才可行；
- internal-test 只应用冻结 thresholds，一次性计算，不重新校准。

除 AUROC/AUPRC/Spearman 外，B-direct/C-direct/两类 C-permuted 使用完全相同的 per-seed threshold 协议与 [metrics spec](metrics_spec.md)。每 seed 只在 dev retention LCB 可行集合中冻结最低 CVaR operating point；internal-test 主政策指标为该冻结点的 cluster-balanced `CVaR/WorstOf3@Dev-LCB-Ret>=0.80`，hypervolume 与 image-weighted 曲线仅作 sensitivity。每 seed 分别给 cluster CI，三 seed 只报告 mean±SD 并要求点方向一致。

## H-semantic decision

Claim-F 仅在以下条件同时满足时通过：

1. internal-test 上每 seed 的 `C-direct−B-direct` AUROC ≥0.03，paired scene/drive-cluster bootstrap 95% CI 下界 >0，且三个固定 seed 方向一致；
2. 每 seed 的 `C-direct−C-permuted-global/local` AUROC 差值 cluster CI 下界均 >0；
3. C-direct 相对 B-direct 和两类 C-permuted 在各自 dev-frozen constrained operating point 上的 internal-test `CVaR/WorstOf3@Dev-LCB-Ret>=0.80` 风险差 cluster CI 上界均 <0，且无 test-retention STOP；HV 只作 secondary sensitivity，不是通过门；
4. held-out captioner 和 held-out error family 上方向一致；
5. 连续 advantage regression/Spearman 不与分类结论矛盾。

任一失败记录 `STOP_CLAIM_F` 或 `REFRAME_NON_SEMANTIC`，不得进入语义算法叙事。

## Pseudocode

```text
freeze split manifest, OOF/final expert cache, denylisted feature schema, tie band
for seed in [17, 29, 43]:
    for outer_fold in ClusterGroupKFold(K=5):
        split outer-train into outer-fit/outer-validation by cluster hash
        for trial in 20 preregistered trials:
            build inner ClusterGroupKFold(K=4) nuisance OOF predictions
            train residual branch only on inner-OOF residual targets
            rank trial on outer-validation only
        emit B-direct/C-direct/two C-permuted/Main-PR outer-OOF scores once
    choose trial by minimum mean outer-validation rank; tie by trial ID
    refit final direct models on all router-train
    refit final Main using full-train nuisance OOF targets, then full nuisance
    calibrate 21 thresholds on independent dev using retention LCB
    evaluate frozen controls and Main once on internal_test
for each fixed seed, paired-bootstrap whole sequence/drive clusters 10,000 times
apply AUROC and dev-frozen constrained-risk gates; report HV only as sensitivity
report three-seed mean +/- SD and require direction agreement
```

## Expected artifacts

- `paper1/experiments/covol/crossfit_semantic_advantage.py`
- `paper1/tests/test_crossfit_no_leakage.py`
- `paper1/experiments/covol/features.py`
- `paper1/tests/test_feature_schema_no_intervention_metadata.py`
- `paper1/results/covol/claim_f_controls.csv`
- `paper1/artifacts/covol/crossfit_manifest.json`
- fold manifest、feature schema、scaler/trial hashes、inner/outer OOF uniqueness audit。
