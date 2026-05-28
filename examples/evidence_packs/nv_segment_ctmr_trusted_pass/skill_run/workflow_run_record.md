# Workflow Run Record

- run id: b7c04abe9f70
- skill: medagent.nv_segment_ctmr v0.1.0
- started: 2026-05-26T04:44:08.796881+00:00
- finished: 2026-05-26T04:44:18.397784+00:00
- elapsed: 9.601s
- exit code: 0

## Skill
- dir: skills/nv-segment-ctmr
- entrypoint: scripts/run_ctmr.py

## Fixture
- path: skills/nv-segment-ct/fixtures/spleen_03.nii.gz
- sha256: 18fcb3df7da91366440dc4e14a9cc814024fce4df73db999b1d32e659ad127f9
- size: 11352181 bytes

## Validation
- overall: passed
- schema: passed
- sanity: passed
- runtime: within_envelope
- cost: passed
- env_pin: skipped
- integrity: clean

## Output (excerpt)
```json
{
  "skill": "nv_segment_ctmr",
  "model": "NVIDIA-Medtech/NV-Segment-CTMR (VISTA3D CT/MRI)",
  "model_repo": "https://github.com/NVIDIA-Medtech/NV-Segment-CTMR/tree/main/NV-Segment-CTMR",
  "license": "Wrapper Apache-2.0; upstream model and repository licenses apply.",
  "input": {
    "path": "<repo>/skills/nv-segment-ct/fixtures/spleen_03.nii.gz",
    "shape": [
      512,
      512,
      40
    ],
    "ndim": 3,
    "spacing": [
      0.738281,
      0.738281,
      5.0
    ],
    "modality": "CT_BODY",
    "ground_truth_path": null
  },
  "output": {
    "shape": [
      512,
      512,
      40
    ],
    "label_prompts_requested": null,
    "label_ids_present": [
      1,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11,
      12,
      13,
      14,
      17,
      19,
      28,
      29,
      31,
      32,
      33,
      34,
      35,
      36,
      37,
      38,
      39,
      40,
      48,
      49,
      58,
      59,
      60,
      61,
      62,
      68,
      69,
      70,
      71,
      72,
      73,
      74,
      80,
      81,
      82,
      83,
      84,
      85,
      86,
      94,
      95,
      96,
      97,
      100,
      101,
      104,
      105,
      106,
      107,
      114,
      115,
      116,
      119,
      121,
      122,
      125,
      127
    ],
    "unexpected_label_ids": [],
    "label_set_valid": true,
    "label_map_loaded": true,
    "label_map_source": "
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.