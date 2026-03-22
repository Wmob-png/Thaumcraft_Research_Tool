# solver_edges.py
"""
"""

from solver_core.solver_board import hex_distance, compute_aspect_components
from solver_core.solver_paths import (
    find_path_of_length,
    _find_straightest_path,
    _path_straightness,
)
from solver_core.solver_graph import _find_chain_dijkstra


# ============================================================
# Nearby target helper
# ============================================================

def _get_nearby_targets(temp_grid, pos_r, max_dist=8):
    """
    """
    targets = []
    for p, c in temp_grid.items():
        if not c.get("aspect") or c.get("void", False):
            continue
        if p == pos_r:
            continue
        if hex_distance(pos_r, p) <= max_dist:
            targets.append((p, c["aspect"]))
    return targets


# ============================================================
# Edge finding — two-phase: fast BFS then straightest refinement
# ============================================================

def _find_best_edge(
    grid,
    pos_a,
    asp_a,
    pos_b,
    asp_b,
    weights,
    extra_slack,
    existing_branch_paths=None,
):
    """
    """
    base_dist = hex_distance(pos_a, pos_b)
    min_len = max(2, base_dist + 1)
    max_len = min_len + extra_slack

    best_edge = None
    best_score = None
    best_length = None
    best_chain = None

    for length in range(min_len, max_len + 1):

        aspect_chain = _find_chain_dijkstra(asp_a, asp_b, length, weights)
        if not aspect_chain:
            continue

        tile_path = find_path_of_length(grid, pos_a, pos_b, length)
        if not tile_path:
            continue

        placements = []
        valid = True

        for k in range(1, length - 1):
            pos = tile_path[k]
            asp = aspect_chain[k]
            cell = grid[pos]

            existing = cell.get("aspect")
            if existing is not None and existing != asp:
                valid = False
                break
            if existing is None:
                placements.append((pos, asp))

        if not valid:
            continue

        count = len(placements)
        weight = sum(weights.get(asp, 10) for _, asp in placements)
        score = (count, weight)

        if best_score is None or score < best_score:
            best_score = score
            best_length = length
            best_chain = aspect_chain
            best_edge = {
                "placements": placements,
                "count": count,
                "weight": weight,
                "tile_path": tile_path,
                "aspect_chain": aspect_chain,
                "from_pos": pos_a,
                "from_asp": asp_a,
                "to_pos": pos_b,
                "to_asp": asp_b,
            }

    if best_edge is None:
        return None

    straight_path = _find_straightest_path(grid, pos_a, pos_b, best_length)
    if straight_path:
        placements = []
        valid = True

        for k in range(1, best_length - 1):
            pos = straight_path[k]
            asp = best_chain[k]
            cell = grid[pos]

            existing = cell.get("aspect")
            if existing is not None and existing != asp:
                valid = False
                break
            if existing is None:
                placements.append((pos, asp))

        if valid:
            best_edge["tile_path"] = straight_path
            best_edge["placements"] = placements
            best_edge["count"] = len(placements)
            best_edge["weight"] = sum(
                weights.get(asp, 10) for _, asp in placements
            )

    best_edge["straightness"] = _path_straightness(best_edge["tile_path"])

    return best_edge


# ============================================================
# Pairwise edge building
# ============================================================

def build_pairwise_edges(
    grid,
    user_placed,
    weights,
    extra_slack=6,
    progress_cb=None,
    base=0.0,
    span=1.0,
):
    """
    """
    edges = []
    n = len(user_placed)
    total_pairs = max(1, n * (n - 1) // 2)
    pair_idx = 0

    components = compute_aspect_components(grid)

    for i in range(n):
        pos_a, asp_a = user_placed[i]
        comp_a = components.get(pos_a)

        for j in range(i + 1, n):
            pos_b, asp_b = user_placed[j]

            if comp_a is not None and components.get(pos_b) == comp_a:
                pair_idx += 1
                if progress_cb:
                    frac = base + span * (pair_idx / total_pairs)
                    progress_cb(frac, f"MST: pair {pair_idx}/{total_pairs}")
                continue

            edge = _find_best_edge(
                grid, pos_a, asp_a, pos_b, asp_b, weights, extra_slack
            )
            if edge is not None:
                edge["a"] = i
                edge["b"] = j
                edges.append(edge)

            pair_idx += 1
            if progress_cb:
                frac = base + span * (pair_idx / total_pairs)
                progress_cb(frac, f"MST: pair {pair_idx}/{total_pairs}")

    return edges


# ============================================================
# MST
# ============================================================

class UnionFind:
    """
    """

    def __init__(self, n):
        self.parent = list(range(n))

    def find(self, x):
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra == rb:
            return False
        self.parent[rb] = ra
        return True


def build_mst(user_placed, edges):
    """
    """
    uf = UnionFind(len(user_placed))
    mst = []
    for edge in sorted(edges, key=lambda e: (e["count"], e["weight"])):
        if uf.union(edge["a"], edge["b"]):
            mst.append(edge)
        if len(mst) == len(user_placed) - 1:
            break
    if len(mst) != len(user_placed) - 1:
        return None
    return mst


def merge_mst_placements(grid, mst_edges):
    """
    """
    temp_grid = {pos: dict(cell) for pos, cell in grid.items()}
    placements = []
    for edge in mst_edges:
        for pos, asp in edge["placements"]:
            existing = temp_grid[pos].get("aspect")
            if existing is None:
                temp_grid[pos]["aspect"] = asp
                temp_grid[pos]["player_placed"] = False
                placements.append((pos, asp))
            elif existing != asp:
                return None
    return placements
