"""Tests for provenance enrichment from skill output.json."""
from __future__ import annotations

import json
from pathlib import Path

from eval_engine.provenance import enrich_provenance_from_skill_output, write_provenance


def test_enrich_adds_container_from_invocation(tmp_path: Path) -> None:
    out = tmp_path / "pack"
    out.mkdir()
    write_provenance(
        out=out,
        manifest={"runtime": {"side_effects": {"requires_gpu": True}}},
        skill_dir=tmp_path,
        side_effects_before=[],
    )
    payload = enrich_provenance_from_skill_output(
        out,
        {
            "invocation": {
                "container_image": "holohub-imaging_ai_segmentator:main",
                "container_image_id": "sha256:abc",
                "holohub_commit": "deadbeef",
                "holohub_root": "/data/holohub",
                "command": ["./holohub", "run"],
            },
            "logs": {"stderr_tail": "container build ok"},
        },
    )
    assert payload is not None
    container = payload["container"]
    assert container["image_ref"] == "holohub-imaging_ai_segmentator:main"
    assert container["image_digest_observed"] == "sha256:abc"
    assert container["holohub_commit"] == "deadbeef"
    on_disk = json.loads((out / "provenance.json").read_text())
    assert on_disk["container"]["image_digest_observed"] == "sha256:abc"
