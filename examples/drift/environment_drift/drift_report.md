# Drift Report

- pack A: `examples/drift/baseline`
- pack B: `examples/drift/environment_drift`
- drift detected: **YES**

## Environment fingerprint
- A: `d316cdf996823757`
- B: `6f38a6c9e5e7d4f2`
- env_drift: **True**

### Pip freeze diff

Only in A (removed in B):
  - numpy==2.3.1
Only in B (added in B):
  - numpy==2.2.0

## Validation gate status
- (no gate-status drift)

## Output payload diffs
- (no payload drift)
