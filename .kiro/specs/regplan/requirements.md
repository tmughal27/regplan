# Requirements Document

## Introduction

`regplan` is a regulatory compliance planning library and CLI tool that helps organisations analyse their application landscape, match applicable regulations, schedule compliance and modernisation work, evaluate financial outcomes, and simulate uncertainty. All business logic lives in an importable Python package; the CLI and a Streamlit UI are thin shells with no logic of their own. Every output number is traceable to the input identifiers and assumption identifiers that produced it. When a plan is infeasible the tool explains why rather than silently producing a plausible-looking but wrong result.

The six pipeline stages are: Ingest → Derive → Optimize → Evaluate → Simulate → Report. Each stage consumes the typed output of the previous stage and can be executed and tested independently.

---

## Glossary

- **Application**: A software system described in the landscape file with attributes such as owner, business value, technical health, and data-processing characteristics.
- **Interface**: A directed dependency between two Applications, described in the landscape file.
- **Vendor**: A third-party supplier associated with one or more Applications.
- **RegulationRule**: A single compliance obligation drawn from a regulation pack, with a trigger condition, deadline, effort estimate, and source URL.
- **Assumptions**: A YAML document declaring financial and operational assumptions (discount rate, cost distributions, capacity, etc.) used by the Evaluate and Simulate stages.
- **ScenarioConfig**: A named configuration transformation (e.g. big-bang, progressive, minimum-compliance) applied on top of the base problem before optimisation.
- **WorkItem**: The common schedulable unit representing either a modernisation task or a compliance obligation, carrying duration, cost, capacity demand, benefit profile, predecessor list, and an optional hard deadline.
- **Schedule**: The ordered assignment of WorkItems to time periods (quarters) produced by the Optimizer.
- **InfeasibilityReport**: An explanation produced when no valid Schedule exists, identifying a minimal set of conflicting constraints.
- **Landscape**: The YAML input file describing the full set of Applications, Interfaces, and Vendors in scope.
- **RegulationPack**: A YAML file containing a collection of RegulationRules for a specific regulation (e.g. GDPR, AI Act, NIS2, DORA).
- **RunManifest**: A provenance record that captures input file hashes, package versions, random seeds, and git commit at the time a plan is produced.
- **CP-SAT**: The constraint-programming SAT solver from Google OR-Tools used by the Scheduler.
- **TCO**: Total Cost of Ownership over the planning horizon.
- **NPV**: Net Present Value, calculated using the discount rate from Assumptions.
- **Disposition**: A recommended modernisation action for an Application (retire, rehost, replatform, refactor, replace, or retain).
- **Trigger Condition**: A declarative boolean expression over Application attributes used by the rule engine to determine which RegulationRules apply.
- **Streamlit App**: The optional browser-based UI shell that delegates entirely to the library.
- **CLI**: The command-line interface implemented with Typer that delegates entirely to the library.
- **Tornado Ranking**: A sensitivity analysis that ranks input assumptions by their influence on NPV.
- **Wave**: A cohort of WorkItems scheduled in the same quarter or planning period.

---

## Requirements

### Requirement 1: Library-First Architecture

**User Story:** As a developer, I want all business logic to reside in an importable Python package, so that I can integrate regplan into my own tools and pipelines without depending on the CLI or UI.

#### Acceptance Criteria

1. THE `regplan` Package SHALL expose public functions for each of the six pipeline stages (Ingest, Derive, Optimize, Evaluate, Simulate, Report) that can be called independently without invoking the CLI or Streamlit App.
2. THE CLI SHALL contain zero business logic and SHALL delegate all computation to the `regplan` Package.
3. THE Streamlit App SHALL contain zero business logic and SHALL delegate all computation to the `regplan` Package.
4. WHEN a caller imports the `regplan` Package, THE Package SHALL not produce side effects such as writing files, printing to stdout, or accessing the network.

---

### Requirement 2: YAML Input Loading and Schema Validation

**User Story:** As a compliance analyst, I want the tool to load and validate YAML input files, so that I receive clear errors for malformed or incomplete inputs before any computation begins.

#### Acceptance Criteria

