# Offline NIfTI test fixtures

Maintainer infrastructure for small deterministic NIfTI inputs. The generator
writes constant-valued int16 arrays for file-format, geometry, and command
contract tests. It does not simulate anatomy, call a model, access the network,
or establish clinical correctness. Generated images are not committed.

## Prerequisites and commands

Use an already prepared Python 3.11+ environment with NumPy, NiBabel, and
pytest (for tests). No additional packages or installation steps are required
beyond the repository's no-GPU test dependencies.

From the repository root:

```bash
python -m tools.test_fixtures.generate_nifti runs/fixture_checks/volume.nii.gz
python -m tools.test_fixtures.generate_nifti runs/fixture_checks/four_dimensional.nii \
  --shape 4 5 6 2 --spacing-mm 2 --value 0
python -m pytest tools/test_fixtures/tests -q
```

The CLI emits a JSON record explicitly marked as synthetic and not model
inference. It accepts 3D and 4D shapes, limits allocations to 2 MiB of voxel
data, and refuses to replace existing files or symlinks. Compressed files use
fixed gzip metadata for byte-repeatability within the same library environment.
Use fresh output paths for repeated commands.

## Pytest integration

`make test` loads the optional fixture provider. To use it for a focused suite:

```bash
python -m pytest -p tools.test_fixtures.pytest_plugin PATH_TO_TESTS -q
```

Tests consume a fixture by name; production wrappers need no import from
repository tooling:

```python
def test_input_geometry(synthetic_nifti_factory):
    volume = synthetic_nifti_factory("input.nii.gz", shape=(8, 9, 10))
    assert volume.is_file()
```

Each factory writes only within pytest's per-test temporary directory. There
is no global pytest registration or environment modification. Standalone test
bundles must either receive this provider explicitly or use separately supplied
input files; they must not silently substitute generated data for live inputs.

Delete only the task-created fixture directories when finished. Keep
caller-owned inputs and shared caches intact.
