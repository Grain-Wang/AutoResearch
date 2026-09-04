# Review Round 5

## 1. 🎯 强CCF-B达标判定

- **当前状态**：未达标
- **核心差距**：Round 5 已完整执行 M2，但当前 BlockStamp 数值算法的唯一正机制信号被 contractive-interface pointwise B2 解释；Claim D/E 已停止，六个实例上没有任何 fixed/adaptive slab 击败该强简单基线，且全部 2,250 个配置级 verdict 均为 `UNKNOWN`，因此当前方法既没有可辩护的算法新颖性，也没有形成可用的整轨认证闭环。
- **高分录用潜力**：否。Round 5 的实验纪律、强基线补充和负结果记录达到高质量研究过程标准，但负结果本身不能支撑强 CCF-B 论文。只有提出一个非等价的新状态/依赖表示或新的可验证复用机制，并在 contractive pointwise 与对应 validated-numerics killer baseline 下通过低成本 canary，才值得重新开启算法论文路线。

## 2. 🔄 改进效果评估

针对 Round 5 新增的实现、实验和 `steps/009_m2_result_gate.md`：

- ✅ **有效改进**：
  1. 冻结 M2 网格已执行完成：6 个电路实例、`steps={100,300,1000}`、`slab={1,2,4,8,16}`、5 个独立 replicate、5 个方法，共 450 个 warm-up 和 2,250/2,250 个 measured rows；manifest 报告 0 missing、0 duplicate、共享 hash 匹配、完整成本字段和未筛选失败记录。
  2. `B2-strong` 已从占位状态推进为可执行、组件匹配的 verified-sparse pointwise baseline；`b2_fairness.json` 中 `all_required_hashes_present=true`、`all_shared_hashes_match=true`、`strong_baseline_status=IMPLEMENTED`，17 个已知坏样本无 confirmed false accept。
  3. 四级 component ladder 已完成。单 replicate canary 中，B2 获得 545/3000 accepted step slots，BlockStamp 为 457/3000；B2 累计 checker time 30.7220 s，BlockStamp 32.6835 s。该结果诚实地表明当前 BlockStamp 没有资源优势，而不是继续寻找有利切片。
  4. `operator_stress.json` 将全部 16 个 dimension/slab 单元扩展到 nonzero-width interval RHS，并覆盖四个条件数桶、强次对角耦合、非正规和 near-singular case；3,200 个 supported stress cases 无 observed containment violation，32 个预期 inconclusive/singular case fail closed。Claim I 的实现可信度明显提高。
  5. 已实现真实 producer 路径、3-stage NMOS ring、diode-RC precision/tolerance/radius sweep，并明确 candidate/tube 不读取 Decimal test reference。该 reference 被正确降级为非严格的 post-hoc diagnostic。
  6. Round 4 指出的 `C=0` 代数错误已经修正。Step 003 现在明确 `C=0` 时 `K(X)=X`，并把 `C=M^{-1}` 限定为 checker profile，而非一般 Krawczyk 定理必要前提。
  7. 先例审计已经对 Frommer--Hashemi 完成公式级核验，并接受 `REFRAME-SYSTEM`：普通 factorized Krawczyk、block forward substitution 和避免显式逆均不再作为算法贡献。
  8. 最关键的有效改进是补入 contractive-interface killer baseline：pointwise checker 在每次 `ACCEPT` 后传播其 Krawczyk image，而不是传播完整 producer tube。该基线在 6/6 实例上改善旧 B2 prefix，并支配或追平全部固定 slab；largest-first 自适应策略在 0/6 实例获得增益。项目据此主动撤销原 Claim W 的晋级资格。
  9. 仓库报告 Ruff、逐文件 Black 和 94 项测试通过，并新增手动 GitHub Actions workflow。虽然远程没有自动 CI status，这仍比上一轮的复现基础更完整。

