# Remote GPU Execution

This guide explains how an authorized collaborator can use ResearchClaw with a
lab A800 node. It intentionally contains no real password, private key, fixed
username, or internal host address. Obtain those values through the lab's
approved private channel.

AutoResearch is the outer main repository. Run the local toolbox commands from
its `tools/` subdirectory; keep research records and selected results in the
outer `paper*/` workspace.

## 1. Local prerequisites

- Python 3.12
- Git
- OpenSSH client providing both `ssh` and `scp`
- Access to the lab network or VPN
- An authorized account and SSH private key for the GPU node

Install ResearchClaw from `AutoResearch/tools` after cloning the outer
repository. Conda is preferred:

```bash
cd AutoResearch/tools
conda create -n auto_research python=3.12 -y
conda activate auto_research
python -m pip install -e ".[dev]"
```

As a second choice, use `uv` inside `AutoResearch/tools`:

```bash
uv venv --python 3.12
uv pip install --python .venv -e ".[dev]"
```

All dependencies must be declared in `tools/pyproject.toml`; isolated
environment directories and package caches must remain untracked.

The built-in `ssh_remote` backend invokes the system `ssh` and `scp` commands.
It does **not** require Paramiko. A locally isolated Paramiko installation used
for one-off diagnostics is not a repository dependency.

## 2. Configure SSH

Test the connection using values supplied privately by the lab administrator:

```bash
ssh -p <A800_PORT> <A800_USER>@<A800_HOST>
```

Key-based authentication is required for unattended experiment runs. Do not
store a password in this repository. A convenient local SSH configuration is:

```sshconfig
Host autoresearch-a800
    HostName <A800_HOST>
    User <A800_USER>
    Port <A800_PORT>
    IdentityFile ~/.ssh/id_ed25519
    IdentitiesOnly yes
```

Save that block in the user's local `~/.ssh/config`, then verify:

```bash
ssh autoresearch-a800 "hostname; nvidia-smi -L"
```

Verify the server host-key fingerprint with the lab administrator before the
first connection. Never commit `~/.ssh/config`, a private key, a password, or
the repository-local `sshconfig.md` file.

## 3. Prepare Python 3.12 on the node

The node's default `python3` may not be Python 3.12. Create or request a Python
3.12 environment under the large shared storage volume, then record its exact
interpreter path. One possible Conda setup is:

```bash
conda create -p /u3disk/$USER/envs/autoresearch-py312 python=3.12 -y
conda activate /u3disk/$USER/envs/autoresearch-py312
python --version
```

Do not place datasets, model checkpoints, or large caches under `/home`. Use an
authorized directory such as `/u3disk/$USER/autoresearch/` and monitor its free
space before launching a run.

The node exposes CUDA 12.2 through `/usr/local/cuda`. If `nvcc` is needed but
not on `PATH`, add it only inside the remote experiment environment:

```bash
export CUDA_HOME=/usr/local/cuda
export PATH="$CUDA_HOME/bin:$PATH"
```

## 4. Configure ResearchClaw

Copy the tracked example into a local, ignored configuration file:

```bash
cp config.researchclaw.example.yaml config.yaml
```

Set the remote experiment section without placing credentials in YAML:

```yaml
experiment:
  mode: "ssh_remote"
  ssh_remote:
    host: "autoresearch-a800"
    user: ""
    port: 22
    key_path: ""
    gpu_ids: [0]
    remote_workdir: "/u3disk/<A800_USER>/autoresearch/runs"
    remote_python: "/u3disk/<A800_USER>/envs/autoresearch-py312/bin/python"
    setup_commands: []
```

When `host` is an SSH alias, its user, port, and identity come from the local
SSH configuration. Alternatively, fill `host`, `user`, `port`, and `key_path`
with non-secret connection metadata in the ignored `config.yaml`.

Use only GPUs allocated to the current run. The repository `AGENTS.md` limits a
run to at most four GPUs; the current A800 node has fewer than that limit.

## 5. Verify before a run

```bash
ssh autoresearch-a800 "nvidia-smi --query-gpu=index,name,memory.free,utilization.gpu --format=csv"
researchclaw tools list
researchclaw tools init --run-dir ../paper1/steps/a800-run --topic "YOUR TOPIC" --config config.yaml
```

Check free GPU memory, CPU load, and storage capacity before executing stages
13-14. GPU utilization can briefly read 0% while existing processes still hold
large memory allocations, so inspect both utilization and free memory.

## 6. Files that must stay local

The following must never be committed:

- the outer repository's `sshconfig.md`
- `config.yaml` and other credential-bearing local overrides
- `.env*`, passwords, tokens, and private keys
- `.local-deps/` and `.pip-cache/`
- experiment artifacts, datasets, checkpoints, and remote caches

Tracked documentation and example configuration must use placeholders such as
`<A800_HOST>` and `<A800_USER>`. Distribute real access details separately.
