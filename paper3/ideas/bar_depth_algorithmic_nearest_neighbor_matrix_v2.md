# BAR-Depth algorithmic nearest-neighbor matrix v2

## Scope

This matrix audits the surviving decision mechanism, not patch-depth backbones.
It asks whether point signed-utility prediction, cost-aware selection, abstention,
and train-only harm calibration already follow from generic selective prediction,
learning-to-defer, risk-control, or spatial adaptive-inference algorithms.

| Work | Action / expert | Cost model | Utility or risk | Abstention | Calibration guarantee | Training target | Solver / decision | Real latency evidence | Consequence for BAR and primary locator |
|---|---|---|---|---|---|---|---|---|---|
| [SelectiveNet, ICML 2019](https://proceedings.mlr.press/v97/geifman19a.html) | Accept or reject one whole prediction | Target coverage, not local action cost | Selective risk over covered examples | Yes | Post-training coverage calibration; not BAR's net-harm event | Joint prediction, selection, and auxiliary heads | Coverage-constrained risk minimization | Fast single-network regression experiments, not spatial patch timing | Already covers learned regression rejection. BAR must not claim novelty for a selection head or abstention. Paper p.2 Eq. (1), p.3 Eq. (2). |
| [Learn then Test, 2022](https://arxiv.org/abs/2110.01052) | Choose a calibrated parameter from a finite decision family | Arbitrary parameter-dependent cost can enter the loss | User-defined bounded risk | A parameter can be rejected as unsafe | Finite-sample family-wise risk control | Black-box predictor; no refit required | Multiple testing over a frozen parameter grid | Application-dependent | Directly covers train/calibration-only risk selection over 101 thresholds. BAR's uncorrected per-threshold Clopper--Pearson search is weaker, not novel. Paper pp.3--5, Algorithm 1 and Proposition 3. |
| [Conformal Decision Theory, 2024](https://arxiv.org/abs/2310.05921) | Tune an autonomous decision or safe-backup controller | Encoded in decision loss | Direct decision loss, including non-i.i.d. online risk | Safe backup is explicit | Pathwise empirical-risk bounds and exchangeable offline corollary | Prediction model can remain fixed | Feedback update of controller parameter | Robotics/manufacturing demonstrations | Covers calibration of decisions rather than prediction sets. A BAR threshold controller alone is an application. Paper p.3, Theorem 1, Eqs. (5)--(6); p.4 Eq. (9). |
| [Regression with Multi-Expert Deferral, ICML 2024](https://proceedings.mlr.press/v235/mao24d.html) | Predict locally or defer a regression output to one of multiple experts | Instance- and label-dependent bounded costs | Regression loss plus expert cost | Yes | H-consistency bounds, not finite-sample harm control | Single-stage and two-stage surrogate losses | Cost-sensitive expert choice | Accuracy/cost experiments; no spatial patch latency | Covers regression expert routing with heterogeneous costs. BAR needs a genuinely set-coupled local-action mechanism, not a renamed expert deferral loss. Official paper Secs. 2--4 and PMLR pp. 34738--34759. |
| [Post-hoc Estimators for Learning to Defer, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/bc8f76d9caadd48f77025b1c889d2e2d-Abstract-Conference.html) | Base prediction or costly model/human expert | Fixed plus example-dependent expert error cost | Base error versus expert error and cost | Yes | Surrogate/excess-risk guarantees, not finite-sample event control | Post-hoc rejector predicts whether expert error is lower than base error | Threshold correction or learned rejector | FLOPs/accuracy adaptive-inference curves | Closely covers predicting whether an extra forward is beneficial. Per-patch signed utility plus a threshold is not enough novelty. Paper p.3 Eqs. (1)--(3), p.6 Eqs. (13)--(15). |
| [LASNet, NeurIPS 2022](https://proceedings.neurips.cc/paper_files/paper/2022/hash/ef472869c217bf693f2d9bbde66a6b07-Abstract-Conference.html) | Activate coarse spatial feature patches per block | Predicted hardware latency using device, layer, granularity, and activation rate | Task loss with compute regularization | Implicitly skips spatial computation | No statistical harm guarantee | Binary spatial masks with distillation and sparsity terms | Masker plus latency-guided granularity/scheduling search | V100, GTX1080, Nano, and TX2 measured latency | Already covers latency-aware spatial compute allocation. BAR must compare formal latency and cannot call unit-cost Top-K a new allocator. Paper Sec. 3.1 and Sec. 3.3, especially `l=G(H,P,S,r)`. |
| [LookWhere?, NeurIPS 2025](https://proceedings.neurips.cc/paper_files/paper/2025/hash/7dd74dcef03c8f88a58d18a9d49d7a10-Abstract-Conference.html) | Low-resolution selector chooses sparse high-resolution patches for an extractor | Fixed sparse patch/token budget | Self-supervised teacher representation approximation | Unselected patches are skipped | None | Joint what/where self-supervised distillation | Learned selector-extractor sparse representation | Reports FLOPs and wall-time speedups | Directly covers low-res-to-high-res learned patch selection without task labels. BAR needs more than supervised utility scoring. Paper Secs. 3--4 and official abstract. |
| [GFNet, NeurIPS 2020 / TPAMI](https://arxiv.org/abs/2010.05300) | Low-resolution global glance followed by sequential high-resolution focus patches | Number of focus steps / patches | Classification loss and policy reward | Early exit variants in later GFNet formulation | None | Recurrent patch locator plus classifier | Sequential learned locator | Mobile and GPU latency reported in the extended work | Covers coarse global features choosing fine regions under a patch budget. Point score plus fixed K is not novel. Paper Sec. 3 and official [`GFNet-Pytorch`](https://github.com/blackfeather-wang/GFNet-Pytorch) `network.py`. |
| [AdaFocus, ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Wang_Adaptive_Focus_for_Efficient_Video_Recognition_ICCV_2021_paper.html) | Lightweight full-frame network localizes patches for a heavy network | Patch count and optional frame skipping | Recognition reward minus efficiency pressure | Can skip low-value frames | None | Reinforcement-learned recurrent spatial policy | Sequential decision policy, parallel offline execution | Reports practical GPU efficiency across five datasets | Covers learned task-utility patch localization and computation skipping. BAR needs signed net-harm control that beats this generic policy class. Paper Secs. 3.2--3.4. |
| [DynamicViT, NeurIPS 2021](https://proceedings.neurips.cc/paper_files/paper/2021/hash/747d3443e319a22747fbb873e8b2f9f2-Abstract.html) | Keep or prune tokens at multiple layers | Target token-retention ratios / FLOPs | Classification and distillation losses | Token rejection is built in | None | Lightweight token-importance predictor | Progressive differentiable masking | Reports throughput gains above 40% | Covers learned spatial importance scoring and hardware-friendly sparse execution. BAR cannot claim token/region scoring itself. Paper Sec. 3, especially the prediction module and attention masking. |
| [SkipNet, ECCV 2018](https://openaccess.thecvf.com/content_ECCV_2018/html/Xin_Wang_SkipNet_Learning_Dynamic_ECCV_2018_paper.html) | Execute or skip each residual block per input | Number of executed blocks | Classification reward with computation reward | Skips computation, not prediction | None | Hybrid supervised and reinforcement policy objective | Sequential binary routing | Reports 30--90% computation reduction | Covers cost-aware dynamic routing from prior activations. BAR's base-feature gate is not a new routing primitive. Paper Sec. 3.2 and policy objective. |
| [FrugalML, NeurIPS 2020](https://proceedings.neurips.cc/paper/2020/hash/789ba2ae4d335e8a2ad283a3f7effced-Abstract.html) | Select a base API and conditionally call a second heterogeneous API | Explicit per-expert monetary cost and user budget | Expected accuracy under expected cost | Stops after the base API when confident | Optimization guarantee, no calibrated harm probability | API label/quality-conditioned performance estimates | Sparse sequential strategy under a budget | Monetary cost; training/runtime also reported | Strictly stronger than BAR's current homogeneous-cost claim as a budgeted solver. Paper p.4 Definition 1, Eq. (3.1). |
| [SaccadeCam, ICCV 2021](https://openaccess.thecvf.com/content/ICCV2021/html/Tilmon_SaccadeCam_Adaptive_Visual_Attention_for_Monocular_Depth_Sensing_ICCV_2021_paper.html) | Learned attention chooses a fixed number of high-resolution foveae for monocular depth | Fovea count and sensor bandwidth | Downstream depth error | Unobserved high-resolution regions are omitted | None | Attention policy for foveated depth sensing | Top locations / foveated acquisition | Hardware/sensor-motivated efficiency evaluation | Depth-specific killer for learned Top-K high-resolution regions. BAR cannot claim the allocation pattern as novel. Paper Secs. 3--4. |

## Coverage result

The current v2 proposal has no surviving algorithmic component that is both
necessary and uncovered:

1. pointwise prediction of whether an extra expert is beneficial is covered by
   post-hoc deferral and multi-expert regression;
2. train-only threshold selection with an explicit risk level is covered more
   generally by Learn then Test and Conformal Decision Theory;
3. low-resolution features selecting high-resolution spatial computation are
   covered by GFNet, AdaFocus, SaccadeCam, LASNet, and LookWhere;
4. heterogeneous budgeted routing is handled more generally by FrugalML, while
   the current BAR probe has only identical unit costs.

Therefore the falsifiable statement for the **current** mechanism is:

> If BAR uses independent point utility scores followed by Top-K and a calibrated
> scalar abstention threshold, its algorithm is an application-level composition
> of existing deferral, risk calibration, and spatial adaptive inference.

The audit decision is `STOP_NOVELTY_CURRENT_POINT_THRESHOLD_ROUTER`; W08 under
`router_probe_v2.json` must not run as a paper-method experiment.

## Non-equivalent opportunity retained for one mechanism probe

The empirical problem is not disproved: harmful patch actions and oracle margin
remain real under the frozen canary. A different algorithm hypothesis may be
tested only if it models the **joint selected-set utility distribution** rather
than calibrating a scalar point-score threshold. The required killer comparison
is:

> A budget-conditioned joint residual model must produce a lower confidence
> bound for `sum_{i in S} u_i` after adaptive subset selection and improve raw
> signed utility at the same image-level harm bound over (i) point Top-K,
> (ii) Learn-then-Test calibration of the same point scores, and (iii) direct
> conformal decision calibration.

This is a Research Opportunity hypothesis, not a novelty claim. If the joint
model reduces to a threshold on independent point scores, or fails to beat the
three generic killers, the direction receives final `STOP_NOVELTY`.
