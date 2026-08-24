# 003 Intervention Dataset Preregistration

## Status

`FEASIBILITY-GATE-STOP, CORPUS NOT BUILT`。2026-08-24 在远程 `whr` 用 commit `435240e`、Python 3.12.13 和 CPU-only 队列完成 official-training pilot：NYUv2 coverage 通过，但冻结的 KITTI RGB source 没有可信 local instance mask/depth oracle，因而 two-dataset gate 返回 `STOP_TWO_DATASET_CLAIM`。调度器按合同阻断 conditional detectability，未生成 power artifact，未启动 GPU、Step 005 或 official test。完整 intervention/caption corpus builder 尚未实现，因此整个 Step 003 仍不标为完成。

可移植证据见 [`annotation_coverage.json`](../results/covol/annotation_coverage.json)、[`annotation_coverage.csv`](../results/covol/annotation_coverage.csv) 与 [`step003_feasibility_gate.json`](../results/covol/step003_feasibility_gate.json)。1000-row pilot 与独立 replay 的 manifest、split audit、coverage CSV/JSON 均逐字节同哈希。

## Canary sampling

- NYUv2 与 KITTI **各 500 张都只从 official training pool 选择**；official benchmark test 在方法、阈值和超参数完全冻结前不得读取。
- 300 train / 100 dev / 100 internal-test 仅是首轮 power/coverage pilot，不是无条件冻结的最终样本量；若主门禁 power <0.80，必须增加独立 internal-test scenes，不能增加 patch 冒充样本。
- Step 003 唯一 builder 是 `build_training_pilot_manifest.py`，配置中出现任何 official-test 路径即硬失败；`build_image_manifest.py` 已改为 Step-008-only integrity audit，必须显式 `--allow-official-test-read` 才能读取 test manifest。
- 源 manifest 每行强制包含 `rgb_sha256, sequence_id, frame_index`；pilot builder 另写入由完整训练池 scene–sequence 图计算的 `cluster_id`；重复 RGB 内容即使 image ID 不同也硬失败。
- scene 与 sequence 形成 bipartite connected components，component 按稳定 hash 排序且不可跨 split；`cluster_id` 是 component 节点集合的 SHA256，coverage/power 按该独立单位计数并拒绝同一 scene/sequence 映射到多个 cluster。
- 真实适配器必须从原始 RGB bytes 计算 SHA256，不得信任下载清单中的预填值；NYUv2 scene/sequence 与 KITTI drive/frame 映射需各自单测。
- official benchmark test 只允许在 Step 008 完全冻结方法后运行一次；任何提前读取都使正式结果失效。
- 正式 Step-003 rows 必须通过可信源合同：NYUv2 adapter/archive/splits/eval-crop SHA 全部固定；KITTI adapter、canonical training list、source revision 与 selection-audit SHA 全部固定；Virtual KITTI 2 固定为官方 `2.0.3`，校验 RGB/depth/class/instance/textgt 五个 archive 的官方 MD5、逐文件 SHA256、全图 metric protocol 与 non-commercial license。任意自报 64 位字符串不能通过 coverage/detectability gate。

## Structured intervention corpus

每张图像保存一个 predicate-clean base caption，含义仅是“未检测到当前启用 predicates 的错误”，不代表整条 caption 完全真实。每图生成 4 个 local family、每类 3 个变体；pilot `N=1,000` 时为 `12,000` 条，power gate 扩样后总数固定为 `12N`：

1. `semantic_preserving`：同义改写、句序变化、删除无关形容词，作为等价性正控制；
2. `target_deletion`：删除目标实体短语、删除另一有 mask 实体短语、只删除局部深度关系短语；三者都必须是局部删除；
3. `local_entity_conflict`：将目标实体替换为图中不存在实体、冲突材质、冲突几何属性；
4. `depth_relation_conflict`：对有可靠 GT depth 的实体对反转前后/远近关系，或写入与中位深度差冲突的关系。

`null_diagnostic` 每图单独保存完整 null caption，不进入任何 local-family worst-of-3/CVaR 或 H-fallback 门禁。`global_caption_swap` 同样只作容易识别的诊断集；两者均不进入 `12N` 条核心数据。

## Natural-error slice

自然错误必须来自 captioner 的**未经编辑原始输出**。机器检查只允许下列两种 verified predicate：

