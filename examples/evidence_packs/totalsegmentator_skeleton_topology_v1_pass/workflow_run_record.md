# Workflow Run Record

- run id: 83fb091fa63e
- skill: medagent.verifiers.totalsegmentator_skeleton_topology_v1 v0.1.0
- started: 2026-05-26T03:58:42.826563+00:00
- finished: 2026-05-26T03:58:43.811956+00:00
- elapsed: 0.985s
- exit code: 0

## Skill
- dir: verifiers/totalsegmentator_skeleton_topology_v1
- entrypoint: scripts/grade.py

## Fixture
- path: runs/totalsegmentator_skeleton_topology_source_pass
- sha256: 293d728d82affc46733ae402020fa7604f2d3d14b32c834a4fa46fb47de607bc
- size: 83711 bytes

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
  "input_inventory": {
    "label_map_path": "<repo>/runs/totalsegmentator_skeleton_topology_source_pass/predicted_seg.nii.gz",
    "label_map_readable": true,
    "label_map_shape": [
      200,
      200,
      200
    ]
  },
  "overall": "pass",
  "rib_pair_symmetry": {
    "asymmetric_pairs": [],
    "checks": [
      {
        "missing": [],
        "name": "rib_pair_bilateral_present",
        "reason": "all rib indices have both left+right",
        "status": "pass"
      },
      {
        "asymmetric": [],
        "name": "rib_pair_volume_symmetric",
        "reason": "all pairs within 40%",
        "status": "pass"
      }
    ],
    "missing_partners": [],
    "pairs": [
      {
        "left_present": true,
        "left_voxel_count": 2250,
        "ok": true,
        "relative_diff": 0.0,
        "rib_index": 1,
        "right_present": true,
        "right_voxel_count": 2250
      },
      {
        "left_present": true,
        "left_voxel_count": 2250,
        "ok": true,
        "relative_diff": 0.0,
        "rib_index": 2,
        "right_present": true,
        "right_voxel_count": 2250
      },
      {
        "left_present": true,
        "left_voxel_count": 2250,
        "ok": true,
        "relative_diff": 0.0,
        "rib_index": 3,
        "right_present": true,
        "right_voxel_count": 2250
      },
      {
        "left_present": true,
        "left_voxel_count": 2250,
        "ok": true,
        "relative_diff"
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.