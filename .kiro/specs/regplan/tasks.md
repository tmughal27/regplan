# Implementation Plan: regplan

## Overview

Implement the `regplan` Python library and CLI as a six-stage pipeline (Ingest → Derive → Optimize → Evaluate → Simulate → Report). Each task builds incrementally on the previous ones, wiring new components into the package's public API as they are implemented. All business logic lives in the `regplan` package; the CLI and Streamlit app are zero-logic shells.

## Tasks

- [x] 1. Set up project structure, package skeleton, and CI configuration
  - Create the directory layout: `regplan/`, `cli/`, `streamlit_app/`, `tests/unit/`, `tests/property/`, `tests/golden/`
  - Write `pyproject.toml` with pinned runtime dependencies (pydantic, pyyaml, google-or-tools, networkx, numpy, typer, streamlit, jinja2, matplotlib, hypothesis, pytest, ruff, mypy)
  - Create `regplan/__init__.py` exporting one placeholder function per pipeline stage (ingest, derive, optimize, evaluate, simulate, report)
  - Create `regplan/errors.py` with `RegplanError`, `IngestError`, `SemanticError`, `TriggerEvalError`, `MissingAssumptionError`
  - Write `.github/workflows/ci.yml` running ruff, mypy --strict, pytest, and coverage check (≥ 80%) on push and pull requests to main
  - Write a minimal `Dockerfile` (non-root user, `regplan --help` smoke-test)
  - _Requirements: 1.1, 17.1–17.5, 19.1–19.5_

- [x] 2. Implement data models
  - [x] 2.1 Implement landscape models (`regplan/models/landscape.py`)
    - Write Pydantic v2 models for `Application`, `Interface`, `Vendor`, `ScenarioConfig`, `Landscape` and the `Disposition` enum
    - _Requirements: 2.1, 5.1_

  - [x] 2.2 Implement regulation and assumption models (`regplan/models/regulation.py`, `regplan/models/assumptions.py`)
    - Write `TriggerCondition` (recursive model), `RegulationRule`, `RegulationPack`
    - Write `DistributionSpec`, `DispositionRule`, `Assumptions`
    - _Requirements: 2.2, 2.3, 4.1–4.2, 12.2_

  - [x] 2.3 Implement work, finance, simulation, manifest, and report models
    - Write `WorkItem`, `Wave`, `Schedule` (`regplan/models/work.py`)
    - Write `CashFlow`, `FinancialResult` (`regplan/models/finance.py`)
    - Write `SimulationRun`, `TornadoEntry`, `SimulationResult` (`regplan/models/simulation.py`)
    - Write `RunManifest` (`regplan/models/manifest.py`)
    - Write `InfeasibilityReport`, `PipelineResult` (`regplan/models/report.py`)
    - _Requirements: 6.1–6.4, 8.1, 9.2, 11.1, 12.1, 12.5–12.7, 14.1, 15.1_

  - [ ]* 2.4 Write property test for pipeline result round-trip serialisation
    - **Property 5: Pipeline Result Round-Trip Serialization**
    - Serialise a `PipelineResult` to JSON and deserialise it, assert equality
    - **Validates: Requirements 14.1, 18.5**

- [x] 3. Implement the Ingest stage
  - [x] 3.1 Implement YAML loader (`regplan/ingest/loader.py`)
    - Read YAML files with PyYAML and construct Pydantic models for Landscape, RegulationPack, and Assumptions
    - Wrap `ValidationError` into `IngestError` with file path and field path
    - Expose `ingest(landscape_path, packs_paths, assumptions_path) -> IngestResult`
    - Ensure no side effects (no stdout, no network, no file writes) in the library
    - _Requirements: 1.4, 2.1–2.4_

  - [x] 3.2 Implement semantic validator (`regplan/ingest/validator.py`)
    - Check Interface source/target ids exist in the Landscape
    - Check Application and Interface id uniqueness within a Landscape
    - Check RegulationRule `source_url` non-empty and `last_verified` present
    - Check RegulationRule `deadline >= planning_start`
    - Raise `SemanticError(entity_id, rule_name, suggestion)` on any failure
    - _Requirements: 3.1–3.5_

  - [x] 3.3 Create example YAML files
    - Write `regplan/examples/landscapes/legacy_heavy.yaml` and `cloud_native.yaml` (each with ≥ 5 Applications, ≥ 3 Interfaces, ≥ 1 Vendor, ≥ 1 ScenarioConfig)
    - Write `regplan/examples/packs/gdpr.yaml`, `ai_act.yaml`, `nis2.yaml`, `dora.yaml` (each with ≥ 3 RegulationRules, valid source_url, last_verified)
    - Verify all example files pass schema and semantic validation
    - _Requirements: 2.5_