- ⚠️ **部分解决**：
  1. contractive-interface killer 只执行了六实例、100-step canary，没有覆盖 300/1000 steps 和五 replicate。它足以阻止当前方法晋级，因为原 W 的机制解释已经被更强简单基线推翻；但不能被写成对所有长轨迹/slab 方法的普遍支配定理。
  2. `B2-strong` 使用项目自实现的 correctness-oriented sparse-row interval elimination，不是高性能第三方 verified sparse package。该限制不会挽救当前 BlockStamp——它已经比这一基线更慢——但若以后重新提出效率 claim，仍需更强实现基线。
  3. `certificate_bytes` 只序列化 candidate 与 tube，没有包含不同方法的 factor/witness 载荷，因此相同 bytes 只能说明当前 metric 无区分力，不能支持或否定真正的证书尺寸贡献。
  4. Round 5 artifacts 仍记录 `dirty_worktree=true`，并绑定生成时 commit `51351daa...`，而最终提交为 `e040110...`。对于已被停止的当前算法，不值得再投入完整 clean replay；但这些结果若进入任何论文、技术报告或公开 benchmark，必须从冻结干净 commit 重放。
  5. Chen--Hashimoto 和 Schwandt 的全文公式仍未获得，先例边界采用保守 `REFRAME-SYSTEM` 是合理的；但未来新机制若再次涉及 block/interval dependency reduction，仍必须重新完成相关全文核验。
  6. `ring_producer_canary.json` 体积极大，不适合作为长期 Git 主分支中的单个可读 artifact。科学摘要已足够，但未来 raw per-step trace 应使用分片 JSONL/压缩 artifact，并在 Git 中只保存 summary、manifest 和小型 replay case。

- ❌ **无效/偏离**：
  1. 原注册 M2 中 `W=PASS` 只相对于一个遗漏 accepted-image contraction 的 legacy B2。该结果不能再用于说明 joint slab coupling 的优势；最多只能作为“弱基线如何制造假阳性机制结论”的历史结果。
  2. Claim D 已停止：`temporal_only` 与 `temporal_device_blockstamp` 的 verdict、acceptance、prefix 和 margin 相同，且所谓 device-local 路径仍消费 globally assembled Jacobian。当前实现没有独立的 device-local 算法贡献。
  3. Claim E 已停止：BlockStamp 没有稳定 checker-time、RSS 或 certificate-byte 优势；相对 B2 的聚合 check-time ratio 反而不利于 BlockStamp。扩大网表或重复同一实现不能修复这一机制失败。
  4. 全部 2,250 个配置级 checker verdict 为 `UNKNOWN`；1,800 个 primary rows 触发 whole-run strict fallback，0 个恢复为 `ACCEPT`。因此当前系统不能声称整轨认证成功、选择性恢复有效或端到端成本有实际价值。
  5. adaptive largest-first slab 在 0/6 实例击败 contractive pointwise，且 adaptive verified step/splitting 已有直接 validated-numerics 先例。不得把 adaptive slab 重新包装为下一轮 headline。
  6. 当前 BlockStamp recurrence 已满足其停止条件。继续做 clean replay、BSIM、Verilog-A、SRAM、第二 producer或更大矩阵，只会增加工程工作量，不会恢复 CCF-B 所需的算法差异。

## 3. 🔍 强CCF-B维度深度审查

- **问题与动机**：
  独立认证外部、松容差或低精度 transient MNA 结果仍是一个真实且有价值的问题。Round 5 证明了 producer、checker、严格算术和公平基线可以形成可执行实验链；但也证明当前 axis-aligned tube + ordinary block substitution 无法提供整轨可用性。后续动机应从“BlockStamp 已解决问题”改为“现有 axis-aligned certificate 在真实 producer 轨迹上迅速丢失可组合性，contractive pointwise 是必须击败的最低基线”。

- **技术完备性与创新深度**：
  当前 recurrence 是标准 verified block forward substitution，先例与 killer baseline 均已消除其 headline 资格。系统组合本身也不能自动达到 CCF-B：producer/certificate/checker、Krawczyk、参数化组合、verified sparse solve 和 adaptive splitting均有基础先例。重新开启算法路线必须新增一个可以写成独立数学对象的机制，例如：

  1. 保留跨节点/跨时间相关性的稀疏 affine/doubleton interface representation，并以 interval remainder 对稀疏截断作可靠补偿；或
  2. 利用 device-stamp 局部 Jacobian 变化，对 verified sparse factor witness 执行可检查的增量复用决策，避免每步重新验证因子。

  第一类优先解决当前“没有整轨 certificate”的可用性障碍；第二类只能在认证率先达到可用水平后解决成本问题。普通 affine arithmetic、Lohner/doubleton、低秩近似或 factor reuse 均不能直接当作创新，必须给出 circuit-specific representation/decision、定理和 killer baseline。

