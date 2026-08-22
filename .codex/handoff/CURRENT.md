# AutoResearch 当前接续状态

> **2026-08-22 Round-5 最新覆盖状态（优先于本文全部旧内容）**
>
> - 已从远端 fast-forward 到审稿基线 `ba4bf48`，新增意见为 `paper1/responce_from_reviewer/review_round5.md`；本轮回复为 `response_round5.md`。
> - 用户已改为授权本机运行小规模代码测试，但校内 Linux 仍不可达：本机不得下载完整研究数据、训练模型或生成科学结论；在用户明确通知恢复前不得再连接 Linux。
> - 上一轮 47 文件的 paper1 回归已在本机隔离 Python 3.12 环境复核：`ruff check paper1`、`black --check paper1` 通过，`pytest paper1/tests -q` 为 `92 passed`。仓库级检查仍被 `tools/` 中既存 lint/format debt 阻断，本轮未批量改写该无关范围。
> - Round-5 已修正：Main-PR 的 complete-caption WorstOf3 风险、标准 signed Lagrangian 与冻结优化常量；`cluster_id` bootstrap；dev-only frozen threshold + internal-test CVaR/WorstOf3 paired CI；VKITTI2 2.0.3 adapter/provenance 和 hash-linked fallback decision；feature extractor allowlist/runtime sanitizer；D0 learned-null/active-gradient 公平合同；conditional detectability 的克制命名。
> - VKITTI2 的所有变化按基础 `SceneXX` 聚类，官方只有 5 个独立基础场景；不得把天气/相机 clone 冒充 20 个独立场景。真实门禁可能因此 STOP，这是协议要求而非待绕过的工程问题。
> - 科学状态仍为 **Research Opportunity / Claim-F UNVERIFIED / Claim-M UNVERIFIED**。仍缺真实 manifest、coverage/detectability、checkpoint、实体级 OOF cache、缺陷复现、killer baselines 和主结果。
> - 旧恢复点 `stash@{0}`（`codex-pre-review-pull-20260822`）仍保留，不得无授权删除。

> **2026-08-22 最新覆盖状态（优先于下方旧快照）**
>
> - 当前分支 `chore/integrate-tools-and-paper1` 已包含远端审稿基线 `cae15e4`；审稿改进提交 `6e197dc` 已于 2026-08-22 推送到同名远端分支。新增意见与回复分别为 `review_20260821_153624.md`、`response_20260821_153624.md`。
> - 拉取前工作保存在 `stash@{0}`（`codex-pre-review-pull-20260822`），且已成功 apply 到当前工作树；远程验证、提交和推送完成前不得删除该恢复点。
> - 用户明确要求：本机禁止运行测试或下载实验数据；所有测试与数据操作只能在 `sshconfig.md` 指定的远程 Linux 上执行，数据必须放在远程 `whr` 下。禁止提交或披露 `sshconfig.md` 中的私密连接信息。
> - 审稿后主线改名为 **Main-PR**（cross-fitted partial residual，而非 orthogonal moment）。唯一待证伪边界是在两个冻结同任务 metric-depth candidates 之间，在 clean retention `>=0.80` 约束下最小化局部 caption-error upper-tail regret；dev 固定最低 CVaR threshold，internal-test 主报 CVaR/WorstOf3，hypervolume 降为 secondary。
> - 已实现但尚未远程验证：TIGER 最近邻/机制矩阵、唯一目标与 RU-CVaR/dual/伪代码、training-only NYUv2/KITTI adapters、scene-sequence connected-component split、trusted provenance、coverage/power gates、formal failure lineage、bootstrap invalid-denominator stop、扩展 feature firewall、B/C 等宽双 permutation、faithful/matched baseline 合同。回复草案为 `paper1/responce_from_reviewer/response_20260821_153624.md`。
> - 科学状态仍为 **Research Opportunity / UNVERIFIED**；没有真实数据门禁、checkpoint 或主结果，不能升级 Paper Candidate。
> - 2026-08-22 用户说明当前在校外，暂时无法访问校内 Linux 节点，并明确要求停止连接 Linux、直接提交本轮工作。故本轮 Ruff/Black/Pytest、真实数据下载及 coverage/power 门禁均为 `DEFERRED_BY_USER`，不得写成已通过。
> - 用户后续明确通知 Linux 可用后，下一原子动作是：在远程 `whr` 下保留已有文件并建立隔离工作副本 → 同步修改 → 在 `vlm` 环境确认 Python 3.12 → 远程 Ruff/Black/Pytest → 仅用 official-training 数据运行 NYUv2/KITTI coverage 与 20-grid × 5,000 formal power gate → 同步必要修复并追加提交。
>
> 下方为 2026-08-21 旧快照，只保留作历史导航；其中基线提交、环境命令和“下一原子动作”如与本覆盖状态冲突，均已失效。

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
