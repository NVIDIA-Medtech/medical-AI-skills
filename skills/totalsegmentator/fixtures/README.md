# TotalSegmentator Fixture Protocol

This skill intentionally does not commit CT or MR NIfTI volumes. Medical image
volumes stay out of the public tree; use the shared public spleen CT fixture
from `skills/nv-segment-ct/fixtures/fetch_spleen_fixture.py` when a tiny local
smoke input is needed.

Suggested smoke input after fetching:

```bash
python skills/nv-segment-ct/fixtures/fetch_spleen_fixture.py
python skills/totalsegmentator/scripts/run_totalsegmentator.py \
  skills/nv-segment-ct/fixtures/spleen_03.nii.gz \
  --task total \
  --roi-subset "spleen,kidney_right,kidney_left,liver" \
  --output-dir runs/totalsegmentator_smoke
```

The generated output is engineering evidence only and is not for clinical use.
