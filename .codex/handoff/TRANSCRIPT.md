# 脱敏会话历史

本文件是当前 Codex 会话的**压缩接续记录**，不是逐字转录。它保留用户目标、关键决定、已执行结果和研究状态变化，用于另一台机器追溯“为什么仓库变成现在这样”。当前事实必须以 Git、源码、测试和实验产物为准。

已删除或泛化：SSH 主机/端口/账号/密码/私钥、认证令牌、用户目录绝对路径、原始工具输出、系统/开发者提示、隐藏推理、原始 session ID 和本机应用数据库。仓库路径统一写作 `<REPO_ROOT>`。

## 1. 主仓库与工具箱定位

1. 用户要求移除原 `AutoResearchClaw` 子目录自身的 Git 仓库属性，并把最外层目录初始化为唯一 Git 仓库。
2. 用户要求解读 `AGENTS.md` 与 AutoResearchClaw 的融合状态，并继续完成融合。
3. 最终定位被明确为：最外层 `AutoResearch` 是主仓库和研究工作区；子目录后来重命名为 `tools/`，只作为通用工具箱，调用时必须发现、注入并服从根 `AGENTS.md`。
4. 研究问题、文献、实验记录、结果和论文材料放在 `paper*/`；`tools/` 不拥有独立研究目标、规则或 Git 属性。
5. 曾因 `AutoReasearch` 与 `AutoResearch` 拼写差异出现“不是 Git 仓库”的判断问题。规范名称已经锁定为 `AutoResearch`，不能重新创建错误拼写的第二仓库。

## 2. Git、GitHub 与远程执行

1. 用户遇到 `git push -u origin main` 弹出账号密码框。会话核对并转为 GitHub SSH remote；当前 remote 为 `git@github.com:Grain-Wang/AutoResearch.git`。
2. 用户要求利用本地私密 SSH 配置检查远程服务器和 GPU。该步骤涉及的真实连接信息与设备原始清单不进入本记录；后续只允许从被忽略的 `sshconfig.md` 或其他私密渠道读取。
3. 仓库文档补充了 A800 通用执行方式，但明确禁止提交真实主机、端口、账号、密码和私钥。
4. 用户看到 GitHub 的 2FA 提示后，得到的结论是：这是账号安全要求，与当前 SSH push 是否成功是两件事；应在期限前启用 2FA。
5. 当前研究与工具整合工作持续在 `chore/integrate-tools-and-paper1` 分支进行。远程默认 `main` 尚未合并这些工作。

## 3. 环境、依赖与文档

1. 用户要求依赖环境不提交，但 clone 使用者必须知道如何安装依赖及如何连接 A800。
2. 根 README 和工具文档已规定：所有需要的包必须写入依赖声明，不能只在某台机器临时安装。
3. 首选 Python 3.12 Conda 环境 `auto_research`；次选在项目工具目录使用 `uv`。
4. 已在本机创建 `auto_research` 环境并安装 PyMuPDF，用于 PDF 文本转换。本地环境本身不在 Git 中，另一台机器需要按 README 重建。
5. 根目录已经有 `README.md`，用于声明最外层主仓库定位、工具箱用途、依赖安装、A800 通用流程和不得提交的敏感内容。

## 4. 文献处理与想法形成

1. 用户把原始参考论文放入 `paper1/reference_papers_origin/`，要求判断是否需要转换为省 token 的格式。
2. 结论是转换为结构化 Markdown 更适合检索和按需阅读；处理后的论文位于 `paper1/reference_papers_processed/`，并有 manifest/README。
3. 原始 PDF 按用户要求不提交，`.gitignore` 持续忽略 `paper1/reference_papers_origin/*.pdf`。
4. 依据文献和 `AGENTS.md` 形成两个独立想法：
   - `01_counterfactual_value_of_language_depth.md`，后来收敛为唯一主线 CoVoL-Depth；
   - `02_query_adaptive_budgeted_geometry_routing.md`，后来降为 Q-GeoRoute Phase-0 备用方向。
5. 随着最近邻审计推进，CoVoL 中“错误语言有害”“区域 defer”“连续 advantage”“冻结候选 post-hoc routing”等宽泛表述均不再被当作独立新颖性。

## 5. 三轮强 CCF-C 审查与改进

### 第一轮

- 审稿文件：`review_20260821_013339.md`。
- 主要结果：收紧 CoVoL 研究范围、主张语言、候选门禁、缺陷复现和公平比较协议。
- 对应审稿与研究修改分别进入提交 `1e4ede8`、`e60ae26`。

### 第二轮

- 审稿文件：`review_20260821_022250.md`。
- 主要结果：移除 official test 开发污染；拆分 sensitivity 与正式 fallback defect；锁定同构 D0/D1 路线；分开 Claim-F/Claim-M；增加可运行 split/metrics 基础与更严格 gate。
- 对应审稿与研究修改分别进入提交 `a070991`、`2475ac0`。

### 第三轮

- 审稿文件：`review_20260821_032352.md`。
- 主要问题：expert 训练内 prediction 污染 meta-router；Claim-F 同时改变语义输入和 residualization；特征可利用干预元数据；image bootstrap 与候选相关 HV reference 可能产生伪显著；缺少直接 deferral 和 robust expert killers。
- 已完成的修正：scene-group OOF expert stacking plan/cache 审计、feature denylist/provenance、scene/drive cluster bootstrap、固定 HV reference、RGB/sequence/frame split 审计、Claim-F direct/permuted controls、outer-5/inner-4 cross-fit 协议及更强 baseline 合同。
- 对应审稿与研究修改分别进入提交 `4d7686d`、`9d48060`。
- 第三轮修改后共有 22 个单元测试通过；Ruff、Black 和 Git diff 检查通过，但没有生成真实科学结果。

## 6. 当前研究判断

1. CoVoL-Depth 仍是 Research Opportunity，不是 Paper Candidate。
2. Claim-F 与 Claim-M 均未验证。
3. Q-GeoRoute 保持 PARKED，不允许与 CoVoL 并行占用资源。
4. 当前最强反对意见是：直接 regression/density-ratio/dense-coherence/LOO routers 或 robust single-expert training 可能解释全部收益。
5. 下一动作必须先解决真实数据可用性：NYUv2/KITTI adapters、annotation coverage 和 power gate；在这些门禁通过前不得启动 A800 大规模训练。

## 7. Git 历史检查点

| 提交 | 含义 |
| --- | --- |
| `6ef3982` | 初始化最外层主仓库 |
| `0595044` | 融合工具箱与 paper1 材料 |
| `1e4ede8` | 第一轮强 CCF-C 审查 |
| `e60ae26` | 第一轮研究范围与验证门禁修正 |
| `a070991` | 第二轮强 CCF-C 审查 |
| `2475ac0` | 第二轮协议与指标强化 |
| `4d7686d` | 第三轮强 CCF-C 审查 |
| `9d48060` | 第三轮 OOF stacking、控制与统计修正 |

## 8. 本次跨机器接续决定

用户先要求提供方案，随后批准执行。最终选择是提交脱敏的 `CURRENT.md`、本历史和 manifest，并由 `AGENTS.md` 自动引导新会话读取；明确拒绝提交原始 JSONL、`auth.json`、日志或 SQLite 状态库。

因此，另一台机器获得的是可核验的项目上下文和决策历史，而不是对本机 Codex 聊天存储的非官方移植。
