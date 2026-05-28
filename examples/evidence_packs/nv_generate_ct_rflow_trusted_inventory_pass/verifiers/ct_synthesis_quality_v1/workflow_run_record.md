# Workflow Run Record

- run id: e0e922134014
- skill: medagent.verifiers.ct_synthesis_quality_v1 v0.1.0
- started: 2026-05-26T03:26:22.713857+00:00
- finished: 2026-05-26T03:26:24.593875+00:00
- elapsed: 1.88s
- exit code: 0

## Skill
- dir: verifiers/ct_synthesis_quality_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/nv_generate_ct_rflow_trusted_hash_current/skill_run
- sha256: faaac376b19a0f193ed053fee2000bbb6dcf28f9ff54d1f0b97deea1eb47b610
- size: 11590270 bytes

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
  "artifact_inventory": {
    "failed_checks": [],
    "samples": [
      {
        "image_bytes": 10984688,
        "image_path_declared": "<repo>/runs/nv_generate_ct_rflow_trusted_hash_current/skill_run/samples/sample_20260526_042618_406127_image.nii.gz",
        "image_resolved": true,
        "image_sha256": "c40cdee0ba78b1ae3c095962f8aca68898e29a4b27dc385959f4e8ba3af60fa9",
        "label_bytes": 293199,
        "label_path_declared": "<repo>/runs/nv_generate_ct_rflow_trusted_hash_current/skill_run/samples/sample_20260526_042618_406127_label.nii.gz",
        "label_resolved": true,
        "label_sha256": "608adc6afd0cff3fab1d5bbcbba3f1ae7f3030b896d73328cce661f12110096e"
      }
    ],
    "verdict": "pass"
  },
  "geometry_consistency": {
    "failed_checks": [],
    "verdict": "pass"
  },
  "image_hu_plausibility": {
    "failed_checks": [],
    "verdict": "pass"
  },
  "label_set_sanity": {
    "failed_checks": [],
    "union_label_ids_present": [
      1
    ],
    "verdict": "pass"
  },
  "overall": "pass",
  "target": {
    "evidence_pack": "runs/nv_generate_ct_rflow_trusted_hash_current/skill_run",
    "num_samples_declared": 1,
    "skill_id": "medagent.nv_generate_ct_rflow",
    "source_overall_status": "passed"
  },
  "verifier": {
    "id": "medagent.verifiers.ct_synthesis_quality_v1",
    "version": "0.1.0"
  }
}
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.