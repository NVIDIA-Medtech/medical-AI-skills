# With-vs-without-skill experiment — backlog

Options to investigate after the first local baseline (backend=nemotron-3-super:120b,
inner anonymizer=medgemma, judge=medgemma) is running and understood.

## Roles (keep these distinct)
- **Backend / agent** — reads the doc (SKILL.md vs upstream README) and generates ONE
  shell command. Needs strong instruction-following. medgemma:27b is too weak here
  (wrote wrong script path, dropped `.csv`). Prior runs used gptoss / nemotron120-remote.
- **Inner anonymizer** — the model the generated command actually runs (GLiNER +
  validator/augmenter). medgemma:27b is proven good here (0 residual PHI on 5-row + 3-row).
- **Judge / reviewer** — scores residual PHI per row. Currently medgemma (per request);
  prior runs used gpt-oss-120b.

## Backlog
1. **Backend comparison** — nemotron-3-super:120b (local) vs medgemma (weak) vs
   gptoss / nemotron120-remote (remote, needs NVIDIA_API_KEY). Quantify command-gen
   correctness per backend (tier reached, path/`.csv` mistakes).
2. **Why medgemma-as-backend fails** — is it fixable with a stricter prompt, few-shot,
   or is 27B just under the bar? Decides whether small local models can self-serve.
3. **Repeats > 1** — average out backend command-gen variance (single-shot is noisy;
   one bad command nulls an arm).
4. **Judge calibration** — medgemma judge vs gpt-oss-120b judge: do they agree on
   residual-PHI counts? Re-score the same outputs with both and compare.
5. **nemotron reasoning control** — `chat_template_kwargs.enable_thinking:false` and
   `think:false` are NOT honored by Ollama (confirmed: ~15k reasoning tokens, JSON
   validator fails). `/no_think` stops reasoning but empties output. Investigate
   `reasoning_budget`, a proxy injecting the "detailed thinking off" system prompt, or
   a vLLM/NIM serving path — needed if we ever want nemotron as the inner validator.
6. **Harness output-discovery fix** — `_find_output_csv` now also matches a rep-named
   sibling CSV in the arm dir. Keep or revert once backends reliably write into
   `.../arm/repN/` (strong backends do). Symmetric across arms either way.
7. **Local-inner mechanism** — currently forced via `sitecustomize.py` on PYTHONPATH
   (monkeypatches `Anonymizer()` to local config). Document in the report so the run is
   reproducible; consider a first-class `--model-providers` path in the skill script.
8. **Inner speed** — raise `max_parallel_requests` / `OLLAMA_NUM_PARALLEL` to cut the
   ~14-22 s/report inner cost; measure quality impact.
9. **gpt-oss-120b as inner** — blocked by disk (65 GB > ~47 GB free on C:). Revisit if
   disk is freed or a second drive is added.
10. **Fairness note in report** — both arms use the same local medgemma inner via the
    sitecustomize patch; the arms differ ONLY in the doc the backend reads. State this.
11. **Execution mode: whole-job-at-once vs chunking** — the CURRENT baseline feeds the
    ENTIRE CSV into ONE anonymizer invocation per arm — call these
    **`with-whole-job-at-once`** and **`without-whole-job-at-once`**:
    - without: `anonymizer run --source <whole.csv> --output <one.csv>`
    - with:    `anonymize_reports.py <whole.csv> --full`
    One pipeline over all reports (row-parallel via `max_parallel_requests`; GLiNER
    chunks *within* a report, but there is no batching *across* reports).
    **Chunking is allowed** and worth adding: split the reports into batches, run one
    invocation per batch, then concatenate. Benefits: resumability, rate-limit
    resilience, bounded memory, and parallelism. Add a `--chunk-size` option and a
    `*-chunked` mode label alongside the whole-job baseline so the two are comparable.
