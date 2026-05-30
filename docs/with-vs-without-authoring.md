# Adding With-vs-Without Skill Comparisons

Use this guide when adding a with-vs-without comparison for a new skill.
The purpose is to test whether `LLM + SKILL.md` helps an agent read
documentation and take the right action compared with `LLM + upstream
README/guide`.

This is an engineering reproducibility protocol. It is not a clinical,
diagnostic, regulatory, or model-quality claim.

## Core Rule

Keep the prompt simple. The prompt should describe only the user's task, a
neutral input path, and the required output directory. It must not leak the
operational details the docs are supposed to teach.

Good prompt shape:

```text
The input image is at runs/with_vs_without_nv/_inputs/<skill>/case.nii.gz.
Run the requested workflow and write outputs under
runs/with_vs_without_nv/<skill>_<study>/<backend>/<arm>.
```

Do not put these in the prompt unless they are the actual user request:

- Wrapper script names.
- Upstream entrypoint names.
- Config filenames.
- Label IDs, model variants, anatomy controls, or modality constants.
- Setup commands copied from either documentation arm.
- Local machine paths such as `/home/<user>/...`.

Those details should be discoverable from `SKILL.md` in the with-skill arm
or from the upstream README/guide in the without-skill arm.

## Fair Comparison Contract

Both arms must differ only in the documentation available to the agent.

| Area | Requirement |
|---|---|
| User request | Same natural-language task, same staged input path, same output directory shape. |
| Backend | Same model, provider-default request shape, retry policy, and baseline correction budget. |
| Tools | Same command executor and same safety guard. |
| Input | Stage the fixture to `runs/with_vs_without_nv/_inputs/<skill>/...`; do not expose the source fixture path as the user input. |
| Output | Separate per-arm output dirs under `runs/with_vs_without_nv/`. Clean the arm output dir before execution. |
| Documentation | With arm reads `skills/<skill>/SKILL.md`; without arm reads one selected upstream README/model card/guide. |
| Forbidden access | Without arm must not read or call `skills/<skill>/`, wrapper scripts, manifests, validators, or evidence packs. |
| Grading | Same deterministic five-tier grader for both arms. |
| Repair budget | Main comparison uses `max_correction_steps=0` for both arms and all backends; repair-loop studies are separate diagnostics. |
| Repeats | Run three independent repeats for every skill/backend/arm configuration in the exploratory baseline; rerun selected groups with five repeats later when needed. |

The without-skill arm is not a no-docs baseline. It is the upstream-docs
baseline a reasonable user would have.

## Clean Environment

Use a clean execution state for each repeat. A comparison is not fair if one
arm or repeat inherits files, environment variables, activated shells, or
generated outputs from another arm or repeat.

At minimum:

- Run from the Medical AI Skills repo root in a noninteractive shell.
- Delete or recreate the repeat output directory before executing the generated
  command.
- Execute tier 5 with bare `python` and `pip` resolved to a fresh per-arm
  venv; do not credit packages installed in the host environment.
- Do not run tier 5 in a pre-activated conda environment. Conda is fine for
  developing the harness, but the generated command must prove its own Python
  runtime setup inside the per-arm execution venv.
- Use the neutral staged input path, not `skills/<skill>/fixtures/...`.
- Use separate output directories for every skill/backend/arm/repeat.
- Keep backend credentials outside prompts and reports.
- Record the exact command, exit code, stdout/stderr tails, output checks, and
  generated files in study JSON.
- Record the prompt artifact under `tools/nat_audit/data/`. Generate one
  prompt record per backend/arm/repeat so the path in the prompt already
  points at that repeat's output directory.

Dependency and model caches can be shared only when they are part of the
documented test environment and are equally available to both arms. Examples:

- A repo-local upstream cache under `.workbench_data/upstreams/...`.
- A Hugging Face model cache.
- The runner-managed transfer cache under
  `.workbench_data/with_vs_without_cache/`, exposed equally to both arms via
  cache environment variables such as `PIP_CACHE_DIR`, `HF_HOME`,
  `HF_HUB_CACHE`, `TORCH_HOME`, `XDG_CACHE_HOME`, `CONDA_PKGS_DIRS`,
  `UV_CACHE_DIR`, `CUDA_CACHE_PATH`, and `NUMBA_CACHE_DIR`.

