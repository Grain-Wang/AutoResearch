# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

本研究仍是 **Research Opportunity**，没有实验结果，不能称为 Paper Candidate。唯一主线是 CoVoL-Depth；Q-GeoRoute 已停放为 Gate-0 失败后的备用方向。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [最新审稿意见](responce_from_reviewer/review_round5.md)
6. [最新回应](responce_from_reviewer/response_round5.md)

## 执行顺序

主依赖链固定为：

`003 数据适配/coverage/power → 005 sequence/drive-cluster OOF 公平专家 → 004-fallback 正式缺陷复现 → 006 direct/permuted Claim-F Gate → 007 faithful+matched killer baselines → 008 最终 canary`。

`004-sensitivity` 只测同一 `D1` 的 clean→corrupted 敏感性，可在 003 后用 TR2M checkpoint 提前运行，但不能替代正式 H-fallback-defect。

当前已有 training-only split/source/coverage/conditional-detectability audits、OOF stacking plan、feature firewall、核心指标、dev-frozen constrained comparison 和 denominator-aware `cluster_id` bootstrap 代码，但尚无真实门禁结果、checkpoint 或科学结果。任何前置 Gate 失败都先记录原因和 STOP/ITERATE 决策，不得跳过并直接训练完整方法。`paper1/results/` 为空时，所有研究主张均为预注册假设。

## 当前可运行检查

校外阶段允许本机执行 Ruff、Black、Pytest 和微型合成数据测试，但不下载真实数据、不训练模型、不生成科学结果。真实数据门禁在 Linux 恢复后于 `whr/AutoResearch` 执行；先由 NYUv2/KITTI/VKITTI2 source adapters 生成 training-only JSONL，再复制并填写 [training pilot example](configs/covol/training_pilot_manifest.example.json)：

```bash
cd whr/AutoResearch
conda run -n vlm python paper1/experiments/covol/build_training_pilot_manifest.py \
  --config paper1/configs/covol/training_pilot_manifest.json \
  --output paper1/data/covol/image_manifest.jsonl \
  --audit paper1/data/covol/split_audit.json

conda run -n vlm python -m ruff check .
conda run -n vlm python -m black --check .
conda run -n vlm python -m pytest paper1/tests -q \
  --basetemp paper1/data/tmp/pytest-paper1
```

Step 003 配置中出现 official-test manifest 会立即失败。`build_image_manifest.py` 仅用于 Step 008 完全冻结后的 test integrity audit，且必须显式传入 `--allow-official-test-read`；不得用它替代当前 training-only builder。

生成真实 router manifest 后，可先冻结 OOF stacking 计划（仍不代表模型已训练）：

```powershell
conda run -n auto_research python paper1/experiments/covol/cache_oof_experts.py `
  --router-manifest paper1/data/covol/image_manifest.jsonl `
  --official-training-manifest paper1/data/source/official_train_all.jsonl `
  --output paper1/artifacts/covol/expert_stacking_plan.json
```
