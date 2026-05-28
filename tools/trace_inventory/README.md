# trace_inventory

Maintainer inventory for `agent_run_trace.jsonl` records.

The goal is to learn from existing packs before introducing a formal trace
schema. The tool reports observed fields, record shapes, event names, parse
errors, and coverage for candidate stable fields such as `event_type`,
`timestamp`, `command`, `cwd`, `tool`, `duration_seconds`, `files_read`, and
`model`.

## Commands

```bash
python tools/inventory_trace_shapes.py
python tools/inventory_trace_shapes.py examples --format markdown
python tools/inventory_trace_shapes.py examples runs \
  --out runs/trace_inventory/report.json \
  --markdown-out runs/trace_inventory/report.md
```

By default the command scans committed example packs under `examples/`. Include
`runs/` only when you want local generated evidence in the inventory.

Generated reports belong under `runs/` unless a report is explicitly promoted
as curated design evidence.
