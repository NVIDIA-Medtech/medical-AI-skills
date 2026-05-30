# Workflow Run Record

- run id: 80e6a1c6001f
- skill: medagent.verifiers.mr_synthesis_quality_v1 v0.1.0
- started: 2026-05-26T03:37:22.120450+00:00
- finished: 2026-05-26T03:37:23.859148+00:00
- elapsed: 1.739s
- exit code: 0

## Skill
- dir: verifiers/mr_synthesis_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/nv_generate_mr_brain_trusted_hash_current/skill_run
- sha256: 24de767d82ecf4e9fbaf0fc0bf008e7271914ccbc0df4c7d865e64c5dac447d5
- size: 9375861 bytes

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
      "reason": "skill_id='medagent.nv_generate_mr_brain'",
      "status": "pass"
    },
    {
      "name": "source_pack_passed",
      "reason": "source pack overall='passed'",
      "status": "pass"
    },
    {
      "name": "output_skill_supported",
      "reason": "output.skill='nv_generate_mr_brain'",
      "status": "pass"
    },
    {
      "name": "version_matches_skill",
      "reason": "input.version='rflow-mr-brain', expected='rflow-mr-brain'",
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
          "declared_path": "<repo>/runs/nv_generate_mr_brain_trusted_hash_current/skill_run/samples/mr_brain_mri_t1_seed1234_size256x256x256_spacing1.00x1.00x1.00_20260526043719_rank0_modality9.nii.gz",
          "exists": true,

```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.