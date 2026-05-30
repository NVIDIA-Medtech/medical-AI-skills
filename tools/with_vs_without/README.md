# with_vs_without — experiment harness for skill-value comparisons

This directory hosts harnesses that answer **does using a skill produce
a better outcome than not using it, and at what token cost?** Experiment
design lives in
[`docs/with-vs-without-skill-experiment.md`](../../docs/with-vs-without-skill-experiment.md).
Add-new-skill protocol lives in
[`docs/with-vs-without-authoring.md`](../../docs/with-vs-without-authoring.md).

## Endpoint reference

Two NVIDIA LLM endpoints are wired into Medical AI Skills. Their conventions
matter — these are the durable facts the experiment harnesses rely on.

| | NVIDIA Build (NIM catalog) | NVIDIA Inference route |
|---|---|---|
| Catalog URL (browser) | <https://build.nvidia.com> | <https://inference.nvidia.com> |
| **API base URL** | `https://integrate.api.nvidia.com/v1` | `https://inference-api.nvidia.com/v1` |
| Env var (key value) | `NVIDIA_BUILD_KEY` in `~/.bashrc` (Medical AI Skills convention) | `NV_INFER_TOKEN` in `~/.bashrc` |
| Env var (SDK reads) | `NVIDIA_API_KEY` (NIM SDK convention) | `NV_INFER_TOKEN` (Medical AI Skills scripts read directly) |
| **Bridge command** | `export NVIDIA_API_KEY="$NVIDIA_BUILD_KEY"` | (no bridge needed) |
| Example model | `meta/llama-3.3-70b-instruct` | `nvidia/nvidia/nemotron-3-super-v3`, `aws/anthropic/bedrock-claude-opus-4-7` |
| Models seen in Medical AI Skills | `meta/llama-3.3-70b-instruct` (older NAT cost baselines) | `nvidia/nvidia/nemotron-3-super-v3`, `openai/openai/gpt-5.5`, `aws/anthropic/...` |
| Auth | `Authorization: Bearer <key>` | `Authorization: Bearer <key>` |
| Study request body | Provider-default protocol: send only `model` and `messages`; omit `temperature`, `top_p`, `max_tokens`, backend-specific reasoning controls, and other extra body fields. | Same provider-default protocol: send only `model` and `messages`. |

### Common gotchas

- `~/.bashrc` won't auto-source in non-interactive shells. The current direct
  with-vs-without backends all read `NV_INFER_TOKEN`; older Build/NIM
  experiments may still need `NVIDIA_API_KEY` bridged from `NVIDIA_BUILD_KEY`.
- The browser URL `https://inference.nvidia.com/...` returns the catalog
  HTML page, not JSON — easy to mistake for the API base. The API base
  is `https://inference-api.nvidia.com/v1` (separate subdomain).
- The direct study intentionally uses provider defaults for model behavior.
  Extra request fields such as `temperature`, `top_p`, `max_tokens`,
  `reasoning_effort`, and `chat_template_kwargs` are not sent unless a future
  experiment explicitly defines a pinned-parameter arm.
- Reasoning defaults are therefore backend-owned in this protocol. That makes
  the result a service-default baseline, not a tuned or recommended-parameter
  baseline.

## When to use NeMo Agent Toolkit (NAT) vs a direct API call

Medical AI Skills already has NAT scaffolding at
[`tools/nat_audit/`](../nat_audit/) — NAT function wrappers for every
skill in `src/nat_audit/register.py`, a working `eval_config.yml`, and a
dedicated venv. **Reuse NAT whenever an experiment involves the agent
deciding to call a skill or reading skill documentation.** That is most
experiments.

| Experiment shape | Use |
|---|---|
| "Agent decides whether to call skill X given fuzzy prompt" | **NAT** — register/unregister the skill in `tool_names`, NAT captures the decision and the cost natively |
| "Agent reads SKILL.md vs reads upstream model card, then produces a command" | **NAT** — use `read_file` as a registered tool, point at different files per arm |
| "Agent invokes skill X end-to-end, output is graded by paired verifier" | **NAT** + thin grader on top — NAT for the agent loop, our grader for tier-5 (execute + verify) |
| One-shot calibration ping ("does this endpoint reply?") | **Direct OpenAI SDK** — overkill to spin up NAT for a connectivity check |
| Ablation under a different model than NAT's `nim_llm` config | **Direct API mode in `run_nv_model_studies.py`** when NAT model swap is more friction than worth |

