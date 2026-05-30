# Benchmark Run Record

- run id: 903885c2ae1c
- skill: medagent.nv_segment_ct v0.2.0
- benchmark manifest: .workbench_data/datasets/decathlon_spleen_with_corruption.benchmark.yaml
- started: 2026-05-11T06:53:19.772256+00:00
- finished: 2026-05-11T06:58:57.437091+00:00
- elapsed: 337.665s
- cases: 43 / 44 passed
- overall: failed (case execution/metrics)

## Aggregate Output
```json
{
  "case_count": 44,
  "pass_count": 43,
  "fail_count": 1,
  "coverage_pct": 97.727273,
  "dice": {
    "count": 43,
    "mean": 0.9355890403848778,
    "median": 0.9608419814293517,
    "p10": 0.9408993838173975,
    "min": 0.0,
    "max": 0.9722633891472897
  },
  "iou": {
    "count": 43,
    "mean": 0.8979707462746058,
    "median": 0.9246351028989609,
    "p10": 0.8883954570927524,
    "min": 0.0,
    "max": 0.9460238925813934
  },
  "hd": {
    "count": 43,
    "mean": 10.985404223096452,
    "median": 5.0,
    "p10": 4.0038561628391225,
    "min": 3.2362229509135885,
    "max": 233.56465278647045
  }
}
```

## Files
- dataset_run.jsonl: one line per case with metrics and paths
- output.json: aggregate benchmark summary

## Caveats
- Metrics are engineering-time checks, not clinical performance claims.
- Benchmark replay requires the same local case data and ground-truth paths.