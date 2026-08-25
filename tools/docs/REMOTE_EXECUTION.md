# Remote GPU execution

本文说明已授权研究者如何使用实验室 GPU 节点。示例不包含真实主机、账号、
端口、密码或密钥；这些信息必须通过实验室私密渠道获取，不能提交到仓库。

## SSH 前置条件

- 本地和远端均使用 Python 3.12；
- 本地安装 `ssh` 与 `scp`；
- 使用密钥认证，并由管理员核对首次连接的主机密钥指纹；
- 数据、模型、缓存和大体积结果放在节点授权的大容量目录；
- 单次运行最多使用根目录 `AGENTS.md` 允许的 4 张 GPU。

建议在本机 `~/.ssh/config` 保存别名，而不是把连接信息写进仓库：

```sshconfig
Host autoresearch-a800
    HostName <A800_HOST>
    User <A800_USER>
    Port <A800_PORT>
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

先人工验证：

```bash
ssh autoresearch-a800 'python3.12 --version; nvidia-smi -L'
```

ResearchClaw 强制 `BatchMode=yes`，不会关闭 OpenSSH 主机密钥检查，也不支持在
配置中保存密码。

## 项目专用快捷连接

需要由自动化科研负责人反复检查同一授权节点时，使用项目内已忽略的 SSH
目录，而不是修改系统级 SSH 配置或自动化密码：

```text
.local-deps/ssh/
├── a800                 # 私密快捷入口
├── a800.yaml            # ResearchClaw remote profile
├── a800_ed25519         # chmod 0600，不得提交
├── a800_ed25519.pub
├── config               # OpenSSH alias，不得提交
└── known_hosts          # 经 SHA256 指纹核验的固定主机公钥
```

远端只向该公钥开放登录；`authorized_keys` 项禁用 agent、端口和 X11 转发以及
user rc。客户端同时强制 `BatchMode=yes`、`PasswordAuthentication=no`、
`KbdInteractiveAuthentication=no`、`StrictHostKeyChecking=yes`、
`IdentitiesOnly=yes` 和 `ClearAllForwardings=yes`。不得设置
`StrictHostKeyChecking=no`，也不得把密码放进参数、环境变量、日志或 Git。

私密 profile 从 [`config.remote.example.yaml`](../config.remote.example.yaml)
派生。完成一次性公钥安装后，仓库根目录下的快捷接口为：

```bash
.local-deps/ssh/a800 check
.local-deps/ssh/a800 connect
.local-deps/ssh/a800 snapshot
.local-deps/ssh/a800 show
```

- `check` 只检查认证、Python、GPU 与 `whr`，不写远端；
- `connect` 进入交互式终端；
- `snapshot` 才会原子更新 `~/whr/A800_STATUS.md`；
- `show` 只读取当前快照。

状态采集器通过标准输入临时传到远端，不部署常驻脚本，不导入远端研究代码，
也不分配 GPU。Markdown 使用权限 `0600`，只保留最新版本；写入失败时旧文件
保持不变。内容包括系统/GPU、Conda 和项目 Python 环境、`whr` 两层目录摘要，
并深入发现 `paper*/results`、`artifacts`、`runs` 和 `queue`。原始数据、缓存、
密钥、token、`.env`、私密配置与符号链接目标不会展开或读取。

## 阶段 13 的 SSH 后端

复制配置模板为已忽略的 `tools/config.yaml`：

```yaml
research:
  topic: "YOUR RESEARCH TOPIC"

experiment:
  mode: ssh_remote
  time_budget_sec: 600
  ssh_remote:
    host: autoresearch-a800
    user: ""
    port: 22
    key_path: ""
    gpu_ids: [0]
    remote_workdir: "/u3disk/<A800_USER>/autoresearch/runs"
    remote_python: "/u3disk/<A800_USER>/envs/py312/bin/python"
    setup_commands: []
    timeout_sec: 600
```

SSH 别名已指定用户、端口和密钥时，可保持对应字段为空或默认值。运行阶段 13
前同时检查显存占用、利用率、计算进程和磁盘空间；GPU 利用率暂时为 0 不代表
没有进程占用显存。

```bash
researchclaw tools experiment \
  --run-dir ../paper1/steps/a800-run \
  --config config.yaml