The default is NAT. Direct API study support lives in
`run_nv_model_studies.py` and is used only for the approved backend modes that
cannot read repo files directly.

## Files in this directory

| File | Role |
|---|---|
| `README.md` | this file |
| `run_nv_model_studies.py` | Shared NV model-skill study runner. Generates fair path prompts, stages neutral inputs, runs direct-API embedded-doc arms when requested, applies the bounded repair loop, creates fresh per-attempt venvs, and writes study JSON. |
| `audit_nv_model_studies.py` | Checks that prompt artifacts, prompt-pair symmetry, direct-study JSON, and saved repair traces match the current repeat protocol before reports are cited as complete. |
| `preflight_nv_model_studies.py` | Local readiness check for direct reruns. It verifies docs, fixtures, prompt artifacts, path-like runtime caches, shell/Python basics, and required API key variable names without API calls. |
| `manifest_nv_model_data_transfer.py` | No-network manifest of pending direct-study external LLM calls under `--resume-missing`, including endpoints, models, prompt hashes/sizes, selected docs, initial prompt policy, and repair-data policy. |
| `write_nv_model_reports.py` | Regenerates gitignored per-skill Markdown reports under `runs/with_vs_without_nv/reports/` and the checked-in aggregate `docs/with-vs-without-skill-experiment.md` from study JSON. |
| `write_nv_model_invariants.py` | Writes the checked-in invariant snapshot that repeaters compare in PRs instead of committing raw study records. |

## Current Protocol

The active comparison is **LLM + SKILL.md** vs **LLM + one upstream
README/guide**. The prompt gives only the natural task, a neutral staged input
path, a repeat-specific output directory, and the arm-specific document path.
It must not leak entrypoints, config filenames, label IDs, modality constants,
or model variants outside the document the arm is allowed to read.
The README-only arm uses selected repo-local snapshots under
`tools/with_vs_without/upstream_docs/`; prompt generation and auditing must not
depend on a developer's local `.workbench_data` upstream cache.
Direct reruns also do not clone or refresh upstream documentation implicitly;
selected upstream README/guide snapshots must be committed and pass preflight
before any approved LLM call is made.

Generate the fair tool-agent/NAT prompt artifacts without API calls:

```bash
python tools/with_vs_without/run_nv_model_studies.py --mode prompts --prompt-style path
```

`--mode prompts` accepts only `--prompt-style path`; embedded-doc `minimal`
prompts are reserved for direct API study runs. If `--write-prompt-artifacts`
is used alongside a direct run, the runner still writes fair `path` artifacts
while the direct run uses its own embedded-doc prompt.
Direct API study modes require `--prompt-style minimal`; legacy guarded
prompts are rejected before external transfer because they are not part of the
current comparison protocol. The repeat count and correction budget are fixed
at `--repeats 3` and `--max-correction-steps 0`; non-protocol values are
rejected before prompt generation or external transfer.

Each `tools/nat_audit/data/eval_nv_model_studies_*_prompts.json` file contains
one record per backend/arm/repeat. The `question` and `expected_output_dir`
fields both include `/repeat_N`, matching the clean-repeat execution protocol.
Every path-prompt question must name the selected workflow document, explicitly
say to read it, and include the arm-specific document boundary.
The audit compares each with/without prompt pair and permits only the intended
documentation path, documentation-boundary instruction, and output-directory
differences.
It also pins shared protocol metadata, including the fixed system prompt,
generic answer template, runner path, prompt-source function, backend label,
backend model, endpoint, provider-default request shape, retry policy, and
five-step correction budget, so a stale artifact cannot pass only because both
arms share the same mistake.
For path-prompt artifacts, the audit recomputes the exact runner-generated
question for each skill/backend/arm/repeat and rejects shared extra hints as
well as one-sided prompt drift.
For direct API fallbacks, the same audit also generates the embedded-doc
`minimal` prompt pair and permits only the documentation text,
documentation-boundary instruction, and output-directory differences.
Both prompt styles are also checked for operational marker leakage outside the
allowed document content, including concrete wrapper names, config paths, label
IDs, and source fixture basenames.

