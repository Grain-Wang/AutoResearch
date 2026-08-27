# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

本研究仍是 **Research Opportunity**，不能称为 Paper Candidate。post-Step003 范围已冻结为 `RECOVER_TWO_REAL_DATASETS`，但原 `NYUv2 + current frozen KITTI source` 分支为 `STOPPED_CURRENT_DATA_BRANCH`；当前只允许第二数据集/KITTI gap 审计与 NYUv2 train-only diagnostic，不允许正式 D0/D1、Claim-F 或 Claim-M 实验。唯一研究问题仍是 CoVoL-Depth；Q-GeoRoute 保持停放。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [Post-Step003 范围决策](steps/015_post_step003_scope_decision.md)
6. [最新审稿意见](responce_from_reviewer/review_round8.md)
7. [Round-7 回应](responce_from_reviewer/response_round7.md)

## 执行顺序

正式主依赖链改为：

`015 范围决策 → 第二数据集/KITTI gap 审计 → 新 Step003 PASS authorization → 005 sequence/drive-cluster OOF 公平专家 → 004-B fallback 正式缺陷复现 → 006 constrained Claim-F Gate → 007 faithful+matched killer baselines → 008 最终 canary`。

`004-A sensitivity` 只测同一 `D1` 的 clean→corrupted 敏感性；现在允许在 NYUv2 official-train 固定 100 图 diagnostic corpus 上用 released checkpoint 提前运行，但不能替代正式 H-fallback-defect、Claim-F 或 Claim-M。

training-only diagnostic 已从 Step003 的 hash-linked 1000-row manifest 中稳定选择 100 图/59 clusters，生成四个 local families 各 300 行，共 1200 行，machine-check 通过率 100%；null/global 各 100 行且与 local rows 分离。可移植审计见 [diagnostic intervention audit](results/covol/diagnostic_intervention_audit.json)。独立规则解析器对每族稳定抽取 25 行，共 100/100 满足预注册 predicate 合同；只读 raw text 的 unigram classifier 按每族留一套模板测试，macro-F1 为 0.488，低于预注册 0.60 上限，见 [intervention validity audit](results/covol/intervention_validity.json)。自动 surface-form 检查 1200/1200 通过，但这不是人类自然度评估；004-A H-sensitivity 仍待运行。

真实 Step003 CPU gate 已返回 `STOP_TWO_DATASET_CLAIM`：NYUv2 local-oracle feasibility 通过，**当前冻结 KITTI source 未提供满足合同的 local depth/mask oracle**，power 因而未运行。该结果不证明 KITTI 数据族不可行，也不证明 intervention corpus 或语言鲁棒性成立。当前最多审计 Cityscapes、ScanNet v2、Matterport3D 三个真实候选，并单独核对 KITTI depth/mask/frame 对齐缺口；VKITTI2 固定为 synthetic structured auxiliary set。

所有正式 downstream 入口必须验证 [Step003 authorization](artifacts/covol/step003_authorization.json)，不能仅凭非空 `local_claim_datasets` 启动。当前正式步骤固定 exit code 3；只有 train-only diagnostic 与数据审计获得授权。

TR2M 官方代码 revision、released ScaleMap checkpoint 与 Depth Anything ViT-S checkpoint 已完成 SHA256 锁定，见 [TR2M release audit](results/covol/tr2m_release_audit.json)。可续跑的批量诊断 runner 已实现并通过合成回归测试；DINOv2/CLIP encoder 权重需在首次真实执行时下载并由 runner 写入哈希。当前仍没有 `sensitivity_diagnostic.csv` 或 GPU 科学结果。

A800 shared CUDA canary 已通过，说明“剩余显存满足时启动并记录结果”的基础设施可用；它没有运行 D0/D1、router 或真实数据实验。exclusive scheduler 已暂停并保留 PENDING state，只有在科学门禁恢复且用户再次通知后才重启。

## 当前可运行检查

本机允许执行 Ruff、Black、Pytest 和微型合成数据测试；真实逐行 manifest/intervention 保存在 Git 忽略目录，只提交不含机器路径的计数与哈希审计。Step003 真实门禁已在远程 `whr` 完成；下列命令只用于在保留的私有数据上重建相同 training-only manifest 和 QA，不代表允许越过 STOP。VKITTI2 adapter 仅服务合成结构化辅助分析。active 配置由 [training pilot example](configs/covol/training_pilot_manifest.example.json) 派生且不提交：

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
  --authorization paper1/artifacts/covol/step003_authorization.json `
  --router-manifest paper1/data/covol/image_manifest.jsonl `
  --official-training-manifest paper1/data/source/official_train_all.jsonl `
  --output paper1/artifacts/covol/expert_stacking_plan.json
```
