# Processed Reference Papers

Token-efficient Markdown converted from `../reference_papers_origin/`.
Original PDFs remain authoritative for equations, tables, figures, and
citation verification. Bibliographies and repeated page furniture are removed.

## Corpus summary

- Papers: 14
- Source words: 140,235
- Processed words: 37,766
- Word reduction: 73.1%
- Good text layers: 5
- Partial/insufficient text layers: 9

## Papers

| Paper | Pages | Source words | Processed words | Quality |
| --- | ---: | ---: | ---: | --- |
| [Finding All DC Operating Points Using Interval](akhter2019_finding_all_dc_operating_points.md) | 4 | 3,541 | 0 | partial |
| [271](burmen2024_free_veriloga_support.md) | 11 | 7,138 | 0 | partial |
| [Adjoint-based A Posteriori Error Analysis for Semi-explicit Index-1 and Hessenberg Index-2 Differential-Algebraic Equations](chaudhry2025_adjoint_dae_error.md) | 36 | 13,986 | 12,202 | good |
| [Takustr. 7](cheung2017_verifying_integer_programming_results.md) | 13 | 5,762 | 4,678 | good |
| [Verification of Analog and Mixed-Signal Circuits](dang2004_ams_verification.md) | 16 | 6,121 | 0 | partial |
| [JOURNAL OF LATEX CLASS FILES, VOL. 18, NO. 9, SEPTEMBER 2020](data_driven_mna_solver_2023.md) | 8 | 6,099 | 0 | partial |
| [Hindawi Publishing Corporation](drzevitzky2010_proof_carrying_hardware.md) | 11 | 8,040 | 6,858 | good |
| [Rob Sumners, Cuong Chau (Eds.): 17th ACL2 Workshop (ACL2 2022)](hunt2022_vwsim.md) | 15 | 7,104 | 0 | partial |
| [Invited paper in Design Automation Conference (DAC), 2018](ivanov2019_safety_learning_enabled_components.md) | 11 | 5,264 | 0 | partial |
| [CAPD::DynSys: a flexible C++ toolbox for rigorous numerical analysis of dynamical systems](kapela2021_capd_dynsys.md) | 25 | 10,421 | 8,516 | good |
| [arXiv:0811.2984v1 [cs.NA] 18 Nov 2008](kolev2008_sensitivity_fixed_point_interval.md) | 5 | 2,156 | 0 | partial |
| [Fast Verified Solutions of Sparse](ogita2013_fast_verified_sparse_systems.md) | 15 | 5,975 | 5,512 | good |
| [rump.dvi](rump2010_verification_methods.md) | 163 | 55,336 | 0 | partial |
| [Formal Verification of Nonlinear Analog Circuits](yasmin2024_formal_nonlinear_analog.md) | 4 | 3,292 | 0 | partial |

## Regeneration

```bash
conda run -n auto_research python tools/scripts/convert_reference_papers.py \
  --input-dir paper2/reference_papers_origin \
  --output-dir paper2/reference_papers_processed
```
