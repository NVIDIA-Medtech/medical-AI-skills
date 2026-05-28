---
name: find-skills-quality-v1
description: Used to verify find-skills evidence packs for recommendation ordering, manifest consistency, no-fit semantics, and selector-scope disclosure.
license: Apache-2.0
allowed-tools: Bash
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - discovery
    - verifier
---

# Find Skills Quality Verifier

## Purpose
- Used for deterministic second-pass review of a `find-skills` evidence pack.
- Checks that the source pack passed, recommendations are score-sorted, referenced manifests exist and match reported ids/kinds, `no_fit` matches the top score, and the selector-only scope is disclosed.
- Manifest I/O: inputs are `find_skills_evidence_pack`; outputs are `find_skills_quality_report`.

## Instructions
- Use this verifier only on an evidence pack directory produced by `skills/find-skills`.
- Run it through `eval_engine/run.py` when producing verifier evidence.
- The verifier entrypoint is `scripts/grade.py`; do not reimplement its checks in an agent prompt.
- Do not treat a pass as proof that the selected skill is suitable for a specific user artifact.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- Runtime requirements: Python packages listed in `runtime.side_effects.pip_packages`.
- The input directory must contain `manifest.json`, `validation_summary.json`, and `output.json` from a `find-skills` evidence pack.

## Limitations
- Audits selector evidence consistency, not true task suitability.
- For the repository fixture query, expects `medagent.nv_segment_ct` as the top CT NIfTI segmentation match.
- Does not query external marketplaces or compare live model performance.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `target_skill_matches` fails | The fixture is not a `find-skills` evidence pack. | Re-run the verifier against the source skill pack directory. |
| `recommendation_0_manifest_exists` fails | The selector returned a path that no longer resolves in the repo. | Regenerate the source pack after updating the catalog. |
| `scores_sorted_desc` fails | The selector output is not rank ordered. | Fix the selector sorting logic and regenerate evidence. |

## Example

```bash
python verifiers/find_skills_quality_v1/scripts/grade.py \
  runs/find_skills_demo

python eval_engine/run.py verifiers/find_skills_quality_v1 \
  --fixture runs/find_skills_demo \
  --out runs/find_skills_quality
```
