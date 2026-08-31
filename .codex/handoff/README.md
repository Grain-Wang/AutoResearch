# Codex 可移植接续包（paper2）

本目录用于让另一台机器上的 Codex 在克隆 `paper2` 分支后恢复 **BlockStamp-Cert** 的研究语境。它保存的是经过审阅的状态摘要和决策历史，不是 Codex 原始会话导出，也不能让 `codex resume` 直接恢复另一台机器上的聊天。

## 在另一台机器继续 paper2

首次克隆：

```bash
git clone -b paper2 git@github.com:Grain-Wang/AutoResearch.git
cd AutoResearch
codex -C .
```

仓库已存在时：

```bash
git fetch origin
git switch paper2
git pull --ff-only
codex -C .
```

建议新会话首条消息：

```text
请遵循根目录 AGENTS.md，读取 .codex/handoff/CURRENT.md，并用当前 Git、源码、测试和实验产物核对其中状态；然后从 paper2 的下一原子动作继续。只有需要追溯 paper2 决策时才读取 TRANSCRIPT.md。
```

## 读取优先级

1. 根目录 `AGENTS.md`；
2. 当前 Git 状态、源码、测试和实验产物；
3. `.codex/handoff/CURRENT.md`；
4. `.codex/handoff/TRANSCRIPT.md`。

接续摘要不能充当科学证据，过期内容不得覆盖当前仓库事实。

## 文件说明

- `CURRENT.md`：paper2 当前目标、研究状态、阻断项和下一动作；
- `TRANSCRIPT.md`：仅包含 paper2 / BlockStamp-Cert 的脱敏压缩历史；
- `manifest.json`：paper2 快照元数据与清理声明；
- `README.md`：本说明。

## Reviewer 与历史 note

正式 reviewer round 只在：

```text
paper2/responce_from_reviewer/
```

历史阶段技术评估如果没有对应研究增量，不进入 reviewer numbering；这类内容放在：

```text
paper2/research/notes/
```

## 安全与污染边界

本 handoff 不得保存：

- 其他 paper 项目的研究状态、数据集、门禁或 reviewer 历史；
- 原始 session JSONL、应用日志或 SQLite 状态库；
- `auth.json`、令牌、密码、私钥或 Cookie；
- SSH 主机、账号、端口或机器绝对路径；
- 系统/开发者提示、隐藏推理或未经筛选的工具输出。

更新接续包时必须重新核对：当前分支是否为 `paper2`、active project 是否为 `paper2`、active direction 是否为 `BlockStamp-Cert`，并检查是否出现 `paper1`、`CoVoL`、`NYUv2`、`KITTI` 等其他项目专用语义。
