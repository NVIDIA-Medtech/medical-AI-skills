# Paired Verifiers Protocol

`paired_verifiers[]` declares that a skill evidence pack should be audited by
one or more verifier specs.

```yaml
paired_verifiers:
  - id: medagent.verifiers.ct_segmentation_quality_v1
    status: implemented
    checks:
      - output label map exists
      - geometry matches source image
      - anatomy volumes are plausible
```

- `implemented`: a matching manifest must exist under `verifiers/`.
- `planned`: explicit gap declaration only.
- `checks`: human-readable intent; executable behavior lives in the verifier
  code, schema, and manifest gates.

Verifiers are peer spec objects. They are not children of the skills they
audit and are not internal eval_engine modules.
