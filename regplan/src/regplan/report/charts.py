"""Chart generators for the Report stage — saves PNG files to the run directory."""
from __future__ import annotations

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from regplan.models.report import PipelineResult


def generate_all_charts(result: PipelineResult, out_dir: Path) -> None:
    """Generate and save all charts for *result* into *out_dir*."""
    out_dir.mkdir(parents=True, exist_ok=True)
    if result.schedule:
        _gantt_chart(result, out_dir)
    if result.simulation:
        _npv_histogram(result, out_dir)
        _tornado_chart(result, out_dir)
        _deadline_miss_chart(result, out_dir)


def _gantt_chart(result: PipelineResult, out_dir: Path) -> None:
    sched = result.schedule
    if sched is None:
        return
    fig, ax = plt.subplots(figsize=(12, max(4, len(sched.work_item_starts) * 0.4 + 1)))
    items = sorted(sched.work_item_starts.items(), key=lambda kv: kv[1])
    for i, (wi_id, start_q) in enumerate(items):
        ax.barh(i, 1, left=start_q, height=0.6, align="center")
    ax.set_yticks(range(len(items)))
    ax.set_yticklabels([wi_id for wi_id, _ in items], fontsize=7)
    ax.set_xlabel("Quarter")
    ax.set_title(f"Wave Plan — {result.landscape_id} ({result.scenario_name})")
    plt.tight_layout()
    fig.savefig(out_dir / "gantt.png", dpi=100)
    plt.close(fig)


def _npv_histogram(result: PipelineResult, out_dir: Path) -> None:
    sim = result.simulation
    if sim is None:
        return
    npvs = [r.npv for r in sim.runs]
    if not npvs:
        return
    fig, ax = plt.subplots(figsize=(8, 4))
    ax.hist(npvs, bins=min(50, len(npvs)), edgecolor="black")
    ax.axvline(sim.p50_npv, color="orange", linestyle="--", label="P50")
    ax.axvline(sim.p80_npv, color="red", linestyle="--", label="P80")
    ax.set_xlabel("NPV (£)")
    ax.set_ylabel("Frequency")
    ax.set_title("NPV Distribution")
    ax.legend()
    plt.tight_layout()
    fig.savefig(out_dir / "npv_histogram.png", dpi=100)
    plt.close(fig)


def _tornado_chart(result: PipelineResult, out_dir: Path) -> None:
    sim = result.simulation
    if sim is None or not sim.tornado:
        return
    entries = sorted(sim.tornado, key=lambda e: e.npv_variance_contribution)
    names = [e.assumption_name for e in entries]
    values = [e.npv_variance_contribution for e in entries]
    fig, ax = plt.subplots(figsize=(8, max(3, len(names) * 0.5 + 1)))
    ax.barh(range(len(names)), values, align="center")
    ax.set_yticks(range(len(names)))
    ax.set_yticklabels(names)
    ax.set_xlabel("NPV Variance Contribution")
    ax.set_title("Tornado Chart — NPV Sensitivity")
    plt.tight_layout()
    fig.savefig(out_dir / "tornado.png", dpi=100)
    plt.close(fig)


def _deadline_miss_chart(result: PipelineResult, out_dir: Path) -> None:
    sim = result.simulation
    if sim is None or not sim.deadline_miss_probabilities:
        return
    probs = sim.deadline_miss_probabilities
    names = list(probs.keys())
    values = [probs[n] * 100 for n in names]
    fig, ax = plt.subplots(figsize=(max(6, len(names) * 0.8 + 2), 4))
    ax.bar(range(len(names)), values)
    ax.set_xticks(range(len(names)))
    ax.set_xticklabels(names, rotation=45, ha="right", fontsize=8)
    ax.set_ylabel("Miss Probability (%)")
    ax.set_title("Deadline-Miss Probabilities")
    plt.tight_layout()
    fig.savefig(out_dir / "deadline_miss.png", dpi=100)
    plt.close(fig)