Before launching direct API reruns, run the local preflight. It checks the
current prompt artifacts, selected docs, source fixtures, path-like runtime
caches, shell/Python basics, and required API key variable names without
printing secret values:

```bash
make preflight-with-vs-without
```

Direct API modes enforce this local preflight by default before the first API
call. `--skip-local-preflight` exists only for controlled debugging and does
not bypass `--confirm-external-llm-data-transfer`.

Then review the no-network data-transfer manifest. It lists the pending
initial calls that `--resume-missing` would send, the target endpoints and
models, backend protocol settings, aggregate payload sizes, prompt
hashes/sizes, selected docs, correction budget, initial prompt local-path
policy, and the bounded repair-feedback policy. It also prints the reviewed
payload fingerprint used by the approval packet and approved rerun log:

```bash
make transfer-manifest-with-vs-without
```

The Markdown view groups repeats for review. Use
`python tools/with_vs_without/manifest_nv_model_data_transfer.py --format json`
for exact per-repeat records and prompt hashes.

For a single local approval review artifact, use:

```bash
make approval-packet-with-vs-without
```

The packet makes no network calls. It combines preflight readiness, pending
transfer scope, current audit status, data policy, and the exact remediation
commands that include `--confirm-external-llm-data-transfer`.
It also records a reviewed payload fingerprint covering the prompt hashes,
selected documentation hashes, staged input path, output directory, backend,
model, backend protocol settings, prompt style, correction budget, arm, and
repeat records that define the external transfer scope.
The packet is approval-ready only when every pending external skill/mode group
is matched by a direct `codex-opus` or `nemotron` remediation command for the
selected mode, with no duplicate direct commands for the same skill/mode group,
and with zero pending prompt payload policy issues.

To preview the post-approval rerun sequence without network calls:

```bash
make approved-rerun-plan-with-vs-without
```

The underlying helper defaults to dry-run. Actual execution requires both
`--execute` and `--confirm-external-llm-data-transfer`, and it refuses to run
commands that do not match the reviewed approval-packet protocol. It writes a
JSONL execution log at `runs/with_vs_without_nv/approved_reruns.jsonl` by
default, and the dry-run plan repeats the reviewed payload fingerprint,
coverage count, duplicate-command count, invalid-command count, and any
approval errors from the approval packet. Pass `--resume-log` with the same log
after an interruption to annotate commands that previously recorded
`returncode=0` for the same reviewed payload fingerprint. The helper still
reruns any command that remains in the current audit-derived plan; the inner
study runner's `--resume-missing` then reuses only valid per-repeat artifacts.
The dry-run exits nonzero if the approval packet is not ready.

Run direct API studies only when the target backend cannot read files itself:

```bash
python tools/with_vs_without/run_nv_model_studies.py \
  --skills nv_segment_ct \
  --mode codex-opus \
  --prompt-style minimal \
  --max-correction-steps 0 \
  --repeats 3 \
  --resume-missing \
  --confirm-external-llm-data-transfer
```

