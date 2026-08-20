"""PromptManager — domain-aware registry for pipeline prompts.

Loads defaults from ``researchclaw.prompts.ml`` or ``researchclaw.prompts.hep``
(selected by the ``domain`` kw), merges optional YAML user overrides, and
renders templates with ``{variable}`` substitution.

Domain selection happens exactly once — at construction time. Every stage
implementation just calls ``pm.for_stage(name, **vars)`` and receives the
domain-native prose.  No per-stage overlay plumbing.
"""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

import yaml

from researchclaw.prompts.shared import (
    _DEFAULT_BLOCKS,
    _DEFAULT_SUB_PROMPTS,
)

logger = logging.getLogger(__name__)


# Domain identifiers accepted by ``PromptManager`` / ``_load_bank``.
SUPPORTED_DOMAINS = ("ml", "hep_ph", "biology_metabolic")

# Bundled AGENTS.md per-stage directives (always injected for covered stages).
_AGENTS_DIRECTIVES_PATH = Path(__file__).parent / "agents_directives.yaml"


def find_agents_file(search_start: str | Path | None) -> Path | None:
    """Find the nearest ``AGENTS.md`` at or above *search_start*.

    ``search_start`` may name either a file or a directory.  The nearest file
    wins, matching the usual project-scoped AGENTS.md convention.
    """
    if search_start is None:
        return None
    start = Path(search_start).expanduser().resolve()
    current = start.parent if start.is_file() else start
    for directory in (current, *current.parents):
        candidate = directory / "AGENTS.md"
        if candidate.is_file():
            return candidate
    return None


# ---------------------------------------------------------------------------
# Template rendering
# ---------------------------------------------------------------------------


def _render(template: str, variables: dict[str, str]) -> str:
    """Replace ``{var_name}`` placeholders with *variables* values.

    Only bare ``{word_chars}`` tokens are substituted — JSON schema examples
    like ``{candidates:[...]}`` are left untouched because the regex requires
    the closing ``}`` immediately after the identifier.
    """

    def _replacer(match: re.Match[str]) -> str:
        key = match.group(1)
        return str(variables[key]) if key in variables else match.group(0)

    return re.sub(r"\{(\w+)\}", _replacer, template)


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderedPrompt:
    """Fully rendered prompt ready for ``llm.chat()``."""

    system: str
    user: str
    json_mode: bool = False
    max_tokens: int | None = None


# ---------------------------------------------------------------------------
# Bank loader
# ---------------------------------------------------------------------------


def _load_bank(domain: str) -> tuple[
    dict[str, dict[str, Any]],
    dict[str, dict[str, str]],
    dict[str, dict[str, str]],
]:
    """Return ``(stages, debate_hyp, debate_analysis)`` for *domain*.

    Unknown domains fall back to the ML bank. This is intentional —
    downstream callers pass the domain id derived from the profile
    detector, which covers many non-hep domains not yet forked.
    """
    if domain == "hep_ph":
        from researchclaw.prompts import hep as _bank
    elif domain == "biology_metabolic":
        from researchclaw.prompts import biology as _bank
    else:
        from researchclaw.prompts import ml as _bank
    stages = _bank.STAGES
    debate_hyp = getattr(_bank, "DEBATE_ROLES_HYPOTHESIS", {})
    debate_ana = getattr(_bank, "DEBATE_ROLES_ANALYSIS", {})
    return stages, debate_hyp, debate_ana


# ---------------------------------------------------------------------------
# PromptManager
# ---------------------------------------------------------------------------


