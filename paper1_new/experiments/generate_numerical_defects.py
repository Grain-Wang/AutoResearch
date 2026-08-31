"""Generate a deterministic ill-conditioned passive-MNA defect canary."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path


def generate_cases() -> list[dict[str, str]]:
    """Return natural conditioning cases with small residual and large state error.

    The system diag(1, epsilon) x = (1, epsilon) is the nodal equation of two
    uncoupled unit-voltage Norton branches with conductances 1 and epsilon.  A loose
    residual test may accept x_hat=(1,0), although the exact second voltage is one.
    """
    cases: list[dict[str, str]] = []
    tube_radius = 1e-3
    for exponent in range(5, 17):
        epsilon = 10.0**-exponent
        for precision in ("float32", "float64"):
            residual = epsilon
            forward_error = 1.0
            threshold = 1e-5
            cases.append(
                {
                    "case_id": f"gmin_1e-{exponent}_{precision}",
                    "mechanism": "weak_conductance_conditioning",
                    "center_precision": precision,
                    "epsilon_siemens": f"{epsilon:.17g}",
                    "condition_estimate": f"{1.0 / epsilon:.17g}",
                    "normalized_residual": f"{residual:.17g}",
                    "residual_threshold": f"{threshold:.17g}",
                    "producer_converged": str(residual <= threshold).lower(),
                    "forward_error_inf": f"{forward_error:.17g}",
                    "declared_tube_radius": f"{tube_radius:.17g}",
                    "certificate_verdict": "REJECT_ROOT_OUTSIDE_TUBE",
                }
            )
    return cases


def write_cases(output: Path) -> None:
    """Write all cases without filtering accepted or rejected rows."""
    rows = generate_cases()
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args()
    write_cases(arguments.output)


if __name__ == "__main__":
    main()
