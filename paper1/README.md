# paper1：自动描述错误下的选择性深度候选路由

## 当前状态

CoVoL-Depth 已在预注册的 004-A 对照门禁上返回 **`STOP_H_SENSITIVITY`**，不能称为 Paper Candidate，也不再是活跃 Research Opportunity。两个冲突族的区域 AbsRel 退化 95% CI 下界虽大于 0，但 semantic-preserving 对照也稳定退化，故现有证据只支持 TR2M 对文本表面形式敏感，不支持“局部语义冲突特异地造成退化”。按照冻结规则，004-B、公平 D0/D1、Claim-F、Claim-M 与 Main-PR 均不得继续。第二数据集/KITTI gap 审计可作为已完成的数据可行性记录保留，但不能恢复 CoVoL。Q-GeoRoute 仍保持停放，只有另行更新范围锁和完成新的最近邻/机会门禁后才能启动。

## 阅读顺序

1. [主线范围锁定](steps/001_primary_scope_lock.md)
2. [最近邻审计](steps/002_related_work_audit.md)
3. [主研究方案](ideas/01_counterfactual_value_of_language_depth.md)
4. [执行状态表](steps/README.md)
5. [Post-Step003 范围决策](steps/015_post_step003_scope_decision.md)
6. [最新审稿意见](responce_from_reviewer/review_round8.md)
7. [Round-8 回应](responce_from_reviewer/response_round8.md)
8. [Round-7 回应](responce_from_reviewer/response_round7.md)

## 执行顺序

原正式依赖链已被 004-A 停止。不得继续新的 Step003 恢复、005、004-B、006、007 或 008；这些协议只作为负结果可复现记录保留。任何新方向都必须先完成独立的 Research Opportunity Gate 和范围变更，不能复用 CoVoL 的未成立主张。

training-only diagnostic 从 Step003 的 hash-linked 1000-row manifest 中稳定选择 100 图/59 clusters，生成四个 local families 各 300 行，共 1200 行，machine-check 通过率 100%；null/global 各 100 行且与 local rows 分离。可移植审计见 [diagnostic intervention audit](results/covol/diagnostic_intervention_audit.json)。独立规则解析器对每族稳定抽取 25 行，共 100/100 满足预注册 predicate 合同；只读 raw text 的 unigram classifier 按每族留一套模板测试，macro-F1 为 0.488，低于预注册 0.60 上限，见 [intervention validity audit](results/covol/intervention_validity.json)。自动 surface-form 检查 1200/1200 通过，但这不是人类自然度评估。

004-A 已在 NYUv2 official-train diagnostic 上完成 100 图、1200 配对、59 clusters、10,000 次 cluster bootstrap。区域 AbsRel 退化为：semantic-preserving `0.001156 [0.000579, 0.001777]`、target deletion `0.000055 [-0.001198, 0.001109]`、local entity conflict `0.001620 [0.000195, 0.002903]`、depth relation conflict `0.000806 [0.000347, 0.001298]`。由于预注册要求 semantic-preserving CI 包含 0，该结果返回 `STOP_H_SENSITIVITY`。逐行结果与运行时、权重、输入和代码哈希见 [CSV](results/covol/sensitivity_diagnostic.csv) 和 [summary](results/covol/sensitivity_diagnostic_summary.json)。

真实 Step003 CPU gate 已返回 `STOP_TWO_DATASET_CLAIM`：NYUv2 local-oracle feasibility 通过，**当前冻结 KITTI source 未提供满足合同的 local depth/mask oracle**，power 因而未运行。该结果不证明 KITTI 数据族不可行，也不证明 intervention corpus 或语言鲁棒性成立。当前最多审计 Cityscapes、ScanNet v2、Matterport3D 三个真实候选，并单独核对 KITTI depth/mask/frame 对齐缺口；VKITTI2 固定为 synthetic structured auxiliary set。

所有正式 downstream 入口必须验证 [Step003 authorization](artifacts/covol/step003_authorization.json)，不能仅凭非空 `local_claim_datasets` 启动。当前正式步骤固定 exit code 3；只有 train-only diagnostic 与数据审计获得授权。

TR2M 官方代码 revision、released ScaleMap checkpoint、Depth Anything ViT-S、DINOv2 ViT-L 与 CLIP ViT-L/14 权重均已完成 SHA256 锁定，见 [TR2M release audit](results/covol/tr2m_release_audit.json) 和 004-A summary。可续跑 runner 已通过合成回归测试；正式运行环境为 Python 3.12.13、PyTorch 2.5.0+cu121、NVIDIA A800 80GB PCIe。该 GPU 结果是诊断性负门禁，不是 D0 fallback 或 router 证据。

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
