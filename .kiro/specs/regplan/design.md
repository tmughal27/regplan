# Design Document: regplan

## Overview

`regplan` is a Python library and CLI for regulatory compliance planning. It implements a six-stage pipeline (Ingest → Derive → Optimize → Evaluate → Simulate → Report) where each stage produces typed output consumed by the next. All business logic lives in the `regplan` package; the CLI (Typer) and Streamlit UI are zero-logic shells. Every numeric output is traceable to the input identifiers and assumption identifiers that produced it.

---

## Architecture

### Package Layout

```
regplan/
├── __init__.py              # Public API re-exports
├── models/
│   ├── landscape.py         # Application, Interface, Vendor, ScenarioConfig
│   ├── regulation.py        # RegulationRule, RegulationPack
│   ├── assumptions.py       # Assumptions, DistributionSpec
│   ├── work.py              # WorkItem, Schedule, Wave
│   ├── finance.py           # CashFlow, FinancialResult
│   ├── simulation.py        # SimulationResult, TornadoEntry
│   ├── manifest.py          # RunManifest
│   └── report.py            # PipelineResult, InfeasibilityReport
├── ingest/
│   ├── loader.py            # YAML loading and Pydantic parsing
│   └── validator.py         # Semantic validation rules
├── derive/
│   ├── rule_engine.py       # Declarative trigger-condition interpreter
│   ├── scorer.py            # Application scoring and disposition
│   ├── matcher.py           # Obligation matching → WorkItems
│   └── graph.py             # NetworkX dependency graph builder
├── optimize/
│   ├── scheduler.py         # CP-SAT scheduler
│   └── infeasibility.py     # Infeasibility report builder
├── evaluate/
│   ├── finance.py           # TCO, NPV, payback, cost-of-delay
│   └── explainer.py         # explain-command logic
├── simulate/
│   └── monte_carlo.py       # Monte Carlo simulation engine
├── scenario/
│   └── engine.py            # Scenario transformation and comparison
├── report/
│   ├── serializer.py        # Pipeline result → JSON
│   ├── renderer.py          # Jinja2 memo rendering
│   └── charts.py            # Matplotlib/Plotly chart generation
├── manifest/
│   └── builder.py           # RunManifest construction
├── examples/
│   ├── landscapes/
│   │   ├── legacy_heavy.yaml
│   │   └── cloud_native.yaml
│   └── packs/
│       ├── ai_act.yaml
│       ├── gdpr.yaml
│       ├── nis2.yaml
│       └── dora.yaml
cli/
├── __init__.py
└── main.py                  # Typer CLI — delegates to regplan package
streamlit_app/
└── app.py                   # Streamlit UI — delegates to regplan package
tests/
├── unit/
├── property/
└── golden/
    ├── legacy_heavy_expected.json
    └── cloud_native_expected.json
pyproject.toml
Dockerfile
.github/workflows/ci.yml
```

---

## Data Models

### Landscape Models (`regplan/models/landscape.py`)

```python
class Application(BaseModel):
    id: str
    name: str
    owner: str
    business_value: float          # 0.0–1.0 raw score
    technical_health: float        # 0.0–1.0 raw score
    data_residency: bool
    data_classification: str       # e.g. "PII", "financial", "public"
    ai_enabled: bool
    vendor_id: Optional[str]
    attributes: dict[str, Any]     # open-ended for trigger conditions
    disposition: Optional[Disposition] = None

class Interface(BaseModel):
    id: str
    source_id: str
    target_id: str
    protocol: str
    data_classification: str

class Vendor(BaseModel):
    id: str
    name: str
    tier: int                      # 1=critical, 2=important, 3=standard

class ScenarioConfig(BaseModel):
    name: str
    capacity_multiplier: float = 1.0
    budget_multiplier: float = 1.0
    scope_filter: Optional[list[str]] = None  # Application id list
    deadline_extension_days: int = 0

class Landscape(BaseModel):
    applications: list[Application]
    interfaces: list[Interface]
    vendors: list[Vendor]
    scenarios: list[ScenarioConfig] = []
```

