# 003 Intervention Dataset Preregistration

## Status

`SPECIFIED, NOT EXECUTED`。本文件固定数据构造与泄漏规则；当前尚无生成脚本、JSONL 或通过率结果，不能记为完成。

## Canary sampling

- NYUv2 official test/validation pool 与 KITTI Eigen test pool 各取 500 张，只用于问题与机制 canary，不作为最终 benchmark test claim。
- 按 `SHA256(dataset + / + image_id + /20260821)` 升序选择，scene 去重优先；固定后写入 `paper1/data/covol/image_manifest.jsonl`。
- 统计/训练按 scene group 做 60/20/20 划分：总计 600/200/200 张图像进入 train/dev/test；同一 scene、RGB frame 或近邻视频帧不得跨 split。
- 最终论文实验必须另保留从未参与 canary/router 选择的正式 test set。

## Structured intervention corpus

每张图像保存一个 verified-clean base caption，并生成 4 个 family、每类 3 个变体，共 `1,000×4×3=12,000` 条：

1. `semantic_preserving`：同义改写、句序变化、删除无关形容词，作为等价性正控制；
2. `target_deletion`：删除一个有 mask 的实体、删除一个远处实体、完整 null caption；
3. `local_entity_conflict`：将目标实体替换为图中不存在实体、冲突材质、冲突几何属性；
4. `depth_relation_conflict`：对有可靠 GT depth 的实体对反转前后/远近关系，或写入与中位深度差冲突的关系。

`global_caption_swap` 只作为容易识别的诊断集，不进入 12,000 条核心数据，也不能代表自然 caption 风险。

## Natural-error slice

自然错误必须来自 captioner 的**未经编辑原始输出**。机器检查发现下列任一矛盾后纳入：

- 提及数据集标签/可靠检测结果中不存在的实体；
- 给出与两个实体 mask 的 GT median depth 显著冲突的远近关系；
- 遗漏不算错误，只单独登记 completeness。

natural-error 与 structured intervention 分开报告。若自然错误数量不足以形成稳定图像级 CI，只能声明合成干预结果，不能外推真实 captioner 鲁棒性。

## Captioner isolation

- development captioner：TR2M bundled LLaVA-v1.6 captions；其上游 commit 锁为 `a45925862bcd76c84ac38c6fc98da1e187f1146e`。
- held-out captioner：`OpenGVLab/InternVL3-8B`，只进入 test natural-error slice 和 test base captions。
- 在第一次生成前把 Hugging Face snapshot SHA、tokenizer revision、prompt 文本 SHA256、最大 token 数、temperature、top-p 和框架版本写入 manifest；revision 缺失时脚本必须拒绝运行。
- caption decoding 默认 greedy；若使用采样，随机种子固定为 `17/29/43` 并逐条记录。

## Leakage isolation

- 原始 `interventions_all.jsonl` 对每张图都生成四个 family；用于模型拟合的 materialized split 中，`depth_relation_conflict` 在 train/dev 完全隔离到 quarantine，只在 test 出现，作为 held-out error family。
- train/dev/test 使用不重叠 template IDs；实体替换词表按 canonical class 分组后隔离。
- held-out captioner 不用于训练任何 gate、阈值或特征归一化。
- 图像、scene、caption hash、template、captioner、error family 任一 group key 泄漏都使构建失败。

## JSONL schema

每条 structured 记录至少包含：

`image_id, dataset, scene_id, split, clean_caption, intervention, error_type, variant_id, target_region, generator, generator_revision, template_id, seed, source_caption_hash, machine_check`。

`machine_check` 至少包含：

`predicate, predicate_version, passed, evidence_source, evidence_ids, evidence_hash, valid_depth_count, thresholds`。

target region 使用 dataset mask/detection mask 的稳定 ID，不嵌入大型数组；mask 文件单独保存并记录 SHA256。

## Machine-verification rules

- entity absence：canonicalized target class 不在 dataset label 或通过预注册阈值的 detector set 中；
- entity presence/deletion：被删除实体必须有有效 mask，面积 ≥32 像素；
- depth relation：两个 mask 各至少 32 个有效深度像素，median-depth 相对差至少 10%，再允许反转；
- semantic-preserving：实体集合与结构化关系三元组不变；
- 所有 structured rows 的 `machine_check.passed` 必须为 true；否则脚本退出非零，不静默丢弃。

VLM 只可生成表面语言，不可同时充当唯一 correctness judge。

## Expected artifacts

- `paper1/experiments/covol/build_interventions.py`
- `paper1/data/covol/image_manifest.jsonl`
- `paper1/data/covol/interventions_all.jsonl`：12,000 rows
- `paper1/data/covol/interventions_train.jsonl`：5,400 rows（600 images × 3 seen families × 3）
- `paper1/data/covol/interventions_dev.jsonl`：1,800 rows（200 images × 3 seen families × 3）
- `paper1/data/covol/interventions_test.jsonl`：2,400 rows
- `paper1/data/covol/interventions_quarantine.jsonl`：2,400 rows（train/dev images 上的 held-out family，不进入任何拟合/调参）
- `paper1/data/covol/natural_captions.jsonl`：数量由原始 captioner 错误率决定
- `paper1/data/covol/intervention_manifest.json`：schema/version/hash/count/leakage audit

## Acceptance checks

1. structured 总行数正好 12,000，主键 `(image_id,error_type,variant_id)` 唯一；
2. machine-check 通过率 100%；
3. all/train/dev/test/quarantine 数量为 12,000/5,400/1,800/2,400/2,400，且 train/dev/quarantine/test 是 all 的无重叠视图；
4. scene/template/captioner/held-out error-family 泄漏均为 0；
5. 同一脚本和 manifest 重跑产生相同排序与内容 SHA256；
6. 随机抽查只能由程序生成报告，不依赖用户长期人工标注。

未满足任一项时，步骤 004 不得开始。
