# Medical Anonymization — With vs Without Skill

## Failure modes tracked

- `invocation_nonzero_exit`
- `missing_run_report`
- `missing_nested_jsonl`
- `missing_kv_compact_jsonl`
- `missing_audit_jsonl`
- `missing_anonymized_csv`
- `dicom_phi_field_leak`
- `dicom_uid_not_remapped`
- `structured_id_not_hashed`
- `kv_round_trip_failed`
- `nemo_pipeline_failed`
- `text_bracket_token_missing`
- `no_structured_policy_applied`
- `no_format_evaluation`

## Timing summary

| Arm | Total seconds |
|-----|--------------:|
| with skill | 92.7 |
| without skill | 77.6 |

### Per-task seconds

| Task | with | without |
|------|-----:|--------:|
| dicom-metadata | 3.1 | 1.3 |
| ehr | 54.7 | 33.8 |
| reports | 34.8 | 42.5 |

## Per-task results

### dicom-metadata

| Arm | Seconds | Pass | Failures |
|-----|--------:|:----:|----------|
| with | 3.1 | yes | — |
| without | 1.3 | yes | no_structured_policy_applied (expected: no_structured_policy_applied) |

### ehr

| Arm | Seconds | Pass | Failures |
|-----|--------:|:----:|----------|
| with | 54.7 | yes | — |
| without | 33.8 | yes | structured_id_not_hashed (expected: structured_id_not_hashed) |

### reports

| Arm | Seconds | Pass | Failures |
|-----|--------:|:----:|----------|
| with | 34.8 | yes | — |
| without | 42.5 | yes | — |
