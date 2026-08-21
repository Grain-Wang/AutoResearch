# AutoResearch 当前接续状态

- 更新时间：2026-08-21 14:13（Asia/Shanghai）
- 接续类型：脱敏、可移植状态快照
- 原始 Codex 会话：未包含

## 启动检查

1. 完整读取根目录 `AGENTS.md`；
2. 运行 `git status --short --branch`、`git log -1 --oneline`，以实际工作树为准；
3. 阅读 `paper1/README.md`、`paper1/steps/README.md` 和最新 review/response；
4. 确认没有新的真实结果后，再执行本文的“下一原子动作”。

本文只是接续导航，优先级低于 `AGENTS.md`、源码、配置、测试和实验产物。

## 仓库状态

- 规范主目录名：`AutoResearch`。历史上曾出现 `AutoReasearch` 拼写，不能据此创建第二个仓库。
- 唯一 Git 主仓库：最外层 `AutoResearch`；`tools/` 只是遵循根 `AGENTS.md` 的通用工具箱，没有独立 Git 属性或研究目标。
- 接续快照所在分支：`chore/integrate-tools-and-paper1`。
- 接续前基线提交：`9d48060162bce151798e7361220afe02fd78905e`（`research: harden OOF stacking and review controls`）。
- 远程：`git@github.com:Grain-Wang/AutoResearch.git`。
- 远程默认 `main` 仍较旧；在本分支合并前，另一台机器必须显式 checkout 本分支。
- `paper1/responce_from_reviewer/` 的目录名虽有历史拼写问题，但已被现有链接使用，本任务不顺带改名。

## 用户的持续目标

在有限时间和算力内，依据根 `AGENTS.md` 自主推进一篇以算法创新为核心、具有弱 CCF-B 或强 CCF-C 竞争力的完整论文。用户主要负责最终方向确认与论文责任，不应被要求长期参与标注、调参或手工评测。

## paper1 当前结论

- 唯一主线：**CoVoL-Depth**，即在自动 caption 出现局部、可机器验证的语义错误时，在冻结的纯视觉候选 `D0` 与图文候选 `D1` 之间做选择性区域路由。
- 当前等级：**Research Opportunity**，不是 Paper Candidate。
- `Claim-F`（语义增量）和 `Claim-M`（路由方法增量）均为 `UNVERIFIED`。
- 备用想法 Q-GeoRoute 为 `PARKED`；只有 CoVoL Gate-0 被证据否定且先更新范围锁定后才能启动。
- 尚无 NYUv2/KITTI 真实数据、checkpoint、缺陷复现、置信区间、延迟或主结果表，因此不能声称任何科学增益。

主阅读入口：

- `paper1/README.md`
- `paper1/ideas/01_counterfactual_value_of_language_depth.md`
- `paper1/steps/README.md`
- `paper1/responce_from_reviewer/review_20260821_032352.md`
- `paper1/responce_from_reviewer/response_20260821_032352.md`

## 已完成的可执行基础

- image/scene/sequence/RGB 内容哈希级 split 与 official-test 泄漏审计；
- scene-group OOF expert stacking plan/cache 审计，禁止 router 使用 expert 训练内预测；
- router feature denylist 与逐列 provenance，禁止干预元数据泄漏；
- paired scene/drive cluster bootstrap，replicate 内重算 clean denominator、retention、CVaR、Pareto 与 hypervolume；
- 候选无关的固定 hypervolume reference；
- 同构 D0/D1、image-only twins、shuffled-caption negative control、outer-5/inner-4 cross-fit 的协议；
- Claim-F 的 `B-direct`、`C-direct`、`C-permuted` 正交对照；
- 四类 direct deferral baseline、四类 robust expert killer 和 artifact/grounding control 的合同。

截至基线提交，`paper1` 共 22 个单元测试通过，Ruff、Black 和 Git diff 检查通过。这些检查只验证协议实现，不是科学证据。

## 仍未完成

- NYUv2/KITTI source adapters、真实 RGB manifest 和 `split_audit.json`；
- annotation coverage 与 20-grid power simulation；
- PyTorch 同构 `D0/D1`、OOF/final checkpoints 和真实 expert cache；
- image-only twins 与 shuffled-caption control 结果；
- outer/inner cross-fit router、AUROC 和 Claim-F controls；
- direct baselines、robust expert baselines、artifact/grounding controls；
- official crop/valid-depth adapters、真实 cluster CI、latency 和结果表。

## 下一原子动作

先实现 NYUv2/KITTI source adapters 和 annotation-coverage audit，并在真实局部 mask/depth 可用率及 power 达标前禁止启动 A800 大规模 expert 训练。

预注册回退：如果 KITTI 局部 oracle coverage 失败，切换到 Virtual KITTI 2 structured set；KITTI 只保留 image-level sensitivity/fallback。不要通过降低 coverage/power 门槛来强行继续。

后续固定依赖链：

`003 adapters/coverage/power → 005 scene-group OOF experts → 004-B fallback defect → 006 Claim-F → 007 killer baselines → 008 final canary`

## 环境与验证

首选环境为 Python 3.12 的 Conda 环境 `auto_research`；依赖必须写入声明文件，不能只存在于某台机器。基础检查从仓库根目录执行：

```powershell
conda run -n auto_research python -m ruff check paper1
conda run -n auto_research python -m black --check paper1
conda run -n auto_research python -m pytest paper1/tests -q --basetemp .local-deps/pytest-paper1
```

原始 PDF、环境目录和缓存不提交。`sshconfig.md` 只保存在本地并已忽略；A800 的真实主机、账号与认证材料需要私密分发，仓库只保留 `tools/docs/REMOTE_EXECUTION.md` 中的通用流程。

## 建议接续提示

```text
遵循 AGENTS.md 和 .codex/handoff/CURRENT.md，先核对 Git、paper1 状态以及最新 review/response。当前唯一允许推进的研究动作是 NYUv2/KITTI source adapters 与 annotation coverage/power gate；不得把现有单元测试写成科学结果，也不得提前启动大规模 GPU 训练。
```
