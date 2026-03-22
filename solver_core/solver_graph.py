# solver_graph.py
"""
"""

from heapq import heappush, heappop
from aspects import aspect_parents, PRIMALS

# ============================================================
# Aspect graph
# ============================================================

ASPECT_GRAPH = {}
for child, parents in aspect_parents.items():
    ASPECT_GRAPH.setdefault(child, set())
    for p in parents:
        ASPECT_GRAPH.setdefault(p, set())
        ASPECT_GRAPH[child].add(p)
        ASPECT_GRAPH[p].add(child)

for primal in PRIMALS:
    ASPECT_GRAPH.setdefault(primal, set())

_GRAPH_FROZEN = {k: frozenset(v) for k, v in ASPECT_GRAPH.items()}
_EMPTY_FSET = frozenset()


def _compute_tiers():
    """
    """
    memo = {}

    def tier(a):
        if a in memo:
            return memo[a]
        if a in PRIMALS or a not in aspect_parents:
            memo[a] = 0
            return 0
        v = max(tier(p) for p in aspect_parents[a]) + 1
        memo[a] = v
        return v

    return {a: tier(a) for a in ASPECT_GRAPH}


ASPECT_TIERS = _compute_tiers()

# ============================================================
# Weights
# ============================================================

_weight_cache = {}


def calculate_aspect_weights(prefer_ordo=True):
    """
    """
    if prefer_ordo in _weight_cache:
        return _weight_cache[prefer_ordo]

    weights = {}
    # Primals
    for a in PRIMALS:
        weights[a] = 1

    # Special cases
    if "Ordo" in ASPECT_GRAPH:
        weights["Ordo"] = 0
    if prefer_ordo and "Instrumentum" in ASPECT_GRAPH:
        weights["Instrumentum"] = 0

    # All others by tier
    for a in ASPECT_GRAPH:
        if a not in weights:
            weights[a] = ASPECT_TIERS[a] + 1

    _weight_cache[prefer_ordo] = weights
    return weights

ASPECT_WEIGHTS = calculate_aspect_weights(True)

# ============================================================
# Exact-length aspect chain search (Dijkstra)
# ============================================================

_chain_cache = {}


def clear_chain_cache():
    _chain_cache.clear()


def _find_chain_dijkstra(start_asp, end_asp, length, weights):
    """
    """
    if length < 2:
        return None
    if start_asp not in ASPECT_GRAPH or end_asp not in ASPECT_GRAPH:
        return None

    if length == 2:
        if end_asp in _GRAPH_FROZEN.get(start_asp, _EMPTY_FSET):
            return [start_asp, end_asp]
        return None

    target_steps = length - 1

    heap = [(0, 0, start_asp, [start_asp])]
    best_state_cost = {}
    best_result = None
    best_cost = float("inf")

    while heap:
        cost, steps, current, path = heappop(heap)

        if cost >= best_cost:
            continue

        if steps == target_steps:
            if current == end_asp:
                best_result = path
                best_cost = cost
            continue

        state = (current, steps)
        if state in best_state_cost and best_state_cost[state] <= cost:
            continue
        best_state_cost[state] = cost

        remaining = target_steps - steps

        for nbr in _GRAPH_FROZEN.get(current, _EMPTY_FSET):

            if remaining == 1 and nbr != end_asp:
                continue

            add_cost = 0 if nbr == end_asp else weights.get(nbr, 10)
            new_cost = cost + add_cost

            if new_cost >= best_cost:
                continue

            heappush(heap, (new_cost, steps + 1, nbr, path + [nbr]))

    return best_result


def find_aspect_chain_exact(start_asp, end_asp, length, prefer_oi=True):
    """
    """
    weights = calculate_aspect_weights(prefer_oi)
    key = (start_asp, end_asp, length, prefer_oi)
    if key in _chain_cache:
        return _chain_cache[key]
    chain = _find_chain_dijkstra(start_asp, end_asp, length, weights)
    _chain_cache[key] = chain
    return chain
