# 对第 8 轮审稿意见的回应

## 总体结论

Round 8 指出的首要问题是远端 `paper1` 缺少 Round 7 回应和对应增量。该问题已修复：Round 7/P0 实现提交为 `f88ff65`，本地 Depth Anything 锁定修复为 `04b28d2`，运行时 provenance 增补为 `65a4b3f`，均已推送到既有 `paper1` 分支；没有新建分支，也没有改变远端 `paper2`。历史文件名 `responce_round6.md`、`responce_round7.md` 已分别更正为 `response_round6.md`、`response_round7.md`。

更重要的是，Round 8 要求的 004-A 已产生决定性负结果。预注册判据要求至少一个 conflict family 的 region AbsRel degradation 95% CI 下界大于 0，同时 semantic-preserving CI 包含 0。前半项满足，但 semantic-preserving 对照为 `0.001156 [0.000579, 0.001777]`，明确不含 0，因此返回 `STOP_H_SENSITIVITY`。我们据此停止 CoVoL，而不是继续训练 D0/D1、router 或选择性报告两个正向冲突族。

## P0 工单完成情况

| Round-8 P0 | 状态 | 可审计产物与结论 |
| --- | --- | --- |
| 同步 Round 7 回应和远端提交 | DONE | [`response_round7.md`](response_round7.md)；提交 `f88ff65`、`04b28d2`、`65a4b3f` 已在 `paper1` |
| 冻结 Step003 后范围 | DONE-DESIGN, SUPERSEDED-BY-004-A-STOP | [`015_post_step003_scope_decision.md`](../steps/015_post_step003_scope_decision.md) 选择 `RECOVER_TWO_REAL_DATASETS`；004-A 后该恢复路径不再授权 CoVoL |
| 审计最多三个第二真实数据集 | BLOCKED-SOURCE-ACCESS | Cityscapes、ScanNet v2、Matterport3D 恰好三个候选均为 `PENDING_SOURCE_ACCESS`，不是 coverage FAIL；见 [`JSON`](../results/covol/second_dataset_candidate_audit.json) 与 [`CSV`](../results/covol/second_dataset_candidate_audit.csv) |
| 生成 100 图 diagnostic corpus | DONE | 100 图、59 clusters、四族各 300 行，共 1200 local rows；null/global 各 100 行；machine-check 1200/1200 |
| 独立 predicate 与模板伪影审计 | DONE-AUTOMATED | 独立规则 parser 100/100；held-out-template unigram macro-F1 0.488 ≤0.60；surface-form 1200/1200。人类 naturalness 明确为 `NOT_ASSESSED` |
| 运行锁定 TR2M 的 004-A | DONE-STOP | 100 图、1200 配对、59 clusters、10,000 paired cluster bootstrap；结果见 [`CSV`](../results/covol/sensitivity_diagnostic.csv) 和 [`summary`](../results/covol/sensitivity_diagnostic_summary.json) |
| full-crop risk 与 cluster-balanced estimand | DONE-CODE | 未覆盖质量固定走 D0；50% coverage × 0.2 local regret = 0.1 手算测试；weighted CVaR/Mean/Worst 回归测试通过 |
| 统一 authorization loader | DONE-CODE | 004-B/005/006/007/008 在当前 artifact 上固定 `BLOCKED_BY_STEP003`、exit 3；非空 dataset 数组不能绕过 hash/status/decision 检查 |

Round 8 的 NYUv2-only 分支没有被选择，因此对应 P0 为 `NOT-SELECTED`，而不是漏做。候选数据因账户/协议无法读取时，没有代替责任人接受条款，也没有把 source access 缺失伪造为科学 coverage 失败。

## 004-A 结果与停止决定

主指标是每图先聚合、再按冻结 scene cluster 配对 bootstrap 的 `REGION_ABS_REL_DEGRADATION`：

| family | point | 95% CI | 解释 |
| --- | ---: | ---: | --- |
| semantic-preserving | 0.001156 | [0.000579, 0.001777] | 对照失败，CI 不含 0 |
| target deletion | 0.000055 | [-0.001198, 0.001109] | 无稳定退化 |
| local entity conflict | 0.001620 | [0.000195, 0.002903] | 有敏感性信号，但不具冲突特异性 |
| depth relation conflict | 0.000806 | [0.000347, 0.001298] | 有敏感性信号，但不具冲突特异性 |

运行使用 Python 3.12.13、PyTorch 2.5.0+cu121、CUDA 12.1 和单张 NVIDIA A800 80GB PCIe。TR2M、Depth Anything ViT-S、DINOv2 ViT-L、CLIP ViT-L/14、NYUv2 输入、runner、授权和协议文件均在 summary 中记录 SHA256。逐行 CSV SHA256 为 `a2d45fe96581d3234aa41d62c2a63f3e793f705e56c6054e9c8c3818111db721`；summary SHA256 为 `e4a304b1e6c2d8db6b1b95a666fe7f9fb88e73c7200addc400aecb10b2ce4659`。

该结果只支持“released TR2M 对文本改写敏感”，不支持“局部语义冲突特异地造成退化”。效应量很小，且 target deletion 不稳定。按照事前规则，004-B、公平 D0/D1、Claim-F、Claim-M、Risk-L2D-C、Main-PR 和后续 CoVoL GPU queue 全部停止；未生成这些正式模型 artifact 是停止规则的预期结果，不是实现遗漏。

## 可复现性与证据边界

- `run_sensitivity_diagnostic.py` 支持每图原子 checkpoint/resume，并严格验证 identity、schema 和有限数值；本地构造 Depth Anything backbone 时禁止隐藏网络依赖。
- release audit 与 summary 锁定所有模型权重和运行时；diagnostic corpus 在远端由同一确定性 builder 重建，三个 corpus 哈希与本地冻结值一致。
- full-crop residual mass、cluster-balanced weighted CVaR、dev retention one-sided LCB、internal-test retention stop、固定三 seed 重复、实体级 OOF/hash validator、operating-point lineage 和 feature firewall 均已实现并有合成/手算测试，但不构成科学模型结果。
- 人类自然度没有评估；自动 predicate 和 surface-form 审计不能替代开放式人评。
- 当前没有 D0-relative fallback、Claim-F、Claim-M、killer baseline、消融或延迟结果，也不得声称存在。

## 当前研究判断

- CoVoL：`STOPPED_BY_H_SENSITIVITY_CONTROL`。
- Claim-F：`STOPPED_BY_H_SENSITIVITY_CONTROL`。
- Claim-M：`STOPPED_BY_H_SENSITIVITY_CONTROL`。
- Paper Candidate：否。
- 最强反方意见：结果更符合一般表面改写敏感性，而非语义错误特异机制；因此 fallback-aware router 的核心动机没有通过最小可证伪 probe。

下一步不应继续给 CoVoL 调参、补数据或训练 router，而应重新完成近期文献缺口审计，形成至多五个满足 Research Opportunity Gate 的非等价候选，再更新唯一主线范围。
