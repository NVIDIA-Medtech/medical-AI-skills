---
name: find-skills
description: Used for recommending local Medical AI Skills skills or verifiers from committed manifests. Not for model benchmarking or clinical suitability.
license: Apache-2.0
allowed-tools: Bash, Read
metadata:
  author: "NVIDIA MedTech <noreply@nvidia.com>"
  tags:
    - medtech
    - discovery
    - routing
---

# Find Skills

## Purpose
- Used for recommending local Medical AI Skills skills or verifiers from committed manifests. Not for model benchmarking or clinical suitability.
- Use the wrapper exactly as documented; do not replace the upstream entrypoint with a handwritten implementation.
- Manifest I/O: inputs are `task_request`; outputs are `recommendation`.

## Instructions
- Read `skill_manifest.yaml` before changing arguments, side effects, or validation gates.
- Run `scripts/find_skills.py` through the documented command below; keep outputs under a caller-provided run directory.
- If a host agent exposes `run_script`, use `run_script("scripts/find_skills.py", args=[...])`; otherwise run the Bash/Python command shown below.
- Check the emitted JSON and the paired `find_skills_quality_v1` verifier before treating the run as evidence.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/find_skills.py` | Primary entrypoint declared by skill_manifest.yaml. | `QUERY [--limit N] [--json] [--markdown]` |
| `scripts/list_local_skills.py` | Helper command for catalog listing. | `[--skills] [--verifiers]` |

## Prerequisites
- Runtime requirements: Python packages listed in `runtime.side_effects.pip_packages`.
- Run commands from the repository root unless an existing section below says otherwise.

## Limitations
- Recommendations come from a lightweight lexical ranker over locally committed manifests. It is a selection aid, not a performance benchmark or proof that the skill fits every user constraint.
- Local-only: does not query external skill marketplaces, install counts, or live repository metadata. Adding a new candidate requires committing its skill_manifest.yaml under skills/ or verifiers/.
- The score is only a deterministic shortlist heuristic. Agents and reviewers must still inspect the candidate's SKILL.md, skill_manifest.yaml, side effects, and limitations before running it or recommending it for a specific artifact.
- Verifiers consume evidence packs produced by their paired skill; this recommender will surface a verifier when the user asks about quality assessment, but the verifier itself does not replace the primary skill.
- Not for clinical interpretation, regulatory submission, ranking model performance, autonomous deployment decisions.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing dependency or import error | Runtime package drift from `skill_manifest.yaml`. | Install the packages declared in the manifest or use the documented setup command. |
| Empty or schema-invalid output | Wrong input path, unsupported modality, or upstream failure. | Re-run with a known fixture and inspect the wrapper JSON plus stderr. |
| Validation gate failure | Output violated a declared engineering invariant. | Keep the failed evidence pack and use the gate message to repair inputs or wrapper code. |

Select a committed Medical AI Skills skill or verifier for a user's engineering task.
The script ranks local `skill_manifest.yaml` files and returns a JSON
shortlist. Treat the shortlist as a starting point: read the selected
candidate's `SKILL.md` and `skill_manifest.yaml` before adapting an
invocation.

## Run

For an evidence-pack run, pass a text fixture containing the task:

```bash
python eval_engine/run.py skills/find-skills \
  --fixture skills/find-skills/fixtures/example_task.txt \
  --out runs/find_skills_demo
```

For a trusted run with the paired verifier:

```bash
python -m eval_engine.run_trusted skills/find-skills \
  --fixture skills/find-skills/fixtures/example_task.txt \
  --out runs/find_skills_trusted
```

For an interactive local shortlist:

```bash
python skills/find-skills/scripts/find_skills.py \
  "segment a CT NIfTI volume" \
  --markdown
```

To dump the manifest catalog without ranking:

```bash
python skills/find-skills/scripts/list_local_skills.py
```

## Review Checklist

After the script returns candidates:

1. Check input formats against the user's artifact.
2. Check declared outputs against the user's requested result.
3. Read `runtime.side_effects` for GPU, Docker, network, cache, and env-var requirements.
4. Read `limitations` and `intended_use.not_for`; do not recommend a skill for a listed non-scope.
5. If the user asks whether output quality is good enough, prefer an implemented paired verifier over a primary wrapper alone.

## Output

The JSON output contains:

- `recommendations[]`: ranked skill or verifier candidates.
- `score`: deterministic lexical match score, not a quality or performance metric.
- `rationale`: matched terms and declared input/output hints.
- `caveats`: side effects and leading limitations worth checking before a run.
- `no_fit`: true when no candidate has a positive match score.

## Limitations

This skill does not query external marketplaces, install skills, run candidate
skills, or produce clinical suitability judgments. The ranker is intentionally
small and deterministic; final selection still depends on reading the target
manifest and invocation guide.