class PromptManager:
    """Central registry for pipeline prompts with optional YAML overrides.

    Parameters
    ----------
    overrides_path
        Optional path to a YAML file with user prompt overrides.
    domain
        Prompt bank to load. ``"ml"`` (default) or ``"hep_ph"``.  Unknown
        values fall back to ``"ml"`` so legacy call sites keep working.
    """

    def __init__(
        self,
        overrides_path: str | Path | None = None,
        *,
        domain: str = "ml",
        extra_prompts: dict[str, str] | None = None,
        agents_path: str | Path | None = None,
        agents_search_start: str | Path | None = None,
    ) -> None:
        self._domain = domain if domain in SUPPORTED_DOMAINS else "ml"
        stages, debate_hyp, debate_ana = _load_bank(self._domain)

        # Deep-copy so mutations don't leak across PromptManager instances
        # or back into the module-level banks.
        self._stages: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in stages.items()
        }
        self._blocks: dict[str, str] = dict(_DEFAULT_BLOCKS)
        self._sub_prompts: dict[str, dict[str, Any]] = {
            k: dict(v) for k, v in _DEFAULT_SUB_PROMPTS.items()
        }
        self._debate_hypothesis: dict[str, dict[str, str]] = {
            k: dict(v) for k, v in debate_hyp.items()
        }
        self._debate_analysis: dict[str, dict[str, str]] = {
            k: dict(v) for k, v in debate_ana.items()
        }
        # Per-stage additional guidance (appended to the user prompt at render
        # time).  Keys are stage names; values are the resolved text after
        # reading any file paths.
        self._extras: dict[str, str] = {}
        # Bundled AGENTS.md directives and workspace policy remain active when
        # config-level guidance (prompts.extra_prompts) is present.
        self._directives: dict[str, str] = {}
        self._agents_path: Path | None = None
        self._agents_text = ""
        self._agents_bytes = b""

        if overrides_path:
            self._load_overrides(Path(overrides_path))
        if extra_prompts:
            self._load_extras(extra_prompts)
        self._load_bundled_directives()
        self._load_project_agents(
            agents_path,
            agents_search_start if agents_search_start is not None else Path.cwd(),
        )

    # -- properties -------------------------------------------------------

    @property
    def domain(self) -> str:
        return self._domain

    # -- loading ----------------------------------------------------------

    def _load_overrides(self, path: Path) -> None:
        if not path.exists():
            logger.warning("Prompts file not found: %s — using defaults", path)
            return
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except yaml.YAMLError as exc:
            logger.warning("Bad prompts YAML %s: %s — using defaults", path, exc)
            return

        for stage_name, stage_data in (data.get("stages") or {}).items():
            if stage_name in self._stages and isinstance(stage_data, dict):
                self._stages[stage_name].update(stage_data)
            else:
                logger.warning("Unknown stage in prompts file: %s", stage_name)

        for block_name, block_text in (data.get("blocks") or {}).items():
            if isinstance(block_text, str):
                self._blocks[block_name] = block_text

        for sub_name, sub_data in (data.get("sub_prompts") or {}).items():
            if sub_name in self._sub_prompts and isinstance(sub_data, dict):
                self._sub_prompts[sub_name].update(sub_data)

        logger.info("Loaded prompt overrides from %s", path)

    def _load_extras(self, spec: dict[str, str]) -> None:
        """Resolve per-stage extra prompts.

        *spec* maps stage names to either a file path or inline text.  When
        the value names an existing file the contents are read; otherwise
        it is used verbatim.  Unknown stage names are warned about and
        dropped so a typo in config.yaml never silently disappears.
        """
        for stage, value in spec.items():
            if stage not in self._stages:
                logger.warning(
                    "prompts.extra_prompts: unknown stage %r — available: %s",
                    stage, ", ".join(sorted(self._stages.keys())),
                )
                continue
            text = str(value).strip()
            if not text:
                continue
            candidate = Path(text).expanduser()
            if candidate.exists() and candidate.is_file():
                try:
                    text = candidate.read_text(encoding="utf-8").strip()
                except OSError as exc:
                    logger.warning(
                        "prompts.extra_prompts[%s]: cannot read %s: %s",
                        stage, candidate, exc,
                    )
                    continue
            self._extras[stage] = text
            logger.info("Loaded extra prompt for stage %r (%d chars)", stage, len(text))

    def _load_bundled_directives(self) -> None:
        """Load AGENTS.md per-stage directives shipped with the package.

        Directives apply to every stage key found in the bundled YAML.  Extra
        prompts supplement these rules; they do not replace AGENTS.md policy.
        """
        if not _AGENTS_DIRECTIVES_PATH.exists():
            return
        try:
            data = (
                yaml.safe_load(_AGENTS_DIRECTIVES_PATH.read_text(encoding="utf-8"))
                or {}
            )
        except yaml.YAMLError as exc:
            logger.warning("agents_directives.yaml parse failed: %s", exc)
            return
        for stage, text in (data.get("stages") or {}).items():
            if text is None:  # explicit disable
                continue
            if isinstance(text, str) and text.strip():
                self._directives[stage] = text.strip()
        logger.debug("Loaded %d AGENTS.md stage directives", len(self._directives))

    def _load_project_agents(
        self,
        agents_path: str | Path | None,
        search_start: str | Path | None,
    ) -> None:
        """Load the authoritative workspace ``AGENTS.md`` when available."""
        path = (
            Path(agents_path).expanduser().resolve()
            if agents_path is not None
            else find_agents_file(search_start)
        )
        if path is None:
            logger.warning(
                "No workspace AGENTS.md found; using bundled stage directives only"
            )
            return
        if not path.is_file():
            logger.warning("Configured AGENTS.md not found: %s", path)
            return
        try:
            raw = path.read_bytes()
            text = raw.decode("utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            logger.warning("Cannot read workspace AGENTS.md %s: %s", path, exc)
            return
        if not text:
            logger.warning("Workspace AGENTS.md is empty: %s", path)
            return
        self._agents_path = path
        self._agents_text = text
        self._agents_bytes = raw
        logger.info("Loaded authoritative workspace rules from %s", path)

    def _append_project_agents(self, user_text: str) -> str:
        if not self._agents_text:
            return user_text
        return (
            f"{user_text}\n\n"
            "## Authoritative Workspace AGENTS.md\n"
            "The following project rules have highest priority within this task. "
            "Additional guidance must not weaken or contradict them.\n\n"
            f"{self._agents_text}"
        )

    # -- primary API ------------------------------------------------------

    def for_stage(
        self,
        stage: str,
        *,
        evolution_overlay: str = "",
        **kwargs: Any,
    ) -> RenderedPrompt:
        """Return a fully rendered prompt for *stage* with variables filled.

        If *evolution_overlay* is provided, it is appended to the user prompt
        so the LLM can learn from prior run lessons.
        """
        entry = self._stages[stage]
        kw = {k: str(v) for k, v in kwargs.items()}
        user_text = _render(entry["user"], kw)
        if evolution_overlay:
            user_text = f"{user_text}\n\n{evolution_overlay}"
        directive = self._directives.get(stage, "")
        if directive:
            user_text = (
                f"{user_text}\n\n"
                "## AGENTS.md Directives\n"
                "_(project research rules — comply strictly)_\n\n"
                f"{directive}"
            )
        extra = self._extras.get(stage, "")
        if extra:
            user_text = (
                f"{user_text}\n\n"
                "## Additional Stage Guidance\n"
                "_(from prompts.extra_prompts in config.yaml)_\n\n"
                f"{extra}"
            )
        user_text = self._append_project_agents(user_text)
        return RenderedPrompt(
            system=_render(entry["system"], kw),
            user=user_text,
            json_mode=entry.get("json_mode", False),
            max_tokens=entry.get("max_tokens"),
        )

    def system(self, stage: str) -> str:
        """Return the raw system prompt template for *stage*."""
        return self._stages[stage]["system"]

    def user(self, stage: str, **kwargs: Any) -> str:
        """Return the rendered user prompt for *stage*."""
        return _render(
            self._stages[stage]["user"],
            {k: str(v) for k, v in kwargs.items()},
        )

    def json_mode(self, stage: str) -> bool:
        return self._stages[stage].get("json_mode", False)

    def max_tokens(self, stage: str) -> int | None:
        return self._stages[stage].get("max_tokens")

    # -- blocks -----------------------------------------------------------

    def block(self, name: str, **kwargs: Any) -> str:
        """Render a reusable prompt block."""
        return _render(
            self._blocks[name],
            {k: str(v) for k, v in kwargs.items()},
        )

    # -- sub-prompts (code repair, etc.) ----------------------------------

    def sub_prompt(self, name: str, **kwargs: Any) -> RenderedPrompt:
        """Return a rendered sub-prompt (e.g. code_repair)."""
        entry = self._sub_prompts[name]
        kw = {k: str(v) for k, v in kwargs.items()}
        user_text = _render(entry["user"], kw)
        return RenderedPrompt(
            system=_render(entry["system"], kw),
            user=self._append_project_agents(user_text),
        )

    # -- debate roles (domain-specific) -----------------------------------

    def debate_roles_hypothesis(self) -> dict[str, dict[str, str]]:
        """Return the hypothesis-stage debate roles for this domain."""
        return {k: dict(v) for k, v in self._debate_hypothesis.items()}

    def debate_roles_analysis(self) -> dict[str, dict[str, str]]:
        """Return the analysis-stage debate roles for this domain."""
        return {k: dict(v) for k, v in self._debate_analysis.items()}

    # -- introspection ----------------------------------------------------

    def stage_names(self) -> list[str]:
        return list(self._stages.keys())

    def has_stage(self, stage: str) -> bool:
        return stage in self._stages

    def extra_prompts(self) -> dict[str, str]:
        """Return a shallow copy of the configured extra-prompt texts.

        Keys are stage names; values are the resolved texts (after any file
        loads).  Useful for the CLI ``info`` subcommand to surface which
        stages carry custom guidance.
        """
        return dict(self._extras)

    def directive(self, stage: str) -> str:
        """Return the bundled AGENTS.md directive for *stage* (or empty str)."""
        return self._directives.get(stage, "")

    def directives(self) -> dict[str, str]:
        """Return a shallow copy of all bundled AGENTS.md directives."""
        return dict(self._directives)

    @property
    def agents_path(self) -> Path | None:
        """Path of the authoritative workspace rules, if discovered."""
        return self._agents_path

    @property
    def agents_sha256(self) -> str:
        """Digest of the loaded workspace rules for run provenance."""
        if not self._agents_bytes:
            return ""
        return sha256(self._agents_bytes).hexdigest()

    @property
    def agents_text(self) -> str:
        """Loaded authoritative workspace rules, or an empty string."""
        return self._agents_text

    @property
    def agents_bytes(self) -> bytes:
        """Original UTF-8 bytes of the workspace rules for exact snapshots."""
        return self._agents_bytes

    def export_yaml(self, path: Path) -> None:
        """Write current prompts (defaults + overrides) to a YAML file."""
        data: dict[str, Any] = {
            "version": "1.0",
            "domain": self._domain,
            "blocks": dict(self._blocks),
            "stages": {k: dict(v) for k, v in self._stages.items()},
            "sub_prompts": {k: dict(v) for k, v in self._sub_prompts.items()},
        }
        path.write_text(
            yaml.dump(data, default_flow_style=False, allow_unicode=True, width=120),
            encoding="utf-8",
        )
