---
name: sloppy_skill
description: Anti-pattern fixture that intentionally violates skill-completeness requirements so the verifier has known-bad input.
---

# sloppy_skill

Not a real skill. It omits required manifest fields and references missing
files on purpose. Keep it broken as a calibration fixture for
`verifiers/skill_completeness_v1`.
