## Description: <br>
Run NV-Reason-CT inference on user-provided 3D NIfTI chest or abdominal CT volumes for engineering and research workflows. Not for diagnosis, treatment, or clinical reporting. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
OpenMDW-1.1 <br>
## Use Case: <br>
Developers and engineers running NV-Reason-CT model inference on 3D NIfTI chest or abdominal CT volumes for engineering validation and research workflows. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [Optional] <br>
**Credential Type(s):** [API key] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Reason-CT Installation Instructions](https://github.com/NVIDIA-Medtech/NV-Reason-CT#installation) <br>


## Skill Output: <br>
**Output Type(s):** [Analysis, JSON] <br>
**Output Format:** [JSON on stdout] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Structured result including input geometry and hash, anatomy-region selection, response text, runtime identity, dependency versions, and limitations] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`) <br>
- Codex (`openai/openai/gpt-5.5`) <br>



## Evaluation Tasks: <br>
9 evaluation tasks with 3 attempts per task, each in an isolated sandbox pod. Dataset digest: sha256:df577b70bec14f79cd9d434a2db86fd8aaab1d9fda79314f3d42d6e9494e6ab9. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Whether the skill is safe to use, checking for unsafe operations, secret leakage, and unauthorized access. <br>
- Correctness: Whether the answer produced by the skill-assisted agent is correct against the reference. <br>
- Discoverability: Whether the right skill was selected and activated when needed, and decoys were avoided. <br>
- Effectiveness: Whether the skill helped complete the user's goal and followed the expected workflow. <br>
- Efficiency: Whether the skill avoided wasted tool calls and token usage. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Unsafe operations, secret leakage, and unauthorized access. <br>
- `accuracy`: Final-answer correctness against the reference answer. <br>
- `skill_execution`: Whether the expected skill was selected, decoys were avoided, and the workflow executed. <br>
- `goal_accuracy`: Whether the user's goal was achieved. <br>
- `behavior_check`: Whether the expected workflow behavior was followed. <br>
- `skill_efficiency`: Tool-call productivity. <br>
- `token_efficiency`: Actual uncached prompt plus completion usage. <br>



## Evaluation Results: <br>
| Measure | Claude Code | Codex |
|---|---:|---:|
| Overall | 90.9% | 79.3% |
| Security | 100.0% | 72.7% |
| Correctness | 97.8% | 83.6% |
| Discoverability | 86.1% | 84.6% |
| Effectiveness | 87.4% | 75.0% |
| Efficiency | 83.1% | 80.6% |

## Skill Version(s): <br>
ffeef8f (source: git SHA, committed 2026-09-23) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
