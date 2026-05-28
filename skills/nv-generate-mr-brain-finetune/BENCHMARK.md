# Evaluation Report

Evaluation of the `nv-generate-mr-brain-finetune` skill before publication through NVSkills-Eval.

This benchmark summarizes 3-Tier Evaluation from NVSkills-Eval results for the skill. The goal is to document whether the skill is safe, discoverable, effective, and useful for agents before it is published for broader workflow use.

## Evaluation Summary

- Skill: `nv-generate-mr-brain-finetune`
- Evaluation date: 2026-05-28
- NVSkills-Eval profile: `external`
- Overall verdict: FAIL
- Tier 3 live agent evaluation: not available in this report

## Agents Used

- Tier 3 agent details were not available in this report.

## Metrics Used

Reported benchmark dimensions:

- Security: checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access.
- Correctness: checks whether the agent follows the expected workflow and produces the correct final output.
- Discoverability: checks whether the agent loads the skill when relevant and avoids using it when irrelevant.
- Effectiveness: checks whether the agent performs measurably better with the skill than without it.
- Efficiency: checks whether the agent uses fewer tokens and avoids redundant work.

Underlying evaluation signals used in this run:

- No Tier 3 evaluation signal details were available in this report.

## Test Tasks

Tier 3 evaluation task details were not available in this report.

## Results

Tier 3 dimension rollup was not available in this report.

## Tier 1: Static Validation Summary

Tier 1 validation passed with observations. NVSkills-Eval ran 9 checks and found 12 total findings.

Top findings:

- MEDIUM PII/gps_coordinates: GPS coordinates (location information) (`tests/test_run_mr_brain_finetune.py:38`)
- MEDIUM SCHEMA/body_recommended_section: Missing recommended section: '## Examples' (`skills/nv-generate-mr-brain-finetune/SKILL.md`)
- MEDIUM SECURITY/subprocess module call (AST4): Dangerous Code Execution:     return subprocess.run(
        command,
        cwd=str(upstream_root),
        env=env,
        capture_output=True,
        text=True,
        check=False,
    ) (`scripts/run_mr_brain_finetune.py:391`)
- MEDIUM SECURITY/Unknown (LP3): MCP Least Privilege: The skill exercises significant system capabilities (environment variable access, file reads/writes, and shell execution (`SKILL.md:1`)
- MEDIUM SECURITY/Unknown (SQP-2): The GPU finetuning usage example silently runs `pip install -r "$NV_GENERATE_ROOT/requirements.txt"` against an external (`SKILL.md:71`)

## Tier 2: Deduplication Summary

Tier 2 validation reported findings. NVSkills-Eval ran 2 checks and found 1 total findings.

Top findings:

- HIGH DUPLICATE/duplicate: Duplicate content found across SKILL.md and scripts/run_mr_brain_finetune.py:
  "## Purpose" in SKILL.md (lines 3-8)
  vs "(module docstring)" in scripts/run_mr_brain_finetune.py (lines 1-9) (`SKILL.md:3`)

## Publication Recommendation

The skill should be reviewed before NVSkills-Eval publication. Skill owners should address the findings above and rerun NVSkills-Eval to refresh this benchmark.