### Regulation Models (`regplan/models/regulation.py`)

```python
class TriggerCondition(BaseModel):
    # Recursive union: leaf comparison or logical combinator
    all: Optional[list["TriggerCondition"]] = None
    any: Optional[list["TriggerCondition"]] = None
    not_: Optional["TriggerCondition"] = Field(None, alias="not")
    attribute: Optional[str] = None
    operator: Optional[str] = None   # eq, neq, gt, gte, lt, lte, in
    value: Optional[Any] = None

class RegulationRule(BaseModel):
    id: str
    regulation: str
    title: str
    trigger: TriggerCondition
    deadline: date
    effort_person_days: float
    source_url: HttpUrl
    last_verified: date

class RegulationPack(BaseModel):
    regulation: str
    version: str
    rules: list[RegulationRule]
```

### Assumptions Model (`regplan/models/assumptions.py`)

```python
class DistributionSpec(BaseModel):
    type: Literal["triangular", "lognormal"]
    low: Optional[float] = None
    mode: Optional[float] = None
    high: Optional[float] = None
    mu: Optional[float] = None
    sigma: Optional[float] = None

class Assumptions(BaseModel):
    planning_start: date
    horizon_quarters: int
    discount_rate: float
    daily_rate_gbp: float
    quarterly_capacity_days: float
    cumulative_budget_gbp: float
    cost_overrun_dist: DistributionSpec
    duration_slip_dist: DistributionSpec
    benefit_realization_dist: DistributionSpec
    overrun_correlation: float = 0.3
    ramp_up_quarters: int = 2
    decision_table: list[DispositionRule]
    simulation_seed: int = 42
```

### Work Models (`regplan/models/work.py`)

```python
class Disposition(str, Enum):
    retire = "retire"
    rehost = "rehost"
    replatform = "replatform"
    refactor = "refactor"
    replace = "replace"
    retain = "retain"

class WorkItem(BaseModel):
    id: str
    application_id: str
    rule_id: Optional[str]          # None for modernisation items
    disposition: Optional[Disposition]
    duration_quarters: int
    cost_gbp: float
    capacity_demand_days: float
    benefit_profile: list[float]    # quarterly savings after completion
    predecessors: list[str]         # WorkItem ids
    deadline: Optional[date]
    source_requirement: str         # traceability: "req-id / assumption-id"

class Wave(BaseModel):
    quarter: int
    work_item_ids: list[str]

class Schedule(BaseModel):
    waves: list[Wave]
    work_item_starts: dict[str, int]   # id → quarter index
    objective_value: float
    solver_wall_time_s: float
    seed: int
```

### Financial Models (`regplan/models/finance.py`)

```python
class CashFlow(BaseModel):
    quarter: int
    capex: float
    opex: float
    run_cost_savings: float
    migration_cost: float
    net: float

class FinancialResult(BaseModel):
    cash_flows: list[CashFlow]
    tco: float
    npv: float
    payback_quarter: Optional[int]
    cost_of_delay: dict[str, float]   # WorkItem id → £/quarter
    assumption_ids: list[str]          # traceability
```

### Simulation Models (`regplan/models/simulation.py`)

```python
class SimulationRun(BaseModel):
    run_index: int
    total_cost: float
    npv: float
    completion_dates: dict[str, date]   # WorkItem id → simulated completion

class TornadoEntry(BaseModel):
    assumption_name: str
    npv_variance_contribution: float

class SimulationResult(BaseModel):
    runs: list[SimulationRun]
    p50_cost: float
    p80_cost: float
    p95_cost: float
    p50_npv: float
    p80_npv: float
    p95_npv: float
    deadline_miss_probabilities: dict[str, float]  # rule_id → probability
    tornado: list[TornadoEntry]
    seed: int
```

