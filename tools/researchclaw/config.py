"""Minimal configuration for the AGENTS-governed research toolbox."""

from __future__ import annotations

import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Self

import yaml

DEFAULT_PYTHON_PATH = sys.executable
EXAMPLE_CONFIG = "config.researchclaw.example.yaml"
CONFIG_SEARCH_ORDER = ("config.yaml",)
EXPERIMENT_MODES = frozenset({"sandbox", "ssh_remote"})
LITERATURE_SOURCES = frozenset({"openalex", "semantic_scholar", "arxiv"})
_REMOTE_WORKDIR = re.compile(r"^(?:/|~/)[A-Za-z0-9_./-]*$")
_SSH_ADDRESS = re.compile(r"^[A-Za-z0-9_.-]+$")


def _mapping(value: object, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise TypeError(f"{name} must be a mapping")
    return {str(key): item for key, item in value.items()}


def _string(value: object, name: str, *, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise TypeError(f"{name} must be a string")
    return value.strip()


def _positive_int(value: object, name: str, *, default: int) -> int:
    result = default if value is None else int(value)
    if result <= 0:
        raise ValueError(f"{name} must be positive")
    return result


def _reject_unknown(value: dict[str, Any], allowed: frozenset[str], name: str) -> None:
    unknown = sorted(set(value) - allowed)
    if unknown:
        raise ValueError(f"{name} contains unsupported keys: {unknown}")


def resolve_config_path(explicit: str | None) -> Path | None:
    """Resolve an explicit config or the first local default."""

    if explicit:
        return Path(explicit).expanduser().resolve()
    for name in CONFIG_SEARCH_ORDER:
        candidate = Path(name)
        if candidate.is_file():
            return candidate.resolve()
    return None


@dataclass(frozen=True)
class ResearchConfig:
    """Research topic used by the stage workspace."""

    topic: str
    domains: tuple[str, ...] = ()


@dataclass(frozen=True)
class LiteratureSearchConfig:
    """Public scholarly search policy."""

    sources: tuple[str, ...] = ("openalex", "semantic_scholar", "arxiv")
    max_results_per_query: int = 20
    year_min: int = 0
    openalex_email: str = ""
    openalex_api_key_env: str = "OPENALEX_API_KEY"
    s2_api_key_env: str = "S2_API_KEY"

    def validate(self) -> None:
        """Validate source names and limits."""

        unknown = sorted(set(self.sources) - LITERATURE_SOURCES)
        if unknown:
            raise ValueError(f"unknown literature sources: {unknown}")
        if self.max_results_per_query <= 0:
            raise ValueError("literature_search.max_results_per_query must be positive")
        if self.year_min < 0:
            raise ValueError("literature_search.year_min must be nonnegative")


@dataclass(frozen=True)
class SandboxConfig:
    """Local Python subprocess settings."""

    python_path: str = DEFAULT_PYTHON_PATH


@dataclass(frozen=True)
class SshRemoteConfig:
    """Key-authenticated SSH execution settings."""

    host: str = ""
    user: str = ""
    port: int = 22
    key_path: str = ""
    gpu_ids: tuple[int, ...] = ()
    remote_workdir: str = "~/autoresearch/runs"
    remote_python: str = "python3"
    setup_commands: tuple[str, ...] = ()
    timeout_sec: int = 600

    def validate(self) -> None:
        """Validate SSH addressing and the four-GPU policy limit."""

        if not _SSH_ADDRESS.fullmatch(self.host):
            raise ValueError("experiment.ssh_remote.host is required and must be safe")
        if self.user and not _SSH_ADDRESS.fullmatch(self.user):
            raise ValueError("experiment.ssh_remote.user contains unsafe characters")
        if self.port <= 0 or self.port > 65535:
            raise ValueError("experiment.ssh_remote.port must be between 1 and 65535")
        if not _REMOTE_WORKDIR.fullmatch(self.remote_workdir):
            raise ValueError(
                "experiment.ssh_remote.remote_workdir must be an absolute or ~/ path"
            )
        if not self.remote_python or any(
            character.isspace() for character in self.remote_python
        ):
            raise ValueError("experiment.ssh_remote.remote_python must be one command")
        if len(self.gpu_ids) > 4:
            raise ValueError("experiment.ssh_remote.gpu_ids cannot exceed four GPUs")
        if len(set(self.gpu_ids)) != len(self.gpu_ids) or any(
            gpu_id < 0 for gpu_id in self.gpu_ids
        ):
            raise ValueError(
                "experiment.ssh_remote.gpu_ids must be unique and nonnegative"
            )


@dataclass(frozen=True)
class ExperimentConfig:
    """Real experiment execution policy."""

    mode: str = "sandbox"
    time_budget_sec: int = 300
    sandbox: SandboxConfig = field(default_factory=SandboxConfig)
    ssh_remote: SshRemoteConfig = field(default_factory=SshRemoteConfig)

    def validate(self) -> None:
        """Reject simulated and unsupported execution backends."""

        if self.mode not in EXPERIMENT_MODES:
            raise ValueError(
                f"experiment.mode must be one of {sorted(EXPERIMENT_MODES)}"
            )
        if self.time_budget_sec <= 0:
            raise ValueError("experiment.time_budget_sec must be positive")
        if not self.sandbox.python_path:
            raise ValueError("experiment.sandbox.python_path is required")
        if self.mode == "ssh_remote" and not self.ssh_remote.host:
            raise ValueError("experiment.ssh_remote.host is required")
        if self.mode == "ssh_remote":
            self.ssh_remote.validate()


@dataclass(frozen=True)
class RCConfig:
    """Complete minimal toolbox configuration."""

    research: ResearchConfig
    literature_search: LiteratureSearchConfig = field(
        default_factory=LiteratureSearchConfig
    )
    experiment: ExperimentConfig = field(default_factory=ExperimentConfig)
    project_root: Path = field(default_factory=Path.cwd)

    @classmethod
    def load(cls, path: Path) -> Self:
        """Load and validate YAML configuration."""

        source = path.expanduser().resolve()
        raw = yaml.safe_load(source.read_text(encoding="utf-8")) or {}
        if not isinstance(raw, dict):
            raise TypeError("config must be a mapping")
        return cls.from_dict(
            {str(key): value for key, value in raw.items()},
            project_root=source.parent,
        )

    @classmethod
    def from_dict(cls, raw: dict[str, Any], *, project_root: Path) -> Self:
        """Build a validated config from a mapping."""

        _reject_unknown(
            raw,
            frozenset({"research", "literature_search", "experiment"}),
            "config",
        )
        research_raw = _mapping(raw.get("research"), "research")
        _reject_unknown(research_raw, frozenset({"topic", "domains"}), "research")
        topic = _string(research_raw.get("topic"), "research.topic")
        domains_raw = research_raw.get("domains", ())
        if isinstance(domains_raw, str) or not isinstance(domains_raw, (list, tuple)):
            raise TypeError("research.domains must be a list of strings")
        domains = tuple(
            _string(value, "research.domains item") for value in domains_raw
        )

        literature_raw = _mapping(raw.get("literature_search"), "literature_search")
        _reject_unknown(
            literature_raw,
            frozenset(
                {
                    "sources",
                    "max_results_per_query",
                    "year_min",
                    "openalex_email",
                    "openalex_api_key_env",
                    "s2_api_key_env",
                }
            ),
            "literature_search",
        )
        sources_raw = literature_raw.get(
            "sources", ("openalex", "semantic_scholar", "arxiv")
        )
        if isinstance(sources_raw, str) or not isinstance(sources_raw, (list, tuple)):
            raise TypeError("literature_search.sources must be a list")
        literature = LiteratureSearchConfig(
            sources=tuple(
                _string(value, "literature_search.sources item")
                for value in sources_raw
            ),
            max_results_per_query=_positive_int(
                literature_raw.get("max_results_per_query"),
                "literature_search.max_results_per_query",
                default=20,
            ),
            year_min=int(literature_raw.get("year_min", 0)),
            openalex_email=_string(
                literature_raw.get("openalex_email"),
                "literature_search.openalex_email",
            ),
            openalex_api_key_env=_string(
                literature_raw.get("openalex_api_key_env"),
                "literature_search.openalex_api_key_env",
                default="OPENALEX_API_KEY",
            ),
            s2_api_key_env=_string(
                literature_raw.get("s2_api_key_env"),
                "literature_search.s2_api_key_env",
                default="S2_API_KEY",
            ),
        )

        experiment_raw = _mapping(raw.get("experiment"), "experiment")
        _reject_unknown(
            experiment_raw,
            frozenset({"mode", "time_budget_sec", "sandbox", "ssh_remote"}),
            "experiment",
        )
        sandbox_raw = _mapping(experiment_raw.get("sandbox"), "experiment.sandbox")
        _reject_unknown(
            sandbox_raw,
            frozenset({"python_path"}),
            "experiment.sandbox",
        )
        sandbox = SandboxConfig(
            python_path=_string(
                sandbox_raw.get("python_path"),
                "experiment.sandbox.python_path",
                default=DEFAULT_PYTHON_PATH,
            ),
        )
        ssh_raw = _mapping(experiment_raw.get("ssh_remote"), "experiment.ssh_remote")
        _reject_unknown(
            ssh_raw,
            frozenset(
                {
                    "host",
                    "user",
                    "port",
                    "key_path",
                    "gpu_ids",
                    "remote_workdir",
                    "remote_python",
                    "setup_commands",
                    "timeout_sec",
                }
            ),
            "experiment.ssh_remote",
        )
        gpu_ids_raw = ssh_raw.get("gpu_ids", ())
        if isinstance(gpu_ids_raw, str) or not isinstance(gpu_ids_raw, (list, tuple)):
            raise TypeError("experiment.ssh_remote.gpu_ids must be a list")
        setup_raw = ssh_raw.get("setup_commands", ())
        if isinstance(setup_raw, str) or not isinstance(setup_raw, (list, tuple)):
            raise TypeError("experiment.ssh_remote.setup_commands must be a list")
        ssh = SshRemoteConfig(
            host=_string(ssh_raw.get("host"), "experiment.ssh_remote.host"),
            user=_string(ssh_raw.get("user"), "experiment.ssh_remote.user"),
            port=int(ssh_raw.get("port", 22)),
            key_path=_string(ssh_raw.get("key_path"), "experiment.ssh_remote.key_path"),
            gpu_ids=tuple(int(value) for value in gpu_ids_raw),
            remote_workdir=_string(
                ssh_raw.get("remote_workdir"),
                "experiment.ssh_remote.remote_workdir",
                default="~/autoresearch/runs",
            ),
            remote_python=_string(
                ssh_raw.get("remote_python"),
                "experiment.ssh_remote.remote_python",
                default="python3",
            ),
            setup_commands=tuple(str(value) for value in setup_raw),
            timeout_sec=_positive_int(
                ssh_raw.get("timeout_sec"),
                "experiment.ssh_remote.timeout_sec",
                default=600,
            ),
        )
        experiment = ExperimentConfig(
            mode=_string(
                experiment_raw.get("mode"),
                "experiment.mode",
                default="sandbox",
            ),
            time_budget_sec=_positive_int(
                experiment_raw.get("time_budget_sec"),
                "experiment.time_budget_sec",
                default=300,
            ),
            sandbox=sandbox,
            ssh_remote=ssh,
        )
        config = cls(
            research=ResearchConfig(topic=topic, domains=domains),
            literature_search=literature,
            experiment=experiment,
            project_root=project_root.resolve(),
        )
        config.validate()
        return config

    def validate(self) -> None:
        """Validate the complete configuration."""

        if not self.research.topic:
            raise ValueError("research.topic is required")
        self.literature_search.validate()
        self.experiment.validate()

    def openalex_api_key(self) -> str:
        """Resolve the optional OpenAlex key without persisting it."""

        return os.environ.get(self.literature_search.openalex_api_key_env, "")

    def semantic_scholar_api_key(self) -> str:
        """Resolve the optional Semantic Scholar key without persisting it."""

        return os.environ.get(self.literature_search.s2_api_key_env, "")


def load_config(path: str | None, *, topic: str = "") -> RCConfig:
    """Load an explicit/default config or create a local sandbox config."""

    resolved = resolve_config_path(path)
    if resolved is not None:
        config = RCConfig.load(resolved)
        if topic and topic != config.research.topic:
            return RCConfig(
                research=ResearchConfig(topic=topic, domains=config.research.domains),
                literature_search=config.literature_search,
                experiment=config.experiment,
                project_root=config.project_root,
            )
        return config
    if not topic:
        raise ValueError("--topic or --config is required")
    return RCConfig(research=ResearchConfig(topic=topic))
