---
name: ct-synthesis-quality-v1
description: Deterministic paired verifier for nv_generate_ct_rflow evidence packs. Audits per-sample image/mask geometry, CT-HU plausibility, mask label-set sanity, declared output-label coverage, and lung-lobe HU plausibility. CPU-only; does not re-run synthesis.
license: Apache-2.0
allowed-tools: Bash
---

# CT Synthesis Quality v1

## Purpose
- Audits `nv_generate_ct_rflow` evidence packs for synthesized image/label inventory, geometry consistency, CT-HU plausibility, mask label-set sanity, declared output-label coverage, and lung-lobe HU plausibility.
- Use this after the CT synthesis wrapper has emitted an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `nv_generate_ct_rflow_evidence_pack`; outputs are `ct_synthesis_quality_report`.

## Instructions
- Run `scripts/grade.py` on the source evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/CT_SYNTHESIS_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain `output.json` with the generated sample inventory.
- Referenced synthesized NIfTI image and label files must still exist.
- Side effects: optional `--out` writes a small JSON audit report to the caller-provided path.

## Limitations
- CPU-only audit; it does not re-run synthesis or judge clinical realism.
- HU and label floors are engineering detectors for silent failures, not publication-quality image assessment.
- Lung-lobe HU checks are narrow engineering bounds for obvious soft-tissue-valued lung masks; they are not a full organ-quality model.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing sample files | Generated image/label paths no longer resolve. | Preserve run artifacts with the evidence pack. |
| Geometry mismatch | Image and label outputs do not share shape, spacing, or affine. | Re-run the source skill and inspect generated file pairing. |
| HU plausibility failure | Synthesized image is constant or lacks expected CT intensity ranges. | Treat the pack as failed engineering evidence. |

Reads an evidence pack produced by `skills/nv-generate-ct-rflow` and emits a
pass/fail report across six tiers. CPU-only — re-reads the synthesized NIfTI
pairs the wrapper already wrote, recomputes geometry and label statistics from
the headers, and compares them against engineering floors.

## Usage

```bash
python verifiers/ct_synthesis_quality_v1/scripts/grade.py <evidence-pack-dir>
```

Tiers:

- **artifact_inventory** — every sample's image and label NIfTI resolve and
  are readable.
- **geometry_consistency** — image and label share shape, spacing, and
  affine for every sample.
- **image_hu_plausibility** — image arrays contain both air-range
  (HU < -500) and bone-range (HU > 200) voxels and are non-constant. A
  constant synthetic image is the canonical silent failure here.
- **label_set_sanity** — every observed label id is in [0, 132] (VISTA3D
  schema), at least one foreground class is present somewhere in the
  generated set, and label_id_count > 0 per sample.
- **declared_anatomy_coverage** — every `output_label_mapping[*].output_label_id`
  declared by the wrapper appears in the generated labels.
- **anatomy_hu_plausibility** — lung-lobe labels have lung-like median HU
  rather than soft-tissue-valued intensity.

Output: `verifier.id`, `target.skill_id`, per-tier verdict + failed checks,
and an `overall` verdict.

Not a clinical quality assessment. Not a substitute for human review of
synthetic medical imagery used as training data.
