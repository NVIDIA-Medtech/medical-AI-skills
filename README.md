# Medical AI Skills

Medical AI Skills is the verified skills catalog for NVIDIA MedTech. It
publishes standard, agent-callable skills that wrap medical AI tools, models,
and pipelines, starting with medical AI workflows such as medical imaging,
MONAI-based workflows, NVIDIA MedTech models, DICOM utilities, and related
tools.

The catalog makes NVIDIA MedTech capabilities easier for agents and engineers
to discover, invoke, chain, reproduce, and verify in their own environments.
The core value of this skills repository is trust: skills are published only
after passing NVIDIA verification and evaluation through a domain-aware
evaluation engine.

Each published skill is packaged with the assets needed to support
reproducibility, validation, and review, including a skill manifest, skill
card, implementation scripts, tests, validators, evaluation assets, benchmarks,
requirements, and example inputs or outputs where applicable. Engineers run
these skills locally in their own secure hospital, research, or development
environments using their own data.

This repository is a tools catalog only. It is not an agent runtime, an LLM
orchestrator, or a clinical diagnostic tool.

## What this repo publishes

Each publishable skill under `skills/` wraps **one** upstream tool through its
documented entry point. A skill ships:

- **`SKILL.md`** — when to use the skill and how to run it with your data
- **`scripts/`** — entrypoint that calls the upstream tool and emits structured
  JSON on stdout
- **`skill_manifest.yaml`** — machine contract for inputs, outputs, runtime,
  side effects, and validation gates
- **fixtures** — small synthetic or public samples for examples and evidence
  (optional fixture manifest when data is not committed)

"Skill" is the canonical term in the agentic-AI ecosystem (Anthropic Skills,
agentskills.io, NVIDIA skill-evaluation systems). The product is the **skill
catalog**; evidence and verification are how you prove a skill behaves as
declared.

## Skill format and install

Each `SKILL.md` follows the external NVIDIA agent-skill publishing format built
on the [Agent Skills spec](https://agentskills.io/specification):

- YAML frontmatter starts the file; nothing appears above it.
- `name` is the agent-facing kebab-case skill name, max 64 characters.
- `description` is specific, third-person, trigger-keyword-rich, and states
  engineering-only or non-clinical scope.
- `license` and `allowed-tools` are declared in frontmatter; tool access stays
  minimal.
- Runtime details, gates, and evidence semantics live in
  `skill_manifest.yaml`, not in frontmatter.

The canonical source path in this repo is `skills/<skill-name>/SKILL.md`.
Skill directories use the same kebab-case name as the `name` frontmatter field.
The Makefile still normalizes legacy `SKILL=snake_case` values for local
developer convenience, but new docs and examples should use kebab-case names.

There are two equivalent install paths:

**Option A — npx, from the source repo or NVIDIA catalog:**

```bash
# Interactive — pick a skill, pick an agent
npx skills add NVIDIA-Medtech/medical-AI-skills

# When mirrored to the public NVIDIA catalog
npx skills add nvidia/skills

# Non-interactive
npx skills add NVIDIA-Medtech/medical-AI-skills \
  --skill nv-segment-ct \
  --agent claude-code \
  --yes
```

The CLI copies the selected skill directory into your agent's expected
location. Engineering verification only — for the full trust harness
(evidence packs, paired verifiers, gate ladder), use Option B.

**Option B — clone the Medical AI Skills repo (full trust harness):**

1. Open the skill's `SKILL.md` (for example
   [`skills/nv-segment-ct/SKILL.md`](skills/nv-segment-ct/SKILL.md)).
2. Install prerequisites listed there (packages, GPU, upstream repos).
3. Run the documented `scripts/` entrypoint with **your** input paths and
   output directory.

Example (direct script — no eval engine required):

```bash
python skills/nv-segment-ct/scripts/run_vista3d.py \
  /path/to/volume.nii.gz \
  --output-dir /path/to/out_dir
```

To generate an **evidence pack** (audit record for CI, review, or publication),
use the local harness:

```bash
make run-skill SKILL=nv-segment-ct \
  FIXTURE=skills/nv-segment-ct/fixtures/spleen_03.nii.gz \
  OUT=runs/nv-segment-ct_demo
```

