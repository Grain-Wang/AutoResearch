# paper2：Proof-Carrying SPICE Research Opportunity

## 当前状态

当前主机会是面向非线性瞬态离散 MNA 的可独立检查证书。最新机器 gate 为：

- `Research Opportunity: PASS`；
- `M0 soundness chain: PASS-CANARY`；
- `M1 operator gate: ITERATE`，其中 `Claim I: IMPLEMENTATION-CANARY-PASS`，但
  theorem-level novelty unresolved、efficiency unverified；
- `M2 matched nonlinear probe: NOT-STARTED`；
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
| `results/blockstamp/b2_fairness.json` | `ITERATE / B2-CANARY-ONLY`；200 easy accepts、17 bad cases 0 false accept；required hashes incomplete | 不能支持 B2-strong fairness |
| `results/blockstamp/next_round_gate.json` | `M0 PASS-CANARY / M1 ITERATE / M2 NOT-STARTED` | `Paper Candidate FAIL-UNVERIFIED` |

这些 artifacts 均记录 `dirty_worktree=true` 并绑定其 source/configuration hashes；仍需
clean independent replay。Canary 没有把条件式 Krawczyk argument 升级为机器证明，也没有
关闭 recurrence-specific prior art。

## 复现

当前 artifact 使用 Python 3.12、MPFR 4.2.1 (`libmpfr.so.6`) 和 256-bit backend。
从 `paper2/` 运行 JSON 中记录的命令：

```bash
python3 -m experiments.generate_numerical_defects --output results/blockstamp/numerical_defect_cases.csv --seed 17
python3 -m experiments.run_rigorous_backend --samples 50000 --seed 20260831
python3 -m experiments.run_mna_canary --steps 100 --step-size 1e-05
python3 -m experiments.run_operator_canary --cases-per-grid 200 --dense-canary-cases 2 --seed 20260831
python3 -m experiments.run_next_round_gate
```

代码回归命令：

```bash
ruff check .
black --check .
pytest tests/
```

## 下一步

1. 完成冻结 recurrence 与 Chen--Hashimoto、Schwandt、Frommer--Hashemi 及 verified
   sparse solve 的 theorem-level 对照；若无非等价 device/time mechanism，停止算法首创。
2. 实现 verified-sparse B2-strong，并补齐所有共享组件 hash；当前 dense pointwise canary
   不能冒充 killer baseline。
3. B2 fairness 可判定后，运行 diode-RC/3-stage ring 的四级 component ladder 和未筛选
   M2 probe，完整计入 generation/check/fallback、RSS 和 certificate bytes。
4. 若 Claim W/D/E 无跨配置稳定信号，按 Step 008 停止对应主张，不扩张 SRAM、BSIM、
   Verilog-A、第二 producer 或大规模网表掩盖失败。
