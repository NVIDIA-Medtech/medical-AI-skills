# MONAI Bundle Notes

Authoritative source: <https://docs.monai.io/en/stable/bundle.html>.

## Bundle shape

```text
<bundle>/
  configs/
  models/
  docs/
```

Prefer the upstream bundle API or model-card helper. Do not rewrite inference
loops unless upstream documentation says to.

## Common failure modes

- State dict keys may have a `network.` prefix. Strictly verify missing and
  unexpected keys when loading manually.
- VISTA3D uses `class_vector`, not `class_prompts`.
- Sliding-window inference needs explicit batch/channel dimensions and an ROI
  compatible with the model.
- Very fast "inference" can be a silent failure; keep runtime floors for large
  models.

If a skill uses an official helper, gate the helper's emitted facts instead of
reconstructing internal load metrics.
