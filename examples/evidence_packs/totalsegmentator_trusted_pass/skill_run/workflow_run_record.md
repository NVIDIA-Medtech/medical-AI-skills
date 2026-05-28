# Workflow Run Record

- run id: b8879b6de3b6
- skill: medagent.totalsegmentator v0.1.0
- started: 2026-05-26T04:32:07.762679+00:00
- finished: 2026-05-26T04:32:38.758409+00:00
- elapsed: 30.996s
- exit code: 0

## Skill
- dir: skills/totalsegmentator
- entrypoint: scripts/run_totalsegmentator.py

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
  "skill": "totalsegmentator",
  "model": "TotalSegmentator (Wasserthal et al.)",
  "model_repo": "https://github.com/wasserth/TotalSegmentator",
  "package_version": null,
  "task": "total",
  "task_license": "non_commercial",
  "license": "Apache-2.0 (code); weights per task \u2014 see task_license",
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
    "ground_truth_path": null
  },
  "output": {
    "shape": [
      512,
      512,
      40
    ],
    "label_prompts_requested": [],
    "label_ids_present": [
      1,
      2,
      3,
      4,
      5,
      6,
      7,
      8,
      9,
      10,
      11,
      13,
      14,
      15,
      18,
      19,
      20,
      25,
      26,
      27,
      28,
      29,
      30,
      31,
      32,
      33,
      34,
      51,
      52,
      63,
      64,
      65,
      66,
      67,
      68,
      77,
      78,
      79,
      82,
      83,
      86,
      87,
      88,
      89,
      97,
      98,
      99,
      100,
      101,
      102,
      103,
      109,
      110,
      111,
      112,
      113,
      114,
      115,
      116,
      117
    ],
    "unexpected_label_ids": [],
    "label_set_valid": true,
    "class_counts": {
      "spleen": 58441,
      "kidney_right": 49046,
      "kidney_left": 47771,
      "ga
```

## Caveats
- Best-effort replay only; not deterministic across env changes.
- Engineering-time evidence; not clinical or regulatory artefact.