If shared state is used, document it in the report and make sure it is not
encoded in the prompt as hidden help. Do not let the with arm silently benefit
from a local path the without arm cannot use.

In the current NV runner, this clean state is implemented by
`tools/with_vs_without/run_nv_model_studies.py`: each generated command is run
from the Medical AI Skills repo root after recreating the repeat output directory, with
`PATH` pointing first at a fresh `runs/with_vs_without_nv/_exec_envs/.../venv`,
`VIRTUAL_ENV` set to that venv, `PYTHONNOUSERSITE=1`, and `PYTHONPATH`
removed. The shared transfer-cache environment above is then injected equally
for both arms, followed by scenario-level environment variables such as
`NV_GENERATE_ROOT`.

The benchmark harness must create clean environments. A user-facing skill does
not have to create a clean environment on every ordinary user invocation.
Modifying a caller-selected Python environment can be acceptable when the user
has chosen that environment, but the behavior must be declared in
`skill_manifest.yaml` under `runtime.side_effects.environment`, together with
package installs, local writes, home/cache writes, network endpoints, GPU
requirements, and whether a fresh venv/container is recommended.

## Baseline Prompting Protocol

For the main with-vs-without comparison, stop after the first generated
command. Each backend/arm gets the same no-repair baseline budget:
`max_correction_steps=0`. A failed first command is data, not a reason to
continue repairing inside the baseline study.

The repair-loop implementation is retained for a separate experiment that asks
whether bounded correction improves failed runs. Do not mix that intervention
into the baseline comparison.

If a separate repair experiment is run, the repair prompt may include only:

- failed tier names and deterministic grader reasons;
- execution exit code;
- stdout/stderr tails;
- generated-file paths under the arm output directory;
- a request for a replacement single fenced bash command.

The repair prompt must not reveal the expected passing command, hidden wrapper
details, grader-only markers, or Medical AI Skills skill internals to the README-only
arm. If the generated command was blocked by the safety guard, report that
guard reason and let the model repair within the same documentation arm for
the separate repair experiment.
Before sending repair feedback, redact local home paths and hidden Medical AI Skills
skill paths or wrapper names from README-only prompts. The audit checks both
the prompt-artifact redaction policy and the saved direct-study repair
messages.

Direct API prompts must embed the full selected SKILL.md or README text. Do
not truncate long READMEs: truncation changes the README-only arm into a
different intervention. Prompt artifacts must record selected document paths,
byte counts, and SHA-256 hashes; the audit rejects missing, empty, stale, or
truncated documentation.

Reports must state how many prompting steps were needed:

- `0` means the initial command passed;
- `unresolved` means the initial command failed in the no-repair baseline.

For every failed attempt, save and report why the generated command did not
work. At minimum include failed tiers, exit code or blocked reason,
stdout/stderr tails when present, and generated-file evidence.
Before executing a generated command, the harness must require the
repeat-specific output directory, the neutral staged input path, and an
expected runnable surface. Commands that omit the user's staged data should be
blocked before shell execution, not run and scored afterward.
The README-only arm must also be blocked if it calls hidden Medical AI Skills skill
paths or wrapper basenames from the with-skill arm.

Report aggregate results across all five repeats. Include the pass count,
mean score, the per-repeat `steps_to_pass` values, unresolved repeat count, and
per-repeat attempt traces showing why commands failed.
Keep aggregate JSON derived from the per-repeat JSON files. The audit
recomputes aggregate summary fields and rejects aggregate repeat entries that
do not exactly match their corresponding per-repeat artifacts.
Keep `comparison.md` derived from the aggregate JSON. The audit regenerates the
expected comparison markdown and rejects stale or hand-edited summaries.

Also report paired outcomes by backend and repeat. Compare repeat 1 of the
with-skill arm to repeat 1 of the README-only arm for the same backend, repeat
2 to repeat 2, and so on. Pass/fail is the primary outcome; score should break
ties only when both arms have the same pass status. This prevents an aggregate
summary from hiding backend- or repeat-specific README wins.

