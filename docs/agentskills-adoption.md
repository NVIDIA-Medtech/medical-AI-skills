# agentskills.io adoption + npx distribution

Medical AI Skills is dual-track: a **trust harness** for evaluating skills with
domain gates, and a **catalog** of skills that conform to the public
[Agent Skills specification](https://agentskills.io/specification) so they
can be installed and run by any compliant agent runtime.

This doc records what we adopted from agentskills.io and what we deliberately
kept internal to Medical AI Skills.

## What we adopted

### 1. `SKILL.md` frontmatter compliance

Every publishable skill's `SKILL.md` carries the spec-required `name` and
`description` keys plus repo-required `license` and `allowed-tools`.
Medical AI Skills' authoring guidance treats those four as the contract surface
for npx distribution and external NVIDIA catalog publishing.

Audited 2026-05-22: all committed `skills/*/SKILL.md` files use YAML
frontmatter first, kebab-case `name`, third-person `description`, declared
`license`, scalar `allowed-tools`, and package directories matching
frontmatter `name`.

### 2. `npx skills add` as the install path

End users install skills directly from this repo via the standard
[`skills` CLI](https://github.com/vercel-labs/skills):

```bash
# Interactive — pick a skill, pick an agent
npx skills add NVIDIA-Medtech/medical-AI-skills

# Non-interactive — exact skill, exact agent
npx skills add NVIDIA-Medtech/medical-AI-skills \
  --skill nv-segment-ct \
  --agent claude-code \
  --yes
```

`--skill` values are the kebab-case `name:` frontmatter of each `SKILL.md`
(e.g. `nv-segment-ct`, `dicom-series-preflight`). `--agent`
accepts `claude-code`, `codex`, `cursor`, `kiro-cli`, and the rest of the
[supported clients](https://github.com/vercel-labs/skills#supported-agents).

The CLI copies the skill directory into the agent's expected location
(`.claude/skills/`, `~/.codex/skills/`, etc.). Critically, it ships
`SKILL.md` + `scripts/` + (where present) `evals/`. It does **not**
meaningfully use `skill_manifest.yaml`, `validators/`, paired verifiers, or
the eval engine — those are internal Medical AI Skills artifacts; they ride along
as extra files but the npx-installed agent ignores them.

### 3. `evals/evals.json` for prompt-shaped behavioral evals

Per [agentskills.io/skill-creation/evaluating-skills](https://agentskills.io/skill-creation/evaluating-skills).
Each test case is `{prompt, expected_output, files, assertions}`. Store it
under `skills/<name>/evals/evals.json`. For new external-publication skills,
include positive trigger cases and negative stay-silent or scope-boundary
cases. GPU-heavy skills may use command-shape or preflight evals when full
inference is not suitable for an agent harness.

Current authored examples:

| Skill | Why it has `evals/` |
|---|---|
| `dicom_metadata_extract` | Reference skill; agent must surface the PHI flag, not just dump tags |
| `dicom_series_preflight` | A1 onboarding; agent must use the gates to make a go/no-go call, not bypass them |

Legacy GPU/Docker skills may still rely on `fixtures/` + manifest gates until
their external-publication pass adds prompt evals. NVSkills CI generates the
corresponding `BENCHMARK.md`; this gap is not a reason to skip the eval format
for new skills.

### 4. with_skill vs without_skill baseline framing

Each `evals.json` carries a `baseline_methodology` block describing what
running the test case looks like *with* the skill installed vs *without* it.
`BENCHMARK.md` is the managed publication-facing report for those results:
agents tested, task completion, quality notes, token/time cost where available,
and remaining gaps. Contributors prepare and review the eval inputs; NVSkills
CI runs the publication baseline and generates the report. The Medical AI
Skills evidence harness remains the local domain-gate path.

## What We Deliberately Keep Internal

The agentskills.io eval format is the right tool for *agent-behavior*
correctness ("given a fuzzy human prompt + SKILL.md, did the agent invoke
the right script with the right args?"). It is the wrong tool for
*domain-validation* correctness ("did this CT segmentation hit Dice ≥ 0.70
on the spleen reference cases?").

Medical AI Skills keeps the following internal — they are richer than
agentskills.io conventions and we will not simplify them down to match:

| Medical AI Skills artifact | Why it stays internal |
|---|---|
| `skill_manifest.yaml` | declares `validation.sanity_checks`, `expected_cost`, `env_pin`, paired verifiers, side-effects budget — none of which fit the agentskills `SKILL.md`-only model |
| `validators/output_schema.json` | per-skill JSON-schema gate; assertions-by-LLM-judge can't replace this for medical output shape |
| `verifiers/*/` | paired second-pass auditors with their own gates (anatomy plausibility, Dice/IoU, checkpoint integrity) |
| Evidence pack (manifest.json, validation_summary.json, runtime_profile.json, integrity_check.json, environment.lock, cost_profile.json, agent_run_trace.jsonl, replay.sh) | structured trust artifact, more durable than `benchmark.json` |
| Wilson 95% CI on coverage_pct, repo_git_sha | binomial CI > Gaussian stddev for pass/fail data; git SHA closes the FUTURE-AI traceability gap |

## What this gives us

The split is honest:

- **"Use" lane** (`npx skills add ...`): end-user delivery, low-friction. Gets
  SKILL.md + scripts + evals/. Engineering verification only — the "trust"
  caveats are written into every SKILL.md.
- **"Trust" lane** (`make run-skill` / `make run-trusted` / `make verify`):
  evaluator workflow. Runs the full gate ladder, emits evidence packs,
  invokes paired verifiers.

A skill that ships via `npx skills add` is runnable. A skill that ships an
evidence pack from `make run-trusted` is auditable. Both matter; they are
different artifacts.

## Open follow-ups

- Keep the `nv-*` with-vs-without comparison artifacts current when skill
  instructions or backend configuration changes.
- Investigate whether `evals/evals.json` assertions should be graded in
  addition to pack-level gates. Optional — the two lanes are independent by
  design.