1. WHEN a Landscape YAML file is provided, THE Ingestor SHALL parse it into validated Pydantic model instances for Application, Interface, Vendor, and ScenarioConfig.
2. WHEN a RegulationPack YAML file is provided, THE Ingestor SHALL parse it into validated Pydantic model instances for RegulationRule.
3. WHEN an Assumptions YAML file is provided, THE Ingestor SHALL parse it into a validated Pydantic Assumptions model instance.
4. IF a required field is missing or a field value falls outside its declared type or range, THEN THE Ingestor SHALL raise a structured validation error that identifies the file, the field path, and the violation.
5. THE `regplan` Package SHALL include synthetic example Landscape files (`legacy_heavy.yaml`, `cloud_native.yaml`) and RegulationPack files (`ai_act.yaml`, `gdpr.yaml`, `nis2.yaml`, `dora.yaml`) that pass schema validation.

---

### Requirement 3: Semantic Validation

**User Story:** As a compliance analyst, I want the tool to check logical consistency of the inputs, so that downstream computation is not silently corrupted by references to non-existent entities or implausible dates.

#### Acceptance Criteria

1. WHEN the Ingestor processes a Landscape, THE Ingestor SHALL verify that every Interface references source and target Application ids that exist in the same Landscape.
2. WHEN the Ingestor processes a Landscape, THE Ingestor SHALL verify that all Application ids and Interface ids are unique within that Landscape.
3. WHEN the Ingestor processes a RegulationPack, THE Ingestor SHALL verify that every RegulationRule includes a non-empty `source_url` and a `last_verified` date.
4. WHEN the Ingestor processes a RegulationPack, THE Ingestor SHALL verify that every RegulationRule deadline is a calendar date that is not in the past relative to the planning start date declared in Assumptions.
5. IF any semantic validation check fails, THEN THE Ingestor SHALL raise a structured error that identifies the entity id, the violated rule, and a suggested correction.

---

### Requirement 4: Declarative Trigger-Condition Interpreter

**User Story:** As a regulation author, I want to express rule applicability as a declarative condition over Application attributes, so that I can add new rules without writing Python code.

#### Acceptance Criteria