### Manifest Model (`regplan/models/manifest.py`)

```python
class RunManifest(BaseModel):
    created_at: datetime
    regplan_version: str
    python_version: str
    git_commit: Optional[str]
    git_dirty: bool
    input_file_hashes: dict[str, str]   # path → SHA-256 hex
    installed_packages: dict[str, str]  # name → version
    scheduler_seed: int
    simulation_seed: int
```

### Pipeline Result (`regplan/models/report.py`)

```python
class InfeasibilityReport(BaseModel):
    conflicting_work_item_ids: list[str]
    conflicting_deadline_dates: list[date]
    conflicting_capacity_limits: list[tuple[int, float]]
    conflicting_budget_limits: list[tuple[int, float]]
    remediations: list[str]

class PipelineResult(BaseModel):
    landscape_id: str
    scenario_name: str
    schedule: Optional[Schedule]
    infeasibility: Optional[InfeasibilityReport]
    financial: Optional[FinancialResult]
    simulation: Optional[SimulationResult]
    manifest: RunManifest
```

---

## Stage Designs

### Stage 1: Ingest (`regplan/ingest/`)

**Public function:** `ingest(landscape_path, packs_paths, assumptions_path) -> IngestResult`

`loader.py` reads each YAML file with PyYAML, then constructs Pydantic models. Pydantic raises `ValidationError` on schema failures; the loader wraps these into a structured `IngestError` that includes the file path and field path.

`validator.py` performs semantic checks after schema parsing:
- Cross-references: every `Interface.source_id` and `Interface.target_id` must appear in `Landscape.applications`.
- Uniqueness: duplicate Application/Interface ids within a Landscape raise an error.
- RegulationRule: `source_url` non-empty, `last_verified` present, `deadline >= planning_start`.
- Error format: `SemanticError(entity_id, rule_name, suggestion)`.

### Stage 2: Derive (`regplan/derive/`)

**Public function:** `derive(ingest_result, assumptions) -> DeriveResult`

**Rule Engine (`rule_engine.py`)**

Evaluates `TriggerCondition` trees via a recursive interpreter (no `eval`/`exec`). The interpreter dispatches on the `TriggerCondition` union fields:

```
evaluate(condition, app) -> bool:
  if condition.all:  return all(evaluate(c, app) for c in condition.all)
  if condition.any:  return any(evaluate(c, app) for c in condition.any)
  if condition.not_: return not evaluate(condition.not_, app)
  # leaf: attribute comparison
  value = get_attribute(app, condition.attribute)  # raises if missing
  return apply_operator(condition.operator, value, condition.value)
```

Operator dispatch covers `eq`, `neq`, `gt`, `gte`, `lt`, `lte`, `in`.

**Scorer (`scorer.py`)**

Normalises raw scores to [0.0, 1.0] using min-max scaling across the landscape. Evaluates `Assumptions.decision_table` rules (ordered list of conditions on normalised scores) to assign `Disposition`. Records the matching rule id and score values on each Application. Default: `retain` with a warning if no rule matches.

**Obligation Matcher (`matcher.py`)**

Iterates over `(Application, RegulationRule)` pairs. For each pair where `evaluate(rule.trigger, app) == True`, creates a `WorkItem` with:
- `id = f"{app.id}:{rule.id}"`
- `cost_gbp = rule.effort_person_days * assumptions.daily_rate_gbp`
- `deadline = rule.deadline`
- Predecessor relationships derived from the condensed dependency graph.

Also creates modernisation `WorkItem`s from each Application's Disposition.

**Graph Builder (`graph.py`)**

Uses `networkx.DiGraph` to build the application interface graph. Calls `networkx.condensation()` to handle SCCs. Computes critical path via longest-path algorithm on the DAG of WorkItems. Computes betweenness centrality with `networkx.betweenness_centrality()`.

### Stage 3: Optimize (`regplan/optimize/`)

