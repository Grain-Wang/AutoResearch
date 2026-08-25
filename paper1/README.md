# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

本研究仍是 **Research Opportunity**，已有 Step003 数据可行性负门禁，但没有算法实验结果，不能称为 Paper Candidate。唯一主线是 CoVoL-Depth；Q-GeoRoute 已停放为 Gate-0 失败后的备用方向。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [最新审稿意见](responce_from_reviewer/review_round6.md)
6. [Round-6 回应](responce_from_reviewer/responce_round6.md)

## 执行顺序

主依赖链固定为：

`003 数据适配/coverage/power → 005 sequence/drive-cluster OOF 公平专家 → 004-fallback 正式缺陷复现 → 006 direct/permuted Claim-F Gate → 007 faithful+matched killer baselines → 008 最终 canary`。

`004-sensitivity` 只测同一 `D1` 的 clean→corrupted 敏感性，可在 003 后用 TR2M checkpoint 提前运行，但不能替代正式 H-fallback-defect。

当前已有 training-only split/source/coverage/conditional-detectability audits，以及旧版 OOF stacking、feature firewall、image-weighted scalar metrics、dev point-retention selection 和 `cluster_id` bootstrap 代码。Round6 已冻结 full-crop weighting、cluster-balanced estimand、retention LCB、test-retention stop、seed×cluster inference 和实体级 artifact lineage，但这些修订尚未进入代码。真实 Step003 CPU gate 已返回 `STOP_TWO_DATASET_CLAIM`：NYUv2 local coverage 通过，当前冻结 KITTI source 的 local mask/depth oracle coverage 为零，power 因而未运行。任何前置 Gate 失败都先记录原因和 STOP/ITERATE 决策，不得跳过并直接训练完整方法。VKITTI2 固定为 synthetic structured auxiliary set，不能替代 KITTI 成为第二个 inferential dataset。该结果只判定当前数据分支不可行，不证明或否定路由算法本身。

A800 shared CUDA canary 已通过，说明“剩余显存满足时启动并记录结果”的基础设施可用；它没有运行 D0/D1、router 或真实数据实验。exclusive scheduler 已暂停并保留 PENDING state，只有在科学门禁恢复且用户再次通知后才重启。

## 当前可运行检查

本机允许执行 Ruff、Black、Pytest 和微型合成数据测试，但不保存真实研究数据。Step003 真实门禁已在远程 `whr` 完成；下列命令只用于在保留的私有数据上重建相同 training-only manifest 和 QA，不代表允许越过 STOP。VKITTI2 adapter 仅服务合成结构化辅助分析。active 配置由 [training pilot example](configs/covol/training_pilot_manifest.example.json) 派生且不提交：

```bash
cd <remote-repository-root>
conda run -n vlm python -m paper1.experiments.covol.build_training_pilot_manifest \
  --config paper1/configs/covol/training_pilot_manifest.json \
  --output paper1/data/covol/image_manifest.jsonl \
  --audit paper1/data/covol/split_audit.json

conda run -n vlm python -m ruff check .
conda run -n vlm python -m black --check .
conda run -n vlm python -m pytest paper1/tests -q \
  --basetemp .local-deps/pytest-paper1
```

Step 003 配置中出现 official-test manifest 会立即失败。`build_image_manifest.py` 仅用于 Step 008 完全冻结后的 test integrity audit，且必须显式传入 `--allow-official-test-read`；不得用它替代当前 training-only builder。

只有在数据分支经明确方向确认重新通过后，才可生成 router manifest 并冻结 OOF stacking 计划（仍不代表模型已训练）：

```powershell
conda run -n auto_research python paper1/experiments/covol/cache_oof_experts.py `
  --router-manifest paper1/data/covol/image_manifest.jsonl `
  --official-training-manifest paper1/data/source/official_train_all.jsonl `
  --output paper1/artifacts/covol/expert_stacking_plan.json
```