- [ ] 4. Checkpoint — Ensure ingest tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 5. Implement the Derive stage — rule engine and scorer
  - [ ] 5.1 Implement the declarative trigger-condition interpreter (`regplan/derive/rule_engine.py`)
    - Implement `evaluate(condition: TriggerCondition, app: Application) -> bool` as a recursive interpreter
    - Support `all`, `any`, `not` combinators and leaf comparisons for `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`
    - Raise `TriggerEvalError` when an Application attribute referenced in a condition does not exist
    - Do NOT use `eval()` or `exec()`
    - _Requirements: 4.1–4.4_

  - [ ]* 5.2 Write property test for trigger condition determinism
    - **Property 1: Trigger Condition Determinism**
    - Generate arbitrary valid `Application` and `TriggerCondition` instances with Hypothesis; assert `evaluate(cond, app) == evaluate(cond, app)`
    - **Validates: Requirements 4.5, 18.1**

  - [ ] 5.3 Implement application scorer and disposition assigner (`regplan/derive/scorer.py`)
    - Normalise `business_value`, `technical_health`, `regulatory_exposure`, and `vendor_dependence` to [0.0, 1.0] via min-max scaling across the landscape
    - Evaluate `Assumptions.decision_table` rules in order to assign `Disposition`
    - Record matching rule id and score values on each Application for auditability
    - Default to `Disposition.retain` with a warning if no rule matches
    - _Requirements: 5.1–5.4_

- [ ] 6. Implement the Derive stage — obligation matching and graph builder
  - [ ] 6.1 Implement obligation matcher (`regplan/derive/matcher.py`)
    - Iterate `(Application, RegulationRule)` pairs; call `rule_engine.evaluate` for each
    - Create a compliance `WorkItem` (id = `"{app_id}:{rule_id}"`) for each matching pair, setting deadline, effort, cost from `Assumptions.daily_rate_gbp`, and `source_requirement`
    - Create modernisation `WorkItem`s from each Application's Disposition
    - Record predecessor relationships between WorkItems
    - _Requirements: 6.1–6.4_

  - [ ] 6.2 Implement dependency graph builder (`regplan/derive/graph.py`)
    - Build a `networkx.DiGraph` from `Landscape.interfaces`
    - Detect strongly connected components with `networkx.condensation`; condense each SCC into a single schedulable node
    - Compute critical path through WorkItem DAG using longest-path algorithm
    - Compute betweenness centrality with `networkx.betweenness_centrality`
    - Verify that an acyclic graph produces no multi-Application condensed nodes
    - _Requirements: 7.1–7.5_

  - [ ] 6.3 Wire derive stage public function in `regplan/__init__.py`
    - Expose `derive(ingest_result, assumptions) -> DeriveResult` that calls scorer, rule engine, matcher, and graph builder in sequence
    - _Requirements: 1.1_

- [ ] 7. Implement the Optimize stage — scheduler and infeasibility reporting
  - [ ] 7.1 Implement CP-SAT scheduler (`regplan/optimize/scheduler.py`)
    - Create one CP-SAT `IntervalVar` per WorkItem with duration in quarters
    - Add precedence constraints (`AddEndBeforeStart`) for each predecessor relationship
    - Add hard deadline constraints: `start + duration <= deadline_quarter`
    - Add per-quarter capacity constraints (sum of capacity demand ≤ `quarterly_capacity_days`)
    - Add cumulative budget constraint per quarter
    - Define objective: weighted cost-of-delay sum + wave concentration penalty
    - Set `random_seed` and `num_search_workers=1` for determinism
    - _Requirements: 8.1–8.7_

  - [ ] 7.2 Implement infeasibility report builder (`regplan/optimize/infeasibility.py`)
    - On `INFEASIBLE` solver status, use CP-SAT assumption mechanism to find a minimal infeasible subset
    - Populate `InfeasibilityReport` with conflicting WorkItem ids, deadline dates, capacity and budget limits
    - Generate at least one remediation suggestion per conflicting constraint type
    - _Requirements: 8.8, 9.1–9.3_

  - [ ] 7.3 Wire optimize stage and expose `optimize(derive_result, assumptions) -> OptimizeResult` in public API
    - Return `OptimizeResult` containing either a `Schedule` or an `InfeasibilityReport`
    - _Requirements: 1.1, 8.8_

  - [ ]* 7.4 Write property test for schedule capacity constraint
    - **Property 2: Schedule Capacity Constraint**
    - Generate valid `DeriveResult` and `Assumptions` with Hypothesis; for any feasible `Schedule`, assert no quarter's total capacity demand exceeds `quarterly_capacity_days`
    - **Validates: Requirements 8.4, 18.2**