```

后端为每次调用创建唯一远程目录，复制阶段 11 的实验项目，通过标准输入传递
执行脚本，并在完成、失败或超时后清理该目录。结果日志落在阶段 13 本地目录。
它不会安装依赖、下载模型或选择未明确配置的 GPU。

## 无 Slurm 节点的协作式 GPU 队列

`researchclaw gpu-queue` 用于在远端节点上等待 GPU 连续空闲后执行依赖图。它是
协作式工具：不会终止其他用户进程，也不能消除不同账号同时观察到空闲 GPU 的
竞争。需要严格隔离时应使用 Slurm 或管理员提供的跨账号锁。

建议在授权的 `whr/paper1` 目录中分离代码、运行产物和队列状态：

```bash
mkdir -p ~/whr/paper1/{data,cache,artifacts,runs,queue,envs}
cd ~/whr/paper1
git clone -b grain_paper1 <AUTHORIZED_AUTORESEARCH_URL> AutoResearch
cd AutoResearch/tools
python3.12 -m pip install -e '.[dev]'
```

仓库提供 `paper1/configs/covol/remote_queue.example.yaml`。复制为机器私有配置后，
必须把其中 `cwd`、`run_root` 和输出路径改为该节点的实际绝对路径：

```bash
cp ../paper1/configs/covol/remote_queue.example.yaml \
  ~/whr/paper1/queue/paper1.yaml
researchclaw gpu-queue validate \
  --config ~/whr/paper1/queue/paper1.yaml
researchclaw gpu-queue run \
  --config ~/whr/paper1/queue/paper1.yaml \
  --state ~/whr/paper1/queue/state.sqlite \
  --dry-run
```

GPU 任务支持两种明确分离的分配模式。`exclusive` 要求 4 次连续采样均满足：
无 NVIDIA compute process、已用显存低于 1024 MiB、利用率低于 5%；采样间隔
30 秒（连续窗口共 2 分钟）。`shared` 允许存在其他 compute process，只要求
NVIDIA 报告的剩余显存不少于任务的 `memory_required_mib` 加
`shared_memory_reserve_mib`（默认 4096 MiB）。两种模式在随机退避后都会再次核对；
均不终止或抢占其他用户进程，最多并行两个本队列单 GPU 任务。

需要比较共享与完整空闲运行时，使用相同的 `comparison_group` 声明一对
`shared`/`exclusive` 任务，并保持命令、配置、seed 和声明显存相同。队列会为两次
运行建立不同目录，注入 `RESEARCHCLAW_GPU_ALLOCATION_MODE`，并写入
`allocation.json`。共享运行可用于容量和吞吐诊断；受共租户干扰的耗时不得替代
exclusive 运行作为论文正式计时。

若配置了 `report_path`，调度器会在注册、启动和任务终态时原子更新权限为
`0600` 的 Markdown 报告。报告汇总任务状态、GPU、时间、退出码、运行日志路径和
声明产物的 SHA256，但不会复制命令、环境变量或原始日志内容。后续 SSH 会话可直接
打开该文件，再按其中路径核对 `stdout.log`、`stderr.log`、`completion.json` 和实验产物。
调度器创建的单次运行目录固定为 `0700`；worker 使用 `umask 077`，allocation、
completion、日志和任务在运行目录内写出的结果默认仅当前账号可读。

确认 dry-run 后，可在 `tmux` 中启动：

```bash
tmux new-session -d -s paper1-gpu-queue \
  'researchclaw gpu-queue run \
    --config ~/whr/paper1/queue/paper1.yaml \
    --state ~/whr/paper1/queue/state.sqlite'
researchclaw gpu-queue status \
  --state ~/whr/paper1/queue/state.sqlite
researchclaw gpu-queue stop \
  --state ~/whr/paper1/queue/state.sqlite
```

`stop` 只请求 drain：不再启动新任务，已运行任务继续完成。节点重启后用相同
配置和 SQLite 状态重新启动，调度器会核对 worker 完成记录并恢复未完成任务。

初始 paper1 队列只排到已有真实入口和门禁的步骤；不得为尚不存在的训练或评测
入口制造占位任务，更不能把模拟数据当成实验结果。

## 禁止提交

- `sshconfig.md`、`~/.ssh/config`、密码、令牌和私钥；
- `config.yaml`、机器私有队列 YAML、SQLite 状态与 scheduler 日志；
- `.env*`、环境目录、包缓存；
- 数据集、模型权重、大体积缓存和未经筛选的实验产物。
