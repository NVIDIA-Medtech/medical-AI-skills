## Description: <br>
Used for finetuning NV-Generate-CTMR MR-Brain v1 for T1, T2, FLAIR, SWI, or MRA data from a NIfTI datalist. Not for clinical or production data approval. <br>

This skill is for research and development only. <br>

## Owner
NVIDIA <br>

### License/Terms of Use: <br>
Apache 2.0 <br>
## Use Case: <br>
Developers and engineers finetuning the NV-Generate-CTMR MR-Brain v1 diffusion UNet on custom MRI training volumes (T1, T2, FLAIR, SWI, or MRA) for research and development purposes. <br>

### Deployment Geography for Use: <br>
Global <br>

## Requirements / Dependencies: <br>
**Requires API Key or External Credential:** [No] <br>
**Credential Type(s):** [None] <br>

Do not include secrets in prompts/logs/output; use least-privilege credentials; rotate keys as appropriate. <br>

## Known Risks and Mitigations: <br>
Risk: Review before execution as proposals could introduce incorrect or misleading guidance into skills. <br>
Mitigation: Review and scan skill before deployment. <br>

## Reference(s): <br>
- [NV-Generate-CTMR upstream repository](https://github.com/NVIDIA-Medtech/NV-Generate-CTMR) <br>
- [NV-Generate-MR-Brain model (Hugging Face)](https://huggingface.co/nvidia/NV-Generate-MR-Brain) <br>
- [NV-Generate-CT autoencoder (Hugging Face)](https://huggingface.co/nvidia/NV-Generate-CT) <br>


## Skill Output: <br>
**Output Type(s):** [Files, JSON, Shell commands] <br>
**Output Format:** [Structured JSON result with file paths and provenance metadata] <br>
**Output Parameters:** [1D] <br>
**Other Properties Related to Output:** [Produces a finetuned PyTorch checkpoint, optional NIfTI inference outputs, and a result JSON with exit code, artifact paths, and stderr tail] <br>

## Evaluation Agents Used: <br>
- Claude Code (`aws/anthropic/bedrock-claude-opus-4-8`) <br>
- Codex (`openai/openai/gpt-5.5`) <br>



## Evaluation Tasks: <br>
2 evaluation tasks (2 positive), each run in an isolated sandbox pod. Dataset digest: sha256:9c5f1c36d1b237c2df145c0256504320db1fe26cfb376d92d455962414aec7c2. <br>

## Evaluation Metrics Used: <br>
Reported benchmark dimensions: <br>
- Security: Whether the skill avoids unsafe operations, secret leakage, and unauthorized access. <br>
- Correctness: Final-answer correctness against the reference answer. <br>
- Discoverability: Whether the expected skill was found and executed when needed. <br>
- Effectiveness: Whether the skill helped complete the user's goal and expected workflow (equal-weight mean of goal completion and behavior check). <br>
- Efficiency: Whether the skill avoided wasted tool or skill usage. <br>

Underlying evaluation signals used in this run: <br>
- `security`: Unsafe operations, secret leakage, and unauthorized access. <br>
- `accuracy`: Final-answer correctness against the reference answer. <br>
- `skill_execution`: Whether the expected skill was found and executed. <br>
- `goal_accuracy`: Whether the user's goal was achieved. <br>
- `behavior_check`: Whether the expected workflow behavior was followed. <br>
- `skill_efficiency`: Routing quality, workspace-aware skill reads, and productive tool use. <br>



## Evaluation Results: <br>
| Measure | Claude Code (Baseline → Skill Uplift) | Codex (Baseline → Skill Uplift) |
|---|---:|---:|
| Overall | 46% → 79% (+34 points) | 49% → 84% (+35 points) |
| Security | 100% → 100% (±0 points) | 50% → 100% (+50 points) |
| Correctness | 10% → 90% (+80 points) | 50% → 100% (+50 points) |
| Discoverability | 44% → 97% (+53 points) | 53% → 78% (+25 points) |
| Effectiveness | 33% → 17% (-17 points) | 32% → 61% (+29 points) |
| Efficiency | 42% → 93% (+52 points) | 59% → 79% (+21 points) |

## Skill Version(s): <br>
0.1.0 (source: skill_manifest.yaml) <br>

## Ethical Considerations: <br>
NVIDIA believes Trustworthy AI is a shared responsibility and we have established policies and practices to enable development for a wide array of AI applications. When downloaded or used in accordance with our terms of service, developers should work with their internal team to ensure this skill meets requirements for the relevant industry and use case and addresses unforeseen product misuse. <br>

(For Release on NVIDIA Platforms Only) <br>
Please report quality, risk, security vulnerabilities or NVIDIA AI Concerns [here](https://app.intigriti.com/programs/nvidia/nvidiavdp/detail). <br>