- [ ] 8. Checkpoint — Ensure optimizer and derive tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 9. Implement the Evaluate stage — finance engine and explainer
  - [ ] 9.1 Implement finance engine (`regplan/evaluate/finance.py`)
    - Compute quarterly cash flows: capex, opex, run-cost savings (with configurable ramp-up), migration costs
    - Compute TCO as sum of all cost cash flows over the planning horizon
    - Compute NPV using `Assumptions.discount_rate`
    - Compute payback period as first quarter where cumulative net cash flow ≥ 0
    - Compute cost-of-delay per WorkItem as the financial impact of deferring by one quarter
    - Raise `MissingAssumptionError` for any missing Assumptions value used in computation
    - Record `assumption_ids` list on `FinancialResult` for traceability
    - _Requirements: 11.1–11.6_

  - [ ]* 9.2 Write property test for TCO equals sum of cash flows
    - **Property 3: TCO Equals Sum of Cash Flows**
    - Generate arbitrary valid `Schedule` and `Assumptions`; assert `financial_result.tco == sum(cf.capex + cf.opex + cf.migration_cost for cf in financial_result.cash_flows)`
    - **Validates: Requirements 11.2, 18.3**

  - [ ]* 9.3 Write property test for NPV discounting monotonicity
    - **Property 4: NPV Discounting Monotonicity**
    - Generate valid `Assumptions` with positive `discount_rate`; assert `financial_result.npv <= sum(cf.net for cf in financial_result.cash_flows)`
    - **Validates: Requirements 11.3, 18.4**

  - [ ] 9.4 Implement schedule explainer (`regplan/evaluate/explainer.py`)
    - Given a WorkItem id, report scheduled quarter, total slack, and critical-path membership
    - Identify the binding constraint fixing earliest possible start (predecessor, deadline pull-forward, capacity, or budget)
    - Report the hypothetical schedule change if the WorkItem were moved one quarter earlier, including cost-of-delay effect and any constraint violations
    - _Requirements: 10.1–10.3_

  - [ ] 9.5 Wire evaluate stage and expose `evaluate(schedule, derive_result, assumptions) -> FinancialResult` in public API
    - _Requirements: 1.1_

- [ ] 10. Implement the Simulate stage
  - [ ] 10.1 Implement Monte Carlo simulation engine (`regplan/simulate/monte_carlo.py`)
    - Accept `n_runs` (1–100 000) and `seed`; initialise `numpy.random.default_rng(seed)`
    - Sample cost overrun, duration slip, and benefit-realization factors from declared distributions (triangular, lognormal)
    - Apply a shared common factor for correlated overruns across all WorkItems per run
    - Propagate sampled duration slips through the existing Schedule without re-running CP-SAT
    - Compute P50, P80, P95 percentiles for total cost and NPV across all runs
    - Compute per-rule deadline-miss probability (fraction of runs where a dependent WorkItem completes after the deadline)
    - Compute Tornado ranking via one-at-a-time variance attribution on NPV
    - _Requirements: 12.1–12.7_

  - [ ] 10.2 Wire simulate stage and expose `simulate(schedule, financial_result, assumptions, n_runs, seed) -> SimulationResult` in public API
    - _Requirements: 1.1_