- `entity_absence`：类别必须属于数据集明确声明为穷举标注的类别，同时两套独立 detector/segmenter 均未检出；任何条件不足都标为 `unverified_mention`；
- 给出与两个实体 mask 的 GT median depth 显著冲突的远近关系；
- 遗漏不算错误，只单独登记 completeness。

natural-error 与 structured intervention 分开报告。若独立 scenes 或自然错误数量不足以形成稳定 cluster CI，只能声明合成干预结果，不能外推真实 captioner 鲁棒性。

若 NYUv2/KITTI 对目标类别没有穷举标注声明，`entity_absence` predicate 自动禁用；“标签中没有”或“两模型未检出”本身不能计入 hallucination prevalence。

## Captioner isolation

- development captioner 1：只取 official-train IDs 的 TR2M bundled LLaVA-v1.6 captions；其上游 commit 锁为 `a45925862bcd76c84ac38c6fc98da1e187f1146e`。
- development captioner 2：`Qwen/Qwen2.5-VL-7B-Instruct`，只在 train/dev 生成。
- held-out captioner：`OpenGVLab/InternVL3-8B`，只进入 internal-test natural-error slice 和 internal-test base captions。
- 在第一次生成前把 Hugging Face snapshot SHA、tokenizer revision、prompt 文本 SHA256、最大 token 数、temperature、top-p 和框架版本写入 manifest；revision 缺失时脚本必须拒绝运行。
- official benchmark test 的 captioner、prompt、revision、decoding 与 predicate audit 在打开任何 official test RGB 前冻结；test caption 不得成为 prompt 调参通道。
- caption decoding 默认 greedy；若使用采样，随机种子固定为 `17/29/43` 并逐条记录。

## Leakage isolation

- 原始 `interventions_all.jsonl` 对每张图都生成四个 family；用于模型拟合的 materialized split 中，`depth_relation_conflict` 在 train/dev 完全隔离到 quarantine，只在 test 出现，作为 held-out error family。
- train/dev/test 使用不重叠 template IDs；实体替换词表按 canonical class 分组后隔离。
- held-out captioner 不用于训练任何 gate、阈值或特征归一化。
- 图像、scene、caption hash、template、captioner、error family 任一 group key 泄漏都使构建失败。

## JSONL schema

每条 structured 记录至少包含：

`image_id, dataset, scene_id, sequence_id, cluster_id, frame_index, rgb_sha256, split, predicate_clean_caption, intervention, error_type, variant_id, target_region, generator, generator_revision, template_id, seed, source_caption_hash, machine_check`。

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

## Predicate validity without circular validation

- 用同一 GT 规则生成再验证的 200 正/200 负例只叫 regression suite，证明实现一致性，不估计自然错误 precision；
- natural predicate precision 必须使用独立证据链：不同来源的 exhaustive annotation 或 detector/segmenter ensemble，加上与生成器独立的 parser/grounding revision；
- 同一模型不得既生成 caption 又作唯一 judge；同一 intervention rule 不得生成并验证自然错误标签；
- precision ≥0.95 只适用于对应 predicate，不得写成完整 caption factuality；失败 predicate 自动禁用。

## Annotation coverage and power gates

在承诺 12,000 条干预前，先对 pilot manifest 运行 annotation-coverage audit：

- 每数据集至少 150 张图具有 reliable mask 且目标内 ≥32 个 valid-depth pixels；
- 每数据集至少 300 个实体对满足两个 mask 各 ≥32 valid-depth pixels 且 median-depth gap ≥10%；
- KITTI 未达门禁时，正式 two-dataset Claim-M 直接返回 `STOP_TWO_DATASET_CLAIM`；KITTI 仅保留 image-level sensitivity，不能由 Virtual KITTI 2 挽救。
- 分支唯一由 coverage JSON 中 hash-linked 的 `claim_dataset_decision` 决定；`power_analysis.py --coverage-decision ...` 只接受 `[NYUv2,KITTI]`。任何 STOP artifact 都不得启动正式双数据集 detectability。
- VKITTI2 的天气、视角与双相机渲染全部按基础 `SceneXX` 连成同一 `cluster_id`。官方只有 5 个基础场景，因此它固定为 `synthetic_structured_auxiliary_only`，只能作描述统计、结构化 stress test 和定性分析，不得给跨场景尾部风险或第二数据集 inferential claim。
- VKITTI2 adapter 不接受外部 frame list；它扫描官方解压目录，要求完整 scene/variation/camera/frame 与 RGB/depth/class/instance/textgt 模态对齐，生成 canonical full-source hash 后才允许固定哈希 pilot selection。

