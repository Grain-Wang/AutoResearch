# paper1_new local repository rules

These rules apply to all work under `paper1_new/` and supplement the repository-root `AGENTS.md`.

## Canonical project location

- Active project: BlockStamp-Cert / Proof-Carrying SPICE research opportunity.
- Active project root: `paper1_new/`.
- Canonical remote write branch: `paper1`.
- `paper1/` contains the stopped CoVoL project history and must not be overwritten or repurposed.

## Branch isolation

- All new code, experiments, results, steps, reviewer feedback, author responses, and documentation for this project must be committed to the remote `paper1` branch.
- The remote `paper2` branch is maintained by another workflow/conversation.
- Work under `paper1_new/` may read a specifically frozen `paper2` commit for provenance or comparison, but must not push, reset, force-update, revert, delete, or otherwise modify `paper2`.
- Never use an implicit `git push` when the destination could be ambiguous. The intended remote ref for this project is `refs/heads/paper1`.
- There is no automatic synchronization with `paper2`. Any later import from `paper2` requires an explicit source commit, source tree hash, and diff audit.

## Active paths

- Ideas: `paper1_new/ideas/`
- Research notes: `paper1_new/research/`
- Steps: `paper1_new/steps/`
- Experiments: `paper1_new/experiments/`
- Tests: `paper1_new/tests/`
- Results: `paper1_new/results/`
- Reviews: `paper1_new/responce_from_reviewer/review_round*.md`
- Responses: `paper1_new/responce_from_reviewer/response_round*.md`

Review numbering is local to BlockStamp-Cert and must not be mixed with the historical CoVoL review numbers in `paper1/responce_from_reviewer/`.

## Migration provenance

The initial project snapshot came from a frozen `paper2` subtree. See `MIGRATION.md` and `import_manifest.json`. Historical files may therefore contain old `paper2/...` paths or references to the source branch; preserve those when they describe historical facts. New executable instructions and new artifacts must use the current `paper1_new/` path and `paper1` branch.

## Execution convention

For modules that retain the imported top-level `experiments` package layout, run from the repository root with:

```bash
PYTHONPATH=paper1_new python -m experiments.<module>
```

New outputs must be written under `paper1_new/` unless the root `AGENTS.md` explicitly requires otherwise.
