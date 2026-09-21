# Medical Anonymization — With vs Without Skill

Engineering comparison: `medical-anonymization/SKILL.md` vs upstream NeMo README baseline on the same staged inputs.

## Failure modes tracked

| Mode | Meaning |
|------|---------|
| `invocation_nonzero_exit` | Script crashed or nonzero return |
| `missing_run_report` | No `run_report.json` |
| `missing_nested_jsonl` | No per-study nested JSONL (with-skill contract) |
| `missing_kv_compact_jsonl` | No `(record_id, field, value)` JSONL |
| `missing_audit_jsonl` | No shareable audit log |
| `missing_anonymized_csv` | No wide CSV output |
| `dicom_phi_field_leak` | Direct identifier unchanged vs source |
| `dicom_uid_not_remapped` | UID identical to source |
| `structured_id_not_hashed` | MRN/ID column left verbatim |
| `kv_round_trip_failed` | KV cannot reconstruct nested |
| `nemo_pipeline_failed` | NeMo records_failed > 0 |
| `text_bracket_token_missing` | No redaction tokens in text output |
| `no_structured_policy_applied` | Expected without-skill gap on DICOM/CSV |
| `no_format_evaluation` | Missing token/format comparison report |

## With-skill workflow

```mermaid
flowchart TB
  subgraph inputs
    TXT[.txt clinical note]
    CSV[mixed CSV]
    DICOM[dicom_metadata_full.csv]
  end

  subgraph skill["medical-anonymization (WITH)"]
    DETECT[input-kind auto]
    POLICY[default-medical.yaml]
    NEMO[NeMo text strategies]
    STRUCT[structured policy]
    DICOM_POL[dicom_policy engine]
    FMT[metadata_formats nested + KV compact]
  end

  subgraph outputs
    RR[run_report.json]
    NESTED[deidentified_metadata_nested.jsonl]
    KV[deidentified_metadata_kv_compact.jsonl]
    AUDIT[audit.jsonl]
    CSVOUT[anonymized_data.csv]
    KVCSV[anonymized_data_kv.jsonl]
  end

  TXT --> DETECT
  CSV --> DETECT
  DICOM --> DETECT
  DETECT --> POLICY
  POLICY --> NEMO
  POLICY --> STRUCT
  POLICY --> DICOM_POL
  DICOM_POL --> FMT
  NEMO --> CSVOUT
  STRUCT --> CSVOUT
  FMT --> NESTED
  FMT --> KV
  DICOM_POL --> AUDIT
  CSVOUT --> KVCSV
  DETECT --> RR
```

**Entrypoint:** `scripts/anonymize_medical_data.py`

## Without-skill workflow

```mermaid
flowchart TB
  subgraph inputs2
    CSV2[CSV with text column]
    DICOM2[dicom_metadata_full.csv]
  end

  subgraph upstream["upstream NeMo README (WITHOUT)"]
    NEMO2[NeMo redact text column only]
    PASS[dicom passthrough wide CSV]
  end

  subgraph outputs2
    RR2[run_report.json]
    CSVOUT2[anonymized_data.csv OR metadata_passthrough.csv]
  end

  CSV2 --> NEMO2
  DICOM2 --> PASS
  NEMO2 --> CSVOUT2
  PASS --> CSVOUT2
  NEMO2 --> RR2
  PASS --> RR2
```

**Entrypoint:** `scripts/without_skill_baseline.py` (text) or passthrough (DICOM)

**Gaps without skill:** no YAML policy, no JSONL formats, no audit, no structured-field hashing, no UID remap/date-shift.

## Run evaluation

```bash
/home/marc/.conda/envs/reports-openai/bin/python \
  skills/medical-anonymization/scripts/run_with_vs_without_eval.py \
  --output-dir /tmp/medical_anon_with_vs_without \
  --report-num-records 3
```

Outputs: `with_vs_without_report.json`, `with_vs_without_report.md`

## Results (2026-07-11, local PHI-safe)

Harness: `run_with_vs_without_eval.py` with GLiNER @ `172.20.0.1:8001`, Ollama `medgemma:27b`.

| Task | with (s) | without (s) | with pass | without pass |
|------|--------:|------------:|:---------:|:------------:|
| dicom-metadata | 3.2 | 1.6 | yes | yes (expected `no_structured_policy_applied`) |
| ehr | 16.9 | 23.7 | yes | yes (expected `structured_id_not_hashed`) |
| reports | 32.9 | 43.8 | yes | yes |

See [`with-vs-without-results.md`](with-vs-without-results.md) for the full JSON report.
