# Contributing

This repo publishes **agent-callable medtech skills** that users run
with their own data and environment. It also accepts skill-shaped **verifiers**
and supporting harness changes. It does not accept generic agent evaluators,
clinical claims, or homegrown reimplementations of upstream inference.

## Quick contribution workflow

Use these steps to take an agent-assisted change from an idea to a pull
request. For skill-specific detail, follow
[`docs/authoring-skills.md`](docs/authoring-skills.md).

### Roles

- An agent may research, author all source-controlled skill components and
  evals, run local checks, diagnose source failures, and draft the submission.
- The contributing engineer defines the intended behavior and reviews the
  actual diff, fixtures, eval expectations, outputs, dependencies, side
  effects, provenance, and limitations.
- A maintainer handles repository access, `/nvskills-ci`, managed-service
  failures, merge approval, and catalog publication.

### 1. Clone and create a source-repository branch

Start from `dev`:

```bash
git clone https://github.com/NVIDIA-Medtech/medical-AI-skills.git
cd medical-AI-skills
git switch dev
git pull --ff-only origin dev
git switch -c <github-user>/<short-topic>
```

In a fresh clone, the source-repository remote is `origin`. For an existing
checkout, skip the first two commands, use `git remote -v` to identify the
remote that points to `NVIDIA-Medtech/medical-AI-skills`, and call it
`<source-remote>` below. Replace `origin` in the pull command when necessary.
Pushing requires source-repository write access; ask a maintainer if access is
missing or `git push` is denied.