Keep artifact completeness and outcome support separate. A refreshed report can
be complete yet still fail to support the skill-advantage claim. The
outcome-support gate supports `SKILL.md` only when the study-artifact audit is
complete, every expected backend-repeat pair is matched, and the with-skill arm
wins more matched pairs than the README-only arm.
Reports also include a descriptive exact one-sided paired sign test over
decisive pairs, ignoring ties. Treat the p-value as a strength-of-evidence
summary for the paired win pattern, not as a clinical or regulatory claim and
not as a replacement for the artifact-completeness gate.

For the stricter proof gate, run:

```bash
python tools/with_vs_without/audit_nv_model_studies.py \
  --strict \
  --require-skill-advantage
```

Before publishing or citing a refreshed aggregate, verify that every expected
prompt artifact, aggregate JSON, per-repeat JSON, and comparison Markdown file
exists and follows the current protocol:

```bash
python tools/with_vs_without/audit_nv_model_studies.py --strict
```

The audit also compares every with/without prompt pair. A pair is valid only
when the prompts differ by documentation path, documentation-boundary
instruction, and arm-specific output directory. It also generates the direct
API `minimal` embedded-doc prompt pair and permits only the documentation
text, documentation-boundary instruction, and output-directory differences.
Prompt text outside the allowed document content must not leak operational
markers such as wrapper names, config paths, label IDs, or source fixture
basenames.
For study JSON, the audit also checks that every repeat preserves the baseline
prompting protocol: attempt steps are sequential, prompt history length
matches the step, system/user roles appear for the first attempt, and
top-level score/command fields match the final attempt. Every accepted attempt
must also preserve the exact backend model, backend protocol settings, raw
backend response text, and usage metadata, including single-attempt successes.
Any recorded command must equal the command extracted from exactly one
shell-style fenced block in that stored response; raw command text or multiple
command blocks make the repeat invalid for reuse.
Direct API study artifacts must also record
`prompt_style: minimal` and `max_correction_steps: 0` in both aggregate and per-repeat JSON. The audit
compares the stored first system/user messages in
each repeat against the runner-generated minimal prompt for that skill, arm,
backend, and repeat-specific output directory; stale repeats from another
prompt or repair protocol are rerun by `--resume-missing`. Reuse also checks
exact message role order, final top-level score/command fields, and
`steps_to_pass`, so old partial artifacts cannot feed a refreshed aggregate.
When a separate repair experiment is enabled, saved repair prompts must exactly
match the runner-generated feedback for the previous attempt; extra hints or
edited failure details invalidate the repeat.

When refreshing an incomplete study, resume rather than rerun valid repeats:

```bash
python tools/with_vs_without/run_nv_model_studies.py \
  --skills <skill> \
  --mode all \
  --prompt-style minimal \
  --max-correction-steps 0 \
  --repeats 3 \
  --resume-missing \
  --confirm-external-llm-data-transfer
```

The runner reloads valid per-repeat JSON, runs only missing or invalid repeats,
then rewrites aggregate JSON and comparison Markdown from the full repeat set.
Before launching direct API reruns, run:

```bash
make preflight-with-vs-without
```

The preflight makes no API calls. It checks prompt artifacts, selected docs,
fixtures, path-like runtime caches, host shell/Python basics, and required API
key variable names without printing secret values. Direct API modes enforce
this local preflight by default before making the first API call;
`--skip-local-preflight` is only for controlled debugging and still does not
bypass `--confirm-external-llm-data-transfer`.
Then review the no-network data-transfer manifest:

```bash
make transfer-manifest-with-vs-without
```

The manifest lists pending initial external LLM calls under `--resume-missing`,
target endpoints/models, aggregate payload sizes, prompt hashes/sizes,
backend protocol settings, selected docs, correction budget, the reviewed
payload fingerprint, initial prompt local-path policy, and the bounded
repair-feedback policy. The Markdown view groups repeats for review; use
`--format json` for exact per-repeat records and prompt hashes.

For a single local review artifact before granting external-run approval, use:

```bash
make approval-packet-with-vs-without
```

