---
name: skill-completeness-v1
description: Grades a skill or verifier directory for required files, valid manifest structure, side-effect declarations, validation gates, paired-verifier resolution, fixtures, and authoring hygiene. Engineering verification only.
license: Apache-2.0
allowed-tools:
  - Bash
---

# skill_completeness_v1

## Purpose
- Grades a skill or verifier directory for required files, valid manifest structure, side-effect declarations, validation gates, paired-verifier resolution, fixtures, authoring hygiene, and derived lifecycle status.
- Use this before publishing or reviewing a skill-shaped artifact. Engineering verification only.
- Manifest I/O: inputs are `target_skill`; outputs are `completeness_report`.

## Instructions
- Run `scripts/grade.py` on a target `skills/<name>` or `verifiers/<name>` directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["skills/<name>"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `TARGET_SKILL_OR_VERIFIER_DIR` |

## Prerequisites
- The target directory must contain `SKILL.md` and `skill_manifest.yaml` to receive a meaningful structural audit.
- Optional LLM review requires `LLM_VERIFIER=1` and `NV_INFER_TOKEN`; leave it unset for deterministic local checks.
- Side effects: deterministic tiers are offline; optional LLM review contacts `https://inference-api.nvidia.com`.

## Limitations
- Tier 3 LLM review is advisory and skipped by default.
- Tier 4 test-quality assessment is still deferred.
- This verifier checks skill shape and authoring hygiene; it does not prove the wrapped medical AI task succeeds.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| `not a directory` | The argument is not a skill or verifier directory. | Pass `skills/<name>` or `verifiers/<name>`. |
| Missing manifest/frontmatter | The target is not skill-shaped or has malformed metadata. | Add the required files before rerunning. |
| Advisory findings | The target is runnable but less agent-friendly. | Fix the listed SKILL.md, fixture, or manifest hygiene gap. |

Meta-verifier for spec quality.

```bash
python verifiers/skill_completeness_v1/scripts/grade.py skills/dicom-metadata-extract
```

```bash
python eval_engine/run.py verifiers/skill_completeness_v1 \
  --fixture skills/dicom-metadata-extract \
  --out runs/audit_dicom_metadata
```

Tier 1 checks required files, frontmatter, manifest fields, entrypoint paths,
and output schemas. Tier 2 checks side effects, gate presence, paired verifier
resolution, fixture presence, import declarations, nontrivial sanity checks,
and SKILL.md hygiene. The report also derives a non-authoritative lifecycle
status (`draft`, `runnable`, `gated`, `verified`, or `published`) from those
checks plus paired-verifier, trusted-run, behavior-eval, benchmark-note, and
curated-evidence signals.

Optional advisory LLM review is disabled by default. Set `LLM_VERIFIER=1` and
`NV_INFER_TOKEN` only when explicitly running that experiment.

This verifier is itself audited by the same eval_engine.
