# 2026 CCF-A Depth Estimation Reference Papers

This folder contains 30 full/regular papers from 2026 CCF-A conferences:

- CVPR 2026: 26 papers from the official CVF Open Access proceedings.
- AAAI 2026: 4 papers from the official AAAI proceedings.

The shortlist is optimized for the research direction **depth estimation with VLMs / multimodal
foundation models**. Selection priority is:

1. language-, prompt-, or VLM-conditioned depth and geometry;
2. generalizable, metric, zero-shot, or foundation-model depth estimation;
3. algorithmic work exposing important failure modes such as boundaries, transparency,
   temporal inconsistency, dynamic scenes, and camera/domain shift.

Sensor-specific and downstream papers were excluded unless they contribute a mechanism useful
for general depth estimation. Workshop, demo, short, and non-2026 papers are excluded.

## Tier A: VLM, language, prompts, and unified geometry

1. [Iris: Integrating Language into Diffusion-based Monocular Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Zeng_Iris_Integrating_Language_into_Diffusion-based_Monocular_Depth_Estimation_CVPR_2026_paper.html)
2. [TR2M: Transferring Monocular Relative Depth to Metric Depth with Language Descriptions and Dual-Level Scale-Oriented Contrast](https://openaccess.thecvf.com/content/CVPR2026/html/Cui_TR2M_Transferring_Monocular_Relative_Depth_to_Metric_Depth_with_Language_CVPR_2026_paper.html)
3. [Zero-Shot Depth Completion with Vision-Language Model](https://openaccess.thecvf.com/content/CVPR2026/html/Yan_Zero-Shot_Depth_Completion_with_Vision-Language_Model_CVPR_2026_paper.html)
4. [PromptDepth: Efficient and Promptable Geometric 3D Vision Model for Embodied Intelligence](https://openaccess.thecvf.com/content/CVPR2026/html/Wang_PromptDepth_Efficient_and_Promptable_Geometric_3D_Vision_Model_for_Embodied_CVPR_2026_paper.html)
5. [G2VLM: Geometry Grounded Vision Language Model with Unified 3D Reconstruction and Spatial Reasoning](https://openaccess.thecvf.com/content/CVPR2026/html/Hu_G2VLM_Geometry_Grounded_Vision_Language_Model_with_Unified_3D_Reconstruction_CVPR_2026_paper.html)
6. [Grounded 3D-Aware Spatial Vision-Language Modeling](https://openaccess.thecvf.com/content/CVPR2026/html/Cheng_Grounded_3D-Aware_Spatial_Vision-Language_Modeling_CVPR_2026_paper.html)
7. [VLM-3R: Vision-Language Models Augmented with Instruction-Aligned 3D Reconstruction](https://openaccess.thecvf.com/content/CVPR2026/html/Fan_VLM-3R_Vision-Language_Models_Augmented_with_Instruction-Aligned_3D_Reconstruction_CVPR_2026_paper.html)
8. [SpatialStack: Layered Geometry-Language Fusion for 3D VLM Spatial Reasoning](https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_SpatialStack_Layered_Geometry-Language_Fusion_for_3D_VLM_Spatial_Reasoning_CVPR_2026_paper.html)
9. [SpaceMind: Camera-Guided Modality Fusion for Spatial Reasoning in Vision-Language Models](https://openaccess.thecvf.com/content/CVPR2026/html/Zhao_SpaceMind_Camera-Guided_Modality_Fusion_for_Spatial_Reasoning_in_Vision-Language_Models_CVPR_2026_paper.html)
10. [Visual Bridge: Universal Visual Perception Representations Generating](https://ojs.aaai.org/index.php/AAAI/article/view/39268)

## Tier B: foundation, zero-shot, metric, and generalizable depth

11. [3D-IDE: 3D Implicit Depth Emergent](https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_3D-IDE_3D_Implicit_Depth_Emergent_CVPR_2026_paper.html)
12. [Depth Any Panoramas: A Foundation Model for Panoramic Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Lin_Depth_Any_Panoramas_A_Foundation_Model_for_Panoramic_Depth_Estimation_CVPR_2026_paper.html)
13. [InfiniDepth: Arbitrary-Resolution and Fine-Grained Depth Estimation with Neural Implicit Fields](https://openaccess.thecvf.com/content/CVPR2026/html/Yu_InfiniDepth_Arbitrary-Resolution_and_Fine-Grained_Depth_Estimation_with_Neural_Implicit_Fields_CVPR_2026_paper.html)
14. [Iris: Bringing Real-World Priors into Diffusion Model for Monocular Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Cai_Iris_Bringing_Real-World_Priors_into_Diffusion_Model_for_Monocular_Depth_CVPR_2026_paper.html)
15. [MD2E: Modeling Depth-to-Edge Cues for Monocular Metric Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Ning_MD2E_Modeling_Depth-to-Edge_Cues_for_Monocular_Metric_Depth_Estimation_CVPR_2026_paper.html)
16. [The Midas Touch for Metric Depth](https://openaccess.thecvf.com/content/CVPR2026/html/Ma_The_Midas_Touch_for_Metric_Depth_CVPR_2026_paper.html)
17. [UniDAC: Universal Metric Depth Estimation for Any Camera](https://openaccess.thecvf.com/content/CVPR2026/html/Ganesan_UniDAC_Universal_Metric_Depth_Estimation_for_Any_Camera_CVPR_2026_paper.html)
18. [VGGT-360: Geometry-Consistent Zero-Shot Panoramic Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Yuan_VGGT-360_Geometry-Consistent_Zero-Shot_Panoramic_Depth_Estimation_CVPR_2026_paper.html)
19. [Enhancing Generalization of Depth Estimation Foundation Model via Weakly-Supervised Adaptation with Regularization](https://ojs.aaai.org/index.php/AAAI/article/view/37433)
20. [Learning Depth from Past Selves: Self-Evolution Contrast for Robust Depth Estimation](https://ojs.aaai.org/index.php/AAAI/article/view/37245)

## Tier C: robustness, structure, temporal cues, and hard cases

21. [DepthFocus: Controllable Depth Estimation for See-Through Scenes](https://openaccess.thecvf.com/content/CVPR2026/html/Min_DepthFocus_Controllable_Depth_Estimation_for_See-Through_Scenes_CVPR_2026_paper.html)
22. [Dual Graph Regularized Deep Unfolding Network for Guided Depth Map Super-resolution](https://openaccess.thecvf.com/content/CVPR2026/html/Zhong_Dual_Graph_Regularized_Deep_Unfolding_Network_for_Guided_Depth_Map_CVPR_2026_paper.html)
23. [Guardians of the Hair: Rescuing Soft Boundaries in Depth, Stereo, and Novel Views](https://openaccess.thecvf.com/content/CVPR2026/html/Zhang_Guardians_of_the_Hair_Rescuing_Soft_Boundaries_in_Depth_Stereo_CVPR_2026_paper.html)
24. [PTC-Depth: Pose-Refined Monocular Depth Estimation with Temporal Consistency](https://openaccess.thecvf.com/content/CVPR2026/html/Han_PTC-Depth_Pose-Refined_Monocular_Depth_Estimation_with_Temporal_Consistency_CVPR_2026_paper.html)
25. [RoSAMDepth: Robust Self-supervised Depth Estimation Leveraging Segment Anything Model](https://openaccess.thecvf.com/content/CVPR2026/html/Gao_RoSAMDepth_Robust_Self-supervised_Depth_Estimation_Leveraging_Segment_Anything_Model_CVPR_2026_paper.html)
26. [SeeGroup: Multi-Layer Depth Estimation of Transparent Surfaces via Self-Determined Grouping](https://openaccess.thecvf.com/content/CVPR2026/html/Wen_SeeGroup_Multi-Layer_Depth_Estimation_of_Transparent_Surfaces_via_Self-Determined_Grouping_CVPR_2026_paper.html)
27. [Seeing Depth Through Frequency and Motion: A Progressive Training Paradigm for Monocular Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/Li_Seeing_Depth_Through_Frequency_and_Motion_A_Progressive_Training_Paradigm_CVPR_2026_paper.html)
28. [SO(3)-Equivariant ViT-Adapter for Data-Efficient Zero-Shot Sim-to-Real Indoor Panoramic Depth Estimation](https://openaccess.thecvf.com/content/CVPR2026/html/He_SO3-Equivariant_ViT-Adapter_for_Data-Efficient_Zero-Shot_Sim-to-Real_Indoor_Panoramic_Depth_Estimation_CVPR_2026_paper.html)
29. [FE2E: From Editor to Dense Geometry Estimator](https://openaccess.thecvf.com/content/CVPR2026/html/Wang_FE2E_From_Editor_to_Dense_Geometry_Estimator_CVPR_2026_paper.html)
30. [AdaDepth: Exploiting Inherent Scene Information for Self-Supervised Depth Estimation in Dynamic Scenes](https://ojs.aaai.org/index.php/AAAI/article/view/42414)

## Verification

All retained files were downloaded from the official CVF or AAAI proceedings. Each file is checked
for a PDF header, an EOF marker, non-trivial size, and a unique SHA-256 digest.
