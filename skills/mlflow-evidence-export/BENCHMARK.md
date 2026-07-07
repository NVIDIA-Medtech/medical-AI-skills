# Benchmark Status

This is a discussion prototype. A publication benchmark has not yet been run.

The proposed with-skill evaluation checks whether an agent selects the committed
exporter, starts in `dry-run` mode, preserves evidence packs as the source of
truth, and avoids uploading raw medical artifacts. The without-skill baseline
and multi-agent measurements remain pending until the MLflow contract is
reviewed with Databricks.

Current proof is limited to deterministic unit tests and the synthetic
`fixtures/sample_pack` dry run. This file must be replaced with measured
with-skill/without-skill results before external publication.
