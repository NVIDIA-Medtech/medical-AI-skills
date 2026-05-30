---
name: ct-segmentation-finetune-quality-v1
description: Deterministic verifier for nv_segment_ct_finetune evidence packs. Audits the finetuned checkpoint, training trajectory, and dataset audit signals already recorded by the wrapper. Engineering verification only.
license: Apache-2.0
allowed-tools: Bash
---

# ct_segmentation_finetune_quality_v1

## Purpose
- Audits `nv_segment_ct_finetune` evidence packs for checkpoint integrity, training trajectory, baseline comparison, dataset-audit consistency, and label coverage.
- Use this after a finetune smoke, sanity, or user-data run has produced an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `nv_segment_ct_finetune_evidence_pack`; outputs are `ct_segmentation_finetune_quality_report`.

## Instructions
- Run `scripts/grade.py` on the finetune evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/FINETUNE_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain `manifest.json`, `validation_summary.json`, and `output.json`.
- Recorded checkpoint paths must still resolve if checkpoint integrity should be assessed.
- Side effects: optional `--out` writes a small JSON audit report to the caller-provided path.

## Limitations
- CPU-only audit; it does not re-run training or load the MONAI network.
- Smoke mode is treated as a plumbing oracle, not a model-quality claim.
- Not for clinical validation, regulatory submission, or patient-care decisions.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing checkpoint | The source pack did not preserve `output.finetuned_ckpt`. | Keep checkpoint artifacts with the pack before auditing. |
| Empty training trajectory | The source wrapper did not record epoch metrics. | Inspect the finetune run output and stderr before trusting the pack. |
| Dataset audit failure | Input labels/images violate recorded engineering assumptions. | Review the `input.dataset_audit` block and rerun with corrected dataset metadata. |

Second-pass auditor for evidence packs produced by
`skills/nv-segment-ct-finetune`. The wrapper proves a finetune run completed,
emitted a checkpoint, and recorded a training trajectory plus a domain audit
of the training dataset. This verifier asks whether what was recorded crosses
an engineering floor:

- **Checkpoint integrity.** The path under `output.finetuned_ckpt` resolves
  to an on-disk file of plausible size. When `torch` is available the
  verifier additionally loads the checkpoint with `map_location='cpu'` and
  reports parameter count and key shape, without instantiating the model.
- **Training trajectory.** `output.val_dice_per_epoch` is non-empty, runs the
  full declared epoch budget, `train_loss_finite==true`, and `oom==false`.
  Smoke mode skips the Dice floor because it is only a plumbing oracle. In
  `--sanity` mode the floor is the manifest-declared sanity threshold; in real
  runs it is set high enough to catch silent regressions but low enough to
  avoid conflating with publication-quality numbers.
- **Improvement over baseline.** When both `output.baseline_val_dice` and
  `output.best_val_dice` are recorded, `improvement_over_baseline` must be
  non-negative (>= 0). In sanity mode `sanity_recovery_demonstrated==true`
  is the required signal.
- **Dataset audit consistency.** The recorded `input.dataset_audit` block
  must be internally consistent: when `image_looks_like_ct==true` the HU
  range must include negative values; when `anatomy` is named and bounds are
  declared, `anatomy_volume_all_in_range==true`; orientation across samples
  is consistent.
- **Label coverage.** Every label declared in `input.label_mappings.default`
  must have shown up at least once in `input.dataset_audit.label_uniques_sampled`
  unless the run is in smoke mode (smoke fixture sampling is intentionally
  shallow).

The verifier is CPU-only, does **not** re-run training, does **not** require
GPU, and does **not** load the upstream MONAI bundle's network. A v2 that
re-runs the bundle's evaluate config against a held-out split is planned but
out of scope here.

```bash
python verifiers/ct_segmentation_finetune_quality_v1/scripts/grade.py \
  runs/<finetune_pack_dir>
```

Engineering verification only. Not for clinical interpretation, regulatory
submission, or any decision about the suitability of the finetuned model for
patient care.
