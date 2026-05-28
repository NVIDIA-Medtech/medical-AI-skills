# Agent verification commands

Run after edits. Order matters: fast checks first.

## Required (every PR)

```bash
make lint          # repo policy + manifest schema
make test          # pytest: eval_engine, find_skills, verifiers
make list-skills   # regenerate SKILL_INDEX.md if manifests changed
```

## Trust path (harness or spec changes)

```bash
make verify                  # lint + canonical dicom_metadata pack diff
make verify-skills           # skill_completeness_v1 on all specs
```

`make verify-skills` treats
`verifiers/skill_completeness_v1/fixtures/negative_sloppy_skill` as an expected
calibration failure. The command still exits nonzero if any real skill or
verifier fails the audit, if any real spec has advisory usability issues, or
if that known-bad fixture unexpectedly passes.

Each `skill_completeness_v1` report also includes a derived lifecycle status:
`draft`, `runnable`, `gated`, `verified`, or `published`. This status is for
review triage only. It is derived from existing structural checks,
reproducibility checks, paired-verifier declarations, trusted-run summaries,
behavior evals, benchmark notes, and curated example evidence; it is not stored in
`skill_manifest.yaml`.

For one target, use `make audit-skill SKILL=<name>`. It applies the same strict
single-report summary and fails on advisory usability issues.

To check the full agent-skill objective without network calls, use:

```bash
make status-agent-skills
```

It first runs the strict skill audit, then reports with-vs-without prompt,
preflight, harness-test, study-completeness, and pending external-call status.
It also prints lifecycle counts from the strict skill audit, which is the
quickest way to see whether the catalog is mostly `gated`, `verified`, or
`published` before opening individual reports. The lifecycle blocker list is a
short triage view only; use `make audit-skill SKILL=<name>` for complete gaps.
The final completion gate is:

```bash
make prove-agent-skills
```

That target stays nonzero until the strict skill audit passes and the
with-vs-without harness tests and studies prove SKILL.md paired advantage for
every covered skill.

For release-readiness review, use [`release-readiness.md`](release-readiness.md).
It records the publication threshold, current readiness snapshot, candidate
review order, and review-packet workflow. Generate a compact packet for any
candidate pack with:

```bash
make review-packet PACK=<pack-or-trusted-run-dir>
```

## Optional (gates / LLM / negative fixtures)

```bash
make verify-mock-gates
make verify-negative-fixtures
```

## Targeted pytest

```bash
python3 -m pytest eval_engine/tests -q
python3 -m pytest skills/<name>/tests -q
python3 -m pytest verifiers/<name>/tests -q
```

## Smoke run (one skill)

```bash
make run-skill SKILL=dicom_metadata_extract \
  FIXTURE=skills/dicom-metadata-extract/fixtures/sample_ct.dcm \
  OUT=runs/smoke
```

## Discovery smoke

```bash
make find-skills QUERY="extract DICOM metadata"
```

See [`agent-tasks.md`](agent-tasks.md) for task-specific read lists.
