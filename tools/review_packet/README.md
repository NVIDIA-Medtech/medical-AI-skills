# review_packet

Maintainer renderer for compact human review of an existing evidence pack or
trusted-run directory.

The renderer is additive. It reads committed pack files such as
`manifest.json`, `validation_summary.json`, `agent_run_trace.jsonl`,
`provenance.json`, and `trust_summary.json` when present. It does not rename or
rewrite evidence-pack files.

## Commands

```bash
make review-packet PACK=examples/evidence_packs/dicom_metadata_pass
make review-packet PACK=examples/evidence_packs/nv_segment_ct_pass \
  REVIEW_PACKET_OUT=runs/review_packets/nv_segment_ct_pass.md
python tools/render_review_packet.py runs/my_trusted_run \
  --out runs/my_trusted_run/review_packet.md
```

## Review Surface

The packet summarizes:

- review verdict and evidence gaps
- capability, fixture, command, replay path, runtime, and cost
- gate statuses from `validation_summary.json`
- paired verifier coverage from `trust_summary.json` or the current manifest
- provenance and observation gaps
- trace event digest
- artifact paths and available hashes
- reviewer checklist and manifest limitations

Generated packets belong under `runs/` unless a pack is explicitly promoted as
curated evidence.
