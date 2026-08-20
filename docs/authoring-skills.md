# Authoring skills

How-to guide for adding a **publishable** wrapper under `skills/<name>/`.
For verifier specs, see [`CONTRIBUTING.md`](../CONTRIBUTING.md#verifier-requirements).
For SKILL.md style, see [`skill-authoring-best-practices.md`](skill-authoring-best-practices.md).

## Before you start

Confirm the contribution belongs in `skills/` (see the decision tree in
[`CONTRIBUTING.md`](../CONTRIBUTING.md#where-to-put-work) and the catalog rules
in [`skill-scope.md`](skill-scope.md)):

- Wraps one upstream tool through its documented entry point
- Exposes at least one silent-failure mode the contract layer can catch
- Has small synthetic or public fixtures
- Maps to a medtech **engineering** task, not clinical decision support
- Declares `validation.env_pin` for direct behavioral dependencies

Copy layout from [`skills/dicom-metadata-extract/`](../skills/dicom-metadata-extract/)
for the smallest end-to-end example.

## Invocation template (`runtime.args`)

When omitted, the engine invokes the script as
`[python, <entrypoint>, <fixture>]`. To pass an output directory, env-resolved
secret, or extra flag, declare a template under `runtime.args`:

```yaml
runtime:
  language: python
  entrypoint: scripts/series_to_volume.py
  args:
    - "${python}"
    - "${script}"
    - "${fixture}"
    - "--output"
    - "${out}/volume.nii.gz"
```

Supported tokens: `${python}`, `${script}`, `${fixture}`, `${out}`,
`${skill_dir}`, `${env.VAR}`. A missing env var fails the run with a clear
error rather than silently expanding to an empty string. `replay.sh` is
generated from the rendered command, so the contract round-trips.

## Required files

```text
skills/<name>/
  SKILL.md                 # spec-compliant invocation guide (agents read this first)
  skill_manifest.yaml      # machine contract
  scripts/<entrypoint>.py  # calls upstream; emits JSON on stdout
  validators/output_schema.json   # when output JSON is gated
  fixtures/                # small synthetic/public inputs
  evals/evals.json         # prompt-shaped skill-behavior evals for publication
  BENCHMARK.md             # with-skill / without-skill results for publication
  tests/                   # optional but encouraged for wrapper internals
```

## Authoring order

1. **SKILL.md** — start with YAML frontmatter and nothing above it. Use a
   lowercase hyphenated `name`, a third-person trigger-rich `description`,
   `license`, and minimal `allowed-tools`. Keep `description` short enough for
   the internal quality profile, with clear `Used for...` and `Not for...`
   scope. Body should state when to use the skill, prerequisites, limitations,
   and the exact run command with your script. Lead with direct script
   invocation, not `eval_engine.run` only.
2. **Manifest** — inputs, outputs, `runtime.entrypoint`, optional
   `runtime.args` invocation template (see below), side effects, validation
   gates, and `validation.env_pin` for direct behavioral dependencies. Validate
   against [`spec/skill_manifest.schema.json`](../spec/skill_manifest.schema.json).
3. **Script** — wrap upstream; handle expected errors with clear messages.
   For fragile model workflows, put staging, output-path handling, label
   remapping, cache use, and validation in the committed script. Do not rely on
   agents to generate new inference glue from upstream internals during normal
   use; generated code is harder to audit than a wrapper command and can bypass
   the intended verifier. Do not patch or rewrite upstream implementation files
   during normal runs. Make the README/requirements/model-card path work first,
   and use reference baselines to detect config, checkpoint, data split, or
   dependency drift before changing training or inference behavior.
4. **Schema and fixtures** — gate output shape; add negative fixtures when they
   teach a real failure mode.
5. **Agent-behavior evals** — add `evals/evals.json` with positive and negative
   prompts, expected skill/script use, and scope assertions. GPU-heavy skills
   may use command-shape or preflight evals when full inference is not suitable
   for an agent harness.
6. **Benchmark report** — add `BENCHMARK.md` summarizing with-skill and
   without-skill behavior, agents tested, task completion, token/time cost, and
   any remaining gaps.
7. **Evidence** — run locally, render a review packet, then promote a small
   pass pack to `examples/` if it should be a regression anchor. Wrapper output
   should include concrete artifact paths, runtime facts, and limitations that
   make the review packet useful without requiring a reviewer to read every JSON
   file first. Prefer repo-relative paths for committed fixtures and
   pack-relative paths for generated files; if a verifier-critical artifact is
   too large or otherwise prohibited from git, record that as an explicit gap
   rather than promoting the pack as a complete trusted pass.

## SkillEvaluator publication preflight

The public SkillEvaluator `external` profile adds publication checks beyond the
base Agent Skills spec. Before opening a PR, make the skill friendly to that
check. Follow the public
[SkillEvaluator installation guide](https://docs.nvidia.com/skills/skillevaluator/installation)
when the CLI is not already available:

- Use kebab-case for both `skills/<name>/` and frontmatter `name`.
- Keep `description` concise, usually under 200 characters. Include both a
  positive trigger (`Used for...`) and a negative boundary (`Not for...`).
- Include these SKILL.md sections: `## Purpose`, `## Instructions`,
  `## Available Scripts`, `## Prerequisites`, `## Limitations`, and
  `## Troubleshooting`.
- In `## Instructions`, say exactly which wrapper script to run and mention
  `run_script("scripts/<entrypoint>.py", args=[...])` for agents that expose
  that helper.
- In `## Available Scripts`, use the exact table header
  `| Script | Purpose | Arguments |`.
- In `## Prerequisites`, `## Usage`, or a compact environment table, document
  every manifest-declared `runtime.env_required`, `runtime.env_optional`, and
  `runtime.env_conditional` variable. Include mock/live/cache switches so
  agents can choose the correct runnable path before executing.
- Avoid local developer paths such as `/home/<user>/...` in committed skills,
  fixtures, and examples.
- Keep fixtures synthetic/public and avoid PII-regex false positives: no
  long dotted synthetic UIDs, no same-line decimal tuples that look like GPS
  coordinates, and no raw 10-digit identifiers in fixture/config files.
- For `scripts/*.py`, use a shebang, validate inputs with `argparse`, `typer`,
  `click`, `raise`, or `ValueError`, keep control-flow nesting at or below the
  internal threshold, and avoid unexplained raw numeric literals.

## Paired verifiers

When a domain claim needs a second pass over artifacts, declare
`paired_verifiers[]` and implement or reference a verifier under `verifiers/`.
Do not stuff domain-quality logic into the wrapper when the upstream tool does
not emit the needed signal.

## Check before PR

```bash
make skill-evaluator-validate
make list-skills
make verify-skills
make run-skill SKILL=<name> FIXTURE=<fixture> OUT=runs/<name>_smoke
make verify
```

Record intentional gaps under the manifest's `limitations` field.

If `skillevaluator` is installed in a local environment rather than on `PATH`,
pass it explicitly:

```bash
make skill-evaluator-validate \
  SKILL_EVALUATOR=/path/to/skillevaluator
```

This runs the public external preflight with Tier 2 disabled, complete
collection reporting, a quality threshold of 70, and JSON/Markdown reports in
`/tmp/medical-AI-skills-skillevaluator`. Override the report directory with
`SKILL_EVALUATOR_OUT=<path>`. Central NVSkills CI may use a newer managed
SkillEvaluator build, agent runtimes, and gate policy, so a local pass does not
replace the managed PR check.

## Related

- [`spec-model.md`](spec-model.md) — where each check belongs
- [`skill-scope.md`](skill-scope.md) — what belongs in `skills/`
- [`trust-and-evidence.md`](trust-and-evidence.md) — evidence packs and gates
- [`CONTRIBUTING.md`](../CONTRIBUTING.md) — review lanes and policies
