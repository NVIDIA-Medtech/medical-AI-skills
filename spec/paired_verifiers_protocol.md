# Paired Verifiers Protocol

`paired_verifiers[]` declares that a skill evidence pack should be audited by
one or more verifier specs.

```yaml
paired_verifiers:
  - id: medagent.verifiers.endoscopy_tool_detection_quality_v1
    status: implemented
    checks:
      - decoded detections exist
      - tools_detected_count > 0
      - bbox sanity is in-frame and non-degenerate
```

- `implemented`: a matching manifest must exist under `verifiers/`.
- `planned`: explicit gap declaration only.
- `checks`: human-readable intent; executable behavior lives in the verifier
  code, schema, and manifest gates.

Verifiers are peer spec objects. They are not children of the skills they
audit and are not internal eval_engine modules.