**Public function:** `optimize(derive_result, assumptions) -> OptimizeResult`

**Scheduler (`scheduler.py`)**

Uses `ortools.sat.python.cp_model`:

1. Create one `IntervalVar` per WorkItem spanning `[start, start + duration]`.
2. Add `AddEndBeforeStart` constraints for predecessors.
3. Add deadline constraints: `start + duration <= deadline_quarter`.
4. Capacity: `AddCumulative` or sum constraints per quarter ≤ `quarterly_capacity_days`.
5. Budget: cumulative cost constraint per quarter.
6. Objective: minimise weighted cost-of-delay sum + risk penalty (Gini coefficient of wave sizes).
7. Set `random_seed` and `num_search_workers=1`.

**Infeasibility (`infeasibility.py`)**

On `INFEASIBLE` status: uses `CpSolverSolutionCallback` / assumption literals to enumerate a minimal infeasible subset. Populates `InfeasibilityReport.remediations` with one suggestion per conflicting constraint type.

### Stage 4: Evaluate (`regplan/evaluate/`)

**Public function:** `evaluate(schedule, derive_result, assumptions) -> FinancialResult`

**Finance Engine (`finance.py`)**

For each quarter `q` in `[0, horizon_quarters)`:
- `capex[q]` = sum of `WorkItem.cost_gbp` for items completing in `q` (capital).
- `opex[q]` = ongoing run cost for active WorkItems.
- `run_cost_savings[q]` = benefit for items completed ≥ `ramp_up_quarters` ago.
- NPV: `sum(net[q] / (1 + discount_rate)^q)`.
- Payback: first `q` where `cumsum(net) >= 0`.
- Cost-of-delay per item: financial delta from shifting completion one quarter later.

**Explainer (`explainer.py`)**

Queries `Schedule.work_item_starts` and the WorkItem predecessor graph to compute:
- Slack = `deadline_quarter - (start + duration)`.
- Critical path membership.
- Binding constraint identification.
- Hypothetical shift analysis.

### Stage 5: Simulate (`regplan/simulate/`)

**Public function:** `simulate(schedule, financial_result, assumptions, n_runs, seed) -> SimulationResult`

**Monte Carlo (`monte_carlo.py`)**

```python
rng = numpy.random.default_rng(seed)
for run in range(n_runs):
    common_factor = sample_distribution(rng, cost_overrun_dist)  # shared
    for item in work_items:
        cost_factor = common_factor * sample_distribution(rng, item_dist)
        duration_slip = sample_distribution(rng, duration_slip_dist)
        simulated_cost = item.cost_gbp * cost_factor
        simulated_end = item.scheduled_end + duration_slip (propagated)
    compute_total_cost, npv for this run
collect percentiles, tornado ranking (OAT variance attribution)
```

Triangular sampling: `numpy.random.Generator.triangular`. Lognormal: `numpy.random.Generator.lognormal`.

Tornado ranking: one-at-a-time variance attribution — fix all assumptions to median, vary each individually, record NPV variance.

### Stage 6: Report (`regplan/report/`)

**Public function:** `report(pipeline_result, out_dir) -> None`

**Serializer (`serializer.py`)**: `pipeline_result.model_dump_json()` → `result.json`.

**Renderer (`renderer.py`)**: Jinja2 template loaded from `regplan/report/templates/memo.md.j2`. Renders from the deserialised JSON.

**Charts (`charts.py`)**: Matplotlib figures:
- Gantt: horizontal bar per WorkItem, x-axis = quarters.
- NPV histogram: `plt.hist` of simulation run NPVs.
- Tornado: horizontal bar chart sorted by variance contribution.
- Deadline miss: bar chart of `deadline_miss_probabilities`.

All figures saved as PNG in the run directory.

---

## CLI Design (`cli/main.py`)

