# Response to Review Round 6

## Overall status

We agree that the work is not yet a Paper Candidate. This round addressed the two Step003 P0 data-branch defects and executed the preregistered real-data feasibility gate. It did not implement the remaining model, objective, seed-aware inference, OOF-cache, or intervention-corpus items. Claim-F remains `UNVERIFIED`; Claim-M is stopped for the current NYUv2+KITTI local-inference branch.

## Dataset-branch corrections

1. We removed the inferential `GO_LOCAL_CLAIMS_NYUV2_VKITTI2` branch. Only NYUv2+KITTI can pass the two-dataset gate. VKITTI2 is now always `synthetic_structured_auxiliary_only`; its five base scenes cannot be inflated through weather, viewpoint, or camera clones.
2. The VKITTI2 adapter no longer accepts an external frame index. It derives the source solely by scanning the official extracted RGB/depth/class/instance/textgt hierarchy, requires the complete scene/variation/camera grid and aligned contiguous frame enumeration, and binds every pilot row to a canonical full-source count and SHA256. A selected subset cannot masquerade as the canonical source.
3. Step003 commands are importable `python -m` entrypoints. The clean-deployment pytest temporary directory now lives below the scheduler-created `.local-deps` root.

The associated implementation is commit `435240e18fd4fbcc4685b2a5ef43e9824f5d4636`. Local regression checks and the remote CPU queue passed Ruff, Black, and 97 paper1 tests.

## Real Step003 feasibility result

We used only official-training material and did not access either official benchmark test split. The fixed pilot contains 500 NYUv2 and 500 KITTI images, split 300/100/100 per dataset with scene/drive-connected components kept disjoint.

| Dataset | Images | Eligible images | Eligible depth-separated pairs | Independent eligible clusters | Gate |
| --- | ---: | ---: | ---: | ---: | --- |
| NYUv2 | 500 | 500 | 105779 | 156 | PASS |
| KITTI | 500 | 0 | 0 | 0 | FAIL |

The frozen KITTI RGB source has no trusted local instance-mask or local depth oracle under the current adapter contract. The formal decision is therefore `STOP_TWO_DATASET_CLAIM`; KITTI is limited to `image_level_sensitivity_only`. The scheduler blocked conditional detectability, so no power artifact, GPU job, Step005 job, or intervention-corpus build was launched. An independent replay produced byte-identical manifest, split-audit, coverage CSV, and coverage JSON hashes.

Portable artifacts are [`annotation_coverage.json`](../results/covol/annotation_coverage.json), [`annotation_coverage.csv`](../results/covol/annotation_coverage.csv), and [`step003_feasibility_gate.json`](../results/covol/step003_feasibility_gate.json).

## Claims and remaining objections

This negative gate validates the reviewer’s objection that VKITTI2 cannot rescue formal two-dataset inference. It does not establish that the routing problem or Main-PR mechanism is false: only the current second-dataset oracle contract failed. Conversely, the NYUv2 pass cannot support a cross-domain Claim-M by itself.

The other Round-6 P0 items remain open, including full-crop-consistent region weighting, retention lower-confidence gating, test-retention stopping, seed×cluster inference, auditable entity-level OOF caches, PyTorch D0/D1 and router training, and the core intervention builder. We will not implement those downstream components on this branch until the two-real-dataset feasibility decision is explicitly reopened with a compliant outdoor dataset or the paper scope is formally narrowed.
