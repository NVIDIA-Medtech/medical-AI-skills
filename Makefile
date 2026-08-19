# Medical AI Skills — one-command flows.
#
# These wrap the scaffolding scripts in eval_engine/. They are not a public CLI.
# See AGENTS.md and ARCHITECTURE.md for the shape this is converging on.

PYTHON ?= python3
PRE_COMMIT ?= pre-commit
SKILL ?= dicom-metadata-extract
SKILL_DIR := $(subst _,-,$(SKILL))
FIXTURE ?= skills/$(SKILL_DIR)/fixtures/sample_ct.dcm
OUT ?= runs/$(SKILL)_demo
PACK ?=
REVIEW_PACKET_OUT ?=
VALIDATE_PACK_ARGS ?=
SCENARIO ?=
VALIDATE_SKILL_OUT ?= runs/validate_skill
WORKFLOW ?=
WORKFLOW_INPUT ?=
WORKFLOW_OUT ?=
BENCHMARK ?=
BENCHMARK_OUT ?= runs/benchmark_demo
BENCHMARK_JOBS ?= 1
BENCHMARK_ARGS ?=
LLM_BACKEND ?= mock
LLM_MODEL ?=
LLM_BASE_URL ?=
LLM_OUT ?= runs/llm_$(SKILL)_demo
LLM_ARGS ?=
RUN_A ?=
RUN_B ?=
DIFF_ARGS ?=
CANONICAL_PACK ?= examples/evidence_packs/dicom_metadata_pass
A ?=
B ?=
COMPARE_OUT ?=
AUDIT_OUT ?= runs/audit_$(SKILL)
ACTION ?=
SKILL_EVALUATOR ?= skillevaluator
SKILL_EVALUATOR_OUT ?= /tmp/medical-AI-skills-skillevaluator
SKILL_EVALUATOR_REPORTS ?= json,markdown
SKILL_EVALUATOR_FLAGS ?= --external --no-dedup -c --min-score 70

WORKFLOW_CT_SEG ?= examples/workflows/ct_dicom_to_segmentation_evidence.yaml
WORKFLOW_CT_SEG_OUT ?= runs/ct_dicom_seg_evidence
.PHONY: help help-run help-author help-trust help-study help-all run-skill run-llm-skill run-workflow run-workflow-ct-seg run-benchmark run-trusted diff lint test verify verify-skills verify-reproducibility verify-negative-fixtures verify-with-vs-without audit-with-vs-without preflight-with-vs-without transfer-manifest-with-vs-without approval-packet-with-vs-without approved-rerun-plan-with-vs-without invariants-with-vs-without check-invariants-with-vs-without status-agent-skills prove-agent-skills prove-with-vs-without plan-with-vs-without study skill-evaluator-check skill-evaluator-validate validate-skills-external nv-base-check nv-base-validate validate-skills-internal list-skills compare-skills audit-skill clean-runs validate-pack review-packet validate-skill bench-matrix copyright copyright-check

help:
	@echo "Targets:"
	@echo "  help-run      execution paths (run-skill, run-workflow, run-benchmark, ...)"
	@echo "  help-author   skill authoring, catalog validation, and repo checks"
	@echo "  help-trust    evidence-pack, verifier, and trust commands"
	@echo "  help-study    with-vs-without study maintenance"
	@echo "  help-all      every target, including compatibility aliases"
	@echo ""
	@echo "Common:"
	@echo "  make list-skills"
	@echo "  make run-skill SKILL=<name> FIXTURE=<path> OUT=<dir>"
	@echo "  make run-trusted SKILL=<name> FIXTURE=<path> OUT=<dir>"
	@echo "  make validate-pack PACK=<dir>"
	@echo "  make review-packet PACK=<dir>"
	@echo "  make lint"
	@echo "  make copyright"
	@echo "  make test"
	@echo "  make verify"
	@echo ""
	@echo "Run 'make help-all' for the full target list."

