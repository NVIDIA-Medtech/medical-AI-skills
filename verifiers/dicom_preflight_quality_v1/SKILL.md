---
name: dicom-preflight-quality-v1
description: Audits dicom_series_preflight evidence packs for pass/warn/fail preflight verdicts with explicit corruption, orientation, PHI, and consistency findings.
license: Apache-2.0
---

# dicom_preflight_quality_v1

## Purpose
- Audits `dicom_series_preflight` evidence packs for explicit pass/warn/fail preflight findings.
- Use this after the preflight wrapper has inspected a DICOM series and written an evidence pack. Engineering verification only.
- Manifest I/O: inputs are `dicom_series_preflight_evidence_pack`; outputs are `dicom_preflight_quality_report`.

## Instructions
- Run `scripts/grade.py` on the preflight evidence-pack directory.
- If a host agent exposes `run_script`, use `run_script("scripts/grade.py", args=["RUNS/PREFLIGHT_PACK"])`.
- Prefer the eval-engine command when you need a verifier evidence pack; use the direct Python command for quick local inspection.

## Available Scripts
| Script | Purpose | Arguments |
|---|---|---|
| `scripts/grade.py` | Primary verifier entrypoint declared by `skill_manifest.yaml`. | `EVIDENCE_PACK_DIR` |

## Prerequisites
- The target pack must contain `output.json` and `validation_summary.json`.
- The source preflight run should have completed before this verifier is called.

## Limitations
- This verifier audits recorded preflight findings; it does not re-read every DICOM instance.
- Not for clinical de-identification, PHI clearance, or regulatory sign-off.

## Troubleshooting
| Error | Cause | Fix |
|---|---|---|
| Missing pack JSON | The fixture path is not a completed evidence pack. | Point to the source preflight run directory. |
| Unexpected fail verdict | The source preflight pack recorded fail-level findings. | Inspect `preflight_gate.findings` in the verifier output. |
| No findings | The source wrapper did not emit preflight details. | Re-run the source skill and preserve `output.json`. |

Paired verifier for `skills/dicom-series-preflight`.

```bash
python verifiers/dicom_preflight_quality_v1/scripts/grade.py runs/preflight_trusted
```

```bash
make run-trusted SKILL=dicom_series_preflight \
  FIXTURE=skills/dicom-series-preflight/fixtures/clean_no_phi \
  OUT=runs/preflight_trusted
```

Reads the target pack's `output.json` and `validation_summary.json`. Emits
`overall` of `pass`, `warn`, or `fail` plus a `preflight_gate.findings` list.

Not for clinical de-identification or regulatory clearance.
