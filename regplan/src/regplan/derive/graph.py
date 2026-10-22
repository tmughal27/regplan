"""NetworkX dependency graph builder for the Derive stage."""
from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx

from regplan.models.landscape import Landscape
from regplan.models.work import WorkItem


@dataclass
class GraphResult:
    app_graph: nx.DiGraph
    condensed_graph: nx.DiGraph
    node_to_scc: dict[str, int]          # app_id → SCC index
    scc_to_apps: dict[int, list[str]]    # SCC index → list[app_id]
    betweenness_centrality: dict[str, float]
    critical_path_item_ids: list[str]


def build_application_graph(landscape: Landscape) -> tuple[nx.DiGraph, nx.DiGraph, dict[str, int], dict[int, list[str]]]:
    """Build directed application graph and its condensed form.

    Returns (app_graph, condensed_graph, node_to_scc, scc_to_apps).
    """
    g: nx.DiGraph = nx.DiGraph()
    for app in landscape.applications:
        g.add_node(app.id)
    for iface in landscape.interfaces:
        g.add_edge(iface.source_id, iface.target_id)

    condensed: nx.DiGraph = nx.condensation(g)
    node_to_scc: dict[str, int] = {}
    scc_to_apps: dict[int, list[str]] = {}
    for scc_idx in condensed.nodes():
        members: list[str] = list(condensed.nodes[scc_idx].get("members", set()))
        scc_to_apps[scc_idx] = members
        for m in members:
            node_to_scc[m] = scc_idx

    return g, condensed, node_to_scc, scc_to_apps


def compute_betweenness_centrality(g: nx.DiGraph) -> dict[str, float]:
    return nx.betweenness_centrality(g)  # type: ignore[no-any-return]


def compute_critical_path(work_items: list[WorkItem]) -> list[str]:
    """Compute the critical path through the WorkItem DAG by total duration."""
    if not work_items:
        return []
    dag: nx.DiGraph = nx.DiGraph()
    item_map = {wi.id: wi for wi in work_items}
    for wi in work_items:
        dag.add_node(wi.id, duration=wi.duration_quarters)
    for wi in work_items:
        for pred_id in wi.predecessors:
            if pred_id in item_map:
                dag.add_edge(pred_id, wi.id)
    if not dag.nodes or not nx.is_directed_acyclic_graph(dag):
        return []
    try:
        return list(nx.dag_longest_path(dag, weight="duration"))
    except Exception:
        return []


def build_graphs(landscape: Landscape, work_items: list[WorkItem]) -> GraphResult:
    """Build all graph structures for the Derive stage."""
    g, condensed, node_to_scc, scc_to_apps = build_application_graph(landscape)
    bc = compute_betweenness_centrality(g)
    cp = compute_critical_path(work_items)
    return GraphResult(
        app_graph=g,
        condensed_graph=condensed,
        node_to_scc=node_to_scc,
        scc_to_apps=scc_to_apps,
        betweenness_centrality=bc,
        critical_path_item_ids=cp,
    )
