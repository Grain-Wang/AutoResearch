# CoVoL-Depth: Diagnostic Negative Result on Deterministic GT Relation Templates

## Abstract

This internal technical note records a stopped diagnostic, not an algorithm paper. Automatic captions were not directly tested. On 100 NYUv2 official-training images grouped into 59 scene clusters, a released TR2M checkpoint was evaluated with 1,200 deterministic short prompts constructed from ground-truth entities, instance masks, and median depths. Two conflict-template families changed regional AbsRel, but rule-defined semantic-preserving templates also produced a stable change, violating the preregistered specificity gate. The current GT-template probe and the proposed Main-PR route were therefore stopped. No D0/D1 comparison, router result, cross-model replication, human naturalness audit, or official test result exists.

## Diagnostic question and construction

The original project asked whether local errors in automatic image captions create a need for selective regional fallback in language-guided metric depth. The executed diagnostic was narrower: it tested the surface-form and conflict-template sensitivity of released TR2M on annotation-derived prompts. Each image supplied a rule-generated clean relation sentence and four intervention families with three templates each. The semantic-preserving variant 0 was identical to clean; variants 1 and 2 were fixed paraphrases. Consequently, the diagnostic cannot estimate a natural automatic-caption error distribution.

Machine checks and an independent parser confirmed that the templates contained the intended entities and depth relations. They did not establish human semantic equivalence, naturalness, or lack of ambiguity. A proposed double-human audit was not run because repository policy prohibits adding human annotation without changed authorization.

## Result and preregistered stop

The cluster-balanced region AbsRel degradation estimates were 0.001156 for semantic-preserving templates, 0.000055 for target deletion, 0.001620 for local entity conflict, and 0.000806 for depth relation conflict. The semantic-preserving 95% CI was `[0.000579, 0.001777]`, excluding zero and violating the preregistered control condition. The formal status is `STOP_H_SENSITIVITY`.

The original aggregate text-only macro-F1 of 0.488 hid family leakage. A one-vs-rest held-template-out audit gives F1 1.000 for target deletion and 0.662 for local entity conflict. The latter is especially important because local entity conflict had the largest positive raw sensitivity estimate. Its effect therefore cannot be attributed cleanly to semantic conflict.

## Exploratory postmortem

A matched cluster analysis compared each intervention family against its semantic-preserving variant. This analysis is explicitly exploratory and cannot reverse the stop. At family level, local entity conflict minus control was approximately +0.000464 with a CI crossing zero; depth relation conflict minus control was approximately -0.000350. Neither family-level result survived Holm correction. Template-level effects changed sign, reinforcing the construction limitation.

The target region occupied a median 8.55% of valid full-image pixels. Practical-effect artifacts report clean regional error, absolute and relative degradation, full-image degradation, and maximum leave-one-cluster-out influence. These diagnostics describe scale and heterogeneity; they do not establish equivalence or task importance.

## Supported and unsupported interpretation

Supported: on this deterministic GT relation-template corpus, released TR2M did not meet the preregistered conflict-specificity gate, so the current probe and Main-PR contribution path stop.

Unsupported: automatic-caption errors are absent or harmless; fixed paraphrases are human-equivalent; fallback routing is generally unnecessary; any algorithmic contribution is validated; or the result generalizes across language-depth models, datasets, or deployment distributions.

## Reusable lessons

Future language-robustness probes should directly match conflict captions to independently validated equivalent controls, predefine a smallest effect size or equivalence region, audit artifacts per family, report practical effect slices, and test natural automatic captions before claiming deployment relevance. Negative gates should be global, hash-linked, and irreversible within the stopped project.