1. THE Rule Engine SHALL evaluate Trigger Conditions expressed as nested `all`, `any`, and `not` boolean operators over Application attribute comparisons.
2. THE Rule Engine SHALL support the attribute comparison operators `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, and `in` applied to Application attributes of type boolean, integer, float, and string.
3. THE Rule Engine SHALL evaluate Trigger Conditions using only the declared interpreter and SHALL NOT use Python's `eval()` or `exec()` functions.
4. WHEN a Trigger Condition references an Application attribute that does not exist in the Application model, THE Rule Engine SHALL raise a descriptive error identifying the unknown attribute name and the RegulationRule id.
5. FOR ALL valid Applications and valid Trigger Conditions, evaluating a Trigger Condition twice on the same Application SHALL produce the same result (deterministic evaluation).

---

### Requirement 5: Application Scoring and Disposition

**User Story:** As an enterprise architect, I want each application to receive a scored Disposition recommendation, so that I can explain and audit every modernisation decision.

#### Acceptance Criteria

1. THE Scorer SHALL compute normalised scores for business value, technical health, regulatory exposure, and vendor dependence for each Application, each in the range [0.0, 1.0].
2. THE Scorer SHALL assign a Disposition (retire, rehost, replatform, refactor, replace, or retain) to each Application by evaluating the normalised scores against a configurable decision table supplied in Assumptions.
3. WHEN a Disposition is assigned, THE Scorer SHALL record the score values and the decision-table rule that produced the Disposition, so that the result is auditable.
4. IF an Application's scores do not match any decision-table rule, THEN THE Scorer SHALL assign a default Disposition of `retain` and SHALL record a warning in the output.

---

### Requirement 6: Obligation Matching and Work Item Generation

**User Story:** As a compliance analyst, I want the tool to automatically derive compliance WorkItems from applicable RegulationRules, so that I don't have to manually cross-reference applications against regulations.

#### Acceptance Criteria

1. WHEN the Rule Engine is run against a Landscape and one or more RegulationPacks, THE Obligation Matcher SHALL produce a WorkItem for each (Application, RegulationRule) pair where the Trigger Condition evaluates to true.
2. THE WorkItem SHALL record the Application id, the RegulationRule id, the deadline, the estimated effort in person-days, and the cost estimate derived from Assumptions.
3. THE Obligation Matcher SHALL also produce WorkItems for modernisation actions derived from each Application's Disposition.
4. WHEN two WorkItems have a dependency (one must complete before the other can start), THE Obligation Matcher SHALL record a predecessor relationship between them.

---

### Requirement 7: Dependency Graph Construction

**User Story:** As an enterprise architect, I want the tool to model application interfaces as a directed dependency graph, so that scheduling respects integration dependencies.

#### Acceptance Criteria

1. THE Graph Builder SHALL construct a NetworkX directed graph where each node represents an Application and each edge represents an Interface.
2. THE Graph Builder SHALL detect strongly connected components (cyclic dependencies) within the graph and SHALL condense each strongly connected component into a single schedulable unit.
3. THE Graph Builder SHALL compute the critical path through the WorkItem dependency graph.
4. THE Graph Builder SHALL compute betweenness centrality for each Application node.
5. WHEN the dependency graph is acyclic, THE Graph Builder's condensation SHALL produce no multi-Application nodes.

---

### Requirement 8: Constraint-Programming Scheduler

**User Story:** As a planning manager, I want the tool to produce an optimised schedule that respects all hard constraints, so that the resulting plan is feasible and directly actionable.

#### Acceptance Criteria

1. THE Scheduler SHALL use CP-SAT interval variables to represent the start and end of each WorkItem in discrete quarter-length time slots.
2. THE Scheduler SHALL enforce precedence constraints so that each WorkItem starts only after all of its predecessors have completed.
3. THE Scheduler SHALL enforce hard deadline constraints so that WorkItems derived from RegulationRules complete no later than the RegulationRule's deadline quarter.
4. WHILE a per-quarter delivery capacity is declared in Assumptions, THE Scheduler SHALL enforce that the total capacity demand of WorkItems assigned to any single quarter does not exceed the declared capacity.
5. WHILE a cumulative budget limit is declared in Assumptions, THE Scheduler SHALL enforce that the cumulative cost of scheduled WorkItems does not exceed the budget in any quarter.
6. THE Scheduler SHALL minimise an objective that combines the weighted sum of cost-of-delay for all WorkItems and a risk penalty for wave concentration and peak quarterly load.
7. THE Scheduler SHALL use a fixed random seed and a single solver worker by default to ensure deterministic output.
8. IF no feasible Schedule exists, THEN THE Scheduler SHALL return an InfeasibilityReport instead of a Schedule.

---

### Requirement 9: Infeasibility Explanation

**User Story:** As a planning manager, I want the tool to explain why a plan is infeasible, so that I can adjust inputs rather than receiving a silent failure or an incorrect schedule.

#### Acceptance Criteria

1. WHEN the Scheduler determines that no feasible Schedule exists, THE Scheduler SHALL use CP-SAT's assumption mechanism to identify a minimal infeasible subset of constraints.
2. THE InfeasibilityReport SHALL list the conflicting WorkItem ids, deadline dates, capacity limits, and budget limits that together make the problem infeasible.
3. THE InfeasibilityReport SHALL include at least one suggested remediation action per conflicting constraint (e.g. extend the deadline, increase capacity, reduce scope).
4. WHEN the Scheduler returns an InfeasibilityReport, THE CLI SHALL display the report and SHALL exit with a non-zero return code.

---

### Requirement 10: Schedule Explanation (`explain` command)

**User Story:** As a planning manager, I want to query why a specific WorkItem is scheduled where it is, so that I can understand the binding constraints and evaluate trade-offs.

#### Acceptance Criteria

1. WHEN the `explain` command is invoked with a WorkItem id, THE Explainer SHALL report the quarter in which the WorkItem is scheduled, its total slack, and whether it lies on the critical path.
2. THE Explainer SHALL identify the binding constraint that fixes the WorkItem's earliest possible start (predecessor completion, deadline pull-forward, capacity, or budget).
3. THE Explainer SHALL report the schedule change that would result if the WorkItem were moved one quarter earlier, including the effect on cost-of-delay and any constraint violations that would occur.

---

### Requirement 11: Financial Evaluation

**User Story:** As a CFO or programme sponsor, I want the tool to compute TCO, NPV, and payback period for the schedule, so that I can justify the investment with auditable financial figures.

#### Acceptance Criteria

1. THE Finance Engine SHALL convert a Schedule into quarterly cash flows that separately itemise capital expenditure, operational expenditure, run-cost savings with a configurable ramp-up period, and one-off migration costs.
2. THE Finance Engine SHALL compute TCO as the sum of all cost cash flows over the planning horizon.
3. THE Finance Engine SHALL compute NPV using the discount rate declared in Assumptions.
4. THE Finance Engine SHALL compute the payback period as the first quarter in which the cumulative net cash flow becomes non-negative.
5. THE Finance Engine SHALL compute the cost of delay for each WorkItem as the financial impact of deferring it by one quarter.
6. WHEN any Assumptions value used in the financial computation is missing, THE Finance Engine SHALL raise an error that identifies the missing assumption by name.

---

### Requirement 12: Monte Carlo Simulation

**User Story:** As a risk manager, I want probabilistic cost and schedule outcomes, so that I can communicate P50/P80/P95 ranges rather than single-point estimates.

#### Acceptance Criteria

1. THE Simulator SHALL execute at least 1 and up to 100,000 simulation runs using a seeded NumPy random generator, with the seed declared in the `simulate` command or in Assumptions.
2. THE Simulator SHALL sample cost overrun, duration slip, and benefit-realization factors from distributions declared in Assumptions, supporting triangular and lognormal distribution types.
3. THE Simulator SHALL apply a shared common factor to correlated overrun samples across all WorkItems in a single run, so that systematic overruns are modelled.
4. THE Simulator SHALL propagate sampled duration slips forward through the existing Schedule without re-solving CP-SAT, producing a simulated completion date for each WorkItem.
5. THE Simulator SHALL compute P50, P80, and P95 percentiles for total cost and NPV across all runs.
6. THE Simulator SHALL compute, for each RegulationRule deadline, the fraction of simulation runs in which at least one dependent WorkItem completes after that deadline.
7. THE Simulator SHALL produce a Tornado Ranking that lists input Assumptions in descending order of their influence on NPV variance.

---

### Requirement 13: Scenario Management

**User Story:** As a planning manager, I want to define and compare named scenarios (e.g. big-bang, progressive, minimum-compliance), so that I can present decision-makers with a range of options from one consistent model.

#### Acceptance Criteria

1. THE Scenario Engine SHALL apply a ScenarioConfig as a transformation on the base problem inputs before the Optimize stage, without duplicating optimizer or evaluation logic.
2. THE `regplan` Package SHALL include at least three built-in ScenarioConfig definitions: `big_bang`, `progressive`, and `minimum_compliance`.
3. WHEN the `compare` command is invoked with two Landscape files or two scenario names, THE Scenario Comparator SHALL produce a side-by-side diff of TCO, NPV, payback period, deadline-miss probability, and wave plan.
4. FOR ALL ScenarioConfigs applied to the same base inputs, the Scenario Engine SHALL produce a Schedule or InfeasibilityReport through the same Optimizer code path.

---

### Requirement 14: Reporting and Output

**User Story:** As a compliance analyst, I want the tool to produce structured JSON output and rendered reports, so that I can archive results, share them with stakeholders, and load them into other tools.

#### Acceptance Criteria

1. THE Reporter SHALL serialise the complete pipeline result (Schedule or InfeasibilityReport, financial metrics, simulation percentiles) to a single JSON file that is the source of truth for all downstream rendering.
2. THE Reporter SHALL render a Markdown or HTML memo from a Jinja2 template, driven entirely by the JSON output.
3. THE Reporter SHALL produce a Gantt chart of the wave plan, an NPV distribution histogram, a tornado chart of sensitivity rankings, and a bar chart of deadline-miss probabilities.
4. WHEN the `report` command is run on an existing run directory, THE Reporter SHALL reproduce the same rendered output from the JSON file without re-running any pipeline stage.

---

### Requirement 15: Run Manifest and Reproducibility

**User Story:** As an auditor, I want every plan to include a provenance record, so that I can reproduce the exact result from the same inputs.

#### Acceptance Criteria

1. THE Manifest Builder SHALL record the SHA-256 hash of every input file, the version of every installed package, the random seeds used, and the git commit hash (if available) at the time the plan is produced.
2. THE Manifest Builder SHALL write the RunManifest to the run output directory alongside the JSON result.
3. WHEN the same input files, seeds, and package versions are used, THE Scheduler and Simulator SHALL produce byte-for-byte identical JSON output.
4. IF the git working tree is dirty at plan time, THEN THE Manifest Builder SHALL record a `dirty` flag in the RunManifest.

---

### Requirement 16: CLI Commands

**User Story:** As a developer or analyst, I want a command-line interface, so that I can run regplan from scripts, CI pipelines, and the terminal without writing Python.

#### Acceptance Criteria

1. THE CLI SHALL provide a `validate` command that loads a Landscape YAML, runs schema and semantic validation, and reports all errors or confirms that the file is valid.
2. THE CLI SHALL provide a `plan` command that accepts a Landscape YAML, an optional `--scenario` name, and one or more `--packs` regulation pack names, and writes a run directory containing the JSON result and RunManifest.
3. THE CLI SHALL provide a `simulate` command that accepts a Landscape YAML, a `--runs` count, and a `--seed` value, and appends simulation results to the run directory.
4. THE CLI SHALL provide a `compare` command that accepts two Landscape YAML files or two scenario names and writes a comparison report.
5. THE CLI SHALL provide an `explain` command that accepts a Landscape YAML and a WorkItem or Application id and writes an explanation to stdout.
6. THE CLI SHALL provide a `report` command that accepts a run directory and an `--out` path and renders the memo and charts.
7. WHEN any CLI command encounters a validation error or infeasibility, THE CLI SHALL print a human-readable error message to stderr and SHALL exit with a non-zero return code.

---

### Requirement 17: Continuous Integration and Quality Gates

**User Story:** As a maintainer, I want automated quality gates on every commit, so that the codebase stays correct, typed, and well-covered as it evolves.

#### Acceptance Criteria

1. THE CI Pipeline SHALL run `ruff` linting and fail the build if any linting errors are detected.
2. THE CI Pipeline SHALL run `mypy --strict` type checking and fail the build if any type errors are detected.
3. THE CI Pipeline SHALL run the full test suite with `pytest` and fail the build if any tests fail.
4. THE CI Pipeline SHALL measure test coverage and fail the build if line coverage falls below 80 percent.
5. THE CI Pipeline SHALL run on every push and pull request to the main branch.
6. THE `regplan` Package SHALL include unit tests, Hypothesis property-based tests, and golden-file regression tests.

---

### Requirement 18: Property-Based and Regression Testing

**User Story:** As a developer, I want property-based tests and golden-file regression tests, so that algorithmic invariants and known-good outputs are continuously verified.

#### Acceptance Criteria

1. THE Test Suite SHALL include a Hypothesis property test that verifies: for any valid Application and valid Trigger Condition, evaluating the condition twice on the same Application produces the same result.
2. THE Test Suite SHALL include a Hypothesis property test that verifies: for any valid Landscape and RegulationPacks where a feasible Schedule exists, the Schedule's total capacity demand in any quarter does not exceed the declared per-quarter capacity.
3. THE Test Suite SHALL include a Hypothesis property test that verifies: for any valid Schedule, the Finance Engine's TCO equals the sum of all quarterly cost cash flows.
4. THE Test Suite SHALL include a Hypothesis property test that verifies: for any valid Assumptions with a positive discount rate, the NPV computed by the Finance Engine is less than or equal to the undiscounted sum of net cash flows.
5. THE Test Suite SHALL include a round-trip property test that verifies: serialising a pipeline result to JSON and deserialising it produces an object equal to the original.
6. THE Test Suite SHALL include golden-file regression tests that verify the JSON output for the `legacy_heavy.yaml` and `cloud_native.yaml` example Landscapes against stored expected outputs.

---

### Requirement 19: Packaging and Containerisation

**User Story:** As an operator, I want a Docker image and a properly declared Python package, so that I can run regplan in any environment without manual dependency installation.

#### Acceptance Criteria

1. THE `regplan` Package SHALL declare all runtime dependencies with pinned versions in `pyproject.toml`.
2. THE `regplan` Package SHALL be installable via `pip install .` from the repository root without errors.
3. THE Dockerfile SHALL produce an image in which `regplan --help` executes successfully.
4. THE Dockerfile SHALL not run as root by default.
5. WHEN built from the same source commit, THE Dockerfile SHALL produce a deterministic image layer hash for the dependency-installation layer.