help-all:
	@echo "Targets, grouped by contributor intent (Discover / Run / Author / Trust / Compare / Study / Maintain):"
	@echo "  --- Help ---"
	@echo "  help                                                    short common target list"
	@echo "  help-run                                                execution paths"
	@echo "  help-author                                             skill authoring, catalog validation, and repo checks"
	@echo "  help-trust                                              evidence-pack, verifier, and trust commands"
	@echo "  help-study                                              with-vs-without study maintenance"
	@echo "  help-all                                                every target, including compatibility aliases"
	@echo "  --- Discover ---"
	@echo "  list-skills                                             regenerate SKILL_INDEX.md"
	@echo "  --- Run ---"
	@echo "  run-skill      SKILL=<name> FIXTURE=<path> OUT=<dir>   single-skill evidence pack"
	@echo "  run-llm-skill  SKILL=<name> FIXTURE=<path> [LLM_ARGS='--max-tokens 256']   LLM-mediated skill call"
	@echo "  run-workflow   WORKFLOW=<yaml> WORKFLOW_INPUT=<path> WORKFLOW_OUT=<dir>   multi-skill workflow"
	@echo "  run-workflow-ct-seg  WORKFLOW_INPUT=<dicom_dir> [WORKFLOW_CT_SEG_OUT=...]  Workflow 1: DICOM->NIfTI->segment+verifier"
	@echo "  run-benchmark  SKILL=<name> BENCHMARK=<yaml> [BENCHMARK_ARGS='--limit 1']  benchmark evidence pack"
	@echo "  run-trusted    SKILL=<name> FIXTURE=<path> OUT=<dir>  skill + every implemented paired verifier"
	@echo "  --- Author ---"
	@echo "  audit-skill    SKILL=<name>                            run skill_completeness_v1 against one skill"
	@echo "  validate-skill SCENARIO=<path> [VALIDATE_SKILL_OUT=<dir>]   paired with/without skill behavior eval (v0: mock backend)"
	@echo "  verify-skills                                           audit every skill/verifier + repeat reproducibility checks"
	@echo "  verify-reproducibility                                  run manifest-declared repeat/preflight reproducibility audit"
	@echo "  skill-evaluator-check                                   verify the public skillevaluator CLI is available"
	@echo "  skill-evaluator-validate [SKILL_EVALUATOR=/path/to/skillevaluator]   run the public external publication preflight"
	@echo "  validate-skills-external                                alias for skill-evaluator-validate"
	@echo "  --- Trust ---"
	@echo "  verify                                                  smoke-test evidence harness (lint + canonical pack diff)"
	@echo "  verify-negative-fixtures                                run every manifest-declared negative fixture"
	@echo "  validate-pack  PACK=<dir> [VALIDATE_PACK_ARGS='--allow-legacy']   validate pack/trusted-run against spec/evidence_pack.schema.json"
	@echo "  review-packet  PACK=<dir> [REVIEW_PACKET_OUT=<path>]              render compact human review packet under runs/"
	@echo "  --- Compare ---"
	@echo "  diff           RUN_A=<dir> RUN_B=<dir> [DIFF_ARGS='--ignore-env']  evidence-pack drift report"
	@echo "  compare-skills A=<pack_a> B=<pack_b>                   declared-shape comparison between two skill packs"
	@echo "  bench-matrix                                            render cross-skill benchmark matrix"
	@echo "  --- Study ---"
	@echo "  verify-with-vs-without                                  test prompt protocol, audit guard, and harness checks"
	@echo "  audit-with-vs-without                                   inspect current NV model study completeness"
	@echo "  preflight-with-vs-without                               check local readiness before direct NV model reruns"
	@echo "  transfer-manifest-with-vs-without                       show no-network data-transfer manifest for pending reruns"
	@echo "  approval-packet-with-vs-without                         compose preflight, transfer, audit, and approval commands"
	@echo "  approved-rerun-plan-with-vs-without                     dry-run reviewed external rerun command plan"
	@echo "  invariants-with-vs-without                              write git-trackable invariant snapshot from local study records"
	@echo "  check-invariants-with-vs-without                        verify local study records match tracked invariant snapshot"
	@echo "  study ACTION=<audit|preflight|transfer-manifest|approval-packet|approved-rerun-plan|invariants|check-invariants|status|prove-agent-skills|prove-with-vs-without|plan>   one-stop dispatcher"
	@echo "  status-agent-skills                                     summarize strict skill/harness readiness + proof state"
	@echo "  prove-agent-skills                                      require strict skill/harness audit and completed advantage proof"
	@echo "  prove-with-vs-without                                   require complete studies and SKILL.md paired advantage"
	@echo "  plan-with-vs-without                                    print resume commands for incomplete NV model studies"
	@echo "  --- Maintain ---"
	@echo "  lint                                                    structural + doc lints"
	@echo "  test                                                    pytest (eval_engine + skills + verifiers + with-vs-without harness)"
	@echo "  clean-runs                                              remove local generated runs"
	@echo "  --- Deprecated compatibility aliases ---"
	@echo "  nv-base-check                                           deprecated alias for skill-evaluator-check"
	@echo "  nv-base-validate                                        deprecated alias for skill-evaluator-validate"
	@echo "  validate-skills-internal                                deprecated alias for skill-evaluator-validate"