Evidence packs are optional for day-to-day use. They are the trust layer when
you need reproducibility, gate status, environment locks, and replay.

## Browse skills

Browse the committed catalog:

```bash
make list-skills    # regenerates SKILL_INDEX.md at repo root
```

The index filters by declared shape and observed gate behavior. It does not
order skills by clinical or benchmark performance.

Scope rules for new catalog entries are in
[`docs/skill-scope.md`](docs/skill-scope.md). In short: wrap real upstream
medtech tools, solve engineering tasks, ship safe fixtures, and avoid clinical
decision support or leaderboards.

## Example workflow 1 — orchestrated DICOM-to-segmentation (trust / evidence path)

Optional multi-skill run with per-step evidence packs — **not** the primary
skill-user path (that remains each skill's `SKILL.md`).

```text
DICOM series
  -> dicom_series_to_volume (metadata + geometry preflight, DICOM-to-NIfTI)
  -> nv_segment_ct (trusted)
  -> ct_segmentation_quality_v1
  -> workflow / trust summary
```

```bash
make run-workflow-ct-seg \
  WORKFLOW_INPUT=/path/to/dicom_series \
  WORKFLOW_OUT=runs/ct_dicom_seg_evidence
```

Spec: [`examples/workflows/ct_dicom_to_segmentation_evidence.yaml`](examples/workflows/ct_dicom_to_segmentation_evidence.yaml).
Details: [`examples/workflows/README.md`](examples/workflows/README.md).

## Example workflow 2 — direct `nv_generate_ct_rflow` skill invocation (no orchestrator)

A different skill: rectified-flow CT synthesis. Generates a paired 3D CT
volume + 132-class segmentation mask via NV-Generate-CTMR, called as a
standalone skill (the `agentskills.io` entry point). No workflow harness,
no upstream multi-step plumbing — just the skill emitting a structured
JSON envelope plus an image/label NIfTI pair (and a mid-slice triptych
HTML card).

```text
fixture config (body_region, anatomy_list)
  -> nv_generate_ct_rflow (run_rflow_ct.py)
  -> structured JSON envelope on stdout + image/label NIfTI pair + summary.html
```

```bash
# One-time setup (clones upstream + downloads ~5.5 GB rflow-ct weights
# and mask-candidate dataset under $HOME/nv-generate-ctmr).
git clone https://github.com/NVIDIA-Medtech/NV-Generate-CTMR.git $HOME/nv-generate-ctmr
pip install -r $HOME/nv-generate-ctmr/requirements.txt
( cd $HOME/nv-generate-ctmr && \
    python -m scripts.download_model_data --version rflow-ct --root_dir ./ )

# Run the skill
NV_GENERATE_ROOT=$HOME/nv-generate-ctmr \
  python skills/nv-generate-ct-rflow/scripts/run_rflow_ct.py \
    skills/nv-generate-ct-rflow/fixtures/abdomen_liver_spleen.json \
    --output-dir runs/nv_generate_ct_rflow_demo \
    --random-seed 0
```

To grade the resulting CT/mask pair afterwards, point the paired verifier
at the output dir:

```bash
python eval_engine/run.py verifiers/ct_synthesis_quality_v1 \
  --fixture runs/nv_generate_ct_rflow_demo \
  --out runs/nv_generate_ct_rflow_demo_quality
```

Skill contract: [`skills/nv-generate-ct-rflow/SKILL.md`](skills/nv-generate-ct-rflow/SKILL.md).
Paired verifier: [`verifiers/ct_synthesis_quality_v1/`](verifiers/ct_synthesis_quality_v1/).
Trusted anchor:
[`examples/evidence_packs/nv_generate_ct_rflow_trusted_inventory_pass/`](examples/evidence_packs/nv_generate_ct_rflow_trusted_inventory_pass/)
records a CUDA rflow-ct run plus verifier pack. The generated NIfTI volumes
are not committed; their bytes and SHA-256 hashes stay in the JSON evidence.
Related MR anchors:
[`nv_generate_mr_trusted_inventory_pass`](examples/evidence_packs/nv_generate_mr_trusted_inventory_pass/)
and
[`nv_generate_mr_brain_trusted_inventory_pass`](examples/evidence_packs/nv_generate_mr_brain_trusted_inventory_pass/)
record CUDA image-only MR runs plus `mr_synthesis_quality_v1` verifier packs
with the same no-generated-volumes policy.

## Trust and evidence

A skill can exit successfully and still produce an artefact you cannot trust
(silent orientation flips, hallucinated findings, PHI in stdout, wrong HU
windowing). Medical AI Skills encodes medtech invariants in manifests and gates;
second-pass domain checks use **paired verifiers** under `verifiers/`.

Core flow and agent-oriented commands: [`docs/agent-tasks.md`](docs/agent-tasks.md).
Gate details, pack files, and replay: [`docs/trust-and-evidence.md`](docs/trust-and-evidence.md),
[`docs/replay.md`](docs/replay.md).

## Author a skill

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for lanes and review rules, and
[`docs/authoring-skills.md`](docs/authoring-skills.md) for the authoring flow.
The short version is: place publishable skills under `skills/`, keep
`SKILL.md` spec-compliant and concise, include script/eval/benchmark artifacts
where needed for external publication, and run the local manifest and evidence
checks before review.

Quick checks before submitting:

```bash
make list-skills
make verify-skills
make verify
```

## Shipping specs

| Directory | Role |
|---|---|
| [`skills/dicom-series-preflight`](skills/dicom-series-preflight/) | GPU-free DICOM folder preflight for corruption, orientation, PHI-tag presence, and series consistency |
| [`skills/dicom-metadata-extract`](skills/dicom-metadata-extract/) | pydicom metadata extraction and limited PHI-tag flagging |
| [`skills/dicom-series-to-volume`](skills/dicom-series-to-volume/) | single-series CT DICOM to HU-scaled NIfTI |
| [`skills/mlflow-evidence-export`](skills/mlflow-evidence-export/) | privacy-limited export of Medical AI Skills evidence summaries to MLflow |
| [`skills/nv-segment-ct`](skills/nv-segment-ct/) | NVIDIA-Medtech NV-Segment-CT / VISTA3D wrapper |
| [`skills/nv-segment-ctmr`](skills/nv-segment-ctmr/) | NVIDIA-Medtech NV-Segment-CTMR CT/MRI segmentation wrapper |
| [`skills/nv-segment-ct-finetune`](skills/nv-segment-ct-finetune/) | Auto-configuring VISTA3D continual-learning finetune via `monai.bundle run` |
| [`skills/nv-generate-ct-rflow`](skills/nv-generate-ct-rflow/) | NV-Generate-CTMR rectified-flow synthesis of paired CT image + 132-class mask |
| [`skills/nv-generate-mr`](skills/nv-generate-mr/) | NV-Generate-CTMR rflow-mr synthetic MRI generation |
| [`skills/nv-generate-mr-brain`](skills/nv-generate-mr-brain/) | NV-Generate-CTMR rflow-mr-brain synthetic brain MRI generation |
| [`skills/nv-generate-mr-brain-finetune`](skills/nv-generate-mr-brain-finetune/) | NV-Generate-CTMR rflow-mr-brain diffusion-UNet finetuning from a user datalist |
| [`skills/nv-generate-vae-finetune`](skills/nv-generate-vae-finetune/) | NV-Generate-CTMR MAISI VAE finetuning from CT/MRI datalists |
| [`skills/nv-reason-cxr`](skills/nv-reason-cxr/) | NV-Reason-CXR-3B inference on a user-provided chest X-ray PNG/JPEG |
| [`verifiers/skill_completeness_v1`](verifiers/skill_completeness_v1/) | structural and manifest-spec verifier |
| [`verifiers/dicom_metadata_quality_v1`](verifiers/dicom_metadata_quality_v1/) | paired verifier for DICOM metadata evidence packs and PHI-scope disclosure |
| [`verifiers/dicom_preflight_quality_v1`](verifiers/dicom_preflight_quality_v1/) | paired verifier for DICOM preflight evidence packs |
| [`verifiers/dicom_volume_quality_v1`](verifiers/dicom_volume_quality_v1/) | paired verifier for DICOM-to-NIfTI geometry and voxel evidence |
| [`verifiers/ct_segmentation_quality_v1`](verifiers/ct_segmentation_quality_v1/) | paired verifier for nv_segment_ct anatomy plausibility + optional GT Dice |
| [`verifiers/ct_segmentation_finetune_quality_v1`](verifiers/ct_segmentation_finetune_quality_v1/) | paired verifier for nv_segment_ct_finetune checkpoint + training trajectory + dataset audit |
| [`verifiers/ct_synthesis_quality_v1`](verifiers/ct_synthesis_quality_v1/) | paired verifier for nv_generate_ct_rflow image/mask pair geometry, HU plausibility, label-set sanity |
| [`verifiers/mr_synthesis_quality_v1`](verifiers/mr_synthesis_quality_v1/) | paired verifier for nv_generate_mr and nv_generate_mr_brain image artifact geometry and numeric sanity |
| [`verifiers/nv_reason_cxr_quality_v1`](verifiers/nv_reason_cxr_quality_v1/) | paired verifier for nv_reason_cxr image/hash binding, runtime identity, and forbidden-phrase guardrails |

## Repository map

| Path | Purpose |
|---|---|
| [`skills/`](skills/) | publishable wrappers (primary product) |
| [`verifiers/`](verifiers/) | skill-shaped auditors for second-pass trust |
| [`eval_engine/`](eval_engine/) | evidence-pack harness (not a public CLI) |
| [`spec/`](spec/) | manifest and evidence-pack schemas |
| [`examples/`](examples/) | curated reference evidence, not normal run output |
| [`benchmarks/`](benchmarks/) | dataset protocols only |
| [`tools/`](tools/) | maintainer utilities (e.g. token-cost measurement) |
| [`runs/`](runs/) | local generated output (gitignored) |

## Commands

```bash
make help            # common target list
make help-all        # full target list
make run-skill SKILL=dicom-metadata-extract \
  FIXTURE=skills/dicom-metadata-extract/fixtures/sample_ct.dcm \
  OUT=runs/demo
```

Agents: see [`docs/agent-tasks.md`](docs/agent-tasks.md) for the task → command map.

## Useful reading

- [`docs/using-skills.md`](docs/using-skills.md) — discover and run skills with your data
- [`docs/authoring-skills.md`](docs/authoring-skills.md) — add a publishable wrapper
- [`docs/skill-scope.md`](docs/skill-scope.md) — what belongs in the catalog
- [`docs/trust-and-evidence.md`](docs/trust-and-evidence.md) — manifests, packs, verifiers
- [`docs/release-readiness.md`](docs/release-readiness.md) — publication threshold, readiness snapshot, review-packet loop
- [`ARCHITECTURE.md`](ARCHITECTURE.md) — object model and gate ladder
- [`AGENTS.md`](AGENTS.md) — map for coding agents
- [`docs/agent-tasks.md`](docs/agent-tasks.md) — agent task → read → command
- [`docs/spec-model.md`](docs/spec-model.md) — where each check belongs
- [`docs/agentskills-adoption.md`](docs/agentskills-adoption.md) — agentskills.io spec + npx distribution
- [`docs/with-vs-without-skill-experiment.md`](docs/with-vs-without-skill-experiment.md) — `nv_*` with-vs-without comparison docs and correction-step protocol
- [`docs/with-vs-without-authoring.md`](docs/with-vs-without-authoring.md) — add a fair with-vs-without comparison for a new skill
- [`docs/skill-vs-readme-current-results-analysis.md`](docs/skill-vs-readme-current-results-analysis.md) — current audited SKILL.md-vs-upstream-docs result summary
- [`examples/README.md`](examples/README.md) — committed reference packs

## Data and safety

Do not commit patient data, DICOM volumes, large NIfTI volumes, DICOM SEG files,
model weights, or large generated run artifacts. Commit only small synthetic
fixtures, benchmark manifests, and small evidence packs.

Generated outputs are engineering artifacts, not clinical endorsements.
Medical AI Skills is not a clinical, diagnostic, or regulatory tool.

## License

Apache License 2.0. Copyright 2026 NVIDIA Corporation. See [`LICENSE`](LICENSE).
Each shipping spec declares its own license.

## References

- Holoscan SDK: <https://docs.nvidia.com/holoscan/index.html>
- MONAI: <https://github.com/Project-MONAI/MONAI>
- NVIDIA-Medtech: <https://github.com/NVIDIA-Medtech>
- pydicom: <https://pydicom.github.io/>
- NiBabel: <https://nipy.org/nibabel/>
