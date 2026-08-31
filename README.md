# AutoResearch

AutoResearch 是最外层主仓库、Git 仓库和自主科研工作区，由仓库级 [`AGENTS.md`](AGENTS.md) 统一约束。目标是在有限资源内形成以算法创新为核心、具备强 CCF-C / 弱到强 CCF-B 竞争力的完整论文证据链。

[`tools/`](tools/) 是通用研究执行工具箱，不拥有独立研究目标；研究问题、文献、实验记录、结果、评审与论文材料保存在 `paper*/` 目录中。

## 当前分支：paper2

当前 `paper2` 分支的活跃研究项目是：

**BlockStamp-Cert — circuit-structured certification of fixed-discretization nonlinear transient MNA**

系统愿景仍可称为 Proof-Carrying SPICE，但当前核心算法问题已经收缩为：利用 transient-MNA 的 device-local stamp 与 block-lower-bidiagonal 时间结构，构造可独立检查、严格向外舍入的轨迹证书，并验证其相对 component-matched pointwise / dense verified baselines 是否具有结构性收益。

当前研究状态：

- Research Opportunity Gate：PASS
- Paper Candidate Gate：FAIL / UNVERIFIED
- 当前目标：稳定 CCF-B 级 Paper Candidate
- 当前最重要阻断项：`C` 可逆性前提、rigorous arithmetic backend、完整 BE MNA、BlockStamp recurrence、B2-strong、nonlinear transient probe

详细状态见：

- [`paper2/README.md`](paper2/README.md)
- [`paper2/research/research_direction.md`](paper2/research/research_direction.md)
- [`.codex/handoff/CURRENT.md`](.codex/handoff/CURRENT.md)

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | 整个仓库的权威研究与执行规则 |
| `.codex/handoff/` | 当前分支的脱敏 Codex 接续包；不得混入其他 paper 项目状态 |
| `tools/` | 通用研究执行工具箱 |
| `paper*/ideas/` | Research Opportunities 与原始构思 |
| `paper*/research/` | 文献审计、研究方向、阶段技术 notes |
| `paper*/steps/` | 门禁、协议、改进记录与可复现研究步骤 |
| `paper*/experiments/` | 研究代码 |
| `paper*/tests/` | 自动化测试 |
| `paper*/results/` | 可重建结果与汇总 |
| `paper*/responce_from_reviewer/` | 正式 reviewer rounds 与作者 response |

## 跨机器继续 paper2

```bash
git clone -b paper2 git@github.com:Grain-Wang/AutoResearch.git
cd AutoResearch
codex -C .
```

已有仓库：

```bash
git fetch origin
git switch paper2
git pull --ff-only
codex -C .
```

新会话先读取 `AGENTS.md`，再读取 `.codex/handoff/CURRENT.md`，并用当前源码、测试、结果和 Git 状态核对接续摘要。只有需要追溯 paper2 决策时才读取 `.codex/handoff/TRANSCRIPT.md`。

## 环境与依赖

项目使用 Python 3.12。通用工具依赖由 `tools/pyproject.toml` 管理；每个 `paper*/pyproject.toml` 负责该论文实验的运行依赖。任何实际使用的运行库都必须写入依赖声明，不得只在某台机器临时安装。

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

paper2 的实验依赖应在 `paper2/pyproject.toml` 中声明；在进入正式 BlockStamp 实验前，需要把 rigorous arithmetic backend 等实际依赖写入并锁定。

## 研究与提交约束

- 核心贡献必须是可明确描述和验证的新算法、目标函数、决策机制或优化过程，不能把工程修复、配置问题或单纯 benchmark 包装成论文贡献。
- 优先验证 baseline 缺陷、最小算法对象和强公平 baseline；未通过 Paper Candidate Gate 前不启动大规模系统扩张。
- 新增代码必须可由命令行重建实验，记录配置、版本、随机种子和机器信息。
- 结果必须区分“协议/计划”“canary”“正式科学证据”，不得把手工 summary 或 oracle 标签冒充 checker 输出。
- 当前 `paper2` 不应读取或继承其他 paper 项目的数据集、研究门禁、reviewer 状态或 handoff 结论。
- 凭据、SSH 信息、私钥、本地绝对路径、环境目录、缓存和未授权大型数据不得提交。

## 代码检查

新增或修改研究代码后，按 `AGENTS.md` 与对应 paper 的配置运行至少：

```bash
ruff check .
black --check .
pytest tests/
```

如果仓库级检查被历史无关代码阻断，应同时报告仓库级失败与 paper 范围结果，不得把范围内通过冒充全仓库通过。

若本 README 与 `AGENTS.md` 冲突，以 `AGENTS.md` 为准。
