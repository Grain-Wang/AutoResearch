# paper2：Proof-Carrying SPICE Research Opportunity

## 当前状态

当前主机会是面向非线性瞬态离散 MNA 的可独立检查证书。2026-08-25 的
红队文献审计未发现直接 prior art，但发现 DC interval verification、validated
integration、proof-carrying computation 和 verified sparse algebra 的强重叠。
方向通过 Research Opportunity Gate，尚未通过 Paper Candidate Gate。

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

## 下一步

1. 阅读并冻结[收缩后的研究方向](research/research_direction.md)。
2. 按[完整实验流程](steps/002_complete_experiment_protocol.md)执行 Stage 0–2。
3. 实现固定 Backward Euler 的最小 diode/MOS slab canary。
4. 对比逐点 Krawczyk、dense slab、可靠稀疏内核与严格重跑。
5. 只有出现稳定结构性优势后才进入完整 Paper Build。
