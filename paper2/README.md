# paper2：Proof-Carrying SPICE Research Opportunity

## 当前状态

当前主机会是面向非线性瞬态离散 MNA 的可独立检查证书。最新机器 gate 为：

- `Research Opportunity: PASS`；
- `M0 soundness chain: PASS-CANARY`；
- `M1 operator gate: REFRAME-SYSTEM`，其中 `Claim I: IMPLEMENTATION-CANARY-PASS`，但
  algorithmic novelty 与 efficiency 仍未通过；
- `B2-strong component fairness: PASS`，四方法 component ladder 为
  `COMPLETE-CANARY / HOLD`；
- 冻结 `M2` 已完成 2250/2250 rows，原始对照为 `W=PASS, D/E=STOP`；
- 更强的 contractive-interface pointwise B2 在六实例 canary 上支配或追平所有 fixed slab，
  因此 `W=FAIL-CANARY / ITERATE`；
- `Paper Candidate: FAIL-UNVERIFIED`。

高威胁先例已包括 block-Krawczyk、interval cyclic reduction、factorized verified
Krawczyk 和 verified sparse algebra。当前递推 canary 通过不能证明算法新颖，也不能证明
BlockStamp 比强 baseline 更快、更省内存或更易认证。

## 目录结构

- `reference_papers_origin/`：原始论文与来源记录。
- `reference_papers_processed/`：便于检索和分析的文献文本。
- `ideas/`：最多 5 个通过 Research Opportunity Gate 的候选方向。
- `steps/`：研究步骤、门禁、证据和决策记录。
- `configs/`：可复现实验配置。
- `experiments/`：数据处理、训练、评价与绘图代码。
- `tests/`：研究代码的自动化测试。
- `results/`：可重建的实验结果与汇总。
- `responce_from_reviewer/`：模拟评审意见与逐轮回应。

## 当前机器证据

| Artifact | 结果 | 可支持的最强表述 |
| --- | --- | --- |
| `results/blockstamp/numerical_defect_cases.csv` + manifest | 24 个实际 float32/float64 residual-stopped solves 均在 0 步提前停止、真根在 tube 外且 forward error 为 1 V；checker 全部 `UNKNOWN`、0 false accept；严格阈值对照一步到根并 `ACCEPT` | 静态线性 motivation canary；非 nonlinear transient 证据 |
| `results/blockstamp/rigorous_backend_summary.json` | 400,056 attempted；400,044 supported；12 structured unsupported；八项操作各 50,000 random + 7 edge；0 containment violation | Directed-rounding implementation canary only |
| `results/blockstamp/mna_canary.json` | RC、diode-RC 各 100 步全部 `ACCEPT`；1,800 Jacobian samples 0 violation；17 negative cases 0 false accept | Restricted BE MNA/dense pointwise checker canary only |
| `results/blockstamp/operator_canary.json` | 12 cells 共 2,400 nonsingular cases（含 24 个 nonzero-width interval RHS）、0 containment violation；额外 1 个 singular case `UNSUPPORTED`；相对 exact coordinate hull 的最大绝对 inflation 为 0.1321725812626729 | `Claim I: IMPLEMENTATION-CANARY-PASS` only；不支持 Claim W |
| `results/blockstamp/b2_fairness.json` | `PASS / B2-STRONG-COMPONENT-MATCHED`；30/30 supported component cases；required hashes 完整且匹配 | 支持进入 component-matched baseline 阶段；非正式 M2 性能结论 |
| `results/blockstamp/component_ladder.csv` + manifest/summary | 120/120 配置、30/30 matched groups、0 missing/duplicate/unsupported；所有配置级 verdict 为 `UNKNOWN` | 完整 frozen component canary；不支持稳定 runtime/memory/device-locality 优势 |
| `results/blockstamp/ring_producer_canary.json` | 3 个预声明 smooth-NMOS ring 实例、100/300/1000 步、float32/float64 producer 的未筛选 trace；tube 只由 producer residual、局部 inverse-Jacobian scale 与冻结 radius rule 生成 | 真实 producer/interface canary；非 BSIM、工业 SPICE 或效率证据 |
| `results/blockstamp/diode_rc_producer_sweep.csv` + manifest | 3 个真实 diode-RC profile 的 precision × tolerance × radius 完整网格，同时保留 `ACCEPT/UNKNOWN/UNSUPPORTED` | producer 认证边界 canary；不支持 Claim W/D/E |
| `results/blockstamp/minimal_probe.csv` + manifest | 2250/2250 配置完整；原注册规则 `W=PASS`、`D/E=STOP`；全部整轨 verdict 为 `UNKNOWN` | 完整 frozen M2，但 W 尚未通过后续 killer baseline |
| `results/blockstamp/interface_contraction_canary.json` | contractive pointwise 在 6/6 实例改善旧 B2，且支配或追平所有 fixed slab；largest-first adaptive 在 0/6 实例增益 | 撤销 W 的晋级资格；非完整三长度重跑 |
| `results/blockstamp/next_round_gate.json` | `M0 PASS-CANARY / M1 REFRAME-SYSTEM / W KILLER-BASELINE-CANARY-FAIL` | `Paper Candidate FAIL-UNVERIFIED` |

这些 artifacts 均记录生成时 `dirty_worktree=true` 并绑定其 source/configuration hashes；
clean independent replay 未执行。由于 Round 5 已关闭且当前方法已停止，它不是本
handoff 授权的后续动作。Canary 没有把条件式 Krawczyk argument 升级为机器证明，也没有
关闭 recurrence-specific prior art。

diode-RC 与 ring 的事后误差诊断统一使用与 checker backend 独立的
`Decimal-160 high-precision test reference`。该 reference 没有 directed sign/error
certificate，因此明确是非严格测试参考，不能称为 MPFR root、rigorous root bracket，
也不能单独确认 false accept。candidate 与 tube 初始化均不读取该 reference。

## 历史复现命令（当前禁止执行）

当前 artifact 使用 Python 3.12、MPFR 4.2.1 (`libmpfr.so.6`) 和 256-bit backend。
以下命令仅记录 Round 5 的生成 provenance；本 handoff 不授权重新运行：

```bash
python3 -m experiments.generate_numerical_defects --output results/blockstamp/numerical_defect_cases.csv --seed 17
python3 -m experiments.run_rigorous_backend --samples 50000 --seed 20260831
python3 -m experiments.run_mna_canary --steps 100 --step-size 1e-05
python3 -m experiments.run_ring_producer_canary
python3 -m experiments.run_diode_rc_sweep
python3 -m experiments.run_operator_canary --cases-per-grid 200 --dense-canary-cases 2 --seed 20260831
python3 -m experiments.run_interface_contraction_canary --steps 100
python3 -m experiments.run_next_round_gate
```

代码回归命令：

```bash
ruff check .
black --check .
pytest tests/
```

## Round 5 closure（不是后续执行计划）

1. 停止当前 BlockStamp numerical-algorithm headline：recurrence 已被 prior art reframe，
   D/E 已失败，W 又被 contractive pointwise killer canary 解释。
2. 不为当前方法运行 clean replay、扩大电路、SRAM/BSIM/Verilog-A 或第二 producer；这些
   工作不能修复算法 novelty。
3. 任何新 dependency representation、witness-reuse decision、优化目标或 probe 都属于
   尚未授权的后续 round；等待用户另行明确指令。
4. 完整数据与裁决见 `steps/009_m2_result_gate.md`。
