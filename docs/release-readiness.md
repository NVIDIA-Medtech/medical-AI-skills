# Release readiness

Use this loop before cutting a release candidate, promoting an evidence pack, or
updating public readiness claims. It keeps the repo skill-first while making the
trust layer easy to review.

## Publication threshold

A user-facing skill is publication-ready only when the use lane, trust lane,
human review, and repo validation all line up:

- Use lane: `SKILL.md` is install-compatible, the documented script path is
  runnable, and prompt-shaped evals or benchmark notes exist when they are part
  of the public story.
- Trust lane: `skill_completeness_v1` reports lifecycle `published`, or an
  explicit release exception records the remaining gap. A curated evidence pack
  or trusted-run anchor exists under `examples/evidence_packs/`, implemented
  paired verifiers pass or warn with understood limits, and missing verifiers are
  planned gaps rather than accidental omissions.
- Human review: a review packet renders the promoted evidence so verdict, gates,
  verifier coverage, provenance gaps, trace digest, artifacts, and limitations
  are readable without opening every JSON file first.
- Repo validation: `make verify-skills` passes. With-vs-without checks pass when
  the skill is part of that backend comparison story. `make nv-base-validate`
  should pass in an NV-BASE environment when the release depends on that
  internal profile, or the unavailable profile is recorded as a release gap.

## Snapshot command

Run the no-network readiness snapshot:

```bash
make status-agent-skills
```

The target runs the strict skill audit, the with-vs-without harness tests, and
the release status renderer. It answers:

- how many real targets are `published`, `verified`, `gated`, `runnable`, or
  `draft`
- which lifecycle blockers should be inspected first
- whether blockers need trusted-run evidence, verifier evidence, or docs/eval
  artifacts
- whether with-vs-without prompt and study artifacts are complete

Use the strict gate before claiming completion:

```bash
make prove-agent-skills
make prove-with-vs-without
```

## Current snapshot, 2026-05-26

Evidence from the local readiness run:

- `make status-agent-skills`: status `complete`; no network calls made.
- `skill_completeness_v1`: 33/33 real specs pass with 0 advisory issues.
- Lifecycle counts: `published=33`; `verified=0`, `gated=0`, `runnable=0`,
  `draft=0` for real targets.
- Catalog split: 16 user-facing skills and 17 verifiers are published.
- The known `negative_sloppy_skill` calibration fixture fails as expected and is
  not counted as a real target.
- With-vs-without: 7/7 covered `nv_*` skills have complete prompt artifacts,
  complete study artifacts, and paired outcomes supporting SKILL.md advantage.
- Pending external LLM calls: 0. Maximum possible repair calls: 0.
- Reviewed with-vs-without payload fingerprint:
  `a226c31aefa65f97a760ee97f3d90560ecda10cd409aed24fe8f4712d1354143`.
- NV-BASE is not part of this no-network snapshot. Run
  `make nv-base-validate` in an NV-BASE environment before claiming internal
  profile readiness.

There are no top lifecycle blockers in this snapshot. Review priority therefore
moves from blocker cleanup to release-claim review and evidence-boundary review.

## Candidate review order

For this snapshot, review these publication candidates before broad release
claims because they cover the main artifact families and risk profiles:

1. `dicom-series-preflight` with
   `examples/evidence_packs/dicom_series_preflight_trusted_pass/`: GPU-free
   onboarding anchor with verifier coverage.
2. `dicom-series-to-volume` with
   `examples/evidence_packs/dicom_series_to_volume_trusted_pass/`: DICOM to
   volume conversion anchor with artifact verifier coverage.
3. `nv-segment-ct` with
   `examples/evidence_packs/nv_segment_ct_trusted_pass/`: CT segmentation anchor
   with anatomy plausibility verifier coverage.
4. Generated CT/MR skills with the `*_trusted_inventory_pass/` anchors:
   trusted inventory evidence for generated outputs, with generated volumes
   referenced rather than bundled.
5. `totalsegmentator` with
   `examples/evidence_packs/totalsegmentator_trusted_pass/`: CUDA multilabel
   segmentation anchor with TotalSegmentator-specific verifier coverage.
6. HoloHub skills with the `holohub_*_trusted_*_pass/` anchors: stream,
   benchmark, and detection artifacts, with performance claims kept scoped to
   what the committed evidence actually proves.
7. Structured LLM skills with the trusted mock anchors:
   `nv_reason_cxr_trusted_mock_pass/` and
   `radiology_note_summarizer_trusted_mock_pass/`. Treat these as plumbing and
   contract evidence, not clinical-quality evidence.

## Review packets

Generate review packets for the selected anchors before promoting or changing
readiness claims:

```bash
make review-packet PACK=examples/evidence_packs/dicom_series_preflight_trusted_pass
make review-packet PACK=examples/evidence_packs/dicom_series_to_volume_trusted_pass
make review-packet PACK=examples/evidence_packs/nv_segment_ct_trusted_pass
```

The default output path is `runs/review_packets/<pack-name>.md`. Override it
when a release run needs a named bundle:

```bash
make review-packet \
  PACK=examples/evidence_packs/nv_segment_ct_trusted_pass \
  REVIEW_PACKET_OUT=runs/release_readiness/nv_segment_ct_trusted_pass.md
```

Review packets are generated views over evidence packs, not sources of truth.
Keep them under `runs/` unless there is an explicit reason to curate one as an
example.

## Blocker triage

If a future snapshot is not all `published`, inspect the first blockers with:

```bash
make audit-skill SKILL=<skill-or-verifier-dir-name>
python tools/render_contract_summary.py skills/<name>
```

For verifier targets, pass the verifier path to `render_contract_summary.py`.
Then render a packet for the best existing pack or trusted run:

```bash
make review-packet PACK=<pack-or-trusted-run-dir>
```

Classify each blocker as one of:

- trusted-run evidence gap
- verifier evidence gap
- documentation or eval artifact gap
- implementation or manifest gap
- accepted release exception

Do not manually store lifecycle status in manifests. It is derived by
`skill_completeness_v1`.

## With-vs-without record

Backend comparisons stay tied to capability contracts and reviewable evidence,
not leaderboard framing. Every backend-run record should preserve:

- backend and model identity
- prompt or context actually given
- generated command or tool call
- correction attempts and reason for stopping
- execution result
- evidence pack path or failure reason
- review-packet summary when evidence exists
- token, cost, and runtime fields when available

Use the existing no-network study gates:

```bash
make verify-with-vs-without
make audit-with-vs-without
make approval-packet-with-vs-without
make approved-rerun-plan-with-vs-without
```

If external reruns are needed, use the approval packet and reviewed rerun plan.
Do not make ad hoc LLM calls from this release loop.

## Definition of done

The release-readiness loop is working when a reviewer can run one status command,
open this readiness note, inspect one review packet per candidate, and
understand:

- what is ready to publish
- what is blocked
- what evidence supports the claim
- what verifier coverage is missing
- what should not be claimed