The approval packet makes no network calls. It combines preflight readiness,
audit completeness, pending transfer scope, data policy, and the exact
remediation commands that include `--confirm-external-llm-data-transfer`. It
also records a reviewed payload fingerprint covering prompt hashes, selected
documentation hashes, staged input path, output directory, backend, model,
backend protocol settings, prompt style, correction budget, arm, and repeat
records. The packet is approval-ready only when every pending
external skill/mode group is matched by a direct `codex-opus` or `nemotron`
remediation command for the selected mode, with no duplicate direct commands
for the same skill/mode group, and with zero pending prompt payload policy
issues.

After approval, preview the exact rerun sequence without network calls:

```bash
make approved-rerun-plan-with-vs-without
```

The helper is dry-run by default. Actual execution requires both `--execute`
and `--confirm-external-llm-data-transfer`, and the helper validates that every
command still matches the reviewed prompt style, repeat count, correction
budget, resume behavior, and external-transfer approval flag. The dry-run plan
repeats the reviewed payload fingerprint, coverage count, and duplicate-command
count from the approval packet, along with invalid-command count and any
approval errors. It writes a JSONL execution log at
`runs/with_vs_without_nv/approved_reruns.jsonl` by default; pass `--resume-log`
with the same log after an interruption to annotate commands already recorded
with `returncode=0` for the same reviewed payload fingerprint. The helper still
reruns any command that remains in the current audit-derived plan; the inner
study runner's `--resume-missing` reuses only valid per-repeat artifacts. The
dry-run exits nonzero if the approval packet is not ready.

## Adding a Scenario

For the current NV model studies, add a `Scenario` entry in
`tools/with_vs_without/run_nv_model_studies.py`.

Fill in:

- `skill`: skill directory name.
- `fixture`: tiny committed fixture or request file used only for staging.
- `kind`: output verifier type. Add a new verifier branch only if the
  existing kinds do not fit.
- `task`: maintainer description of what the scenario tests.
- `user_goal`: minimal user-facing request with `{input_path}` and
  `{out_dir}` placeholders. The prompt audit rejects scenarios that omit either
  placeholder, because the agent must see both the neutral staged input path
  and repeat-specific output directory.
- `with_doc`: usually `("skills/<skill>/SKILL.md",)`.
- `without_doc`: the single upstream README/model card/guide used as the
  baseline. Store the selected document under
  `tools/with_vs_without/upstream_docs/` so prompt artifacts and audits do not
  depend on a local `.workbench_data` cache.
- `tier1`: runnable-surface markers.
- `tier2`: input markers, usually implied by the staged path.
- `tier3`: model, modality, label, or control markers expected in a correct
  command.
- `timeout_s`: long enough for the real workflow, short enough to catch
  wedged runs.
- `env`: optional environment values equally available during execution.

Example shape:

```python
"my_skill": Scenario(
    skill="my_skill",
    title="My Skill",
    fixture="skills/my_skill/fixtures/request.json",
    kind="json",
    task="Run the command-shape smoke test and write schema-valid JSON.",
    user_goal=(
        "The request is at {input_path}. Run the workflow and write "
        "structured JSON under {out_dir}."
    ),
    with_doc=("skills/my_skill/SKILL.md",),
    without_doc=("tools/with_vs_without/upstream_docs/my_skill_MyUpstream_README.md",),
    tier1=("run_my_skill.py", "upstream.entrypoint"),
    tier2=("request.json",),
    tier3=("model-name-or-mode",),
    timeout_s=900,
)
```

If the new skill does not fit the current runner, keep the same protocol in a
new harness under `tools/with_vs_without/` and write artifacts under the same
study and run roots.

## Worked Example: `nv_generate_ct_rflow`

Use this as the pattern for future model-skill comparisons. The task is to
synthesize one paired 3D CT image and segmentation mask for a chest case with a
lung tumor. The user-visible input is staged to:

```text
runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/chest_lung_tumor_controllable.json
```

The committed source fixture is only used for staging:

```text
skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json
```

The scenario entry names the task and docs, but the prompt does not leak
entrypoints or config filenames:

