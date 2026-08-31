# BAR-Depth nearest-neighbor matrix

## Scope and audit rule

This audit asks whether BAR-Depth has an algorithmic distinction after removing
repository names, implementation details, and the already validated oracle
measurement.  Sources are restricted to papers, official project pages, and
official code releases.  A method is considered a direct novelty killer when it
learns where to allocate a fixed amount of high-resolution computation for
monocular depth, even if its sensor or merge operator differs from BAR-Depth.

## Mechanism matrix

| Method | Candidate actions | Selection policy | Budget | Merge / prediction | Supervision | Evaluation protocol | Direct implication for BAR-Depth |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Boosting MDE (CVPR 2021) | Tiled RGB patches expanded until their edge density matches the image | Hand-designed content/edge-density filtering and expansion | Runtime/resolution trade-off, but not a frozen `K`-action contract | Learned double-estimation merge transfers high-frequency detail to a consistent base | Merge training; selector itself is heuristic | Scale/shift-invariant high-resolution relative depth and boundary detail | Kills claims that content-adaptive patch selection or edge-density selection is new; must be reproduced on the same 12 actions |
| SaccadeCam (ICCV 2021) | A fixed number of high-resolution optical foveae | Attention decoder trained from top photometric-error regions; greedy coverage chooses foveae | Explicit fixed number of foveae / imaging bandwidth | Foveated RGB is passed to a depth network | Self-supervised stereo photometric signal | Monocular test-time depth with adaptive sensing | Kills a generic “learn an attention map and select Top-K depth regions” contribution, despite using sensor-space rather than post-base refinement |
| PatchFusion (CVPR 2024) | Dense overlapping tiles plus a global coarse prediction | No sparse selector; processes the prescribed tiles | Number of tiles / CAI passes | Learned global-to-local feature-guided fusion and consistency training | Supervised synthetic high-resolution depth | Metric high-resolution depth | Kills “learned local/global fusion” as novelty; BAR-Depth must keep merge fixed and contribute a decision mechanism |
| PatchRefiner (ECCV 2024) | Fixed or sampled high-resolution patches | Patch sampling is for inference/training coverage rather than signed marginal-utility routing | Patch count controls cost | Coarse-to-fine metric-depth refinement | Synthetic-to-real high-resolution training | Metric depth and boundary metrics | Strong accuracy baseline; does not establish harm-aware budgeted selection |
| PRO (ICCV 2025) | A fixed 4x4 grid of patches, grouped during training | No sparse utility selector | One pass per patch; fixed grid at test time | Grouped patch consistency plus bias-free masking | Synthetic training with masked supervision | Scale-aligned zero-shot evaluation on multiple high-resolution datasets | Strong fixed-grid efficiency killer; BAR-Depth must beat its accuracy-latency point or narrowly scope the claim to a frozen backbone/action space |
| Depth Pro (ICLR 2025) | Whole-image multi-scale features | No regional selector | A single fast 2.25-megapixel prediction | Efficient multi-scale ViT dense decoder | Mixed real/synthetic metric-depth training | Native metric depth and dedicated boundary metrics | Direct full-image high-resolution Pareto killer; also prevents DAV2-S scale-aligned results from being described as metric depth |
| PatchRefiner V2 (ICLR 2026) | Grid, shifted-grid, or `rN` random patches | Fixed grid or random sampling, not signed utility | Patch mode and patch count | Lightweight refiner, guided denoising, noisy pretraining, SSIGM | Synthetic-to-real training | Metric high-resolution depth | Kills a generic “lighter patch network” contribution and provides a stronger efficiency reference |
| URGT (CVPR 2026) | All image patches augmented with coarse depth/normal priors | GridMix samples grids during training; inference is unified multi-patch processing | Patch grid / token count | Cross-patch attention in a shared geometry transformer | High-resolution depth and normal supervision | Metric and relative depth/normal benchmarks | Kills “multi-patch global reasoning” as novelty; sparse utility routing remains distinct only if it wins at matched latency |
| InfiniDepth (CVPR 2026) | Continuous 2D query coordinates | Queries arbitrary coordinates but does not learn a fixed-budget signed refinement-action selector | Number/resolution of coordinate queries | Neural implicit depth field | Relative and metric depth training | Arbitrary-resolution depth | Kills arbitrary-resolution output as a claim; coordinate query allocation is a neighboring formulation that the novelty discussion must address |

## Primary sources

1. Miangoleh et al., “Boosting Monocular Depth Estimation Models to
   High-Resolution via Content-Adaptive Multi-Resolution Merging,” CVPR 2021,
   [paper](https://openaccess.thecvf.com/content/CVPR2021/papers/Miangoleh_Boosting_Monocular_Depth_Estimation_Models_to_High-Resolution_via_Content-Adaptive_Multi-Resolution_CVPR_2021_paper.pdf),
   [official code](https://github.com/compphoto/BoostingMonocularDepth).
2. Tilmon et al., “SaccadeCam: Adaptive Visual Attention for Monocular Depth
   Sensing,” ICCV 2021,
   [paper](https://openaccess.thecvf.com/content/ICCV2021/papers/Tilmon_SaccadeCam_Adaptive_Visual_Attention_for_Monocular_Depth_Sensing_ICCV_2021_paper.pdf),
   [project](https://focus.ece.ufl.edu/research/2021/saccadecam/).
3. Li et al., “PatchFusion,” CVPR 2024,
   [paper](https://openaccess.thecvf.com/content/CVPR2024/html/Li_PatchFusion_An_End-to-End_Tile-Based_Framework_for_High-Resolution_Monocular_Metric_Depth_CVPR_2024_paper.html).
4. Kwon and Kim, “One Look is Enough: Seamless Patchwise Refinement for
   Zero-Shot Monocular Depth Estimation on High-Resolution Images,” ICCV 2025,
   [paper](https://openaccess.thecvf.com/content/ICCV2025/html/Kwon_One_Look_is_Enough_Seamless_Patchwise_Refinement_for_Zero-Shot_Monocular_ICCV_2025_paper.html).
5. Bochkovskii et al., “Depth Pro,” ICLR 2025,
   [paper](https://openreview.net/forum?id=aueXfY0Clv),
   [official project](https://machinelearning.apple.com/research/depth-pro).
6. Li et al., “PatchRefiner V2,” ICLR 2026,
   [paper](https://arxiv.org/abs/2501.01121),
   [official code](https://github.com/zhyever/PatchRefinerV2).
7. Cui et al., “Any Resolution Any Geometry: From Multi-View To Multi-Patch,”
   CVPR 2026,
   [paper](https://openaccess.thecvf.com/content/CVPR2026/html/Cui_Any_Resolution_Any_Geometry_From_Multi-View_To_Multi-Patch_CVPR_2026_paper.html).
8. Yu et al., “InfiniDepth,” CVPR 2026,
   [paper](https://arxiv.org/abs/2601.03252).

## Surviving, falsifiable distinction

The oracle measurement is not a contribution by itself.  A point-estimate
regressor followed by Top-K is also insufficient because learned allocation of
high-resolution attention for depth already exists.  The only currently
plausible distinction is:

> From a single cheap base pass, predict a calibrated distribution of the
> **signed** marginal error reduction of each optional refinement action, then
> select or abstain under an explicit latency budget and a preregistered bound
> on harmful actions.

This distinction remains conditional.  It must outperform a point-utility
ranking head, SaccadeCam-style attention, Boosting MDE selection, base-gradient
selection, and matched-latency whole-image inference.  Otherwise the result is
`STOP_NOVELTY` or `STOP_KILLER_BASELINE`, not a paper method.
