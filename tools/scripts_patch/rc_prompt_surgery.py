"""Step-4 prompt-bank surgery: add baseline_reproduce, strip paper stages.

Modifies:
  - prompts/ml.py      : insert baseline_reproduce key; remove paper keys
  - prompts/hep.py     : insert baseline_reproduce key; remove paper keys
  - prompts/biology.py : drop STAGES["paper_outline"] override; fix docstring
  - prompts/shared.py  : drop 7 paper _DEFAULT_BLOCKS

Idempotent: skips a file if its surgery marker is already applied.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROMPTS = ROOT / "researchclaw" / "prompts"


ML_BLOCK = r'''    # ── Phase C: Baseline Reproduction ─────────────────────────────────────
    "baseline_reproduce": {
        "system": (
            "You are a rigorous reproduction scientist. Before any new method "
            "is proposed, you confirm whether a specific defect in the strongest "
            "existing baseline is real, algorithmic, and worth attacking.\n"
            "Your analysis must:\n"
            "1. MINIMAL: design the SMALLEST experiment that exposes the defect.\n"
            "2. PRECISE: target exactly one baseline and one concrete defect.\n"
            "3. HONEST: distinguish an algorithmic limitation from an engineering / "
            "configuration issue (a wrong hyperparameter or an implementation bug "
            "does NOT count as a research defect).\n"
            "4. FALSIFIABLE: state the numeric symptom and the criteria that would "
            "confirm or refute the defect.\n"
            "{domain_context}"
        ),
        "user": (
            "From the literature synthesis below, identify the STRONGEST baseline "
            "method for the target task and the specific, concrete defect that "
            "justifies improving on it.\n\n"
            "Return a JSON object with EXACTLY these keys:\n"
            "- baseline_name: the specific baseline method (+ version / config)\n"
            "- claimed_defect: the concrete defect being claimed\n"
            "- defect_type: algorithmic or engineering\n"
            "- symptom_metric: the metric that exposes the defect\n"
            "- reproduction_plan: the minimal experiment that demonstrates it\n"
            "- success_criteria: the numeric evidence that confirms the defect\n"
            "- code: a single self-contained Python script (def main()) that "
            "reproduces the defect on small / synthetic data, prints metric lines "
            "as 'name: value', and finishes within the sandbox time budget\n\n"
            "Synthesis:\n{synthesis}"
        ),
        "max_tokens": 8192,
        "json_mode": True,
    },
'''

HEP_BLOCK = r'''    # ── Phase C: Baseline Reproduction ─────────────────────────────────────
    "baseline_reproduce": {
        "system": (
            "You are a rigorous phenomenology reproduction scientist. Before "
            "any new BSM scenario is proposed, you confirm whether a specific "
            "defect in the strongest existing baseline is real, physical, and "
            "worth attacking.\n"
            "Your analysis must:\n"
            "1. MINIMAL: design the SMALLEST parameter scan or recast that "
            "exposes the defect.\n"
            "2. PRECISE: target exactly one baseline scenario and one concrete "
            "defect.\n"
            "3. HONEST: distinguish a physical limitation from a numerical / "
            "engineering issue (a grid-resolution artifact, wrong coupling, or "
            "an implementation bug does NOT count as a research defect).\n"
            "4. FALSIFIABLE: state the numeric observable and the threshold that "
            "would confirm or refute the defect.\n"
            "{domain_context}"
        ),
        "user": (
            "From the literature synthesis below, identify the STRONGEST baseline "
            "scenario for the target process and the specific, concrete defect "
            "that justifies improving on it.\n\n"
            "Return a JSON object with EXACTLY these keys:\n"
            "- baseline_name: the baseline model / scenario (+ version / config)\n"
            "- claimed_defect: the concrete defect being claimed\n"
            "- defect_type: physical or engineering\n"
            "- symptom_observable: the observable (cross section, relic density, "
            "exclusion bound) that exposes the defect\n"
            "- reproduction_plan: the minimal scan / recast that demonstrates it\n"
            "- success_criteria: the numeric evidence that confirms the defect\n"
            "- code: a single self-contained Python script (def main()) that "
            "reproduces the defect with analytical formulas, prints metric lines "
            "as 'name: value', and finishes within the sandbox time budget\n\n"
            "Synthesis:\n{synthesis}"
        ),
        "max_tokens": 8192,
        "json_mode": True,
    },
'''

PAPER_COMMENT = "\n    # ── Phase G: Paper Writing ─"


def surgery_ml_hep(fname: str, block: str) -> None:
    p = PROMPTS / fname
    s = p.read_text(encoding="utf-8")
    orig = s
    if '"baseline_reproduce"' in s:
        print(f"{fname}: baseline_reproduce already present, skipping")
        return
    anchor = '    "hypothesis_gen": {'
    assert s.count(anchor) == 1, f"{fname}: hypothesis_gen anchor not unique ({s.count(anchor)})"
    s = s.replace(anchor, block + anchor, 1)
    # Remove paper section: from Phase G comment to dict close.
    assert PAPER_COMMENT in s, f"{fname}: paper comment missing"
    idx_paper = s.index(PAPER_COMMENT)
    if fname == "ml.py":
        tail_marker = "\n}\n\n# Public name"
        idx_tail = s.index(tail_marker, idx_paper)
    else:
        # hep.py ends with the dict close
        idx_tail = s.rindex("\n}")
    s = s[:idx_paper] + s[idx_tail:]
    # Normalize 3+ blank lines to 2
    s = re.sub(r"\n{4,}", "\n\n\n", s)
    if s == orig:
        raise RuntimeError(f"{fname}: no change produced")
    p.write_text(s, encoding="utf-8")
    print(f"{fname}: baseline_reproduce inserted; paper section removed")


def surgery_biology() -> None:
    p = PROMPTS / "biology.py"
    s = p.read_text(encoding="utf-8")
    orig = s
    # 1. Drop STAGES["paper_outline"] override block
    marker = '# ── paper_outline'
    if marker in s:
        idx_start = s.index("\n\n\n" + marker)
        idx_end = s.index("\n\n\n# ---", idx_start)
        s = s[:idx_start] + s[idx_end:]
    # 2. Fix docstring: five -> four, drop paper_outline mention
    old_doc = (
        "five whose prose is biology-flavoured: ``hypothesis_gen``,\n"
        "``experiment_design``, ``code_generation``, ``result_analysis`` and\n"
        "``paper_outline``. The overrides keep the ML bank's exact placeholder set,\n"
        "``json_mode`` flag and ``max_tokens`` budget so the parity contract in\n"
        ":mod:`tests.test_hep_prompt_hygiene` (and any future strict parity test)\n"
        "holds without modification."
    )
    new_doc = (
        "four whose prose is biology-flavoured: ``hypothesis_gen``,\n"
        "``experiment_design``, ``code_generation`` and ``result_analysis``.\n"
        "The overrides keep the ML bank's exact placeholder set, ``json_mode``\n"
        "flag and ``max_tokens`` budget so the parity contract holds without\n"
        "modification."
    )
    assert old_doc in s, "biology docstring anchor missing"
    s = s.replace(old_doc, new_doc, 1)
    # 3. Fix "overwrite five stages" comment
    s = s.replace(
        "# Stage bank ── start from ML and overwrite five stages",
        "# Stage bank ── start from ML and overwrite four stages",
    )
    s = re.sub(r"\n{4,}", "\n\n\n", s)
    if s == orig:
        raise RuntimeError("biology.py: no change produced")
    p.write_text(s, encoding="utf-8")
    print("biology.py: paper_outline override removed; docstring fixed")


PAPER_BLOCKS = [
    "title_guidelines",
    "abstract_structure",
    "writing_structure",
    "academic_style_guide",
    "narrative_writing_rules",
    "anti_hedging_rules",
    "anti_repetition_rules",
]


def surgery_shared() -> None:
    p = PROMPTS / "shared.py"
    s = p.read_text(encoding="utf-8")
    orig = s
    for name in PAPER_BLOCKS:
        key = f'    "{name}": ('
        if key not in s:
            print(f"shared.py: {name} already absent, skipping")
            continue
        idx_start = s.index(key)
        # Find the closing '    ),' line of this block: next top-level key or dict close
        m = re.search(r'\n    "[a-z_]+": \(|\n}', s[idx_start + 1:])
        assert m, f"shared.py: cannot find end of {name}"
        idx_end = idx_start + 1 + m.start()
        s = s[:idx_start] + s[idx_end:]
    s = re.sub(r"\n{4,}", "\n\n\n", s)
    if s == orig:
        raise RuntimeError("shared.py: no change produced")
    p.write_text(s, encoding="utf-8")
    print(f"shared.py: removed {len(PAPER_BLOCKS)} paper blocks")


def main() -> None:
    surgery_ml_hep("ml.py", ML_BLOCK)
    surgery_ml_hep("hep.py", HEP_BLOCK)
    surgery_biology()
    surgery_shared()


if __name__ == "__main__":
    main()
