from eval_engine.lint_repo import (
    _env_pin_exact_pin_conflicts,
    _has_tracked_upstream_ref,
    _mentions_runtime_upstream_patch,
)


def test_has_tracked_upstream_ref_accepts_commit_revision_or_version() -> None:
    assert _has_tracked_upstream_ref(
        {"upstream_refs": [{"kind": "github_repo", "name": "demo", "git_commit": "a" * 40}]}
    )
    assert _has_tracked_upstream_ref(
        {"upstream_refs": [{"kind": "huggingface_repo", "name": "demo", "revision": "main"}]}
    )
    assert _has_tracked_upstream_ref(
        {"upstream_refs": [{"kind": "pypi_package", "name": "demo", "version_constraint": ">=1"}]}
    )


def test_has_tracked_upstream_ref_rejects_missing_version_data() -> None:
    assert not _has_tracked_upstream_ref({})
    assert not _has_tracked_upstream_ref({"upstream_refs": []})
    assert not _has_tracked_upstream_ref(
        {"upstream_refs": [{"kind": "github_repo", "name": "demo"}]}
    )


def test_mentions_runtime_upstream_patch_flags_hot_patches() -> None:
    assert _mentions_runtime_upstream_patch("def apply_runtime_patches(): pass")
    assert _mentions_runtime_upstream_patch("# monkeypatch upstream trainer")
    assert _mentions_runtime_upstream_patch("patch the upstream implementation")


def test_mentions_runtime_upstream_patch_allows_config_staging() -> None:
    assert not _mentions_runtime_upstream_patch("PATCH_LADDER = [(8000, [64, 64, 64])]")
    assert not _mentions_runtime_upstream_patch("shutil.copy2(src_config, staged_config)")


def test_env_pin_exact_pin_conflicts_flags_mismatched_runtime_pin() -> None:
    manifest = {
        "runtime": {
            "dependencies": {"monai": "==1.4.0"},
            "side_effects": {"pip_packages": ["monai==1.4.0"]},
        },
        "validation": {"env_pin": {"monai": ">=1.5,<1.6"}},
    }

    conflicts = _env_pin_exact_pin_conflicts(manifest)

    assert conflicts
    assert "monai" in conflicts[0]


def test_env_pin_exact_pin_conflicts_accepts_matching_runtime_pin() -> None:
    manifest = {
        "runtime": {
            "dependencies": {"monai": "==1.4.0"},
            "side_effects": {"pip_packages": ["monai==1.4.0"]},
        },
        "validation": {"env_pin": {"monai": "==1.4.0"}},
    }

    assert _env_pin_exact_pin_conflicts(manifest) == []
