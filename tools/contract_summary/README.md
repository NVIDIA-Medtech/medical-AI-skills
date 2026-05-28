# Contract Summary Renderer

`tools/render_contract_summary.py` renders a read-only Markdown view of one
skill or verifier contract. It reads `skill_manifest.yaml`, `SKILL.md`, local
output schemas, paired-verifier declarations, limitations, and committed
example anchors. It does not create a second source of truth.

## Commands

```bash
python tools/render_contract_summary.py skills/dicom-series-preflight
python tools/render_contract_summary.py skills/dicom-series-preflight \
  --out runs/dicom_series_preflight_contract.md
```

Use this before running a skill when an agent or reviewer needs the contract in
one page. Use `tools/render_review_packet.py` after a run to inspect evidence.
