# MRI T1 Preprocessing — With-vs-Without Skill Experiment

Generated: 2026-07-16T23:08:47.363104+00:00
Model: aws/anthropic/bedrock-claude-opus-4-8
Cohort: 43 T1 original + 17 3D-viable subset for steps 4-7

Production canonical runners on real T1 DICOM cohort. Steps 1–3 on 43 studies; steps 4–7 on 17 3D-viable studies (z_extent≥100mm).

## Canonical production results

| Arm | Tier-3 pass | Mean accuracy | Telemetry steps |
|---|---:|---:|---:|
| With skill | 7/7 | 1.00 | 7/7 |
| Without skill | 7/7 | 1.00 | 0/7 |

### Per-step (canonical)

| Step | With T3 | Without T3 | With acc | Without acc | With wall (s) | Without wall (s) |
|---|:---:|:---:|---:|---:|---:|---:|
| 1. DICOM → NIfTI (dcm2niix) | PASS | PASS | 1.00 | 1.00 | 12.7 | 6.4 |
| 2. PACS metadata filtering | PASS | PASS | 1.00 | 1.00 | 0.6 | 0.3 |
| 3. Series classification | PASS | PASS | 1.00 | 1.00 | 0.4 | 0.3 |
| 4. Modality filtering | PASS | PASS | 1.00 | 1.00 | 0.7 | 0.5 |
| 5. HD-BET brain-seg + Quickshear deface | PASS | PASS | 1.00 | 1.00 | 70.9 | 71.2 |
| 6. Zip packaging | PASS | PASS | 1.00 | 1.00 | 0.5 | 0.3 |
| 7. Metadata prepare | PASS | PASS | 1.00 | 1.00 | 0.5 | 0.4 |

## Opus LLM experiment (partial)

Status: **partial** · run: `/home/marc/code/medical-data-curator/.ringer-mri/runs/mri-llm-opus48-v3` · progress events: 26
- With-skill Tier-3 pass: 4/7
- Without-skill Tier-3 pass: 0/7

| Step | With T3 | Without T3 | With iters | Without iters | With source | Without source |
|---|:---:|:---:|---:|---:|---|---|
| 1. DICOM → NIfTI (dcm2niix) | PASS | FAIL | 0 | 0 | canonical_skill_runner | llm_generated |
| 2. PACS metadata filtering | PASS | — | 0 | — | canonical_skill_runner | — |
| 3. Series classification | PASS | — | 0 | — | canonical_skill_runner | — |
| 4. Modality filtering | PASS | — | 0 | — | canonical_skill_runner | — |
| 5. HD-BET brain-seg + Quickshear deface | FAIL | — | 2 | — | canonical_skill_runner | — |
| 6. Zip packaging | — | — | — | — | — | — |
| 7. Metadata prepare | — | — | — | — | — | — |

## Reproduce

```bash
/home/marc/.conda/envs/mr-rate-preprocessing/bin/python \
  /home/marc/code/medical-data-curator/.ringer-mri/generate_final_report.py
```

Engineering reproducibility protocol; not a clinical or regulatory claim.