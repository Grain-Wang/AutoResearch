# Codex 可移植接续包

本目录用于让另一台机器上的 Codex 在克隆仓库后恢复项目语境。它保存的是经过人工审阅的状态摘要和决策历史，**不是** Codex 原始会话导出，也不能让 `codex resume` 直接打开原机器上的同一聊天。

OpenAI 官方文档说明，`codex resume` 用于恢复本机保存的聊天；跨聊天长期有效的项目指引应保存在 `AGENTS.md` 或已检入仓库的文档中：

- <https://learn.chatgpt.com/docs/codex/cli>
- <https://learn.chatgpt.com/docs/projects>

## 在另一台机器继续

当前接续包位于 `grain_paper1` 分支。远程默认分支仍是较早的 `main`，因此需要显式克隆该分支：

```powershell
git clone -b grain_paper1 git@github.com:Grain-Wang/AutoResearch.git
cd AutoResearch
codex -C .
```

如果仓库已经克隆：

```powershell
git fetch origin
git switch grain_paper1
git pull --ff-only
codex -C .
```

使用 IDE 时，打开最外层 `AutoResearch` 文件夹后新建 Codex 聊天。首条提示建议使用：

```text
请遵循根目录 AGENTS.md，读取 .codex/handoff/CURRENT.md，核对当前 Git 和仓库文件，然后从“下一原子动作”继续。只有需要追溯决策时才读取 TRANSCRIPT.md。
```

依赖安装、`auto_research` Conda 环境和 A800 通用连接流程见根目录 `README.md`。真实 SSH 主机、账号和认证材料必须通过私密渠道重新配置。

## 读取优先级

1. 根目录 `AGENTS.md`；
2. 当前 Git 状态、源码、测试和实验产物；
3. `CURRENT.md`；
4. `TRANSCRIPT.md`。

接续摘要可能随代码演进而过期，不能覆盖仓库事实，也不能作为论文实验结果或科学证据。

## 文件说明

- `CURRENT.md`：当前目标、研究状态、已完成内容、阻塞与下一动作；
- `TRANSCRIPT.md`：脱敏、压缩后的历史决策与执行结果；
- `manifest.json`：快照来源、版本和脱敏声明。

## 安全边界

本目录不得保存：

- 原始 session JSONL、应用日志或 SQLite 状态库；
- `auth.json`、令牌、密码、私钥或 Cookie；
- `sshconfig.md` 的真实连接信息；
- 用户目录等机器相关绝对路径；
- 系统/开发者提示、隐藏推理或未经筛选的工具输出。

`.gitignore` 默认拒绝 `.codex/` 下的所有其他文件，只放行本目录内四个已审阅文件。更新接续包时必须重新检查脱敏、JSON 格式、Git 暂存范围及与当前仓库状态的一致性。
