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

Round 1 已完成 S-fixed/S-param 形式化收缩、Stage-0 区间算术 canary、diode/Level-1
MOS 分支 enclosure 测试、selective-recovery 依赖合同和一个病态被动 MNA 缺陷 canary。
这些结果不证明 BlockStamp soundness 或效率。

1. 实现与主方法共享全部组件的 B2-strong pointwise checker。
2. 实现小矩阵 BlockStamp recurrence，并与显式 dense operator 逐元素交叉检查。
3. 运行冻结的 diode/ring-oscillator slab probe 和四级 component ladder。
4. 若结构性优势不能从稀疏性、器件局部性和时间递推中单独归因，则停止 Claim E。
5. 只有 killer baseline 下出现稳定信号后才进入完整 Paper Build。