help-run:
	@echo "Run targets:"
	@echo "  run-skill      SKILL=<name> FIXTURE=<path> OUT=<dir>   single-skill evidence pack"
	@echo "  run-llm-skill  SKILL=<name> FIXTURE=<path> [LLM_ARGS='--max-tokens 256']   LLM-mediated skill call"
	@echo "  run-workflow   WORKFLOW=<yaml> WORKFLOW_INPUT=<path> WORKFLOW_OUT=<dir>   multi-skill workflow"
	@echo "  run-workflow-ct-seg  WORKFLOW_INPUT=<dicom_dir> [WORKFLOW_CT_SEG_OUT=...]  Workflow 1: DICOM->NIfTI->segment+verifier"
	@echo "  run-benchmark  SKILL=<name> BENCHMARK=<yaml> [BENCHMARK_ARGS='--limit 1']  benchmark evidence pack"
	@echo "  run-trusted    SKILL=<name> FIXTURE=<path> OUT=<dir>  skill + every implemented paired verifier"

help-author:
	@echo "Author targets:"
	@echo "  audit-skill    SKILL=<name>                            run skill_completeness_v1 against one skill"
	@echo "  validate-skill SCENARIO=<path> [VALIDATE_SKILL_OUT=<dir>]   paired with/without skill behavior eval (v0: mock backend)"
	@echo "  verify-skills                                           audit every skill/verifier + repeat reproducibility checks"
	@echo "  verify-reproducibility                                  run manifest-declared repeat/preflight reproducibility audit"
	@echo "  skill-evaluator-check                                   verify the public skillevaluator CLI is available"
	@echo "  skill-evaluator-validate [SKILL_EVALUATOR=/path/to/skillevaluator]   run the public external publication preflight"
	@echo "  validate-skills-external                                alias for skill-evaluator-validate"
	@echo "  nv-base-validate                                        deprecated compatibility alias"
	@echo "  list-skills                                             regenerate SKILL_INDEX.md"
	@echo "  lint                                                    structural + doc lints"
	@echo "  test                                                    pytest (eval_engine + skills + verifiers + with-vs-without harness)"
	@echo "  clean-runs                                              remove local generated runs"

help-trust:
	@echo "Trust targets:"
	@echo "  verify                                                  smoke-test evidence harness (lint + canonical pack diff)"
	@echo "  verify-negative-fixtures                                run every manifest-declared negative fixture"
	@echo "  validate-pack  PACK=<dir> [VALIDATE_PACK_ARGS='--allow-legacy']   validate pack/trusted-run against spec/evidence_pack.schema.json"
	@echo "  review-packet  PACK=<dir> [REVIEW_PACKET_OUT=<path>]              render compact human review packet under runs/"
	@echo "  diff           RUN_A=<dir> RUN_B=<dir> [DIFF_ARGS='--ignore-env']  evidence-pack drift report"
	@echo "  compare-skills A=<pack_a> B=<pack_b>                   declared-shape comparison between two skill packs"
	@echo "  bench-matrix                                            render cross-skill benchmark matrix"

