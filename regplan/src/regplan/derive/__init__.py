"""Derive stage: rule engine, scorer, obligation matcher, graph builder."""
from __future__ import annotations

from dataclasses import dataclass, field

from regplan.derive.graph import GraphResult, build_graphs
from regplan.derive.matcher import build_work_items
from regplan.derive.scorer import ScoredApplication, score_applications
from regplan.ingest.loader import IngestResult
from regplan.models.assumptions import Assumptions
from regplan.models.work import WorkItem


@dataclass
class DeriveResult:
    """Typed output of the Derive stage."""
    scored_applications: list[ScoredApplication]
    work_items: list[WorkItem]
    graph: GraphResult


def derive(ingest_result: IngestResult, assumptions: Assumptions) -> DeriveResult:
    """Run the full Derive stage: score apps, match obligations, build graphs."""
    scored = score_applications(ingest_result.landscape, assumptions)

    # Build application graph (needed for predecessor mapping)
    from regplan.derive.graph import build_application_graph
    _g, condensed, node_to_scc, scc_to_apps = build_application_graph(ingest_result.landscape)

    # Build condensed predecessor map: SCC index → list of predecessor SCC indices
    condensed_preds: dict[int, list[int]] = {
        n: list(condensed.predecessors(n)) for n in condensed.nodes()
    }

    work_items = build_work_items(
        scored_apps=scored,
        packs=ingest_result.packs,
        assumptions=assumptions,
        node_to_scc=node_to_scc,
        condensed_predecessors=condensed_preds,
    )

    graph_result = build_graphs(ingest_result.landscape, work_items)

    return DeriveResult(
        scored_applications=scored,
        work_items=work_items,
        graph=graph_result,
    )
