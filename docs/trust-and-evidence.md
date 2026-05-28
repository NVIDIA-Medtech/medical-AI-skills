# Trust and evidence

Explanation of how manifests, the eval engine, evidence packs, and verifiers
make published skills **trustworthy**. For running a skill on your own data
without generating a pack, see [`using-skills.md`](using-skills.md).

## Two paths

| Path | When | Mechanism |
|---|---|---|
| **Use** | Day-to-day engineering | `SKILL.md` + `scripts/` + your data |
| **Trust** | CI, review, publication, regression | fixture + `eval_engine` → evidence pack |

Verification is a **property** of a skill, not the repo's primary product.

## Core flow

```text
skill + user input             -> useful local result
skill + manifest + fixture     -> evidence pack
evidence pack + verifier       -> verifier evidence pack
```

- **Manifest** (`skill_manifest.yaml`) declares inputs, outputs, runtime envelopes,
  side effects, sanity checks, and optional `paired_verifiers[]`.
- **Eval engine** (`eval_engine/`) invokes the skill subprocess, applies generic
  gates, and writes the pack. Skills do not import `eval_engine/`.
- **Evidence pack** records command, hashes, `output.json`, gate status, cost,
  environment lock, integrity scan, and `replay.sh`. File list: [`replay.md`](replay.md).
- **Verifier** — skill-shaped spec under `verifiers/` that audits a skill directory
  or pack when domain quality needs a second pass.

Declaring `paired_verifiers[]` is enforced by lint and completeness audit; running
every domain verifier on every skill run is not automatic unless you invoke it.

Use the trusted-run path to bundle the skill and every implemented paired
verifier in one directory:

```bash
make run-trusted SKILL=<name> FIXTURE=<path> OUT=<dir>
```

Committed reference:
`examples/evidence_packs/dicom_series_preflight_trusted_pass/` is the small
GPU-free trusted-run anchor. It includes `skill_run/`, a
`dicom_preflight_quality_v1` verifier pack, and `trust_summary.json`.

Layout: `<dir>/skill_run/` (full skill pack), `<dir>/verifiers/<id>/` (one full
pack per verifier), and `<dir>/trust_summary.json` linking them. Planned
verifiers and env-skipped verifiers surface as explicit gaps in the summary,
so missing coverage cannot be mistaken for a clean run. Current trust summaries
also include pack hashes, implemented verifier IDs, planned/env-skipped gap
groups, and warning findings so a reviewer can bind the verdict to the nested
evidence packs without opening each file first. The summary's `overall` field
is `passed | failed | warn | gap | no_verifiers`.
Verifier rows also include semantic failure/warning counts derived from the
verifier `output.json` check blocks when available, so domain-floor failures are
visible before opening the nested verifier pack.
`make validate-pack PACK=<trusted-run-dir>` validates the summary and every
nested skill/verifier pack referenced by it.

Trusted-run spawns one `python eval_engine/run.py` subprocess per skill and
per implemented verifier (N+1 cold-starts for N verifiers). That isolation is
the point — a verifier crash cannot pollute the skill pack — but expect a few
seconds of fixed overhead beyond the work itself.

Multi-step workflows can mark a step with `trusted: true` in the workflow YAML
so `eval_engine/run_workflow.py` invokes `run_trusted` for that step.

Flagship workflows (see [`examples/README.md`](../examples/README.md)):

- **A1 onboarding:** `examples/workflows/dicom_preflight_gate.yaml` —
  `dicom_series_preflight` + `dicom_preflight_quality_v1` (pass / warn / fail,
  no GPU).
- **CT segmentation:** `examples/workflows/ct_dicom_to_segmentation_evidence.yaml`
  — convert + trusted `nv_segment_ct`.
- **HoloHub imaging:** `examples/workflows/holohub_imaging_evidence.yaml`
  — trusted `holohub_imaging_ai_segmentator` + flow benchmark + `stream` summary linkage.
- **HoloHub endoscopy (variant):** `examples/workflows/holohub_endoscopy_evidence.yaml`
  — trusted verifier; detection export via log/sidecar.
- **Stream linkage:** `workflow_summary.json` → `stream` block aggregates
  `holohub_flow_benchmark` latency paths, logger/gpu artifacts, and contract status.

`trust_summary.overall` may be `warn` when a verifier reports advisory findings
(e.g. PHI tags present) without hard failures.

For one-file human review, render a review packet from an existing pack or
trusted-run directory:

```bash
make review-packet PACK=<pack-or-trusted-run-dir>
```

The review packet is a generated view, not a source of truth. It reads the
existing pack files, summarizes gates, verifier coverage, provenance gaps,
trace events, artifacts, and manifest limitations, then points reviewers back
to the underlying pack when a finding needs deeper inspection. Generated
packets belong under `runs/` unless a curated example is explicitly promoted.
The target writes to `runs/review_packets/<pack-name>.md` by default; pass
`REVIEW_PACKET_OUT=<path>` to choose a release-specific generated path.

When changing trace fields, inventory current `agent_run_trace.jsonl` records
before adding or tightening a schema:

```bash
python tools/inventory_trace_shapes.py examples --format markdown
```

