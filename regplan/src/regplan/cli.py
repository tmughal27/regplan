"""regplan CLI — thin shell, zero business logic."""
from __future__ import annotations

import sys
from pathlib import Path
from typing import Optional

import typer

from regplan.errors import RegplanError

app = typer.Typer(name="regplan", help="Regulatory compliance planning tool.")


@app.command()
def validate(
    landscape: Path = typer.Argument(..., help="Path to landscape YAML"),
    assumptions: Path = typer.Option(
        ..., "--assumptions", "-a", help="Path to assumptions YAML"
    ),
    packs: Optional[list[Path]] = typer.Option(
        None, "--packs", "-p", help="Regulation pack YAML files"
    ),
) -> None:
    """Validate a landscape YAML file for schema and semantic errors."""
    try:
        from regplan._pipeline import ingest as _ingest
        from regplan.ingest.validator import collect_errors
        result = _ingest(landscape, packs or [], assumptions)
        errors = collect_errors(result)
        if errors:
            for e in errors:
                typer.echo(str(e), err=True)
            raise typer.Exit(1)
        typer.echo(f"✓ {landscape.name} is valid ({len(result.landscape.applications)} applications).")
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def plan(
    landscape: Path = typer.Argument(..., help="Path to landscape YAML"),
    assumptions: Path = typer.Option(
        ..., "--assumptions", "-a", help="Path to assumptions YAML"
    ),
    packs: Optional[list[Path]] = typer.Option(
        None, "--packs", "-p", help="Regulation pack YAML files"
    ),
    scenario: Optional[str] = typer.Option(
        None, "--scenario", "-s", help="Named scenario to apply"
    ),
    out_dir: Path = typer.Option(
        Path("run_output"), "--out", "-o", help="Output directory for run results"
    ),
) -> None:
    """Run the full pipeline and write results to a run directory."""
    try:
        from regplan._pipeline import ingest as _ingest, derive, optimize, evaluate
        from regplan.ingest.validator import validate as _validate
        from regplan.manifest.builder import build_manifest
        from regplan.models.report import PipelineResult
        from regplan.report import report as _report

        ingest_result = _ingest(landscape, packs or [], assumptions)
        _validate(ingest_result)

        landscape_obj = ingest_result.landscape
        assumptions_obj = ingest_result.assumptions

        if scenario:
            from regplan.scenario.engine import BUILTIN_SCENARIOS, apply_scenario
            if scenario not in BUILTIN_SCENARIOS:
                typer.echo(
                    f"Unknown scenario '{scenario}'. Available: {list(BUILTIN_SCENARIOS)}", err=True
                )
                raise typer.Exit(1)
            transformed = apply_scenario(landscape_obj, assumptions_obj, BUILTIN_SCENARIOS[scenario])
            # Re-ingest with transformed landscape/assumptions (use IngestResult directly)
            from regplan.ingest.loader import IngestResult
            ingest_result = IngestResult(
                landscape=transformed.landscape,
                packs=ingest_result.packs,
                assumptions=transformed.assumptions,
            )
            scenario_name = transformed.scenario_name
        else:
            scenario_name = "base"

        derive_result = derive(ingest_result, ingest_result.assumptions)
        optimize_result = optimize(derive_result, ingest_result.assumptions)

        manifest = build_manifest(
            input_paths=[landscape, assumptions] + (packs or []),
            scheduler_seed=42,
            simulation_seed=ingest_result.assumptions.simulation_seed,
        )

        if not optimize_result.is_feasible:
            result = PipelineResult(
                landscape_id=ingest_result.landscape.id,
                scenario_name=scenario_name,
                schedule=None,
                infeasibility=optimize_result.infeasibility,
                financial=None,
                simulation=None,
                manifest=manifest,
            )
            _report(result, out_dir)
            typer.echo(str(optimize_result.infeasibility), err=True)
            raise typer.Exit(1)

        financial = evaluate(optimize_result.schedule, derive_result, ingest_result.assumptions)

        result = PipelineResult(
            landscape_id=ingest_result.landscape.id,
            scenario_name=scenario_name,
            schedule=optimize_result.schedule,
            infeasibility=None,
            financial=financial,
            simulation=None,
            manifest=manifest,
        )
        _report(result, out_dir)
        typer.echo(f"✓ Plan written to {out_dir}/")
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def simulate_cmd(
    landscape: Path = typer.Argument(..., help="Path to landscape YAML"),
    assumptions: Path = typer.Option(
        ..., "--assumptions", "-a", help="Path to assumptions YAML"
    ),
    packs: Optional[list[Path]] = typer.Option(
        None, "--packs", "-p", help="Regulation pack YAML files"
    ),
    run_dir: Path = typer.Option(
        Path("run_output"), "--run-dir", "-r", help="Existing run directory"
    ),
    runs: int = typer.Option(1000, "--runs", help="Number of Monte Carlo runs"),
    seed: int = typer.Option(42, "--seed", help="Random seed"),
) -> None:
    """Append Monte Carlo simulation results to an existing run directory."""
    try:
        from regplan._pipeline import ingest as _ingest, derive, optimize, evaluate
        from regplan.simulate import simulate as _simulate
        from regplan.manifest.builder import build_manifest
        from regplan.models.report import PipelineResult
        from regplan.report import report as _report
        from regplan.report.serializer import deserialise, serialise

        result_path = run_dir / "result.json"
        if result_path.exists():
            existing = deserialise(result_path)
            schedule = existing.schedule
            if schedule is None:
                typer.echo("No feasible schedule in run directory.", err=True)
                raise typer.Exit(1)
            # Re-derive to get work_items and financial
            ingest_result = _ingest(landscape, packs or [], assumptions)
            derive_result = derive(ingest_result, ingest_result.assumptions)
            financial = evaluate(schedule, derive_result, ingest_result.assumptions)
            sim_result = _simulate(
                schedule, financial, ingest_result.assumptions, runs, seed,
                work_items=derive_result.work_items,
            )
            updated = PipelineResult(
                landscape_id=existing.landscape_id,
                scenario_name=existing.scenario_name,
                schedule=existing.schedule,
                infeasibility=existing.infeasibility,
                financial=financial,
                simulation=sim_result,
                manifest=existing.manifest,
            )
            _report(updated, run_dir)
            typer.echo(f"✓ Simulation results appended to {run_dir}/")
        else:
            typer.echo(f"No result.json found in {run_dir}. Run 'plan' first.", err=True)
            raise typer.Exit(1)
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def compare(
    landscape_a: str = typer.Argument(..., help="Landscape YAML path or scenario name"),
    landscape_b: str = typer.Argument(..., help="Landscape YAML path or scenario name"),
    assumptions: Path = typer.Option(
        ..., "--assumptions", "-a", help="Path to assumptions YAML"
    ),
    packs: Optional[list[Path]] = typer.Option(
        None, "--packs", "-p", help="Regulation pack YAML files"
    ),
    out: Path = typer.Option(
        Path("comparison.md"), "--out", "-o", help="Output file for comparison report"
    ),
) -> None:
    """Compare two landscapes or scenarios side-by-side."""
    try:
        from regplan._pipeline import ingest as _ingest, derive, optimize, evaluate
        from regplan.scenario.engine import BUILTIN_SCENARIOS, apply_scenario, compare_scenarios
        from regplan.ingest.loader import IngestResult

        def _run_pipeline(landscape_path: Path, assumed_assumptions: Path, pack_paths: list[Path]) -> tuple:
            ir = _ingest(landscape_path, pack_paths, assumed_assumptions)
            dr = derive(ir, ir.assumptions)
            opt = optimize(dr, ir.assumptions)
            if not opt.is_feasible:
                return ir.landscape.id, None, None, opt
            fin = evaluate(opt.schedule, dr, ir.assumptions)
            return ir.landscape.id, opt.schedule, fin, opt

        # Resolve a or b as landscape paths or scenario names
        def _resolve(name: str) -> tuple[Path, str]:
            p = Path(name)
            if p.exists():
                return p, name
            if name in BUILTIN_SCENARIOS:
                return None, name  # type: ignore[return-value]
            raise RegplanError(f"'{name}' is neither a file nor a known scenario")

        path_a, sname_a = _resolve(landscape_a)
        path_b, sname_b = _resolve(landscape_b)

        if path_a is None or path_b is None:
            typer.echo("Scenario-based comparison requires a landscape file.", err=True)
            raise typer.Exit(1)

        lid_a, sched_a, fin_a, opt_a = _run_pipeline(path_a, assumptions, packs or [])
        lid_b, sched_b, fin_b, opt_b = _run_pipeline(path_b, assumptions, packs or [])

        if fin_a is None or fin_b is None:
            typer.echo("One or both pipelines produced infeasible plans.", err=True)
            raise typer.Exit(1)

        assert sched_a is not None and sched_b is not None
        comp = compare_scenarios(
            name_a=lid_a, financial_a=fin_a, simulation_a=None, schedule_a=sched_a,
            name_b=lid_b, financial_b=fin_b, simulation_b=None, schedule_b=sched_b,
        )
        lines = [
            f"# Comparison: {comp.scenario_a} vs {comp.scenario_b}\n",
            f"| Metric | {comp.scenario_a} | {comp.scenario_b} |",
            f"|--------|-------|-------|",
            f"| TCO | £{comp.tco_a:,.0f} | £{comp.tco_b:,.0f} |",
            f"| NPV | £{comp.npv_a:,.0f} | £{comp.npv_b:,.0f} |",
            f"| Payback Quarter | {comp.payback_a} | {comp.payback_b} |",
        ]
        out.write_text("\n".join(lines), encoding="utf-8")
        typer.echo(f"✓ Comparison written to {out}")
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def explain(
    landscape: Path = typer.Argument(..., help="Path to landscape YAML"),
    item_id: str = typer.Argument(..., help="WorkItem or Application id to explain"),
    assumptions: Path = typer.Option(
        ..., "--assumptions", "-a", help="Path to assumptions YAML"
    ),
    packs: Optional[list[Path]] = typer.Option(
        None, "--packs", "-p", help="Regulation pack YAML files"
    ),
    run_dir: Path = typer.Option(
        Path("run_output"), "--run-dir", "-r", help="Run directory containing result.json"
    ),
) -> None:
    """Explain why a WorkItem is scheduled where it is."""
    try:
        from regplan._pipeline import ingest as _ingest, derive, optimize, evaluate
        from regplan.evaluate.explainer import explain_work_item
        from regplan.report.serializer import deserialise

        result_path = run_dir / "result.json"
        if result_path.exists():
            existing = deserialise(result_path)
            if existing.schedule is None:
                typer.echo("No feasible schedule in run directory.", err=True)
                raise typer.Exit(1)
            ingest_result = _ingest(landscape, packs or [], assumptions)
            derive_result = derive(ingest_result, ingest_result.assumptions)
            financial = evaluate(existing.schedule, derive_result, ingest_result.assumptions)
            explanation = explain_work_item(
                item_id,
                existing.schedule,
                derive_result.work_items,
                derive_result.graph.critical_path_item_ids,
                financial,
            )
        else:
            # Run pipeline from scratch
            ingest_result = _ingest(landscape, packs or [], assumptions)
            derive_result = derive(ingest_result, ingest_result.assumptions)
            opt = optimize(derive_result, ingest_result.assumptions)
            if not opt.is_feasible or opt.schedule is None:
                typer.echo("No feasible schedule could be produced.", err=True)
                raise typer.Exit(1)
            financial = evaluate(opt.schedule, derive_result, ingest_result.assumptions)
            explanation = explain_work_item(
                item_id,
                opt.schedule,
                derive_result.work_items,
                derive_result.graph.critical_path_item_ids,
                financial,
            )

        typer.echo(f"WorkItem: {explanation.work_item_id}")
        typer.echo(f"  Scheduled quarter : Q{explanation.scheduled_quarter}")
        typer.echo(f"  Duration          : {explanation.duration_quarters} quarter(s)")
        typer.echo(f"  Total slack       : {explanation.total_slack} quarter(s)")
        typer.echo(f"  Critical path     : {explanation.on_critical_path}")
        typer.echo(f"  Binding constraint: {explanation.binding_constraint}")
        typer.echo(f"  Hypothetical shift: {explanation.hypothetical_shift}")
    except KeyError as exc:
        typer.echo(f"WorkItem not found: {exc}", err=True)
        raise typer.Exit(1)
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


@app.command()
def report_cmd(
    run_dir: Path = typer.Argument(..., help="Run directory containing result.json"),
    out: Path = typer.Option(
        Path("run_output"), "--out", "-o", help="Output directory for rendered report"
    ),
) -> None:
    """Re-render memo and charts from an existing run directory."""
    try:
        from regplan.report.serializer import deserialise
        from regplan.report.renderer import render_memo
        from regplan.report.charts import generate_all_charts

        result_path = run_dir / "result.json"
        if not result_path.exists():
            typer.echo(f"result.json not found in {run_dir}", err=True)
            raise typer.Exit(1)

        result = deserialise(result_path)
        out.mkdir(parents=True, exist_ok=True)
        render_memo(result_path, out / "memo.md")
        generate_all_charts(result, out)
        typer.echo(f"✓ Report written to {out}/")
    except RegplanError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
