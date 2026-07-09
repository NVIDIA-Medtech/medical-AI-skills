# SPDX-FileCopyrightText: Copyright (c) 2026, NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0
"""With-vs-without-skill evaluation harness for the MR-RATE report-curation skills.

This package runs the three-step curation pipeline (select -> confirm-no-PII ->
disease-label) in two arms (skill enabled vs skill disabled) across one or more
LLM backends, grades every step deterministically against ground truth, and
emits success-rate aggregates plus a markdown report modelled on
``docs/with-vs-without-skill-experiment.md``.

Engineering reproducibility protocol only: it measures whether an agent can
complete the curation task, not clinical/diagnostic quality.
"""

__all__ = ["__version__"]
__version__ = "0.1.0"
