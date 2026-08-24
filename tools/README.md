# ResearchClaw toolbox

`tools/` 是 AutoResearch 主仓库内的通用科研执行工具箱，不是独立研究仓库。
根目录 `AGENTS.md` 是唯一权威规则；研究问题、论文、实验代码和证据应放在
`paper*/`，本目录只保留可复用执行代码、配置模板和工具文档。

精简后的工具箱只提供：

- 16 阶段研究产物契约与关键门禁；
- OpenAlex、Semantic Scholar 和 arXiv 公共文献检索；
- 本地 Python 3.12 与密钥 SSH 的真实实验执行；
- 无 Slurm 节点上的协作式、可恢复 GPU 队列；
- PDF 文献到带页码锚点 Markdown 的可选转换脚本。

不包含 LLM 产品层、网页服务、语音、MCP、Overleaf、HITL、外部 agent、
Docker/Colab 后端、模拟实验结果或兼容旧 CLI 的占位命令。

## 安装

```bash
cd tools
python3.12 -m pip install -e '.[dev]'
```

如需运行 `scripts/convert_reference_papers.py`，额外安装：

```bash
python3.12 -m pip install -e '.[pdf]'
```

## 16 阶段工作流

```bash
cp config.researchclaw.example.yaml config.yaml
researchclaw tools list
researchclaw tools init \
  --run-dir ../paper1/steps/example-run \
  --config config.yaml
researchclaw tools status --run-dir ../paper1/steps/example-run
```

阶段别名依次为：`topic`、`decompose`、`search`、`collect`、`screen`、
`extract`、`synthesize`、`reproduce`、`hypothesize`、`design`、`codegen`、
`plan`、`experiment`、`refine`、`analyze`、`decide`。

工具会向上发现最近的 `AGENTS.md`，在工作区和每个阶段记录其内容快照与
SHA-256。初始化只记录配置摘要，不复制配置或凭据。

阶段 4 `collect` 调用真实公共学术 API；阶段 13 `experiment` 运行真实本地或
SSH 实验。其他阶段验证当前科研负责人生成的产物，不自动生成论文内容，尤其
不会在缺少证据时生成模板、假引用或假结果。

每个阶段目录为 `stage-NN/`。执行前先按 `researchclaw tools list` 的契约写入
对应产物，再调用该阶段命令进行验证或执行。例如：

```bash
researchclaw tools screen --run-dir ../paper1/steps/example-run --config config.yaml
```

阶段 5、8、10 是硬门禁，要求 `gate.json`：

```json
{
  "status": "PASS",
  "reason": "The algorithmic defect is reproduced by the cited probe.",
  "evidence": ["stage-08/defect_report.md", "stage-08/reproduce/metrics.json"]
}
```

`status` 只能为 `PASS` 或 `STOP`；证据路径必须相对工作区、存在且不能逃逸。
任一门禁未通过时不会执行下游阶段。阶段 16 的 `decision.json.decision` 只能为
`STOP`、`REFINE`、`PIVOT` 或 `PAPER_CANDIDATE`。

## 实验调度契约

阶段 11 的 `experiment/` 保存可命令行重建的代码。阶段 12 的
`schedule.json` 使用以下最小格式：

```json
{
  "tasks": [
    {
      "id": "seed-0",
      "project": ".",
      "entry_point": "main.py",
      "args": ["--seed", "0"],
      "env": {},
      "timeout_seconds": 300
    }
  ]
}
```

任务 ID 必须唯一；`project` 必须位于阶段 11 的 `experiment/` 内。标准输出中
形如 `accuracy: 0.91` 的有限数值会写入结果摘要。环境变量的值不会写入摘要。
SSH 后端使用唯一远程目录，结束后清理；不关闭主机密钥校验，不支持密码自动化。

远程实验和 GPU 队列操作见
[Remote GPU Execution](docs/REMOTE_EXECUTION.md)。队列配置可先执行：

```bash
researchclaw gpu-queue validate --config queue.yaml
researchclaw gpu-queue run --config queue.yaml --state queue-state.sqlite --dry-run
researchclaw gpu-queue status --state queue-state.sqlite
```

GPU 队列是协作式调度器，不是跨账号强锁，也不会终止其他用户的进程。

## 质量检查

```bash
ruff check .
black --check .
pytest tests/
```

若本文件与主仓库 `AGENTS.md` 有差异，始终以 `AGENTS.md` 为准。