```python
app = typer.Typer()

@app.command()
def validate(landscape: Path): ...

@app.command()
def plan(landscape: Path, scenario: Optional[str], packs: list[Path]): ...

@app.command()
def simulate(landscape: Path, runs: int, seed: int): ...

@app.command()
def compare(a: str, b: str): ...

@app.command()
def explain(landscape: Path, item_id: str): ...

@app.command()
def report(run_dir: Path, out: Path): ...
```

Each command calls the corresponding `regplan` package function and handles exceptions by printing to stderr and exiting with code 1.

---

## Correctness Properties

The following properties are defined for use in Hypothesis property-based tests.

**Property 1: Trigger Condition Determinism**
For any valid `Application` and valid `TriggerCondition`, evaluating the condition twice on the same Application produces the same boolean result.
`evaluate(cond, app) == evaluate(cond, app)`
_Validates: Requirement 4.5_

**Property 2: Schedule Capacity Constraint**
For any valid Schedule produced by the Optimizer, the total capacity demand of WorkItems assigned to any single quarter does not exceed `Assumptions.quarterly_capacity_days`.
`∀q: sum(item.capacity_demand_days for item in schedule.wave[q]) ≤ assumptions.quarterly_capacity_days`
_Validates: Requirement 8.4_

**Property 3: TCO Equals Sum of Cash Flows**
For any valid Schedule and Assumptions, the Finance Engine's TCO equals the sum of all quarterly cost cash flows.
`financial_result.tco == sum(cf.capex + cf.opex + cf.migration_cost for cf in financial_result.cash_flows)`
_Validates: Requirement 11.2_

**Property 4: NPV Discounting Monotonicity**
For any valid Assumptions with a positive discount rate, the NPV computed by the Finance Engine is less than or equal to the undiscounted sum of net cash flows.
`financial_result.npv ≤ sum(cf.net for cf in financial_result.cash_flows)`
_Validates: Requirement 11.3_

**Property 5: Pipeline Result Round-Trip Serialization**
Serialising a `PipelineResult` to JSON and deserialising it produces an object equal to the original.
`PipelineResult.model_validate_json(result.model_dump_json()) == result`
_Validates: Requirement 14.1, 18.5_

---

## Technology Stack

| Concern | Library |
|---|---|
| Data models & validation | Pydantic v2 |
| YAML loading | PyYAML |
| Constraint solver | google-or-tools (CP-SAT) |
| Graph algorithms | NetworkX |
| Numerical computation | NumPy |
| Statistical distributions | NumPy (triangular, lognormal) |
| Property-based testing | Hypothesis |
| Unit testing | pytest |
| CLI | Typer |
| UI | Streamlit |
| Template rendering | Jinja2 |
| Chart generation | Matplotlib |
| Linting | Ruff |
| Type checking | Mypy (strict) |
| CI | GitHub Actions |
| Containerisation | Docker |

---

## Error Handling Strategy

- **Schema errors**: Pydantic `ValidationError` wrapped in `regplan.errors.IngestError` with file path and field path.
- **Semantic errors**: `regplan.errors.SemanticError(entity_id, rule, suggestion)`.
- **Trigger condition errors**: `regplan.errors.TriggerEvalError(rule_id, attribute_name)`.
- **Infeasibility**: returns `InfeasibilityReport` (not an exception).
- **Missing assumptions**: `regplan.errors.MissingAssumptionError(assumption_name)`.
- **CLI**: catches all `regplan` errors, prints to stderr, exits with code 1.

All error classes inherit from `regplan.errors.RegplanError(Exception)`.

---

## Reproducibility Strategy

- Scheduler: `CpSolver.parameters.random_seed` + `num_search_workers=1`.
- Simulator: `numpy.random.default_rng(seed)`.
- RunManifest: SHA-256 of all input files, package versions from `importlib.metadata`, `git rev-parse HEAD` (suppressed if not a git repo), `dirty` flag from `git status --porcelain`.
- Determinism guarantee: same inputs + seeds + package versions → byte-for-byte identical JSON output.