Direct API runs embed the full selected document in the prompt because the
backend has no file-reading tool. They send the scenario task prompt, selected
SKILL.md or upstream README text, neutral staged input path, generated
commands, and bounded verifier failure summaries to the configured external
LLM API. Run them only after that data transfer is explicitly approved. Treat
those runs as a direct-chat approximation; the path-prompt artifacts are the
fair protocol for tool-enabled agents.
Prompt artifacts record the selected document paths, byte counts, and SHA-256
hashes. The audit rejects missing, empty, stale, or truncated documentation so
the README-only arm is not silently weakened by an unavailable README.
Repair feedback is deliberately bounded: it carries failed tier names,
exit code, generated-file evidence, and stdout/stderr tails only. Before a
repair prompt is sent, local home paths are redacted and README-only arms are
not allowed to receive hidden Medical AI Skills skill paths or wrapper names.
`--resume-missing` reuses valid per-repeat JSON artifacts, runs only missing
or invalid repeats, and then rebuilds aggregate JSON plus comparison Markdown.
Valid direct-study JSON records `prompt_style=minimal` and the five-step
correction budget; stale repeats from a different prompt or repair protocol
are ignored during resume. Reuse also checks saved repair prompts, exact
system/user/assistant/user role order, that each repair transcript reuses the
previous stored backend response verbatim as the next assistant message, final
top-level score/command fields, and `steps_to_pass`, so stale artifacts are
rerun before they can feed a fresh aggregate. Repair prompts must exactly
match the runner-generated feedback for the previous attempt; additional hints
or edited failure details invalidate the repeat.
Before execution, every generated command must reference the exact
repeat-specific output directory, the neutral staged input path, and an
expected runnable surface; otherwise the attempt is recorded as blocked and no
shell command is run. README-only commands are also blocked if they call hidden
Medical AI Skills skill paths or wrapper basenames from the with-skill arm.
Every accepted attempt must preserve the exact backend model, raw backend
protocol settings, raw backend response text, and usage metadata, including
single-attempt successes, so auditors can reconstruct what the model saw and
returned. Any recorded command must equal the command extracted from exactly
one shell-style fenced block in that stored response; raw command text or
multiple command blocks make the repeat invalid for reuse.
The strict audit also checks the actual stored first system/user messages in
each repeat, so an artifact cannot pass by relabeling `prompt_style` if it was
created with an older prompt or hand-edited hint.
Aggregate JSON is treated as derived data: the audit recomputes summary fields
from aggregate repeats and requires every aggregate repeat entry to match the
corresponding per-repeat JSON artifact. This prevents a stale or edited
aggregate from overstating a with-skill advantage.
`comparison.md` is also treated as derived data: the audit regenerates it from
the current aggregate JSON and rejects stale or hand-edited summaries before
they can be cited.
Reports include both aggregate pass/score counts and backend/repeat-paired
outcomes, using pass/fail as the primary outcome and score only to break ties.
They also include an outcome-support gate. A complete artifact set is not
enough to claim the skill helped: the gate supports a SKILL.md advantage only
when the study-artifact audit is complete and the with-skill arm wins more
matched backend-repeat pairs than the README-only arm, with no missing pairs.
The audit and reports also include a descriptive exact one-sided paired sign
test over decisive pairs, ignoring ties, so the paired win pattern has an
explicit strength-of-evidence summary.

Inspect artifact completeness without failing partial worktrees:

```bash
make audit-with-vs-without
```

Require both complete artifacts and SKILL.md paired advantage for every
covered skill:

```bash
make prove-with-vs-without
```

Print only the resume commands needed for the current incomplete artifacts:

```bash
make plan-with-vs-without
```

Before citing aggregate results as complete, require the strict audit to pass:

```bash
python tools/with_vs_without/audit_nv_model_studies.py --strict
```

Regenerate Markdown reports after all required study JSON exists. Detailed
per-skill reports are local generated artifacts under
`runs/with_vs_without_nv/reports/`; the aggregate summary is checked in at
`docs/with-vs-without-skill-experiment.md`.

```bash
python tools/with_vs_without/write_nv_model_reports.py
```

That command also refreshes
`tools/with_vs_without/data/nv_model_study_invariants.json`, a compact
machine-readable snapshot of material state. It records protocol settings,
payload/document/input fingerprints, backend protocol hashes, and pass/fail
outcomes, while excluding local paths, timestamps, generated commands, provider
responses, token counts, logs, and environment details.

Before opening a PR after rerunning local experiments:

```bash
make check-invariants-with-vs-without
```

If the check fails and the audit result changed for a real reason, run
`make invariants-with-vs-without` and include the snapshot diff with the
aggregate summary update. Do not commit files under `runs/` or detailed
`docs/with-vs-without-nv-*.md` reports.

Fast design checks:

```bash
make verify-with-vs-without
```
