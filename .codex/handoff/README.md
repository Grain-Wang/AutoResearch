# Codex 可移植接续包（paper2）

本目录用于让另一台机器上的 Codex 恢复已经关闭的 **BlockStamp-Cert Round 5**，以及
已经完成的 **Round 6 P0 mechanism reselection gate**。它保存的是经过审阅的状态摘要
和决策历史，不是 Codex 原始会话导出，也不能让 `codex resume` 直接恢复另一台机器上的
聊天。P0 的结果为 `ARCHIVE-PAPER2`；当前不授权原型、canary、M2、P1 或新一轮研究。

## 在另一台机器恢复 P0 终态

首次克隆：

```bash
git clone -b paper2 https://github.com/Grain-Wang/AutoResearch.git
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
请遵循根目录 AGENTS.md，读取 .codex/handoff/CURRENT.md，并用当前 Git、源码、测试和
实验产物核对其中状态。Round 5 已关闭，Round 6 P0 已输出 ARCHIVE-PAPER2；不要实现
原型、运行实验、进入 P1/Round 7，也不要把 TRANSCRIPT.md 中的历史计划当作当前指令。
停止并等待用户的新授权；只有需要追溯 paper2 决策时才读取 TRANSCRIPT.md。
```

## 读取优先级

1. 根目录 `AGENTS.md`；
2. 当前 Git 状态、源码、测试和实验产物；
3. `.codex/handoff/CURRENT.md`；
4. `.codex/handoff/TRANSCRIPT.md`。

接续摘要不能充当科学证据，过期内容不得覆盖当前仓库事实。

## 文件说明

- `CURRENT.md`：paper2 Round 5 冻结结论、Round 6 P0 归档裁决和当前生命周期锁；
- `TRANSCRIPT.md`：仅包含 paper2 / BlockStamp-Cert 的脱敏压缩历史；其中出现的
  “当前”或“下一步”只指历史时点，不是可执行指令；
- `manifest.json`：paper2 快照元数据与清理声明；
- `README.md`：本说明。

## Reviewer 与历史 note

正式 reviewer chain 为：

```text
paper2/responce_from_reviewer/review_round1.md
paper2/responce_from_reviewer/review_round2.md
paper2/responce_from_reviewer/review_round3.md
paper2/responce_from_reviewer/review_round4.md
paper2/responce_from_reviewer/review_round5.md
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

更新接续包时必须重新核对：当前分支是否为 `paper2`、active project 是否为 `paper2`、
active direction 是否为 `none (ARCHIVE-PAPER2)`，并检查是否出现 `paper1`、`CoVoL`、
`NYUv2`、`KITTI` 等其他项目专用语义。