- [ ] 11. Implement the Scenario Engine
  - [ ] 11.1 Implement scenario engine and built-in scenarios (`regplan/scenario/engine.py`)
    - Implement `apply_scenario(base_inputs, scenario_config) -> TransformedInputs` that applies capacity, budget, scope, and deadline-extension transformations without duplicating optimizer logic
    - Include three built-in `ScenarioConfig` definitions: `big_bang`, `progressive`, `minimum_compliance`
    - Implement `compare_scenarios(result_a, result_b) -> ComparisonReport` producing side-by-side diff of TCO, NPV, payback period, deadline-miss probability, and wave plan
    - Verify all scenario configs run through the same optimizer code path
    - _Requirements: 13.1–13.4_

- [ ] 12. Implement the Report stage and RunManifest builder
  - [ ] 12.1 Implement pipeline result serialiser (`regplan/report/serializer.py`)
    - Serialise `PipelineResult` to `result.json` in the run output directory using `model_dump_json()`
    - Implement deserialise function for re-rendering from stored JSON
    - _Requirements: 14.1_

  - [ ] 12.2 Implement Jinja2 memo renderer (`regplan/report/renderer.py`)
    - Write `regplan/report/templates/memo.md.j2` covering schedule summary, financial metrics, simulation percentiles, and deadline-miss risks
    - Implement `render_memo(result_json_path, out_path) -> None` driven entirely by the JSON file
    - Verify that re-running `report` on an existing run directory reproduces the same output without re-running any pipeline stage
    - _Requirements: 14.2, 14.4_

  - [ ] 12.3 Implement chart generators (`regplan/report/charts.py`)
    - Gantt chart: horizontal bar per WorkItem, x-axis = quarters
    - NPV distribution histogram from simulation run NPVs
    - Tornado chart: horizontal bars sorted by variance contribution
    - Deadline-miss probability bar chart
    - Save all figures as PNG in the run directory
    - _Requirements: 14.3_

  - [ ] 12.4 Implement RunManifest builder (`regplan/manifest/builder.py`)
    - Record SHA-256 of every input file, installed package versions via `importlib.metadata`, git commit hash, and `dirty` flag from `git status --porcelain`
    - Write `RunManifest` to the run output directory alongside `result.json`
    - _Requirements: 15.1–15.4_

  - [ ] 12.5 Wire report stage and expose `report(pipeline_result, out_dir) -> None` in public API
    - _Requirements: 1.1_

- [ ] 13. Checkpoint — Ensure evaluate, simulate, scenario, and report tests pass
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 14. Implement the CLI
  - [ ] 14.1 Implement all CLI commands (`cli/main.py`)
    - `validate`: load landscape, run schema and semantic validation, report errors or confirm valid
    - `plan`: load landscape + packs, optionally apply scenario, run full pipeline, write run directory with JSON and RunManifest
    - `simulate`: accept `--runs` and `--seed`, append simulation results to existing run directory
    - `compare`: accept two landscape files or scenario names, write comparison report
    - `explain`: accept landscape and WorkItem/Application id, write explanation to stdout
    - `report`: accept run directory and `--out` path, render memo and charts
    - On any error or infeasibility, print human-readable message to stderr and exit with non-zero code
    - Verify CLI contains zero business logic (delegates entirely to `regplan` package)
    - _Requirements: 1.2, 9.4, 16.1–16.7_

- [ ] 15. Implement golden-file regression tests
  - [ ] 15.1 Generate and store golden outputs for example landscapes
    - Run the full pipeline on `legacy_heavy.yaml` and `cloud_native.yaml` and store JSON output as `tests/golden/legacy_heavy_expected.json` and `cloud_native_expected.json`
    - Write pytest tests that re-run the pipeline and compare byte-for-byte against the stored JSON
    - _Requirements: 15.3, 18.6_

- [ ] 16. Final checkpoint — Full test suite and quality gates
  - Ensure all tests pass (unit, property, golden-file regression), ask the user if questions arise.
  - Verify `ruff` passes with no errors
  - Verify `mypy --strict` passes with no type errors
  - Verify line coverage ≥ 80%

## Notes

- Tasks marked with `*` are optional and can be skipped for a faster MVP
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation throughout implementation
- Property tests (Properties 1–5) validate universal algorithmic invariants using Hypothesis
- Unit tests validate specific examples and edge cases
- Golden-file tests lock in known-good outputs for the two example landscapes
- The CLI and Streamlit app must never contain business logic; all computation is in `regplan/`
