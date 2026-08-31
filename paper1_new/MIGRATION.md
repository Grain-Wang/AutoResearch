# BlockStamp-Cert migration record

## Canonical location

- **Active Git branch:** `paper1`
- **Active project root:** `paper1_new/`
- **Archived previous project:** `paper1/` (CoVoL history; do not overwrite)
- **Source snapshot branch:** `paper2` (read-only for this workflow)

## Snapshot provenance

The initial `paper1_new/` tree was copied byte-for-byte from:

- source branch: `paper2`
- source commit: `85e762a5ef9a2b82a97064abd72435982afe34f5`
- source path: `paper2/`
- source tree SHA: `6df1a6c29389c546d291122bb16d391a943e788f`

It was imported onto:

- target branch: `paper1`
- target base commit: `c12f5060a724e20d9dbe5852741dce8df81ba4ad`
- initial import commit: `c18fe9be738379b053acd4ef0b02f8969fb1e88d`
- target path: `paper1_new/`

The import commit was constructed by attaching the exact source subtree under the new path, so the source `paper2/` tree and the imported `paper1_new/` tree had the same Git tree SHA before path-specific documentation edits.

## Branch isolation rule

From this migration onward, this workflow must only write to the remote `paper1` branch. The remote `paper2` branch belongs to a separate workflow/conversation and must not be pushed, reset, reverted, deleted, or otherwise modified here.

This is a one-time snapshot import, not automatic synchronization. Later changes made on `paper2` are not automatically copied into `paper1_new/`; any future import must freeze an explicit source commit and perform a new diff audit.

## Active paths

New BlockStamp-Cert work in this workflow uses:

- ideas: `paper1_new/ideas/`
- research notes: `paper1_new/research/`
- steps: `paper1_new/steps/`
- experiments: `paper1_new/experiments/`
- tests: `paper1_new/tests/`
- results: `paper1_new/results/`
- reviewer feedback: `paper1_new/responce_from_reviewer/review_round*.md`
- author responses: `paper1_new/responce_from_reviewer/response_round*.md`

Historical files copied from the source snapshot may still mention `paper2`, the old source branch, or old paths. Those occurrences are provenance/history unless a current executable instruction explicitly says otherwise.