只有 coverage 返回 `GO_LOCAL_CLAIMS_NYUV2_KITTI` 后，才对 20 组预注册 prevalence、scene 内相关系数和 effect size 配置各运行 5,000 次模拟。它只估计“给定预设 score/loss 分布时的条件检出能力”，不包含模型训练、超参数搜索、captioner 或阈值学习误差，不能称为端到端 study power。主场景 conditional detectability 必须 ≥0.80；formal failure 只有在 dataset-decision/manifest/split-audit/implementation/grid/seed/5,000 simulations/20 scenarios 全部 hash-linked 时才允许扩大 independent internal-test scenes。当前 coverage 已 STOP，所以该模拟按预注册规则未运行。

本机允许运行 Ruff、Black、Pytest 与微型合成 adapter 测试；不得把合成测试写成科学结果。真实下载、coverage 与 conditional-detectability 只在授权 Linux `whr/AutoResearch` 中执行；这些任务均为 CPU-only，不等待或占用 GPU。archive、RGB、cache 和含机器路径的 manifest 不提交 Git。

## Expected artifacts

本轮 feasibility gate 必须生成 source manifest、pilot manifest、split audit 与 coverage；conditional-detectability 只在 coverage PASS 时生成。当前 coverage STOP，故 power artifact 有意不存在。下列 intervention/caption artifacts 属于 gate 通过后的 Step-003 corpus subphase，不在本轮完成范围内：

- `paper1/experiments/covol/build_interventions.py`
- `paper1/experiments/covol/audit_annotation_coverage.py`
- `paper1/experiments/covol/power_analysis.py`
- `paper1/experiments/covol/build_training_pilot_manifest.py`
- `paper1/experiments/covol/build_image_manifest.py`（Step 008 only）
- `paper1/experiments/covol/build_vkitti2_source_manifest.py`
- `paper1/data/covol/image_manifest.jsonl`
- `paper1/data/covol/split_audit.json`
- `paper1/data/covol/interventions_all.jsonl`：`12N` rows（pilot 12,000）
- `paper1/data/covol/interventions_train.jsonl`：`9N_train` rows（pilot 5,400）
- `paper1/data/covol/interventions_dev.jsonl`：`9N_dev` rows（pilot 1,800）
- `paper1/data/covol/interventions_test.jsonl`：`12N_test` rows（pilot 2,400）
- `paper1/data/covol/interventions_quarantine.jsonl`：`3(N_train+N_dev)` rows（pilot 2,400；held-out family，不进入拟合/调参）
- `paper1/data/covol/natural_captions.jsonl`：数量由原始 captioner 错误率决定
- `paper1/data/covol/null_diagnostic.jsonl`：`N` rows（pilot 1,000），不进入 local risk
- `paper1/data/covol/intervention_manifest.json`：schema/version/hash/count/leakage audit
- `paper1/results/covol/annotation_coverage.csv`
- `paper1/results/covol/power_analysis.csv`
- `paper1/configs/covol/dataset_fallback_decision.yaml`

## Acceptance checks

1. structured 总行数正好 `12N`，主键 `(image_id,error_type,variant_id)` 唯一；
2. machine-check 通过率 100%；
3. all/train/dev/test/quarantine 数量满足 `12N/9N_train/9N_dev/12N_test/3(N_train+N_dev)`，且四个 materialized views 是 all 的无重叠视图；
4. scene/template/captioner/held-out error-family 泄漏均为 0；
5. train/dev/internal-test 与 official benchmark test 的 image/scene overlap 均为 0；
6. enabled predicate 的 validity precision ≥0.95，失败 predicate 已自动禁用；
7. 同一脚本和 manifest 重跑产生相同排序与内容 SHA256；
8. 随机抽查只能由程序生成报告，不依赖用户长期人工标注。
9. null_diagnostic 与四个 local families 完全分离；
10. annotation coverage 通过，且主门禁 conditional detectability ≥0.80；否则记录 hash-linked STOP 与增加 independent scenes 的建议，不自动放宽阈值或改用 VKITTI2。

本轮 feasibility gate 已验收 training-only provenance、500/500 pilot、coverage 与 STOP 决策；conditional-detectability 被正确阻断。完整 intervention corpus 的第 1--9 项仍未完成；当前两数据集分支停止，步骤 005 和正式 004-B 均不得开始。
