from __future__ import annotations

import os
import sys
from functools import lru_cache
from typing import Dict, FrozenSet, Optional, Set

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from aspects import PRIMALS, aspect_parents

Aspect = str


def _build_aspect_graph() -> Dict[Aspect, Set[Aspect]]:
    graph: Dict[Aspect, Set[Aspect]] = {}

    for child, parents in aspect_parents.items():
        graph.setdefault(child, set())
        for p in parents:
            graph.setdefault(p, set())
            graph[child].add(p)
            graph[p].add(child)

    for primal in PRIMALS:
        graph.setdefault(primal, set())

    return graph


ASPECT_GRAPH: Dict[Aspect, Set[Aspect]] = _build_aspect_graph()


def _compute_tiers() -> Dict[Aspect, int]:
    tiers: Dict[Aspect, int] = {p: 0 for p in PRIMALS}

    def get_tier(asp: Aspect) -> int:
        if asp in tiers:
            return tiers[asp]
        if asp not in aspect_parents:
            tiers[asp] = 0
            return 0
        parents = aspect_parents[asp]
        tier = max(get_tier(p) for p in parents) + 1
        tiers[asp] = tier
        return tier

    for asp in ASPECT_GRAPH:
        get_tier(asp)

    return tiers


ASPECT_TIERS: Dict[Aspect, int] = _compute_tiers()

_GRAPH_FROZEN: Dict[Aspect, FrozenSet[Aspect]] = {
    k: frozenset(v) for k, v in ASPECT_GRAPH.items()
}
_EMPTY_FSET: FrozenSet[Aspect] = frozenset()

_weight_cache: Dict[bool, Dict[Aspect, float]] = {}


def calculate_aspect_weights(prefer_ordo: bool = True) -> Dict[Aspect, float]:
    if prefer_ordo in _weight_cache:
        return _weight_cache[prefer_ordo]

    weights: Dict[Aspect, float] = {}

    for asp in PRIMALS:
        weights[asp] = 1.0

    for asp in ASPECT_GRAPH:
        if asp not in weights:
            weights[asp] = 1.0 + ASPECT_TIERS.get(asp, 0) * 2.0

    if prefer_ordo:
        if "Ordo" in ASPECT_GRAPH:
            weights["Ordo"] = 0.0
        if "Instrumentum" in ASPECT_GRAPH:
            weights["Instrumentum"] = 0.0
    else:
        if "Ordo" in ASPECT_GRAPH:
            weights["Ordo"] = 1.0
        if "Instrumentum" in ASPECT_GRAPH:
            weights["Instrumentum"] = 5.0

    _weight_cache[prefer_ordo] = weights
    return weights


ASPECT_WEIGHTS: Dict[Aspect, float] = calculate_aspect_weights(True)


def can_connect(a: Optional[Aspect], b: Optional[Aspect]) -> bool:
    if a is None or b is None:
        return True
    return b in _GRAPH_FROZEN.get(a, _EMPTY_FSET)


def get_neighbors_of(aspect: Aspect) -> FrozenSet[Aspect]:
    return _GRAPH_FROZEN.get(aspect, _EMPTY_FSET)


def get_graph() -> Dict[Aspect, Set[Aspect]]:
    return ASPECT_GRAPH


@lru_cache(maxsize=10000)
def shortest_chain_length(a: Aspect, b: Aspect) -> int:
    if a == b:
        return 1
    if b in _GRAPH_FROZEN.get(a, _EMPTY_FSET):
        return 2

    visited = {a}
    frontier = [a]
    depth = 1

    while frontier:
        depth += 1
        next_frontier = []
        for asp in frontier:
            for nbr in _GRAPH_FROZEN.get(asp, _EMPTY_FSET):
                if nbr == b:
                    return depth
                if nbr not in visited:
                    visited.add(nbr)
                    next_frontier.append(nbr)
        frontier = next_frontier

        if depth > 20:
            break

    return 999