```python
"nv_generate_ct_rflow": Scenario(
    skill="nv_generate_ct_rflow",
    title="NV-Generate CT RFlow",
    fixture="skills/nv-generate-ct-rflow/fixtures/chest_lung_tumor_controllable.json",
    kind="ct_pair",
    task="Synthesize one paired 3D CT image and 132-class mask for chest with lung tumor.",
    user_goal=(
        "The case request is at {input_path}. Synthesize one paired 3D CT "
        "image and segmentation mask for a chest case with a lung tumor, and "
        "write the output pair under {out_dir}."
    ),
    with_doc=("skills/nv-generate-ct-rflow/SKILL.md",),
    without_doc=("tools/with_vs_without/upstream_docs/nv_generate_ct_rflow_NV-Generate-CTMR_infer_mask-image-paired.md",),
    tier1=("run_rflow_ct.py", "scripts.inference"),
    tier2=("chest_lung_tumor_controllable.json", "config_infer.json"),
    tier3=("rflow-ct", "lung tumor", "chest"),
    timeout_s=2400,
    env={"NV_GENERATE_ROOT": "<repo>/.workbench_data/upstreams/NV-Generate-CTMR"},
)
```

The `tier*` fields are grader-only markers. Do not put them in the prompt. If
the agent needs an entrypoint, config filename, model variant, anatomy mapping,
or setup command, that information belongs in `SKILL.md` for the with-skill arm
or in the upstream document for the without-skill arm.

The path-prompt artifact for a tool-enabled agent should use one symmetric
template for both arms. Only `<output_dir>`, `<doc_path>`, and the forbidden
path clause change:

```text
You are helping a medical-imaging engineer who has cloned
https://github.com/NVIDIA-Medtech/medical-AI-skills. The case request is at
runs/with_vs_without_nv/_inputs/nv_generate_ct_rflow/chest_lung_tumor_controllable.json.
Synthesize one paired 3D CT image and segmentation mask for a chest case with a
lung tumor, and write the output pair under <output_dir>. Tier-5 execution will
occur in a fresh per-arm Python environment with no runtime dependencies
preinstalled, so include any setup steps the documentation says are required.
The only workflow document available to you is <doc_path>. Read that document.
<forbidden_path_clause> Use list_directory only if you need to confirm paths.
Then produce a SINGLE shell command (or `&&`-chained sequence) inside one
fenced bash code block. Follow the bash block with a brief one-line
explanation. Do not run the command yourself.
```

For the with-skill arm:

```text
<doc_path> = skills/nv-generate-ct-rflow/SKILL.md
<forbidden_path_clause> = Do not inspect any other files under skills/nv-generate-ct-rflow/.
```

For the without-skill arm:

```text
<doc_path> = tools/with_vs_without/upstream_docs/nv_generate_ct_rflow_NV-Generate-CTMR_infer_mask-image-paired.md
<forbidden_path_clause> = Do not read or use any files under skills/nv-generate-ct-rflow/.
```

For direct chat-completion APIs that cannot call `read_file`, use the minimal
embedded-doc fallback: the same user request and constraints, followed by the
full text of the arm-specific document. Record that distinction in the report:
the embedded-doc run is an API fallback, while the path prompt is the primary
tool-agent fairness artifact.

For this example, the environment assumptions are:

- No conda activation is provided to tier 5.
- The generated command runs in a fresh per-arm venv with no runtime packages
  preinstalled.
- The upstream clone and downloaded model/data cache live at
  `.workbench_data/upstreams/NV-Generate-CTMR` and are equally available to
  both arms through `NV_GENERATE_ROOT`.
- The command is responsible for installing runtime Python packages into the
  fresh venv if the documentation says they are required.
- The arm output directory is deleted and recreated before execution.
- The safety guard is identical for both arms; commands with broad destructive
  shell fragments such as `rm`, `sudo`, `apt`, `docker`, `curl`, or `wget` are
  blocked and graded as tier-5 failures.

Reports should include the exact generated commands after the run. Do not put
observed passing commands into future prompts, scenario fixtures, or grader
markers. If a command detail is important for users, add it to the skill or the
selected upstream guide and let the agent discover it from the arm-specific
document.

## Prompt Artifacts

The primary fairness protocol uses A2-style path prompts. The prompt should
give a simple user task, a staged input path, an output path, the clean
environment assumption, and the one document the agent should read. It should
not paste the document text into the prompt, and it should not reveal wrapper
entrypoints, labels, configs, model variants, or command snippets unless those
details are already part of the user's natural request.