- **实验可信度**：
  Round 5 的完整性和负结果可信度较高：网格、replicate、共享 hash、失败记录和成本字段均已冻结。最大的实验结论不是某个 speedup，而是三项负事实：`D=STOP`、`E=STOP`、`W` 被 contractive pointwise canary 推翻。全部整轨 verdict 为 `UNKNOWN` 进一步说明当前方法不能作为系统 paper 直接进入写作。

  新一轮不得再次启动 2,250-row 全矩阵。应先在现有六条 100-step trace 上做一个低成本机制 canary，并把 contractive pointwise、通用相关性保持基线和新方法同时纳入。只有 canary 通过后，才允许重新运行 300/1000-step 与多 replicate。

- **叙事克制性**：
  当前 README、Idea、Step 009 和 handoff 已正确写成 `algorithm headline STOP / REFRAME-SYSTEM / Paper Candidate FAIL`。后续不得继续使用 `BlockStamp-Cert` 暗示当前 recurrence 是新算法；可将其保留为历史 kernel 名称。原 `W=PASS` 必须始终附带“against noncontractive legacy B2”限定。不得使用 `faster`、`less wrapping`、`device-local advantage`、`adaptive certified partition` 或 `successful trajectory certification`。

## 4. ⚔️ 模拟评审攻击
### Top 3 Rejection Risks for Strong CCF-B

### Risk 1：核心算法已被强简单基线和先例共同消解

1. **审稿人可能如何质疑**：BlockStamp 只是 standard block forward substitution；原 W 优势来自没有让 pointwise B2 传播其已认证 Krawczyk image。
2. **当前论文有什么证据可以回应**：没有正面反驳证据；Round 5 自己在 6/6 实例上验证 contractive pointwise 改善旧 B2，且没有 fixed/adaptive slab 击败它。
3. **当前证据能否扛住该攻击**：不能，且该攻击已经成立。
4. **缺少什么具体证据**：需要一个非等价的新状态/依赖表示或复用决策，并在 contractive pointwise 与对应 validated-numerics baseline 下产生稳定优势；不能通过继续调 slab length 修复。

### Risk 2：方法没有完成任何整轨认证，系统价值尚未成立

1. **审稿人可能如何质疑**：2,250 个配置级 verdict 全部 `UNKNOWN`，为何这是一个可用的 SPICE certificate system？
2. **当前论文有什么证据可以回应**：有局部 accepted step、prefix、0 observed false accept 和完整 fallback 计费。
3. **当前证据能否扛住该攻击**：不能。局部 step certificate 不能替代一条可组合的整轨证书；whole-run fallback 且 0 recovery 也不构成 selective recovery。
4. **缺少什么具体证据**：至少需要在两个非线性 workload 上让新机制显著延长连续 certified prefix，并最终在预注册实例中产生可复现的 full-trace `ACCEPT` 或高比例局部恢复，同时报告完整成本。

### Risk 3：系统重构路线仍缺少 CCF-B 级独立贡献

1. **审稿人可能如何质疑**：既然 Krawczyk、proof-carrying、verified sparse、composition、adaptive splitting 都不是新贡献，restricted Proof-Carrying SPICE 是否只是已知组件集成？
2. **当前论文有什么证据可以回应**：问题定义清楚、实现独立、实验链完整，且公开文献中尚未确认完全相同系统。
3. **当前证据能否扛住该攻击**：不能。没有同名系统不等于组合具有非显然性；当前系统还没有整轨可用性或经济性结果。
4. **缺少什么具体证据**：需要一个可单独定义、可消融、具有 circuit-specific 原理的新机制；或把目标降为 CCF-C 系统论文，并用外部 SPICE producer、完整 trace certification、端到端收益和可复现实验补偿较弱的算法新颖性。

