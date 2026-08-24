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

默认 paper1 示例要求 20 次连续采样均满足：无 NVIDIA compute process、已用
显存低于 1024 MiB、利用率低于 5%。采样间隔 30 秒，随机退避后再次确认，最多
并行两个单 GPU 任务。启动后任务运行到结束，不会因其他账号随后占用而抢占。

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