help-study:
	@echo "Study targets:"
	@echo "  study ACTION=<audit|preflight|transfer-manifest|approval-packet|approved-rerun-plan|invariants|check-invariants|status|prove-agent-skills|prove-with-vs-without|plan>   one-stop dispatcher"
	@echo "  audit-with-vs-without                                   inspect current NV model study completeness"
	@echo "  preflight-with-vs-without                               check local readiness before direct NV model reruns"
	@echo "  transfer-manifest-with-vs-without                       show no-network data-transfer manifest for pending reruns"
	@echo "  approval-packet-with-vs-without                         compose preflight, transfer, audit, and approval commands"
	@echo "  approved-rerun-plan-with-vs-without                     dry-run reviewed external rerun command plan"
	@echo "  invariants-with-vs-without                              write git-trackable invariant snapshot from local study records"
	@echo "  check-invariants-with-vs-without                        verify local study records match tracked invariant snapshot"
	@echo "  status-agent-skills                                     summarize strict skill/harness readiness + proof state"
	@echo "  prove-agent-skills                                      require strict skill/harness audit and completed advantage proof"
	@echo "  prove-with-vs-without                                   require complete studies and SKILL.md paired advantage"
	@echo "  plan-with-vs-without                                    print resume commands for incomplete NV model studies"
	@echo "  verify-with-vs-without                                  test prompt protocol, audit guard, and harness checks"

test:
	$(PYTHON) -m pytest eval_engine/tests skills verifiers tools/with_vs_without/tests tools/goal_readiness/tests tools/contract_summary/tests tools/review_packet/tests tools/trace_inventory/tests tools/validate_skill/tests -q --tb=short --import-mode=importlib

lint:
	$(PYTHON) -m eval_engine.lint_repo
	$(PRE_COMMIT) run --all-files

# Add any missing NVIDIA SPDX copyright headers, then bump the year of existing
# ones to the current year. Auto-corrects in place; safe to run repeatedly.
copyright:
	$(PYTHON) .github/workflows/scripts/add_copyright_headers.py . \
	  --exclude-config .github/workflows/scripts/copyright_excludes.txt
	$(PYTHON) .github/workflows/scripts/check_copyright.py . \
	  --exclude-config .github/workflows/scripts/copyright_excludes.txt --update-current-year

# Read-only header check (what CI runs). Fails if any header is missing/stale.
copyright-check:
	$(PYTHON) .github/workflows/scripts/check_copyright.py . \
	  --exclude-config .github/workflows/scripts/copyright_excludes.txt --ignore-year-mismatch

run-skill:
	$(PYTHON) eval_engine/run.py skills/$(SKILL_DIR) --fixture $(FIXTURE) --out $(OUT)

run-trusted:
	$(PYTHON) -m eval_engine.run_trusted skills/$(SKILL_DIR) --fixture $(FIXTURE) --out $(OUT)

run-llm-skill:
	$(PYTHON) eval_engine/run_llm_skill.py skills/$(SKILL_DIR) \
	  --fixture $(FIXTURE) \
	  --out $(LLM_OUT) \
	  --backend $(LLM_BACKEND) \
	  --model "$(LLM_MODEL)" \
	  --base-url "$(LLM_BASE_URL)" \
	  $(LLM_ARGS)

run-workflow:
	@if [ -z "$(WORKFLOW)" ] || [ -z "$(WORKFLOW_INPUT)" ] || [ -z "$(WORKFLOW_OUT)" ]; then \
		echo "Usage: make run-workflow WORKFLOW=<yaml> WORKFLOW_INPUT=<path> WORKFLOW_OUT=<dir>"; exit 2; \
	fi
	$(PYTHON) eval_engine/run_workflow.py $(WORKFLOW) --input $(WORKFLOW_INPUT) --out $(WORKFLOW_OUT)

