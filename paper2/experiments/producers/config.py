"""Loading and consistency checks for the frozen minimal-probe configuration."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from experiments.mna import DIODE_RC_INSTANCES, RING_INSTANCES


def load_minimal_probe_config(path: Path) -> dict[str, Any]:
    """Load the JSON-compatible YAML configuration and validate ring declarations."""

    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("schema_version") != 1:
        raise ValueError("unsupported minimal-probe configuration schema")
    ring_payload = payload.get("ring_canary")
    if not isinstance(ring_payload, dict):
        raise ValueError("ring_canary configuration is missing")
    configured_instances = ring_payload.get("instances")
    declared_instances = [
        {
            **asdict(instance),
            "initial_voltages": list(instance.initial_voltages),
        }
        for instance in RING_INSTANCES
    ]
    if configured_instances != declared_instances:
        raise ValueError("config ring instances differ from executable declarations")
    diode_payload = payload.get("diode_rc_sweep")
    if not isinstance(diode_payload, dict):
        raise ValueError("diode_rc_sweep configuration is missing")
    configured_diode_instances = diode_payload.get("instances")
    declared_diode_instances = [asdict(instance) for instance in DIODE_RC_INSTANCES]
    if configured_diode_instances != declared_diode_instances:
        raise ValueError(
            "config diode-RC instances differ from executable declarations"
        )
    reference = payload.get("test_reference")
    if not isinstance(reference, dict) or reference.get("rigorous") is not False:
        raise ValueError("Decimal test reference must be declared non-rigorous")
    return payload
