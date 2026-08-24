"""Factory for the two permitted real experiment backends."""

from __future__ import annotations

from pathlib import Path

from researchclaw.config import ExperimentConfig
from researchclaw.experiment.sandbox import ExperimentSandbox, SandboxProtocol


def create_sandbox(config: ExperimentConfig, workdir: Path) -> SandboxProtocol:
    """Create a local subprocess or key-authenticated SSH backend."""

    config.validate()
    if config.mode == "sandbox":
        return ExperimentSandbox(config.sandbox, workdir)
    if config.mode == "ssh_remote":
        from researchclaw.experiment.ssh_sandbox import SshRemoteSandbox

        ok, message = SshRemoteSandbox.check_ssh_available(config.ssh_remote)
        if not ok:
            raise RuntimeError(f"SSH connectivity check failed: {message}")
        return SshRemoteSandbox(config.ssh_remote, workdir)
    raise RuntimeError(f"unsupported real experiment mode: {config.mode}")
