# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

本研究仍是 **Research Opportunity**，没有实验结果，不能称为 Paper Candidate。唯一主线是 CoVoL-Depth；Q-GeoRoute 已停放为 Gate-0 失败后的备用方向。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [最新审稿意见](responce_from_reviewer/review_20260821_032352.md)
6. [最新回应](responce_from_reviewer/response_20260821_032352.md)

## 执行顺序

主依赖链固定为：

`003 数据适配/coverage/power → 005 scene-group OOF 公平专家 → 004-fallback 正式缺陷复现 → 006 direct/permuted Claim-F Gate → 007 direct+robust killer baselines → 008 最终 canary`。

`004-sensitivity` 只测同一 `D1` 的 clean→corrupted 敏感性，可在 003 后用 TR2M checkpoint 提前运行，但不能替代正式 H-fallback-defect。

当前已有 split/content-leakage audit、OOF stacking plan audit、feature denylist、核心指标和 scene-cluster bootstrap 代码，但尚无真实数据、checkpoint 或科学结果。任何前置 Gate 失败都先记录原因和 STOP/ITERATE 决策，不得跳过并直接训练完整方法。`paper1/results/` 为空时，所有研究主张均为预注册假设。

## 当前可运行检查

源 manifest 的每行至少包含 `dataset`、`image_id`、`scene_id`、`sequence_id`、`frame_index`、原始 RGB bytes 的 `rgb_sha256` 和 `official_split`。复制并填写 [image_manifest.example.json](configs/covol/image_manifest.example.json) 后，在仓库根目录运行：

```powershell
conda run -n auto_research python paper1/experiments/covol/build_image_manifest.py `
  --config paper1/configs/covol/image_manifest.json `
  --output paper1/data/covol/image_manifest.jsonl `
  --audit paper1/data/covol/split_audit.json

conda run -n auto_research python -m pytest paper1/tests -q `
  --basetemp .local-deps/pytest-paper1
```

若 official test 与开发候选在 image、scene、sequence 或 RGB 内容哈希层面有交集，构建脚本会非零退出，不生成可用的通过审计结果。

生成真实 router manifest 后，可先冻结 OOF stacking 计划（仍不代表模型已训练）：

```powershell
conda run -n auto_research python paper1/experiments/covol/cache_oof_experts.py `
  --router-manifest paper1/data/covol/image_manifest.jsonl `
  --official-training-manifest paper1/data/source/official_train_all.jsonl `
  --output paper1/artifacts/covol/expert_stacking_plan.json
```