# Workflow 1: DICOM series -> dicom-series-to-volume -> nv-segment-ct (trusted) -> trust summary
run-workflow-ct-seg:
	@if [ -z "$(WORKFLOW_INPUT)" ]; then \
		echo "Usage: make run-workflow-ct-seg WORKFLOW_INPUT=<dicom_series_dir> [WORKFLOW_CT_SEG_OUT=runs/ct_dicom_seg_evidence]"; exit 2; \
	fi
	$(PYTHON) eval_engine/run_workflow.py $(WORKFLOW_CT_SEG) --input $(WORKFLOW_INPUT) --out $(WORKFLOW_CT_SEG_OUT)

run-benchmark:
	@if [ -z "$(BENCHMARK)" ]; then \
		echo "Usage: make run-benchmark SKILL=<name> BENCHMARK=<yaml> BENCHMARK_OUT=<dir> BENCHMARK_JOBS=<n> [BENCHMARK_ARGS='--limit 1']"; exit 2; \
	fi
	$(PYTHON) eval_engine/run_benchmark.py skills/$(SKILL_DIR) \
	  --benchmark $(BENCHMARK) \
	  --out $(BENCHMARK_OUT) \
	  --jobs $(BENCHMARK_JOBS) \
	  $(BENCHMARK_ARGS)

diff:
	@if [ -z "$(RUN_A)" ] || [ -z "$(RUN_B)" ]; then \
		echo "Usage: make diff RUN_A=<dir> RUN_B=<dir>"; exit 2; \
	fi
	$(PYTHON) eval_engine/diff_runs.py $(RUN_A) $(RUN_B) --out $(RUN_B)/drift_report.md $(DIFF_ARGS)

# verify runs the doc + structural lints, then regenerates a fresh evidence
# pack from the canonical skill+fixture and diffs it against the committed
# pack. Smoke test that the eval_engine still produces comparable output.
# Output lands in runs/verify/.
verify: lint
	$(PYTHON) eval_engine/run.py skills/dicom-metadata-extract \
	  --fixture skills/dicom-metadata-extract/fixtures/sample_ct.dcm \
	  --out runs/verify
	$(PYTHON) eval_engine/diff_runs.py $(CANONICAL_PACK) runs/verify \
	  --out runs/verify/drift_report.md --ignore-env
	@echo "Verify complete. Pack at runs/verify/. Drift report at runs/verify/drift_report.md"
	@echo "(env_drift between runs is expected; gate_diffs and payload_diffs should be 0.)"

verify-skills:
	@bash eval_engine/audit_skills.sh

verify-reproducibility:
	@$(PYTHON) -m eval_engine.reproducibility

verify-negative-fixtures:
	@bash eval_engine/audit_negative_fixtures.sh

verify-with-vs-without:
	$(PYTHON) -m pytest tools/with_vs_without/tests -q --tb=short --import-mode=importlib

