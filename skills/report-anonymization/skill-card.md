## Description: <br>
Used for de-identifying English radiology reports with NeMo Anonymizer (GLiNER-PII + LLM): replaces detected PHI with bracketed role tokens like [PATIENT], [DOCTOR], [DATE] (MR-RATE reports stage 01). Not for regulatory de-identification or clinical use. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers use this skill to de-identify English radiology reports by replacing PHI entities with bracketed role tokens before sharing or processing data in research pipelines. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Yes] <br>
**Credential Type(s):** [API key] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NeMo Anonymizer (GitHub)](https://github.com/NVIDIA-NeMo/Anonymizer) <br>
- [Upstream NeMo Anonymizer reference](references/upstream-nemo-anonymizer.md) <br>
- [Preview trace columns](references/preview-trace-columns.md) <br>


## Skill Output: <br>
**Output Type(s):** [JSON, Files] <br>
**Output Format:** [JSON (stdout summary) and CSV/JSON (output directory files)] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Validated against validators/output_schema.json] <br>

## Evaluation Agents Used: <br>
- Claude Code (`claude-code`) <br>
- Codex (`codex`) <br>



## Evaluation Tasks: <br>
Evaluated against 3 evaluation tasks (2 positive, 1 negative) in the NVSkills-Eval `external` profile. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Checks whether skill-assisted execution avoids unsafe behavior such as secret leakage, destructive commands, or unauthorized access. <br>
- Correctness: Checks whether the agent follows the expected workflow and produces the correct final output. <br>
- Discoverability: Checks whether the agent loads the skill when relevant and avoids using it when irrelevant. <br>
- Effectiveness: Checks whether the agent performs measurably better with the skill than without it. <br>
- Efficiency: Checks whether the agent uses fewer tokens and avoids redundant work. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Checks for unsafe operations, secret leakage, and unauthorized access. <br>
- `skill_execution`: Verifies that the agent loaded the expected skill and workflow. <br>
- `skill_efficiency`: Checks routing quality, decoy avoidance, and redundant tool usage. <br>
- `accuracy`: Grades final-answer correctness against the reference answer. <br>
- `goal_accuracy`: Checks whether the overall user task completed successfully. <br>
- `behavior_check`: Verifies expected behavior steps, including safety expectations. <br>
- `token_efficiency`: Compares token usage with and without the skill. <br>



## Evaluation Results: <br>
| Dimension | Num | `claude-code` | `codex` |
|---|---:|---:|---:|
| Security | 3 | 100% (+0%) | 100% (+0%) |
| Correctness | 3 | 93% (+30%) | 85% (+32%) |
| Discoverability | 3 | 93% (+38%) | 85% (+23%) |
| Effectiveness | 3 | 75% (+17%) | 75% (+31%) |
| Efficiency | 3 | 77% (+24%) | 82% (+19%) |

## Skill Version(s): <br>
37418d7 (source: git SHA, committed 2026-07-16) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
