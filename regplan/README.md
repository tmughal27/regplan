# regplan

A Python library and CLI for regulatory compliance planning.

## Design Principles

1. **Library-first**: All business logic lives in the `regplan` package. The CLI and Streamlit UI are zero-logic shells that delegate entirely to the library.
2. **Traceable outputs**: Every numeric output is traceable to the input identifiers and assumption identifiers that produced it.
3. **Fail loudly**: When a plan is infeasible, the tool explains why rather than silently producing a plausible-looking but wrong result.
4. **Deterministic by default**: The same inputs, seeds, and package versions produce byte-for-byte identical output, enabling reproducible audits.
5. **Incrementally testable**: Each pipeline stage (Ingest → Derive → Optimize → Evaluate → Simulate → Report) consumes the typed output of the previous stage and can be executed and tested independently.

## Pipeline Stages

```
Ingest → Derive → Optimize → Evaluate → Simulate → Report
```

- **Ingest**: Load and validate Landscape YAML, RegulationPack YAMLs, and Assumptions YAML.
- **Derive**: Score applications, evaluate trigger conditions, match obligations, and build the dependency graph.
- **Optimize**: Schedule WorkItems with CP-SAT, respecting deadlines, capacity, and budget constraints.
- **Evaluate**: Compute TCO, NPV, payback period, and cost-of-delay for the schedule.
- **Simulate**: Run Monte Carlo simulation to produce P50/P80/P95 cost and NPV ranges.
- **Report**: Serialise results to JSON and render Jinja2 memo with Matplotlib charts.

## CLI Usage

```bash
# Install
pip install -e ".[dev]"

# Validate a landscape file
regplan validate landscape.yaml

# Run the full planning pipeline
regplan plan landscape.yaml --packs gdpr.yaml --packs ai_act.yaml

# Run Monte Carlo simulation
regplan simulate landscape.yaml --runs 10000 --seed 42

# Compare two scenarios or landscapes
regplan compare scenario_a scenario_b

# Explain why a WorkItem is scheduled where it is
regplan explain landscape.yaml APP-01:R-GDPR-01

# Render a report from a run directory
regplan report ./runs/2024-01-01/ --out ./reports/
```

## Development

```bash
pip install -e ".[dev]"
ruff check src/ tests/
mypy --strict src/regplan
pytest
```

## Project Structure

```
regplan/
├── src/regplan/          # Main package (src layout)
│   ├── models/           # Pydantic data models
│   ├── ingest/           # YAML loading and validation
│   ├── derive/           # Rule engine, scorer, matcher, graph
│   ├── optimize/         # CP-SAT scheduler and infeasibility
│   ├── evaluate/         # Finance engine and explainer
│   ├── simulate/         # Monte Carlo engine
│   ├── scenario/         # Scenario management
│   ├── report/           # Serialiser, renderer, charts
│   ├── manifest/         # RunManifest builder
│   └── examples/         # Example landscape and pack YAMLs
├── cli/                  # Typer CLI shell
├── app/                  # Streamlit UI shell
├── tests/
│   ├── unit/             # Pytest unit tests
│   ├── property/         # Hypothesis property-based tests
│   └── golden/           # Golden-file regression tests
├── pyproject.toml
└── Dockerfile
```