audit-with-vs-without:
	@$(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --format markdown

preflight-with-vs-without:
	@$(PYTHON) tools/with_vs_without/preflight_nv_model_studies.py --mode all --format markdown

transfer-manifest-with-vs-without:
	@$(PYTHON) tools/with_vs_without/manifest_nv_model_data_transfer.py --mode all --format markdown

approval-packet-with-vs-without:
	@$(PYTHON) tools/with_vs_without/approval_packet_nv_model_studies.py --mode all --format markdown

approved-rerun-plan-with-vs-without:
	@$(PYTHON) tools/with_vs_without/run_approved_nv_model_studies.py --mode all --format markdown

invariants-with-vs-without:
	@$(PYTHON) tools/with_vs_without/write_nv_model_invariants.py

check-invariants-with-vs-without:
	@$(PYTHON) tools/with_vs_without/write_nv_model_invariants.py --check

study: export ACTION := $(value ACTION)
study:
	@action="$${ACTION}"; \
	case "$$action" in \
	  audit) $(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --format markdown ;; \
	  preflight) $(PYTHON) tools/with_vs_without/preflight_nv_model_studies.py --mode all --format markdown ;; \
	  transfer-manifest) $(PYTHON) tools/with_vs_without/manifest_nv_model_data_transfer.py --mode all --format markdown ;; \
	  approval-packet) $(PYTHON) tools/with_vs_without/approval_packet_nv_model_studies.py --mode all --format markdown ;; \
	  approved-rerun-plan) $(PYTHON) tools/with_vs_without/run_approved_nv_model_studies.py --mode all --format markdown ;; \
	  invariants) $(PYTHON) tools/with_vs_without/write_nv_model_invariants.py ;; \
	  check-invariants) $(PYTHON) tools/with_vs_without/write_nv_model_invariants.py --check ;; \
	  status) bash eval_engine/audit_skills.sh && $(PYTHON) -m pytest tools/with_vs_without/tests -q --tb=short --import-mode=importlib && $(PYTHON) tools/goal_readiness/agent_skill_readiness.py --format markdown ;; \
	  prove-agent-skills) bash eval_engine/audit_skills.sh && $(PYTHON) -m pytest tools/with_vs_without/tests -q --tb=short --import-mode=importlib && $(PYTHON) tools/goal_readiness/agent_skill_readiness.py --strict --format markdown ;; \
	  prove-with-vs-without) $(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --strict --require-skill-advantage --format markdown ;; \
	  plan) $(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --format commands ;; \
	  "") echo "Usage: make study ACTION=<audit|preflight|transfer-manifest|approval-packet|approved-rerun-plan|invariants|check-invariants|status|prove-agent-skills|prove-with-vs-without|plan>" >&2; exit 2 ;; \
	  *) printf 'Unknown ACTION: %s\n' "$$action" >&2; exit 2 ;; \
	esac

status-agent-skills: verify-skills verify-with-vs-without
	@$(PYTHON) tools/goal_readiness/agent_skill_readiness.py --format markdown

prove-agent-skills: verify-skills verify-with-vs-without
	@$(PYTHON) tools/goal_readiness/agent_skill_readiness.py --strict --format markdown

