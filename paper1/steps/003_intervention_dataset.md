# 003 Intervention Dataset Preregistration

## Status

`SPECIFIED, NOT EXECUTED`。本文件固定数据构造与泄漏规则；当前尚无生成脚本、JSONL 或通过率结果，不能记为完成。

## Canary sampling

- NYUv2 与 KITTI **各 500 张都只从 official training pool 选择**；official benchmark test 在方法、阈值和超参数完全冻结前不得读取。
- 每个数据集按 scene hash 固定为 300 train / 100 dev / 100 internal-test；两数据集合计 600/200/200。
- `paper1/experiments/covol/build_image_manifest.py` 载入 official-train candidate manifest 与 official benchmark-test manifest，同时断言 image ID 和 scene ID 交集均为 0。
- scene 按 `SHA256(dataset/seed/scene_id)` 排序，scene 内图像再按稳定 hash 排序；边界 scene 只取当前 split 所需图像，其余图像丢弃且该 scene 不进入其他 split。
- 同一 scene、RGB frame 或近邻视频帧不得跨内部 split；输出 `image_manifest.jsonl` 与带输入 SHA256、计数和 overlap 的 `split_audit.json`。
- official benchmark test 只允许在 Step 008 完全冻结方法后运行一次；任何提前读取都使正式结果失效。

## Structured intervention corpus

每张图像保存一个 verified-clean base caption，并生成 4 个 family、每类 3 个变体，共 `1,000×4×3=12,000` 条：

1. `semantic_preserving`：同义改写、句序变化、删除无关形容词，作为等价性正控制；
2. `target_deletion`：删除一个有 mask 的实体、删除一个远处实体、完整 null caption；
3. `local_entity_conflict`：将目标实体替换为图中不存在实体、冲突材质、冲突几何属性；
4. `depth_relation_conflict`：对有可靠 GT depth 的实体对反转前后/远近关系，或写入与中位深度差冲突的关系。

`global_caption_swap` 只作为容易识别的诊断集，不进入 12,000 条核心数据，也不能代表自然 caption 风险。

## Natural-error slice

自然错误必须来自 captioner 的**未经编辑原始输出**。机器检查只允许下列两种 verified predicate：

- `entity_absence`：类别必须属于数据集明确声明为穷举标注的类别，同时两套独立 detector/segmenter 均未检出；任何条件不足都标为 `unverified_mention`；
- 给出与两个实体 mask 的 GT median depth 显著冲突的远近关系；
- 遗漏不算错误，只单独登记 completeness。

natural-error 与 structured intervention 分开报告。若自然错误数量不足以形成稳定图像级 CI，只能声明合成干预结果，不能外推真实 captioner 鲁棒性。

若 NYUv2/KITTI 对目标类别没有穷举标注声明，`entity_absence` predicate 自动禁用；“标签中没有”或“两模型未检出”本身不能计入 hallucination prevalence。

## Captioner isolation

- development captioner 1：只取 official-train IDs 的 TR2M bundled LLaVA-v1.6 captions；其上游 commit 锁为 `a45925862bcd76c84ac38c6fc98da1e187f1146e`。
- development captioner 2：`Qwen/Qwen2.5-VL-7B-Instruct`，只在 train/dev 生成。
- held-out captioner：`OpenGVLab/InternVL3-8B`，只进入 internal-test natural-error slice 和 internal-test base captions。
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

- entity absence：仅对 declared-exhaustive class 启用，并要求两个独立 detector/segmenter 均未检出；否则写 `unverified_mention`；
- entity presence/deletion：被删除实体必须有有效 mask，面积 ≥32 像素；
- depth relation：两个 mask 各至少 32 个有效深度像素，median-depth 相对差至少 10%，再允许反转；
- semantic-preserving：实体集合与结构化关系三元组不变；
- 所有 structured rows 的 `machine_check.passed` 必须为 true；否则脚本退出非零，不静默丢弃。

VLM 只可生成表面语言，不可同时充当唯一 correctness judge。

## Predicate validity test

每个 dataset×enabled predicate 必须先构造至少 200 个程序化正例和 200 个程序化负例。`depth_relation_conflict` 使用 confirmed masks/GT depth 构造；`entity_absence` 只使用 declared-exhaustive classes。precision ≥0.95 才能启用该 predicate，否则自动禁用并在 manifest 记录原因。结果写入 `paper1/results/covol/predicate_validity.csv`。

## Expected artifacts

- `paper1/experiments/covol/build_interventions.py`
- `paper1/experiments/covol/build_image_manifest.py`
- `paper1/data/covol/image_manifest.jsonl`
- `paper1/data/covol/split_audit.json`
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
5. train/dev/internal-test 与 official benchmark test 的 image/scene overlap 均为 0；
6. enabled predicate 的 validity precision ≥0.95，失败 predicate 已自动禁用；
7. 同一脚本和 manifest 重跑产生相同排序与内容 SHA256；
8. 随机抽查只能由程序生成报告，不依赖用户长期人工标注。

未满足任一项时，步骤 005 和正式 004-B 均不得开始。