Generate path prompt artifacts before or after the external run:

```bash
python tools/with_vs_without/run_nv_model_studies.py \
  --skills <skill> \
  --mode prompts \
  --prompt-style path
```

Prompt-artifact mode is intentionally path-only. Do not generate
`minimal` embedded-doc prompt artifacts for the tool-agent fairness record;
`minimal` is only for direct chat-completion study runs that cannot read repo
files. When `--write-prompt-artifacts` is combined with a direct run, it still
writes fair `path` artifacts.

The generated questions should read like:

```text
You are helping a medical-imaging engineer who has cloned
https://github.com/NVIDIA-Medtech/medical-AI-skills. The input is at ... .
The task is ... and write outputs under ... . Tier-5 execution will occur
in a fresh per-arm Python environment with no runtime dependencies
preinstalled, so include setup steps the documentation says are required.
The only workflow document available to you is <doc_path>. Read that document.
<forbidden_path_clause> Then produce a SINGLE shell command
...
```

For the with-skill arm, `<doc_path>` is `skills/<skill>/SKILL.md` and the
forbidden clause blocks other files under that skill directory. For the
without-skill arm, `<doc_path>` is the chosen upstream README/guide and the
forbidden clause blocks all files under `skills/<skill>/`.
The audit requires each path-prompt question to include the selected document
path, the exact read-the-document instruction, and the arm-specific forbidden
path clause.
It also pins shared prompt-artifact metadata such as the system prompt,
generic answer template, runner path, prompt-source function, backend label,
backend model, endpoint, sampling/thinking settings, token cap, retry policy,
and five-step correction budget.
For path-prompt artifacts, the audit recomputes the exact runner-generated
question for every skill/backend/arm/repeat, so shared extra hints fail even
when with/without symmetry is preserved.

Check that the whole path prompt does not leak operational details:

```bash
python - <<'PY'
import json, pathlib, re
for p in pathlib.Path("tools/nat_audit/data").glob("eval_nv_model_studies_<skill>_prompts.json"):
    rows = json.loads(p.read_text())
    leaks = []
    for r in rows:
        request = r["question"]
        if re.search(r"configs/|run_[a-z0-9_]+\\.py|monai\\.bundle|model-name", request):
            leaks.append(r["id"])
    print(p, leaks)
PY
```

Adjust the regex for the new skill's domain markers.

## Running

Run external LLM/GPU experiments outside the sandbox when required by the
workflow:

```bash
python tools/with_vs_without/run_nv_model_studies.py \
  --skills <skill> \
  --mode all \
  --prompt-style minimal \
  --confirm-external-llm-data-transfer
```

`--prompt-style minimal` is the direct-API fallback: it embeds the
arm-specific document because plain chat-completion backends do not have a
file-reading tool. Direct API runs send the scenario task prompt, selected
SKILL.md or upstream README text, neutral staged input path, generated
commands, and, only for separate repair experiments, bounded verifier failure summaries to the configured external
LLM API, so the runner requires `--confirm-external-llm-data-transfer`.
Treat that as a direct-API study, not as the primary tool-agent fairness
prompt. For NAT or another file-reading agent harness, use the `path` prompt
artifacts and let the agent read `SKILL.md` or the upstream README itself. In
both modes, generated commands are executed from clean per-arm output
directories with an isolated tier-5 Python venv. Each direct API arm then runs
the same configured `--max-correction-steps` value; the main baseline uses 0.

For targeted reruns:

```bash
python tools/with_vs_without/run_nv_model_studies.py \
  --skills <skill> \
  --mode codex-opus \
  --prompt-style minimal \
  --confirm-external-llm-data-transfer
```

Use `--mode nemotron` to rerun only the Nemotron baseline study.

## What To Do When With-Skill Fails

A with-skill failure is a product finding, not just an experiment result.
Inspect the generated command, stderr/stdout tails, and failed tiers. If the
agent could reasonably have succeeded with clearer skill guidance or a more
robust wrapper, fix the skill and rerun.

Good skill fixes:

- Make the direct runnable surface obvious.
- Prefer one short wrapper command for normal use.
- Add idempotent setup snippets.
- Add preflight checks with actionable errors.
- Accept the user's input path exactly as the positional input.
- Emit machine-readable stdout when the evaluator depends on stdout.
- Add wrapper fallbacks for conventional repo-local caches.
- Document model/control/label mappings that agents must choose.
- Make dependency constraints explicit.

Bad skill fixes:

- Hardcoding `/home/<user>/...` or another local path.
- Requiring a specific private conda environment name.
- Assuming a specific GPU index unless the user asks.
- Making `SKILL.md` depend on run directories from a previous experiment.
- Telling agents to use a fixture path when the user supplied a staged input.
- Adding hidden evaluator-only behavior that a real user would not have.

The skill may mention optional environment variables, but it should not depend
on local-only values. Prefer this pattern:

```bash
MY_TOOL_ROOT="${MY_TOOL_ROOT:-.workbench_data/upstreams/MyTool}" \
python skills/my_skill/scripts/run_my_skill.py PATH_TO_USER_INPUT \
  --output-dir runs/my_skill_case
```

The wrapper should fail clearly if the upstream cache, weights, or dependencies
are missing. It can search conventional locations, but it should not silently
bind to one user's machine.

## Reporting

After the run, regenerate Markdown reports:

```bash
python tools/with_vs_without/write_nv_model_reports.py
```

Detailed per-skill reports are local generated artifacts under
`runs/with_vs_without_nv/reports/`. The checked-in report is the aggregate
`docs/with-vs-without-skill-experiment.md`.

The report writer also updates
`tools/with_vs_without/data/nv_model_study_invariants.json`. This snapshot is
the PR review surface for repeated experiments: it tracks protocol settings,
selected-document and fixture hashes, backend protocol hashes, and material
outcomes, but excludes local paths, generated commands, provider responses,
token counts, timestamps, logs, and environment details.

Before submitting a rerun PR, check that local raw records match the tracked
snapshot:

```bash
make check-invariants-with-vs-without
```

If the check fails because the protocol or outcome changed, rerun
`make invariants-with-vs-without` and include the compact snapshot diff. Do not
commit raw study records, detailed reports, logs, or files under `runs/`.

Each report must include:

- The experiment question.
- The exact user request shape.
- The staged input path.
- Scores for every backend and arm.
- Failed tiers and execution exit codes.
- For every attempt, the full reason the generated command did not work.
- The number of prompting steps needed to pass, or `unresolved`.
- Provider-reported token profiling: prompt, completion, reasoning when
  available, total tokens, attempts, passes, and executed-runtime summaries by
  backend/arm.
- Exact generated commands from backend responses.
- Source artifact paths.
- Notes on any skill fixes made before the final rerun.
- The strict-audit status used for regeneration; if `--allow-incomplete` is
  used for a saved-artifact refresh, the report must say that the audit is
  incomplete instead of claiming a clean strict audit.
- For Nemotron reports, a diagnostic-only protocol layer that separates strict
  fenced-block compliance from deterministic recovery of malformed command
  text and summarizes protocol-compliance failure buckets. This must not alter
  the main pass/fail grade.

Do not claim a skill advantage until the with-skill arm exits cleanly and the
failure mode has been understood. If the final result is mixed or the upstream
README arm also passes, report that directly.

## Verification

Run at least:

```bash
python -m py_compile tools/with_vs_without/run_nv_model_studies.py
python tools/with_vs_without/write_nv_model_reports.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=. pytest -q tools/with_vs_without/tests
git diff --check
```

Also verify:

- The with arm exposes exactly `skills/<skill>/SKILL.md`, and the without arm
  exposes exactly one vendored upstream document under
  `tools/with_vs_without/upstream_docs/`.
- Each scenario `user_goal` includes both `{input_path}` and `{out_dir}`, and
  each generated prompt names the neutral staged input path.
- Every with-skill final JSON passes the deterministic grader or the report
  clearly explains why the skill is still unresolved.
- Prompt artifacts use `prompt_style=path`.
- The path prompts do not leak operational details.
- Markdown code fences are balanced.
- Large generated outputs remain under `runs/` or another gitignored path.
