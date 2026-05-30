# Workflow Run Record

- run id: 8ac7e0a948ec
- skill: medagent.verifiers.mr_synthesis_quality_v1 v0.1.0
- started: 2026-05-26T03:36:38.640467+00:00
- finished: 2026-05-26T03:36:39.324659+00:00
- elapsed: 0.684s
- exit code: 0

## Skill
- dir: verifiers/mr_synthesis_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/nv_generate_mr_trusted_hash_current/skill_run
- sha256: 51a858d643662c407cc6fd76917dc6988b9e80d81e910b2616e3958279651300
- size: 7041949 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: skipped
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "checks": [
    {
      "name": "target_skill_matches",
      "reason": "skill_id='medagent.nv_generate_mr'",
      "status": "pass"
    },
    {
      "name": "source_pack_passed",
      "reason": "source pack overall='passed'",
      "status": "pass"
    },
    {
      "name": "output_skill_supported",
      "reason": "output.skill='nv_generate_mr'",
      "status": "pass"
    },
    {
      "name": "version_matches_skill",
      "reason": "input.version='rflow-mr', expected='rflow-mr'",
      "status": "pass"
    },
    {
      "name": "modality_supported",
      "reason": "modality='mri_t1', code=9",
      "status": "pass"
    },
    {
      "name": "official_entrypoint_matches",
      "reason": "official_entrypoint='python -m scripts.diff_model_infer'",
      "status": "pass"
    },
    {
      "name": "subprocess_succeeded",
      "reason": "exit_code=0",
      "status": "pass"
    },
    {
      "name": "model_inventory_present",
      "reason": "model_inventory.all_present=True",
      "status": "pass"
    },
    {
      "name": "samples_declared",
      "reason": "num_samples=1, samples=1",
      "status": "pass"
    },
    {
      "images": [
        {
          "all_finite": true,
          "declared_path": "<repo>/runs/nv_generate_mr_trusted_hash_current/skill_run/samples/mr_mri_t1_seed0_size128x256x256_spacing1.25x1.00x1.00_20260526043636_rank0_modality9.nii.gz",
          "exists": true,
          "finite_fraction": 1.0,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.