## 5. 🛠️ 下一轮原子化改进工单
### Atomic Action Items

> Round 6 应是“重新选机制”的短轮次，而不是继续扩展当前 BlockStamp。以下 P0 任务完成前，不运行新的全量 M2，不接入 BSIM/Verilog-A，不增加第二 producer。

| 优先级 | 任务类型 | 原子化执行动作 (What & How) | 强CCF-B对标依据 (Why) | 预期产出物/验证标准 | 关联文件路径 |
| :--- | :--- | :--- | :--- | :--- | :--- |
| P0 | 叙事修正 | 新建 Round-6 选择门禁，固定当前 BlockStamp recurrence、Claim D、Claim E 和对 legacy B2 的 Claim W 为历史停止结果；明确 contractive pointwise B2 是所有后续 acceptance 机制的最低基线，禁止把 adaptive slab、普通 block solve 和 device traversal重新列为候选创新 | 贡献克制性、研究止损；防止下游 Agent 在已证伪路径上继续堆实验 | 新文件包含 `CURRENT_METHOD=ARCHIVED`、禁用 claim 列表、后续 killer baseline 和二选一候选机制；旧 artifacts 不被重写 | `paper2/steps/010_round6_reselection_gate.md` |
| P0 | 文献增补 | 对两个候选机制建立公式级 prior-art matrix：A. sparse affine/doubleton/QR/Lohner/Taylor/zonotope interface propagation；B. verified factor reuse、parametric linear-system enclosure、low-rank/sparse update verification。每类至少核验 8 篇最接近全文，记录状态表示、更新公式、可靠截断、保证、复杂度和 circuit-specific 空白 | 方法创新性、Related Work 定位；两个候选均容易退化为 validated-numerics 直接应用 | 生成矩阵后只允许输出 `SELECT-A`、`SELECT-B` 或 `ARCHIVE-PAPER2`；选择条件是存在一句公式级非等价差异、自动 oracle 和两周内可运行 canary | `paper2/research/round6_mechanism_prior_art.md`, `paper2/steps/010_round6_reselection_gate.md` |
| P0 | 实验补充 | 若门禁输出 `SELECT-A`，实现 `x=c+Aξ+Δ` 形式的 sparse correlation-preserving interface canary；对 generator/drop 操作使用 outward interval remainder 补偿；同时实现 dense doubleton/Lohner-style 参考。只运行现有 6 个 100-step trace，比较 contractive pointwise、dense correlated baseline 和 sparse proposed | 核心机制有效性、Baseline公平性；直接针对 Round 5 暴露的 axis-aligned interface 失效 | 生成 `round6_interface_canary.csv`；新方法在每个 workload 至少 2/3 实例上连续 prefix 相对 contractive pointwise 提高至少 25%，不出现更宽的输出投影，且 check time 不超过 dense correlated baseline；否则输出 `STOP-A` | `paper2/experiments/interfaces/`, `paper2/experiments/run_round6_interface_canary.py`, `paper2/results/round6/round6_interface_canary.csv` |
| P0 | 实验补充 | 若门禁输出 `SELECT-B`，实现 device-stamp Jacobian delta 驱动的 factor-witness reuse：缓存已验证 factor/approximate inverse，使用 outward-rounded扰动范数或残差界判定复用，失败时重新验证。只运行 100-step 的 replicated RC ladder/ring，状态规模 `{32,64,128,256}`，与每步 fresh verified factor 的 contractive pointwise B2 对比 | 方法创新性、精度-性能权衡；验证局部 stamp 变化能否形成真正 EDA-specific 检查成本收益 | 生成 `round6_factor_reuse_canary.csv`；与 fresh-factor B2 保持完全相同 verdict/prefix，0 confirmed false accept；中大规模上 factor-verification time 至少降低 30%，aggregate total-check speedup 的 95% CI 下界大于 1；否则输出 `STOP-B` | `paper2/experiments/checkers/factor_reuse.py`, `paper2/experiments/run_round6_factor_reuse_canary.py`, `paper2/results/round6/round6_factor_reuse_canary.csv` |
| P0 | 消融补全 | 对被选择的机制创建三层消融：`contractive_pointwise`、`generic_new_representation_or_reuse`、`circuit_structured_variant`；三者共享 producer trace、candidate、tube seed、backend、semantics、scaling、ordering、线程与硬件 hash | 核心模块必要性、Baseline公平性；必须证明收益来自 circuit-specific 机制而非采用已有通用方法 | 每个 input hash 同时存在三种方法；manifest 的共享 hash 全部匹配；circuit-structured variant 若不优于 generic variant，则停止 circuit-specific contribution | `paper2/configs/round6_canary.yaml`, `paper2/results/round6/*.manifest.json` |
| P0 | 写作规范 | 在新 canary 通过前，将论文状态固定为 `Research Opportunity / Current Algorithm Archived / Paper Candidate FAIL`；禁止创建 paper draft、摘要或完成时态 contribution list | 贡献克制性、避免用写作掩盖机制失败 | `CURRENT.md`、README 和 Round-6 gate 的状态字符串一致；不存在 `novel/faster/less wrapping/full trajectory certified` 等无新证据表述 | `.codex/handoff/CURRENT.md`, `paper2/README.md`, `paper2/steps/010_round6_reselection_gate.md` |
| P1 | 可复现性 | 为后续 raw per-step producer 数据采用分片 JSONL，并在 Git 中只保存 summary、manifest 与最小失败 replay；单个 tracked text artifact 不得超过 10 MB，完整 raw 数据放入被 `.gitignore` 排除的可重建目录或正式 artifact storage | 可复现性、仓库可维护性；当前 ring JSON 极大，不利于审查、clone 和差异比较 | 新 runner 可从 config 重建 raw；Git 保存的 summary 含 row count、hash 和 replay command；新增测试检查 tracked artifact 大小阈值 | `paper2/results/README.md`, `.gitignore`, `paper2/tests/test_artifact_size_policy.py` |
| P1 | 可复现性 | 只有新的 Round-6 canary 通过后，从冻结源码 commit 的干净 checkout 重放该 canary；不要为已停止的 Round-5 BlockStamp 全矩阵补做 clean replay | 可复现性与资源纪律；旧方法已被 killer baseline 推翻，重放不会改变科学判断 | 新机制 artifact 记录 `dirty_worktree=false` 和正确源码 commit；确定性字段 hash 一致，timing 使用独立进程和预定义容差 | `paper2/results/round6/clean_replay_report.json` |
| P1 | 实验补充 | 若 `SELECT-A/B` 均失败，将目标明确降级或归档：只有在 contractive pointwise 系统接入一个外部 SPICE producer 后，对至少两个非线性电路获得大于 90% 的 full-trace/可恢复认证率且 `producer+check+fallback < strict rerun`，才允许按 CCF-C 系统路线继续；否则归档 paper2 | 研究止损、实际价值；防止无算法增量且无整轨可用性的系统被强行包装 | 输出 `CCFC-SYSTEM-GO` 或 `ARCHIVE-PAPER2`；所有阈值由未筛选结果文件直接计算 | `paper2/steps/011_system_fallback_gate.md`, `paper2/results/system_fallback/` |

### 本轮最终裁决

```text
Round 5 execution: COMPLETE
Research Opportunity: PASS only for the restricted problem
Current BlockStamp algorithm headline: STOP / ARCHIVED
M0 implementation chain: PASS-CANARY
Claim I: established kernel / implementation canary pass, not novelty
Claim W: FAIL-CANARY against contractive pointwise killer
Claim D: STOP
Claim E: STOP
Full-trajectory certification: 0/2250 configuration verdicts ACCEPT
Pre-Paper Candidate: FAIL
Paper Candidate: FAIL
```

下一轮不应“修补 BlockStamp”，而应先通过公式级文献门禁，从 **相关性保持的稀疏接口表示** 与 **器件局部变化驱动的 verified factor witness 复用** 中选择一个真正非等价的算法假设。若两者均不能通过低成本 canary，应结束 CCF-B 算法路线，而不是再次扩大实验规模。