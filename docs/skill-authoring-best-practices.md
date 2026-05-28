# Skill Authoring Best Practices

Medical AI Skills rules for writing `SKILL.md` files that Claude, Codex, Cursor, or any
Skills-aware agent can discover and use reliably. Distilled from Anthropic's
[Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices),
the [Agent Skills specification](https://agentskills.io/specification), and
NVIDIA's external skills publishing guide, then applied to this repo's
`skills/<name>/` and `verifiers/<name>/` layout.

**Publishable skills** under `skills/` are the default case: wrappers users run
with their own data. **Verifiers** under `verifiers/` share the same
`SKILL.md` + `skill_manifest.yaml` shape so the eval engine and agents can run
them consistently; treat them as specialized trust artifacts, not ordinary
catalog entries. Sections below apply to both unless noted.

## Contents

- [Why this exists](#why-this-exists)
- [SKILL.md frontmatter](#skillmd-frontmatter)
- [Naming conventions](#naming-conventions)
- [Writing the `description`](#writing-the-description)
- [Body length and progressive disclosure](#body-length-and-progressive-disclosure)
- [Degrees of freedom](#degrees-of-freedom)
- [Command contracts over generated code](#command-contracts-over-generated-code)
- [Upstream fidelity and reference baselines](#upstream-fidelity-and-reference-baselines)
- [Workflows and feedback loops](#workflows-and-feedback-loops)
- [Scripts: solve, don't punt](#scripts-solve-dont-punt)
- [Internal NV-BASE profile](#internal-nv-base-profile)
- [Anti-patterns](#anti-patterns)
- [Where checks belong](#where-checks-belong)
- [Authoring checklist](#authoring-checklist)

## Why this exists

The `description` field of every `SKILL.md` is pre-loaded into the agent
context. Everything else is read on demand. That makes the frontmatter the
single most important text in a skill: it decides whether the skill is even
considered. The body is the next-most-important text: when an agent reads it,
every token competes with the rest of the conversation.

Three principles drive the rest of this guide:

1. **Concise is key.** Add only context the model doesn't already have.
2. **One purpose per skill.** A skill wraps one upstream tool through its
   documented entry point. See [`CONTRIBUTING.md`](../CONTRIBUTING.md#invocation-rule).
3. **Progressive disclosure.** SKILL.md is a navigator; details live in
   sibling files that the agent loads only when needed.

## SKILL.md frontmatter

Every `skills/<name>/SKILL.md` and `verifiers/<name>/SKILL.md` must start with
YAML frontmatter:

```yaml
---
name: kebab-case-name
description: Third-person sentence describing what the skill does and when to use it.
license: Apache-2.0
allowed-tools: Bash
---
```

### Required fields

| Field         | Rule                                                                                                  |
|---------------|-------------------------------------------------------------------------------------------------------|
| `name`        | Max 64 chars. Lowercase letters, digits, hyphens only. No XML tags. **No reserved words: `anthropic`, `claude`.** |
| `description` | Non-empty. Max 1024 chars. No XML tags. **Third person.** What + when.                                |

### Recommended fields (Medical AI Skills convention)

| Field           | Why                                                                              |
|-----------------|----------------------------------------------------------------------------------|
| `license`       | Declare per-skill license (usually `Apache-2.0`).                                |
| `allowed-tools` | List only the tools the skill needs. Use scalar `Bash` for script-only wrappers. |

The deeper machine-readable spec lives in [`skill_manifest.yaml`](../spec/skill_manifest.schema.json),
not in the SKILL.md frontmatter. SKILL.md is the *human-facing* invocation guide.
For wrappers around external packages, model repos, hosted models, or git repos,
the manifest must also declare `upstream_refs` with a package version constraint,
exact version, model/repo revision, or git commit. This keeps behavior drift
reviewable independently of the skill's own `version`.

Nothing may appear above the opening `---`. Copyright or license prose, when
needed, goes below the frontmatter and initial H1 so agent parsers can read the
metadata reliably.

## Naming conventions

The frontmatter `name` is the agent-facing identifier. Use it consistently
across the SKILL.md and directory name. Medical AI Skills skills use kebab-case on disk
and in frontmatter; the Makefile accepts legacy snake_case `SKILL=...` values
only as a compatibility alias.

**Use kebab-case, prefer a gerund or noun-phrase shape:**

- `nv-segment-ct` (noun phrase)
- `dicom-metadata-extract` (action-oriented)
- `ct-segmentation-quality-v1` (versioned verifier — keep the `-v1` suffix)

**Avoid:**

- Vague names (`helper`, `utils`, `tool`)
- Reserved words (`anthropic-*`, `claude-*`)
- Inconsistent casing or stray underscores in the frontmatter or directory
  name.

## Writing the `description`

The description is what an agent reads to decide whether the skill is
relevant. Write it like an index entry, not a marketing blurb.

### Rules

1. **Third person.** "Extracts...", "Runs...", "Wraps...", "Audits...". Never
   "I", "you", or "this skill helps you".
2. **What + when.** State what the skill does *and* the trigger keywords or
   contexts that should activate it. Mention the input artifact, the upstream
   tool, and the produced artifact.
3. **Engineering scope.** End with `Engineering verification only.` (or
   `Not for clinical use.`) when the wrapper is non-clinical, so the agent
   knows the skill's scope before reading further. This mirrors the
   manifest's `intended_use.not_for` declaration.
4. **Mention upstream tool by name** when the skill is a wrapper — that
   surfaces the trigger keyword for users searching by tool.

### Good examples (current repo)

```yaml
description: Extracts selected metadata from one DICOM file, reports
  modality/study context, and flags a small standard-tag PHI subset.
  Engineering verification only; does not anonymize, inspect private tags,
  or detect burnt-in pixel PHI.
```

### Avoid

```yaml
description: Helps with DICOM files.            # too vague
description: I can run segmentation for you.    # first person
description: You can use this to summarize.     # second person
```

## Body length and progressive disclosure

**Hard cap:** SKILL.md body ≤ 500 lines. Most Medical AI Skills skills are under 50
lines; longer ones such as `nv_segment_ct_finetune` are exceptions that still
stay well under the cap.

**Pattern for short skills (under ~80 lines):** put invocation, evidence-output
summary, and limitations directly in SKILL.md. No reference files needed.

**Pattern for longer skills:** keep SKILL.md as a navigator; push detail into
sibling files inside the skill directory. Allowed locations:

```text
skills/<name>/
  SKILL.md              # navigator + invocation
  skill_manifest.yaml   # machine-readable spec
  scripts/              # entrypoint and helpers (executed, not loaded)
  validators/           # output_schema.json (gated by manifest)
  fixtures/             # small synthetic/public inputs
  evals/evals.json      # prompt-shaped behavior evals for publication
  BENCHMARK.md          # with-skill / without-skill result summary
  tests/                # focused parsing or invariant tests
  REFERENCE.md          # optional — deeper details, one level deep
  EXAMPLES.md           # optional — input/output pairs
```

### Rules

- **References stay one level deep from SKILL.md.** Do not chain references
  (SKILL.md → A.md → B.md). The agent may only partially read nested files.
- **Reference files over 100 lines start with a table of contents.**
- **Make execution intent explicit:**
  - "Run `scripts/foo.py` to extract X." — agent should execute the script.
  - "See `scripts/foo.py` for the X algorithm." — agent should read it as
    reference.
- **Forward slashes only.** `scripts/helper.py`, never `scripts\helper.py`.
- **Bundle large reference material freely** — files that aren't read don't
  cost tokens. The penalty is only paid on read.

### Internal quality section pattern

The internal NV-BASE quality profile expects SKILL.md to be immediately useful
to an agent. Include this shape near the top of every skill body:

```markdown
## Purpose

## Instructions

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|

## Prerequisites

## Limitations

## Troubleshooting
```

`## Instructions` should name the exact script to run and include a
`run_script("scripts/<entrypoint>.py", args=[...])` example for hosts that
provide that helper. `## Available Scripts` should list each executable wrapper
or helper with its purpose and expected arguments. Every path in that table
must be a committed file under the skill directory, and the table must include
the manifest's `runtime.entrypoint`. The `Arguments` cell must be an actual
argument sketch, such as ``INPUT.nii.gz --output-dir OUT --modality CT_BODY``,
or a concrete note such as `Imported only; do not call directly.` for helper
modules. Do not use placeholders like "See Usage below" or "runtime.args in
skill_manifest.yaml". If `skill_manifest.yaml` declares literal `runtime.args`
values such as `--output-dir`, `--modality`, or `mri_t1`, mention those same
tokens in SKILL.md so an agent does not have to infer them.
Also mention the manifest-declared input/output names or clear human-readable
equivalents, such as `task request`, `evidence pack`, `result JSON`, or
`segmentation label map`, so an agent can connect wrapper arguments to the
manifest contract before running anything.

If the manifest declares `runtime.env_required`, `runtime.env_optional`, or
`runtime.env_conditional`, name those variables in SKILL.md and state when to
set them. Optional live/mock/cache controls are still part of the runnable
surface; do not require agents to discover them from YAML after a failed run.

### Anti-pattern: nested references

```markdown
# SKILL.md
See [advanced.md](advanced.md)...

# advanced.md
See [details.md](details.md)...     # ❌ too deep
```

Flatten so every reference is one hop from SKILL.md.

## Degrees of freedom

Match the level of specificity to how fragile the task is.

| Task character                                                | Style          | Example in this repo                                                                                          |
|---------------------------------------------------------------|----------------|---------------------------------------------------------------------------------------------------------------|
| Many valid approaches; outcome depends on context             | High freedom — narrative steps  | a troubleshooting or setup checklist that asks the agent to inspect the chosen spec before running commands    |
| Preferred pattern with some variation                         | Medium freedom — script with parameters | `dicom_series_to_volume` (one entrypoint, configurable output dir)                                            |
| Fragile / consistency-critical / specific sequence            | Low freedom — single exact command       | `nv_segment_ct` (one entrypoint via `HuggingFacePipelineHelper`; no alternative inference loop allowed)       |

**The bridge analogy:** narrow bridge with cliffs = give exact commands. Open
field = give general direction. Don't give exact commands when many valid
paths exist; don't give vague guidance for fragile sequences.

## Command contracts over generated code

For fragile upstream tools, skills should reduce the agent's action space to a
small command contract. Prefer a committed wrapper script plus an exact
runnable command over prose that invites the agent to synthesize new Python or
Bash glue from internal APIs.

Use this preference whenever the task has any of these properties:

- Output correctness depends on staging configs, path isolation, seeds,
  post-processing, label remapping, or output naming.
- A generated command could mutate an upstream checkout or shared cache.
- The verifier can inspect wrapper outputs but cannot audit arbitrary generated
  code paths.
- The upstream docs expose library functions whose preconditions are easy to
  miss.

In those cases:

- Put the exact wrapper invocation near the top of `SKILL.md`.
- Say explicitly that agents should not write custom inference code for normal
  runs.
- Keep low-level algorithm notes, internal function names, and large parameter
  tables in one-hop `references/` files.
- Make wrappers own config staging, output directories, cache use, and
  validation evidence.
- Treat generated Python/Bash glue as out-of-protocol unless the task is
  specifically to develop or modify a wrapper.

The point is not to hide domain knowledge. The point is to make the normal
execution path auditable: wrapper command in, schema-checked JSON out, verifier
facts attached.

## Upstream fidelity and reference baselines

Model-wrapper skills should make the easiest documented upstream path reliable,
not silently repair model code. Runtime implementation patches are a last resort
for wrapper development, not a normal user-facing behavior.

For any skill that wraps an upstream model, CLI, or bundle:

- Follow the upstream README, requirements file, model card, or tutorial before
  changing wrapper behavior. If the upstream has a recommended environment,
  document that environment and prefer it for reproduction.
- Do not patch, monkeypatch, rewrite, or hot-copy upstream implementation files
  from `scripts/` during a normal run. If an upstream bug must be patched for an
  experiment, keep that outside the publishable skill path or make it an explicit
  development-only flag with clear evidence.
- Config staging is allowed when it is the upstream-documented way to run the
  tool, or when it restores a stale local cache to the tracked upstream config.
  Record that action in output metadata so drift is visible.
- Always check a reference baseline before diagnosing training or inference.
  For finetuning skills, evaluate the pretrained checkpoint and compare against
  the tutorial/model-card number before trusting later epochs. A bad baseline
  usually means wrong config, wrong checkpoint, data split drift, or dependency
  drift, not a learning-rate problem.
- When a checkpoint is selected by "best metric" logic, record whether its
  tensors differ from the source checkpoint. `val_at_start` can legally select
  epoch 0; without this check, a "fine-tuned" checkpoint can be identical to the
  pretrained one.
- Treat long silent phases as instrumentation problems first. Capture phase
  logs, per-epoch metrics, and GPU process/memory evidence so users can
  distinguish validation time from a hung run.

## Workflows and feedback loops

For multi-step skills, give Claude an explicit checklist and validation gate.

### Workflow pattern

````markdown
## Workflow

Copy this checklist:

```
- [ ] Step 1: Run scripts/analyze.py
- [ ] Step 2: Validate result with validators/output_schema.json
- [ ] Step 3: ...
```

**Step 1:** ...

**Step 2:** Run validation. If it fails, return to Step 1 with the reported
field path.

**Step 3:** ...
````

### Feedback-loop pattern

Whenever a critical artifact is produced, wire a validator into the workflow:

```text
generate → validate → if fails, fix and re-validate → only then proceed
```

In this repo the feedback loop is structural: `eval_engine/run.py` invokes
the wrapper, applies `validators/output_schema.json`, then runs manifest
gates. Use the same shape inside a SKILL.md when the skill is multi-step.

## Scripts: solve, don't punt

Scripts under `scripts/` should handle expected failure modes themselves
rather than emitting a vague error and hoping the agent figures it out.

**Good:**

```python
def load_volume(path):
    try:
        return nib.load(path)
    except FileNotFoundError:
        raise SystemExit(f"Input volume not found: {path}")
    except nib.filebasedimages.ImageFileError as exc:
        raise SystemExit(f"Not a valid NIfTI: {path} ({exc})")
```

**Bad:**

```python
def load_volume(path):
    return nib.load(path)   # let it crash, Claude will figure it out
```

### Other script rules

- **No voodoo constants.** Justify every threshold inline. If you can't, the
  agent can't either.
- **Use a shebang** on every `scripts/*.py` file.
- **Validate inputs** with `argparse`, `typer`, `click`, explicit `raise`, or
  `ValueError` paths.
- **Keep nesting shallow.** Pull nested staging, parsing, or post-processing
  blocks into small helpers when control flow gets deep.
- **List required packages** in the SKILL.md (or the manifest's
  `runtime.side_effects.packages`). Never assume an import is available.
- **Declare environment mutation** in
  `runtime.side_effects.environment`. A skill may install packages into a
  caller-selected environment when that behavior is explicit, but benchmarks
  and evidence runs should use a fresh venv or container when reproducibility
  matters.
- **Emit JSON on stdout.** This is a Medical AI Skills-wide invariant. See
  [`skills/AGENTS.md`](../skills/AGENTS.md).
- **Reference the script's output schema** from the manifest when the output
  is gated. See [`spec/skill_manifest.schema.json`](../spec/skill_manifest.schema.json).

## Internal NV-BASE profile

Run the same local profile used for this repo before asking for review:

```bash
make nv-base-validate
```

The Makefile defaults to `NV_BASE=nv-base`, writes reports under
`/tmp/medical-AI-skills-nvbase`, and passes `--no-dedup -c` for local no-key
validation. If `nv-base` lives in a local virtualenv, pass it explicitly:

```bash
make nv-base-validate NV_BASE=/path/to/nv-base
```

Internal CI may run the same validator without the local `--no-dedup` flag.

Keep these checks clean:

- **Quality:** short description, explicit positive/negative scope, exact
  headings above, `run_script` mention, and an `Available Scripts` table with
  `Script`, `Purpose`, and concrete `Arguments` cells.
- **PII regex:** no committed `/home/<user>/...` paths, long dotted synthetic
  identifiers, raw 10-digit IDs, or same-line decimal coordinate tuples in
  fixtures/configs.
- **Script lint:** shebangs, input validation markers, shallow control flow,
  function-based scripts, and reviewed numeric thresholds rather than stray
  literals.
- **Naming:** kebab-case directories and frontmatter names.

## Anti-patterns

- ❌ **Reimplementing upstream inference.** Skills wrap; they don't replace.
  See [`CONTRIBUTING.md`](../CONTRIBUTING.md#invocation-rule).
- ❌ **Encouraging ad hoc generated code for fragile inference.** If the agent
  has to invent Python or shell glue to run the normal workflow, the verifier
  cannot easily tell whether preprocessing, label remapping, output paths, or
  cleanup semantics changed. Commit that logic as a wrapper instead.
- ❌ **First/second person in the description.** The description is injected
  into the system prompt; perspective drift breaks selection.
- ❌ **Time-sensitive instructions** ("after August 2025, use the new API").
  Move deprecated patterns into a `Legacy` section if they must stay.
- ❌ **Offering too many options** ("you can use pydicom or pynetdicom or
  GDCM or dcmtk…"). Pick one default; mention alternatives only when an
  escape hatch is genuinely needed.
- ❌ **Windows-style paths** (`scripts\helper.py`). Forward slashes only.
- ❌ **Inventing speculative wrapper validation** when the upstream tool
  doesn't emit the needed signal. Declare the gap under `limitations`
  rather than synthesizing a check.
- ❌ **Clinical / diagnostic / regulatory claims.** This is a hard rule, not
  a style preference. See [`README.md`](../README.md#data-and-safety).
- ❌ **Inconsistent terminology.** Pick one term per concept ("evidence
  pack", "label map", "fixture") and use it throughout.

## Where checks belong

Skill-authoring style is one half of the contract; the other half is
*placement* — putting each check at the narrowest honest layer. This is
covered in [`docs/spec-model.md`](spec-model.md), but the short version is:

| Claim                                                | Put it in                          |
|------------------------------------------------------|------------------------------------|
| Output JSON structure                                | `validators/output_schema.json`    |
| Direct output fact                                   | `validation.sanity_checks`         |
| Cheap artifact invariant                             | wrapper output + manifest gate     |
| Runtime / cost / env drift                           | `eval_engine/` gates               |
| Cross-artifact or domain-quality assessment          | `verifiers/<name>/`                |
| Known missing check                                  | `limitations`                      |

Do not push a domain-quality claim into the SKILL.md narrative when it
should be a manifest gate or a paired verifier.

## Authoring checklist

Before merging a new or modified skill, verify:

### Discovery and framing

- [ ] `name:` is kebab-case, ≤ 64 chars, no reserved words
- [ ] Directory name is kebab-case and matches `name:`
- [ ] `description:` is third person, concise, and names the upstream tool
- [ ] `description:` states both what the skill does and a `Not for...` boundary
- [ ] Scope/non-scope is declared (e.g., `Engineering verification only.`)

### Body

- [ ] SKILL.md body ≤ 500 lines (target: ≤ 80 for simple wrappers)
- [ ] References are one level deep from SKILL.md
- [ ] Reference files > 100 lines have a table of contents
- [ ] Forward slashes in every path
- [ ] Execution intent is explicit for every script mention
- [ ] Fragile upstream workflows lead with a committed wrapper command, not
  generated code or internal API snippets
- [ ] `## Purpose`, `## Instructions`, `## Available Scripts`,
  `## Prerequisites`, `## Limitations`, and `## Troubleshooting` are present
- [ ] `## Instructions` includes the direct wrapper command or `run_script`
- [ ] `## Available Scripts` uses `| Script | Purpose | Arguments |`
- [ ] `## Available Scripts` lists committed script paths and includes
  `runtime.entrypoint`
- [ ] Each `## Available Scripts` `Arguments` cell is concrete; no "See Usage"
  or `runtime.args` cross-reference placeholders
- [ ] Literal `runtime.args` tokens from `skill_manifest.yaml` are visible in
  SKILL.md
- [ ] Manifest-declared inputs and outputs are named in SKILL.md, or described
  with clear equivalent terms
- [ ] Consistent terminology throughout
- [ ] No time-sensitive language

### Scripts and validation

- [ ] Scripts handle expected failures with helpful messages
- [ ] Every `scripts/*.py` file has a shebang
- [ ] Scripts include explicit input validation paths
- [ ] No unjustified raw numeric literals
- [ ] Control-flow nesting stays within the internal lint threshold
- [ ] Required packages listed in SKILL.md or the manifest
- [ ] Output schema referenced from the manifest when output is gated
- [ ] Wrapper calls upstream through the documented entry point

### Manifest coherence

- [ ] `skill_manifest.yaml` passes `spec/skill_manifest.schema.json`
- [ ] `upstream_refs` tracks the external package version, hosted model id,
  model-repo revision, or git commit that the wrapper depends on
- [ ] Side effects (`runtime.side_effects`) match what the script actually does
- [ ] `paired_verifiers[]` declared when a domain invariant needs a second pass
- [ ] `limitations` declares every check intentionally absent

### External publication

- [ ] Skill lives under root-level `skills/`, not `.claude/skills/`,
  `.codex/skills/`, `.cursor/skills/`, or another agent-specific primary path
- [ ] Directory name matches `name:` for externally published skills
- [ ] `evals/evals.json` includes positive and negative trigger cases
- [ ] `BENCHMARK.md` summarizes with-skill and without-skill results, tokens or
  time where available, and remaining gaps

Run before submitting:

```bash
make verify
make verify-skills
make verify-negative-fixtures
make list-skills
```

## Source

This guide is Medical AI Skills-specific application of the public Agent Skills
spec, Anthropic skill-authoring guidance, and NVIDIA's external skills
publishing onboarding guide. When upstream guidance changes, update this file
rather than scattering edits across individual SKILL.md files.