The inventory is also generated from existing files and should be treated as a
compatibility report, not an enforcement mechanism.
Current packs validate each trace record against
`spec/evidence_pack/agent_run_trace.schema.json`; historical alias-only records
are accepted only through `make validate-pack VALIDATE_PACK_ARGS='--allow-legacy'`.
New tool-call start records include sanitized `command` and `cwd` fields, which
review packets surface as the quickest way to understand what executable path
and working directory produced a pack.

## Provenance

Every full skill run also writes `provenance.json` to the pack, capturing what
the manifest **promised** vs. what the host actually showed:

- GPU and CUDA identity from `nvidia-smi` and `nvcc`: GPU model, driver
  version, compute capability, MIG mode, memory total/free at start, and the
  CUDA toolkit release when present.
- Before/after deltas for every declared `runtime.side_effects.local_writes`
  and `home_writes` path: created / modified / grew / unchanged / removed.
  Templated paths (containing `<...>`) are reported as `untracked` so they
  remain visible as gaps.
- `container.requires_docker` mirrors the manifest; observed image digests are
  not yet captured (skill-side instrumentation will fill this in).
- `network.declared_endpoints` mirrors the manifest; observed traffic is not
  yet captured.

Provenance is host-level: it does not enter the container or attach a packet
capture. Use it to spot "declared no home writes but the run filled my HF
cache" or "declared CUDA-only but ran on CPU."

## Gates (floor)

Generic gates live in `eval_engine/` and are opt-in via the manifest:

- preflight, JSON schema, sanity checks
- runtime and cost envelopes
- env pin, factual echo, model identity (when declared)
- integrity scan, replay metadata
- reproducibility audit via `validation.reproducibility`

Medical invariants that need tool-specific signal belong in manifest gates or
wrapper output when honest; otherwise use a verifier. See [`spec-model.md`](spec-model.md).

## Reproducibility

`make verify-skills` now includes `eval_engine.reproducibility` after the
completeness audit. Specs with `validation.reproducibility.mode: repeat` are
run twice on their declared fixture. The audit fails on gate-status drift,
semantic output drift, or changed hashes for emitted artifact paths such as
label maps and checkpoints.

Specs with unavoidable external runtimes use `mode: preflight` plus a written
reason. That mode repeats the declared input/env boundary check only; it is a
visible gap, not proof that a GPU/model/container run is reproducible. Promote
full evidence packs for those runs and compare their artifact hashes before
making stronger claims.

## Dependency drift

For wrappers around installed upstream tools, package drift can silently change
behavior even when the command still runs. A skill that was authored against
`monai==1.4` but runs under a future major version may no longer satisfy the
same contract.

Use `validation.env_pin` for direct **behavioral** dependencies:

- model bundles and inference frameworks
- file-format libraries such as DICOM or NIfTI readers/writers
- SDKs whose versions affect output semantics

Do not pin every transitive dependency by default. Pin tightly enough to catch
major behavior changes and loosely enough to avoid patch-version churn. LLM
skills usually rely on `runtime.llm`, model identity, and factual-echo gates
instead of Python package pins.

## Commands

```bash
make run-skill SKILL=nv_segment_ct \
  FIXTURE=skills/nv-segment-ct/fixtures/spleen_03.nii.gz \
  OUT=runs/demo
make verify          # smoke-test harness + canonical pack diff
make verify-skills   # structural audit + repeat/preflight reproducibility audit
make diff RUN_A=examples/evidence_packs/nv_segment_ct_pass RUN_B=runs/demo
```

`make verify-skills` includes one known-bad calibration fixture and the
reproducibility audit. The expected result is `real specs: N/N pass, 0 fail,
0 advisory issues`, `negative_sloppy_skill: fail (expected fail)`, and a
reproducibility summary with every target passing its declared repeat or
preflight check.

## Examples vs runs

- **`runs/`** — local generated output (gitignored).
- **`examples/`** — curated reference evidence for teaching and regression, not
  the normal artifact of using a skill in production.

Curated examples should keep verifier-critical artifact paths portable:
repo-relative paths for committed fixtures, pack-relative paths for generated
files that are allowed in git, and explicit limitations for external artifacts
that cannot be committed. Verifiers tolerate legacy `<repo>` placeholders and
some stale checkout-root paths when the matching artifact exists locally, but
that compatibility path is not a substitute for promoting a complete,
reviewable pass pack.

## LLM-mediated runs and agent backends

`eval_engine/run_llm_skill.py` is the minimal **LLM dispatch smoke test**: an LLM
reads `SKILL.md`, must call one approved local tool, and produces a nested
`skill_run/` evidence pack via `eval_engine/run.py`.

[`tools/nat_audit/`](../tools/nat_audit/) uses NeMo Agent Toolkit for richer
agent workflow profiling (token cost, realistic multi-tool overhead). NAT is an
optional maintainer adapter under `tools/`, not core harness infrastructure.

## Further reading

- [`ARCHITECTURE.md`](../ARCHITECTURE.md) — object model and directory boundaries
- [`examples/README.md`](../examples/README.md) — committed packs and studies
- [`spec-model.md`](spec-model.md) — enforcement map
