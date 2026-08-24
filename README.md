# AutoResearch

AutoResearch 是最外层的主仓库和自主科研工作区，由仓库级
[`AGENTS.md`](AGENTS.md) 统一约束，
目标是在有限算力内形成以算法创新为核心、具备弱 CCF-B 或强 CCF-C 竞争力的
完整论文证据链。

[`tools/`](tools/) 中保留的 AutoResearchClaw 在本仓库中只作为研究执行工具箱
使用，不是独立研究仓库，也不拥有单独的 Git 仓库属性。
研究目标、权限边界、算法新颖性门槛、实验顺序和代码规范均以根目录
`AGENTS.md` 为最高优先级规则；工具箱内与这些规则冲突的旧版说明不适用于当前
工作流。当前融合后的有效流程为 16 个“选题到实验决策”阶段，不使用旧版论文
写作阶段。

## 仓库结构

| 路径 | 用途 |
| --- | --- |
| `AGENTS.md` | 整个仓库的权威研究与执行规则 |
| `.codex/handoff/` | 脱敏的跨机器 Codex 状态与历史接续包 |
| `tools/` | 可安装的 AutoResearchClaw 16 阶段研究实验工具箱 |
| `paper1/` | 当前论文方向的研究资料与过程文件 |
| `sshconfig.md` | 本地私密的服务器连接信息，禁止提交 |

## 跨机器继续 Codex 工作

当前精简后的研究状态位于 `grain_paper1` 分支；在合并到默认分支前，另一台机器应显式克隆该分支：

```powershell
git clone -b grain_paper1 git@github.com:Grain-Wang/AutoResearch.git
cd AutoResearch
codex -C .
```

新会话会先遵循根目录 `AGENTS.md`。建议首条消息为：

```text
读取 .codex/handoff/CURRENT.md，核对当前 Git 和仓库文件，然后从下一原子动作继续；只有需要追溯决策时才读取 TRANSCRIPT.md。
```

接续包不是原始 Codex session，也不包含认证信息。格式、读取顺序和安全边界见 [`.codex/handoff/README.md`](.codex/handoff/README.md)。

## 环境与依赖

项目使用 **Python 3.12**。所有运行所需依赖都必须写入
[`tools/pyproject.toml`](tools/pyproject.toml) 的依赖声明
中，再由环境管理工具安装；不得只在本机安装而不留下可复现的依赖声明。
环境目录、包缓存和其他依赖隔离产物不提交到 Git。

### 首选：Conda

```bash
conda create -n auto_research python=3.12 -y
conda activate auto_research
cd tools
python -m pip install -e ".[dev]"
```

以后进入项目时先执行：

```bash
conda activate auto_research
cd tools
```

### 次选：uv

在 `tools` 项目目录内创建本地环境并安装已声明的依赖：

```bash
cd tools
uv venv --python 3.12
uv pip install --python .venv -e ".[dev]"
```

Windows PowerShell 可使用 `.\.venv\Scripts\Activate.ps1` 激活环境；macOS/Linux
使用 `source .venv/bin/activate`。也可以通过 `uv run researchclaw ...` 直接运行
命令。

## 开始使用工具箱

先复制配置模板并填写文献检索与真实实验执行方式。`config.yaml` 可能包含
本地路径或凭据，不应提交：

```powershell
cd tools
Copy-Item config.researchclaw.example.yaml config.yaml
researchclaw tools list
researchclaw tools init --run-dir ../paper1/steps/my-run --topic "YOUR RESEARCH TOPIC" --config config.yaml
researchclaw tools status --run-dir ../paper1/steps/my-run
```

推荐逐阶段调用 `researchclaw tools <step>`，检查每个阶段产物后再通过关键门禁。
三个核心门禁分别是文献筛选 `screen`、基线缺陷复现 `reproduce` 和实验设计
`design`。每次运行都会发现并注入根目录 `AGENTS.md`；可在阶段产物中的
`agents_context.json` 核对规则来源和摘要。

完整的工具命令、阶段输入输出和门禁格式见
[`tools README`](tools/README.md)。研究问题、文献、实验记录和论文材料应保存在
外层主仓库的 `paper*/` 研究目录中，而不是把 `tools/` 当作研究项目目录。

## A800 远程实验

远程实验需要授权账号、OpenSSH（`ssh` 和 `scp`）、密钥认证，以及服务器上的
Python 3.12 环境。实际主机、端口、账号、密码和私钥只能通过私密渠道分发，
不得写入 README、配置示例或任何可提交文件。

具体的 SSH 别名、远程 Python、存储路径、GPU 检查和 `ssh_remote` 配置方法见
[`Remote GPU Execution Guide`](tools/docs/REMOTE_EXECUTION.md)。只使用
当前任务获准的 GPU，单次任务不得超过 4 张 GPU。

## 研究与提交约束

- 核心贡献必须是可明确描述和验证的新算法、目标函数、决策机制或优化过程，
  不能把工程修复、配置问题或单纯 benchmark 包装成论文贡献。
- 优先验证 baseline 的算法缺陷，再做最小原型、强 baseline、消融、鲁棒性和
  独立重复；未通过候选门禁前不启动大规模实验。
- 默认不使用付费服务，不对外提交 issue、PR、commit 或公开研究结果。
- 新增代码必须可通过命令行重建实验，记录随机种子、配置与版本，并按
  `AGENTS.md` 要求执行 Ruff、Black 和 Pytest 检查。
- `sshconfig.md`、密码、令牌、私钥、`.env*`、本地配置、依赖环境、缓存、数据集、
  模型权重和大体积实验产物不得提交。真实访问凭据必须始终保留在仓库之外或
  已忽略的本地文件中。

若本文档与 [`AGENTS.md`](AGENTS.md) 存在差异，以 `AGENTS.md` 为准。