Changes under `skills/` require NVSkills CI. Its managed signing flow currently
requires the pull request head to be a source-repository branch, so a fork pull
request is not a workaround. See the public
[`NVIDIA/skills` required-status workflow](https://github.com/NVIDIA/skills/blob/main/.github/workflows/require-nvskills-status.yml).

### 2. Define and author the contribution

An agent may write the skill documentation, manifest, wrapper, schema,
synthetic fixtures, tests, `evals/evals.json`, and scenario YAML. The engineer
confirms the medtech task, upstream tool and documented entry point, expected
inputs and outputs, important failure modes, fixture safety and provenance,
dependencies, side effects, non-goals, and any licensing or IP implications.

Maintainer approval is not required to begin. Ask for early feedback only when
catalog fit, a clinical boundary, licensing, or a shared schema or
`eval_engine` change is unclear.

Do not create or edit `BENCHMARK.md`, `skill-card.md`, or `skill.oms.sig`;
NVSkills CI generates or refreshes these publication artifacts.

### 3. Validate locally and review the result

Run the exact command in `SKILL.md` against the smallest safe fixture. Then use
the applicable focused checks:

```bash
make run-skill SKILL=<name> FIXTURE=<fixture> OUT=runs/<name>_smoke
make validate-skill SCENARIO=skills/<name>/evals/<scenario>.yaml
make audit-skill SKILL=<name>
make skill-evaluator-validate
```

Keep generated output under `runs/`. Finish with the repository checks in
[Run before submitting](#run-before-submitting).

The engineer reviews the actual code, input, and output—not only an agent
summary—and confirms:

- the documented upstream interface is used and failure cases fail clearly
- output matches its schema, artifacts exist, and eval expectations are sound
- fixtures contain no patient data, secrets, local paths, weights, or large
  medical volumes
- `SKILL.md`, the manifest, runtime behavior, dependencies, side effects,
  provenance, claims, and limitations agree

For GPU, model, Docker, dataset, or external-service requirements, the engineer
arranges or supervises an approved integration smoke test and records what was
and was not tested in the pull request.

### 4. Sign off, push, and open the pull request

An agent may prepare these commands when requested, but the engineer must
inspect the staged diff and authorize the DCO sign-off:

```bash
git add <intended-files>
git diff --cached
git commit -s -m "Add <skill or change>"
git push -u <source-remote> <github-user>/<short-topic>
```

Open the pull request against `dev`. State the purpose and upstream tool,
fixture provenance, dependency or licensing changes, commands and results,
unavailable checks, and known limitations. See [Signing your work](#signing-your-work)
for the DCO policy.

### 5. Let the maintainer run NVSkills CI

After review feedback is resolved and skill content is stable, a maintainer or
administrator comments:

```text
/nvskills-ci
```

`make skill-evaluator-validate` is a local preflight; it does not reproduce or
replace the managed evaluation and signing service. When NVSkills CI finishes,
the engineer reviews `BENCHMARK.md` and `skill-card.md`, and the maintainer
confirms the generated-only diff, successful status, and `skill.oms.sig`.
Neither edits the generated artifacts directly.

If a failure points to source, manifests, evals, or fixtures, reproduce and fix
it locally before a maintainer reruns `/nvskills-ci`. The maintainer handles
dispatch, permission, service, signing, or non-reproducible failures. Rerun
managed CI after any later skill-content change.

### 6. Merge and publish

The maintainer merges after engineer review, repository checks, and managed
validation pass. A new skill also needs an explicit entry in
[`NVIDIA/skills`' Medical AI component](https://github.com/NVIDIA/skills/blob/main/components.d/medical-ai-skills.yml),
which the maintainer owns. Adding the source directory alone does not publish
the skill in the catalog.

## Where to put work

```text
Does it help a user call a medtech tool on their own data?
  -> skills/<name>/
Does it audit a skill directory or evidence pack?
  -> verifiers/<name>/
Does it add a generic gate, runner, diff, or pack writer behavior?
  -> eval_engine/
Does it change the manifest or evidence-pack contract?
  -> spec/ (+ docs/spec-model.md)
Does it add a curated proof, tutorial pack, or drift example?
  -> examples/
Does it define a shared dataset protocol without committed data?
  -> benchmarks/
Does it support maintainers, profiling, or experiments?
  -> tools/
Is it generated local output?
  -> runs/
```

See [`docs/skill-scope.md`](docs/skill-scope.md) for catalog admission rules,
[`docs/authoring-skills.md`](docs/authoring-skills.md) for the default
wrapper-skill path, [`docs/agent-tasks.md`](docs/agent-tasks.md) for the
agent task → command map, and [`AGENTS.md`](AGENTS.md) for agent-oriented rules.

## Skill scope

Publishable skills must:

- wrap a real upstream tool through its documented entry point
- solve a medtech engineering task, not a clinical decision
- expose at least one contract-worthy silent-failure mode
- ship safe synthetic/public fixtures or fixture manifests
- declare `validation.env_pin` for direct behavioral dependencies

Do not add clinical decision-support skills, patient-facing chatbots, generic
LLM utilities, model leaderboards, closed proprietary wrappers without
redistributable fixtures, or EHR / FHIR write-path integrations. See
[`docs/skill-scope.md`](docs/skill-scope.md) for the full rationale.

## Skill requirements

Each `skills/<name>/` directory needs:

- `SKILL.md` with valid frontmatter and concise invocation guidance
- `skill_manifest.yaml` with inputs, outputs, entrypoint, side effects, and
  validation gates
- `scripts/` entrypoint that calls the upstream tool the documented way
- small synthetic/public fixtures, never patient data
- `validators/output_schema.json` when output JSON is gated
- focused tests for wrapper parsing or domain invariants when useful

The manifest grammar is checked by `spec/skill_manifest.schema.json`.

SKILL.md frontmatter, naming, description style, body-length budget, and
progressive-disclosure rules are codified in
[`docs/skill-authoring-best-practices.md`](docs/skill-authoring-best-practices.md).
That doc is the source of truth for SKILL.md authoring — applied from
Anthropic's
[Skill authoring best practices](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices).

After authoring a skill, write at least one scenario at
`skills/<name>/evals/<scenario>.yaml` and confirm
`make validate-skill SCENARIO=skills/<name>/evals/<scenario>.yaml` produces
a paired report under `runs/validate_skill/`. v0 supports the mock backend
only; the with-arm should show observable lift over the without-arm in the
assertion table. The scenario YAML is the runnable companion to the existing
prose `evals/evals.json`.

## Contribution lanes

Public contributions should fit one lane:

| Lane | Where | Required proof |
|---|---|---|
| New wrapper skill | `skills/<name>/` | manifest, schema, fixture, tests or runnable smoke pack |
| New verifier | `verifiers/<name>/` | positive and negative fixtures plus tests |
| New eval_engine gate | `eval_engine/` | manifest opt-in or baseline safety rationale plus tests |
| New example | `examples/` | curated pack or fixture with a short reason it should be committed |
| New benchmark manifest | `benchmarks/` | dataset protocol only; no cases or ground truth committed |
| Repo support tool | `tools/<name>/` | README, reproducible command, no patient data; not a skill runtime dependency |
| Spec/docs change | `spec/`, `docs/`, root docs | updated references and verification run |

Everything generated during development goes under `runs/`, which is
gitignored. Do not create or commit a top-level `outputs/` directory.

## Record budget

Keep git history focused on durable source, schemas, compact docs, and curated
proof packs. Regenerable records belong under ignored local output paths:
provider responses, per-repeat study JSON, detailed generated reports, raw
execution logs, large provenance tails, temporary venvs, downloaded models, and
runtime environments.

Do not commit generated with-vs-without detail reports under `docs/` or raw
with-vs-without records under `examples/studies/with_vs_without_skill/`. The
report writer regenerates detail reports under `runs/with_vs_without_nv/reports/`
and keeps only `docs/with-vs-without-skill-experiment.md` as the checked-in
summary. Repeated experiment PRs should update
`tools/with_vs_without/data/nv_model_study_invariants.json`, which records
stable protocol/input/outcome fingerprints instead of user-environment records.
`make lint` fails if generated-record paths are tracked.

## Verifier requirements

Use a verifier when a claim needs a second pass over an evidence pack or
artifacts. A verifier is a peer spec under `verifiers/`, not eval_engine code.
Verifiers use the same skill-shaped contract so the eval engine and agents can
run them consistently; they are specialized trust artifacts, not the default
publishable medtech skill users select for their own data.

A verifier must ship the same spec surface as a skill:

- `SKILL.md`
- `skill_manifest.yaml`
- output schema
- positive and negative fixtures
- tests that assert metrics and failure reasons

Target skills declare verifier dependencies with `paired_verifiers[]`:

```yaml
paired_verifiers:
  - id: medagent.verifiers.ct_segmentation_quality_v1
    status: implemented
    checks:
      - output label map exists
      - affine and shape match the source image
      - anatomy volumes are within configured plausibility bounds
```

`status: planned` is only an explicit gap declaration. Canonical MVP demos
that claim domain-quality evidence need an implemented verifier or a direct
manifest gate.

## Where checks belong

Use the narrowest honest layer:

| Check | Location |
|---|---|
| JSON structure | `validators/output_schema.json` |
| Simple output fact | `validation.sanity_checks` |
| Runtime, cost, dependency drift | manifest gates consumed by `eval_engine/` |
| Cheap artifact invariant the wrapper can compute directly | wrapper output plus manifest gate |
| Second-pass domain or benchmark assessment | `verifiers/` |
| Missing check | `limitations` |

Do not hide a missing domain invariant by adding speculative wrapper logic.
Emit the facts the upstream tool produces and fail loudly when the evidence is
insufficient.

## Invocation rule

Wrappers call external tools through the upstream-recommended entry point:

- NVIDIA-Medtech HuggingFace releases use the model-card helper.
- MONAI bundles use MONAI bundle APIs or CLI.
- pydicom/nibabel wrappers may call those library APIs directly.

A PR that replaces a documented upstream invocation with a local inference
loop should be rejected unless the upstream itself documents that loop.

## Coexistence

Multiple specs can coexist when they wrap different upstream tools,
different major versions, materially different outputs/gates, or materially
different side-effect profiles. Replacement is only justified when the new
wrapper is closer to upstream documentation, covers the same spec, and has
an equal or smaller side-effect profile.

Spec comparison filters by declared shape and observed gate behavior. It
does not order skills by performance.

## Side effects

Declare host changes in `runtime.side_effects`: packages, cache writes, Docker,
network endpoints, GPU requirements, and required env vars. The side-effect
gate is not fully enforced yet, so misleading declarations are review blockers.

Reject skills that require `sudo`, modify shell startup files, write into
system paths, or install outside the active environment.

## Examples policy

`examples/` is open to external contributions, but it is curated. Canonical
single-run evidence packs stay in `examples/evidence_packs/`; narrative
multi-pack demos stay in `examples/studies/`. Accept examples that teach or
test Medical AI Skills:

- a small canonical pass pack for a new or changed spec
- a negative pack that proves a gate catches a real failure mode
- a drift pack that demonstrates meaningful environment or payload drift
- a study that compares a small set of related evidence packs

Do not submit arbitrary `runs/` output. Do not commit patient data, large
DICOM/NIfTI/DICOM SEG artifacts, model weights, recordings, or provider logs
with secrets. A committed evidence pack must be small enough to
review, replayable from its `replay.sh`, and referenced from
`examples/README.md` when it is meant to be canonical.

Verifier-specific anti-patterns and negative fixtures belong under the owning
`verifiers/<name>/fixtures/` directory, not under `examples/`.

## Tools policy

`tools/` is for maintainer utilities (profilers, adapter experiments, measurement
harnesses). Examples: [`tools/nat_audit/`](tools/nat_audit/) for agent token-cost
measurement.

Requirements:

- Ship a `README.md` with purpose, prerequisites, and exact reproduce commands.
- Use a dedicated venv or documented install path when dependencies conflict
  with repo v0 policy (for example NeMo Agent Toolkit under `tools/nat_audit/`).
- Do not commit patient data, secrets, API keys, or large generated outputs.
- Do not add `tools/` imports to `skills/` or `verifiers/` unless the skill
  manifest and `SKILL.md` explicitly document the dependency.

Promotion: move generic, tested logic into `eval_engine/`, `spec/`, or `docs/`
only when it becomes shared infrastructure, not a one-off experiment.

## Signing your work

We require that all contributors "sign-off" on their commits. This certifies
that the contribution is your original work, or you have rights to submit it
under the same license, or a compatible license.

Any contribution which contains commits that are not Signed-Off will not be
accepted.

To sign off on a commit you simply use the `--signoff` (or `-s`) option when
committing your changes:

```bash
$ git commit -s -m "Add cool feature."
```

This will append the following to your commit message:

```text
Signed-off-by: Your Name <your@email.com>
```

Full text of the DCO (https://developercertificate.org/):

```text
Developer Certificate of Origin
Version 1.1

Copyright (C) 2004, 2006 The Linux Foundation and its contributors.

Everyone is permitted to copy and distribute verbatim copies of this
license document, but changing it is not allowed.


Developer's Certificate of Origin 1.1

By making a contribution to this project, I certify that:

(a) The contribution was created in whole or in part by me and I
    have the right to submit it under the open source license
    indicated in the file; or

(b) The contribution is based upon previous work that, to the best
    of my knowledge, is covered under an appropriate open source
    license and I have the right under that license to submit that
    work with modifications, whether created in whole or in part
    by me, under the same open source license (unless I am
    permitted to submit under a different license), as indicated
    in the file; or

(c) The contribution was provided directly to me by some other
    person who certified (a), (b) or (c) and I have not modified
    it.

(d) I understand and agree that this project and the contribution
    are public and that a record of the contribution (including all
    personal information I submit with it, including my sign-off) is
    maintained indefinitely and may be redistributed consistent with
    this project or the open source license(s) involved.
```

## Run before submitting

```bash
make lint
make test
make list-skills
make verify
make verify-skills
make verify-negative-fixtures
```

If a check is intentionally absent, document it under the manifest's
`limitations` field.