prove-with-vs-without:
	@$(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --strict --require-skill-advantage --format markdown

plan-with-vs-without:
	@$(PYTHON) tools/with_vs_without/audit_nv_model_studies.py --format commands

skill-evaluator-check:
	@if ! command -v "$(SKILL_EVALUATOR)" >/dev/null 2>&1; then \
		echo "skillevaluator command not found: $(SKILL_EVALUATOR)"; \
		echo "Install the public release (https://docs.nvidia.com/skills/skillevaluator/installation), or run:"; \
		echo "  make skill-evaluator-validate SKILL_EVALUATOR=/path/to/skillevaluator"; \
		exit 127; \
	fi
	@skill_evaluator_path="$$(command -v "$(SKILL_EVALUATOR)")"; \
		echo "skillevaluator: $$skill_evaluator_path"; \
		"$$skill_evaluator_path" --version

skill-evaluator-validate: skill-evaluator-check
	@skill_evaluator_path="$$(command -v "$(SKILL_EVALUATOR)")"; \
		"$$skill_evaluator_path" validate skills \
		$(SKILL_EVALUATOR_FLAGS) \
		-r "$(SKILL_EVALUATOR_REPORTS)" \
		-o "$(SKILL_EVALUATOR_OUT)"

validate-skills-external: skill-evaluator-validate

nv-base-check:
	@echo "warning: nv-base-check is deprecated; use skill-evaluator-check" >&2
	@$(MAKE) --no-print-directory skill-evaluator-check

nv-base-validate:
	@echo "warning: nv-base-validate is deprecated; use skill-evaluator-validate" >&2
	@$(MAKE) --no-print-directory skill-evaluator-validate

validate-skills-internal:
	@echo "warning: validate-skills-internal is deprecated; use validate-skills-external" >&2
	@$(MAKE) --no-print-directory skill-evaluator-validate

list-skills:
	$(PYTHON) -m eval_engine.list_skills --out SKILL_INDEX.md

audit-skill:
	$(PYTHON) eval_engine/run.py verifiers/skill_completeness_v1 \
	  --fixture skills/$(SKILL_DIR) \
	  --out $(AUDIT_OUT)
	$(PYTHON) -m eval_engine.skill_audit_summary $(AUDIT_OUT)/output.json
	@echo "Audit complete. Pack at $(AUDIT_OUT)/. Open $(AUDIT_OUT)/output.json for the report."

compare-skills:
	@if [ -z "$(A)" ] || [ -z "$(B)" ]; then \
		echo "Usage: make compare-skills A=<pack_a> B=<pack_b> [COMPARE_OUT=<path>]"; exit 2; \
	fi
	@if [ -n "$(COMPARE_OUT)" ]; then \
		$(PYTHON) -m eval_engine.compare_skills $(A) $(B) --out $(COMPARE_OUT); \
	else \
		$(PYTHON) -m eval_engine.compare_skills $(A) $(B); \
	fi

validate-pack:
	@if [ -z "$(PACK)" ]; then \
		echo "Usage: make validate-pack PACK=<dir> [VALIDATE_PACK_ARGS='--allow-legacy']"; exit 2; \
	fi
	$(PYTHON) -m eval_engine.validate_pack $(PACK) $(VALIDATE_PACK_ARGS)

review-packet:
	@if [ -z "$(PACK)" ]; then \
		echo "Usage: make review-packet PACK=<dir> [REVIEW_PACKET_OUT=<path>]"; exit 2; \
	fi
	@if [ -n "$(REVIEW_PACKET_OUT)" ]; then \
		$(PYTHON) tools/render_review_packet.py "$(PACK)" --out "$(REVIEW_PACKET_OUT)"; \
	else \
		pack_name="$$(basename "$(PACK)")"; \
		out="runs/review_packets/$$pack_name.md"; \
		mkdir -p "$$(dirname "$$out")"; \
		$(PYTHON) tools/render_review_packet.py "$(PACK)" --out "$$out"; \
		echo "Review packet at $$out"; \
	fi

validate-skill: export SCENARIO := $(value SCENARIO)
validate-skill: export VALIDATE_SKILL_OUT := $(value VALIDATE_SKILL_OUT)
validate-skill: export LLM_BACKEND := $(value LLM_BACKEND)
validate-skill:
	@if [ -z "$${SCENARIO}" ]; then \
		echo "Usage: make validate-skill SCENARIO=<path> [VALIDATE_SKILL_OUT=<dir>] [LLM_BACKEND=mock]" >&2; \
		exit 2; \
	fi
	@$(PYTHON) -m tools.validate_skill.run "$${SCENARIO}" --out "$${VALIDATE_SKILL_OUT}" --backend "$${LLM_BACKEND}"

clean-runs:
	rm -rf runs/

# Render the cross-skill benchmark matrix from existing benchmark packs.
# Reads runs/ and examples/evidence_packs/ for packs with pack_kind=benchmark_run,
# groups by benchmark dataset, prints a markdown table per benchmark.
#
# Uses MATRIX_OUT (not BENCHMARK_OUT) to avoid colliding with run-benchmark's
# default of runs/benchmark_demo.
#
#   make bench-matrix                                       # all benchmarks, stdout
#   make bench-matrix BENCHMARK=ct_segmentation_spleen_msd09
#   make bench-matrix MATRIX_OUT=runs/matrix.md             # write to file
MATRIX_OUT ?=
MATRIX_ARGS ?=
bench-matrix:
	@if [ -n "$(BENCHMARK)" ] && [ -n "$(MATRIX_OUT)" ]; then \
		$(PYTHON) -m eval_engine.render_baselines $(BENCHMARK) --out $(MATRIX_OUT) $(MATRIX_ARGS); \
	elif [ -n "$(BENCHMARK)" ]; then \
		$(PYTHON) -m eval_engine.render_baselines $(BENCHMARK) $(MATRIX_ARGS); \
	elif [ -n "$(MATRIX_OUT)" ]; then \
		$(PYTHON) -m eval_engine.render_baselines --out $(MATRIX_OUT) $(MATRIX_ARGS); \
	else \
		$(PYTHON) -m eval_engine.render_baselines $(MATRIX_ARGS); \
	fi
