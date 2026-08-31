# AutoResearch

AutoResearch 是最外层主仓库、Git 仓库和自主科研工作区，由仓库级 [`AGENTS.md`](AGENTS.md) 统一约束。目标是在有限资源内形成以算法创新为核心、具备强 CCF-C / 弱 CCF-B 竞争力的完整论文证据链。

[`tools/`](tools/) 是通用研究执行工具箱，不拥有独立研究目标；每篇论文的研究问题、文献、实验记录、结果、评审与论文材料保存在对应的 `paper*/` 目录中。

## 当前分支：paper4

`paper4` 是一个新初始化的独立研究分支。目前仅依据原 `paper2/` 保留了 [`paper4/`](paper4/) 的目录骨架，没有继承 paper2 的研究内容、实验结果、评审结论或 Paper Candidate 状态。

当前状态：

- 研究方向：尚未确定
- Research Opportunities：尚未形成
- Research Opportunity Gate：NOT EVALUATED
- Paper Candidate Gate：NOT EVALUATED
- 下一阶段：阅读近期高质量论文，形成并排序最多 5 个通过 Research Opportunity Gate 的候选问题

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | 整个仓库的权威研究与执行规则 |
| `.codex/handoff/` | 脱敏的 Codex 接续资料；使用前必须与当前分支源码和 Git 状态核对 |
| `tools/` | 通用研究执行工具箱 |
| `paper4/ideas/` | Research Opportunities 与原始构思 |
| `paper4/research/` | 文献审计、研究方向与阶段技术 notes |
| `paper4/steps/` | 门禁、协议、改进记录与可复现研究步骤 |
| `paper4/experiments/` | 研究代码 |
| `paper4/tests/` | 自动化测试 |
| `paper4/results/` | 可重建结果与汇总 |
| `paper4/responce_from_reviewer/` | 正式 reviewer rounds 与作者 response |
| `paper4/configs/` | 可复现实验配置 |
| `paper4/reference_papers_origin/` | 原始参考文献 |
| `paper4/reference_papers_processed/` | 可检索的参考文献处理结果 |

空目录通过 `.gitkeep` 纳入版本控制；在目录产生正式文件后可删除对应占位文件。

## 跨机器继续 paper4

新克隆：

```bash
git clone -b paper4 git@github.com:Grain-Wang/AutoResearch.git
cd AutoResearch
codex -C .
```

已有仓库：

```bash
git fetch origin
git switch paper4
git pull --ff-only
codex -C .
```

新会话应先读取 `AGENTS.md`，再核对当前分支、源码、测试、结果与 Git 状态。历史 handoff 资料只有在确认属于 paper4 后才能作为当前研究状态使用。

## 环境与依赖

项目使用 Python 3.12。通用工具依赖由 `tools/pyproject.toml` 管理；paper4 开始实现实验后，应在 `paper4/pyproject.toml` 中声明并锁定实际运行依赖，不得只在某台机器临时安装。

首选 Conda 环境名：

```bash
conda create -n auto_research python=3.12 -y
conda activate auto_research
```

安装通用工具：

```bash
cd tools
python -m pip install -e ".[dev]"
```

## 研究与提交约束

- 核心贡献必须是可明确描述和验证的新算法、目标函数、决策机制或优化过程，不能把工程修复、配置问题或单纯 benchmark 包装成论文贡献。
- paper4 不继承其他论文项目的数据集、研究门禁、reviewer 状态或 handoff 结论。
- 优先验证 baseline 缺陷、最小算法对象和强公平 baseline；未通过 Paper Candidate Gate 前不启动大规模实验。
- 新增代码必须可由命令行重建实验，并记录配置、版本、随机种子和机器信息。
- 凭据、SSH 信息、私钥、本地绝对路径、环境目录、缓存和未授权大型数据不得提交。

## 代码检查

新增或修改研究代码后，按 `AGENTS.md` 与 paper4 的项目配置运行至少：

```bash
ruff check .
black --check .
pytest tests/
```

如果仓库级检查被历史无关代码阻断，应同时报告仓库级失败与 paper4 范围结果，不得把范围内通过冒充全仓库通过。

若本 README 与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。
