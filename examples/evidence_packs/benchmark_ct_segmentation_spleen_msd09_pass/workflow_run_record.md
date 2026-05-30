# Benchmark Run Record

- run id: 1d12e20a48e2
- skill: medagent.nv_segment_ct v0.2.0
- benchmark manifest: benchmarks/ct_segmentation_spleen_msd09.benchmark.yaml
- started: 2026-05-18T10:26:09.359846+00:00
- finished: 2026-05-18T10:26:45.874816+00:00
- elapsed: 36.515s
- cases: 5 / 5 passed
- overall: passed

## Aggregate Output
```json
{
  "case_count": 5,
  "pass_count": 5,
  "fail_count": 0,
  "coverage_pct": 100.0,
  "coverage_pct_ci_95": {
    "level": 0.95,
    "method": "wilson",
    "lower_pct": 56.551754,
    "upper_pct": 100.0
  },
  "dice": {
    "count": 5,
    "mean": 0.9579706145258683,
    "median": 0.9567655448359116,
    "p10": 0.9520963510921372,
    "min": 0.9512626369442917,
    "max": 0.9660578640796352
  },
  "iou": {
    "count": 5,
    "mean": 0.9193858442135303,
    "median": 0.9171145949981336,
    "p10": 0.9085742298818651,
    "min": 0.9070551602858848,
    "max": 0.9343442253852028
  },
  "hd": {
    "count": 5,
    "mean": 6.149269469054147,
    "median": 5.0,
    "p10": 5.0,
    "min": 5.0,
    "max": 10.0
  }
}
```

## Files
- dataset_run.jsonl: one line per case with metrics and paths
- output.json: aggregate benchmark summary

## Caveats
- Metrics are engineering-time checks, not clinical performance claims.
- Benchmark replay requires the same local case data and ground-truth paths.