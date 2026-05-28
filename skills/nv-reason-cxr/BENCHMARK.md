# nv-reason-cxr Benchmark

## Scope

This benchmark report covers `nv-reason-cxr`, Medical AI Skills skill for NV-Reason-CXR-3B chest X-ray inference wrapper. The skill is engineering verification only and is not clinical, diagnostic, regulatory, or patient-facing tooling.

## Current Evidence

- `SKILL.md` declares the external agent-facing trigger, wrapper command, prerequisites, and limitations.
- `skill_manifest.yaml` declares inputs, outputs, runtime side effects, validation gates, and known limitations for Medical AI Skills trust harness.
- `evals/evals.json` defines prompt-shaped behavior checks for agent routing, command construction, and scope boundaries.

## With-Skill vs Without-Skill Evaluation

| Arm | Document surface | Expected behavior | Status |
|---|---|---|---|
| With skill | `SKILL.md`, `scripts/`, and `evals/evals.json` | Agent should select this skill only for matching engineering tasks, invoke the documented wrapper, and preserve stated limitations. | Authored for publication; run results pending unless a separate study is cited in `examples/` or `docs/`. |
| Without skill | User prompt plus general model knowledge or upstream docs | Agent may guess the upstream invocation, omit Medical AI Skills gates, or miss scope caveats. | Baseline run pending. |

## Reporting Notes

Record future measured results here after running the same prompt set with and without the skill installed. Include agent/runtime version, task completion rate, material output-quality observations, token or wall-clock cost where available, and links to any evidence packs or study artifacts.
