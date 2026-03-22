# solver_strategies.py
"""
"""

from solver_core.solver_board import (
    are_all_aspects_connected,
    get_user_placed,
    hex_distance,
    is_edge_position,
    grid_ring_count,
)
from solver_core.solver_edges import (
    build_pairwise_edges,
    build_mst,
    merge_mst_placements,
    _find_best_edge,
    _get_nearby_targets,
)
from solver_core.solver_graph import (
    calculate_aspect_weights,
    clear_chain_cache,
)


# ============================================================
# Strategies
# ============================================================

def _try_mst_strategy(
    grid,
    user_placed,
    weights,
    extra_slack,
    progress_cb=None,
    base=0.0,
    span=0.33,
):
    """
    """
    edges = build_pairwise_edges(
        grid,
        user_placed,
        weights,
        extra_slack,
        progress_cb=progress_cb,
        base=base,
        span=span,
    )
    if not edges:
        return None, None

    mst = build_mst(user_placed, edges)
    if mst is None:
        return None, None

    placements = merge_mst_placements(grid, mst)
    if placements is None:
        return None, None

    return placements, mst


def _try_spine_with_pair(
    grid,
    user_placed,
    weights,
    extra_slack,
    idx_a,
    idx_b,
    max_branch_dist=8,
    progress_cb=None,
    pair_frac=0.0,
    pair_span=0.0,
):
    """
    """
    pos_a, asp_a = user_placed[idx_a]
    pos_b, asp_b = user_placed[idx_b]

    if progress_cb:
        progress_cb(pair_frac, f"Spine: {asp_a} <-> {asp_b}")

    spine_edge = _find_best_edge(
        grid,
        pos_a,
        asp_a,
        pos_b,
        asp_b,
        weights,
        extra_slack,
        existing_branch_paths=[],
    )
    if spine_edge is None:
        return None, None, None

    edges_used = [spine_edge]
    temp_grid = {pos: dict(cell) for pos, cell in grid.items()}
    all_placements = []

    for pos, asp in spine_edge["placements"]:
        temp_grid[pos]["aspect"] = asp
        temp_grid[pos]["player_placed"] = False
        all_placements.append((pos, asp))

    remaining = [
        i for i in range(len(user_placed)) if i != idx_a and i != idx_b
    ]
    branch_paths = []
    n_branches = max(1, len(remaining))

    for b_idx, idx in enumerate(remaining):
        pos_r, asp_r = user_placed[idx]

        if progress_cb:
            branch_frac = pair_frac + pair_span * ((b_idx + 0.5) / n_branches)
            progress_cb(branch_frac, f"Spine: connecting {asp_r}")

        best_branch = None
        best_branch_score = (
            float("inf"),
            float("inf"),
            float("inf"),
        )

        nearby = _get_nearby_targets(temp_grid, pos_r, max_branch_dist)

        for pos_t, asp_t in nearby:
            branch = _find_best_edge(
                temp_grid,
                pos_r,
                asp_r,
                pos_t,
                asp_t,
                weights,
                extra_slack,
                existing_branch_paths=branch_paths,
            )
            if branch is None:
                continue
            score = (
                branch["count"],
                branch["weight"],
                branch.get("straightness", 0),
            )
            if score < best_branch_score:
                best_branch_score = score
                best_branch = branch

        if best_branch is None:
            all_filled = [
                (p, c["aspect"])
                for p, c in temp_grid.items()
                if c.get("aspect") and not c.get("void", False) and p != pos_r
            ]
            for pos_t, asp_t in all_filled:
                branch = _find_best_edge(
                    temp_grid,
                    pos_r,
                    asp_r,
                    pos_t,
                    asp_t,
                    weights,
                    extra_slack,
                    existing_branch_paths=branch_paths,
                )
                if branch is None:
                    continue
                score = (
                    branch["count"],
                    branch["weight"],
                    branch.get("straightness", 0),
                )
                if score < best_branch_score:
                    best_branch_score = score
                    best_branch = branch

        if best_branch is None:
            return None, None, None

        branch_paths.append(best_branch["tile_path"])
        edges_used.append(best_branch)

        for pos, asp in best_branch["placements"]:
            if temp_grid[pos].get("aspect") is None:
                temp_grid[pos]["aspect"] = asp
                temp_grid[pos]["player_placed"] = False
                all_placements.append((pos, asp))

    if not are_all_aspects_connected(temp_grid):
        return None, None, None

    total_count = len(all_placements)
    total_weight = sum(weights.get(a, 10) for _, a in all_placements)
    return all_placements, edges_used, (total_count, total_weight)


def _try_spine_strategy(
    grid,
    user_placed,
    weights,
    extra_slack,
    progress_cb=None,
    base=0.33,
    span=0.34,
):
    """
    """
    if len(user_placed) < 2:
        return None, None

    best_result = None
    best_edges = None
    best_score = (float("inf"), float("inf"))
    best_spine_pair = None

    n_pairs = sum(
        1
        for i in range(len(user_placed))
        for j in range(i + 1, len(user_placed))
    )
    pair_count = 0

    for i in range(len(user_placed)):
        for j in range(i + 1, len(user_placed)):
            pair_frac = base + span * (pair_count / max(1, n_pairs))
            pair_span_val = span / max(1, n_pairs)

            result, edges, score = _try_spine_with_pair(
                grid,
                user_placed,
                weights,
                extra_slack,
                i,
                j,
                progress_cb=progress_cb,
                pair_frac=pair_frac,
                pair_span=pair_span_val,
            )
            if result is not None and score < best_score:
                best_score = score
                best_result = result
                best_edges = edges
                best_spine_pair = (i, j)

            pair_count += 1

    if best_spine_pair is not None:
        pos_a, asp_a = user_placed[best_spine_pair[0]]
        pos_b, asp_b = user_placed[best_spine_pair[1]]
        print(f"[Spine] Best spine: {asp_a}@{pos_a} <-> {asp_b}@{pos_b}")

    return best_result, best_edges


def _try_all_orderings(
    grid,
    user_placed,
    weights,
    extra_slack,
    progress_cb=None,
    base=0.67,
    span=0.33,
):
    """
    """
    best_result = None
    best_edges = None
    best_score = (float("inf"), float("inf"))

    n_roots = len(user_placed)

    for root_idx in range(n_roots):
        root_frac = base + span * (root_idx / max(1, n_roots))
        root_span = span / max(1, n_roots)

        if progress_cb:
            _, asp_r = user_placed[root_idx]
            progress_cb(root_frac, f"AllOrders: root {asp_r}")

        temp_grid = {pos: dict(cell) for pos, cell in grid.items()}
        all_placements = []
        edges_used = []
        branch_paths = []
        success = True

        root_pos = user_placed[root_idx][0]
        others = sorted(
            [
                (i, hex_distance(root_pos, user_placed[i][0]))
                for i in range(len(user_placed))
                if i != root_idx
            ],
            key=lambda x: -x[1],
        )
        connected = {root_idx}

        for o_idx, (other_idx, _) in enumerate(others):
            pos_o, asp_o = user_placed[other_idx]

            if progress_cb:
                sub_frac = root_frac + root_span * (
                    o_idx / max(1, len(others))
                )
                progress_cb(sub_frac, f"AllOrders: connecting {asp_o}")

            best_branch = None
            best_branch_score = (
                float("inf"),
                float("inf"),
                float("inf"),
            )

            for conn_idx in connected:
                pos_c, asp_c = user_placed[conn_idx]
                branch = _find_best_edge(
                    temp_grid,
                    pos_o,
                    asp_o,
                    pos_c,
                    asp_c,
                    weights,
                    extra_slack,
                    existing_branch_paths=branch_paths,
                )
                if branch:
                    score = (
                        branch["count"],
                        branch["weight"],
                        branch.get("straightness", 0),
                    )
                    if score < best_branch_score:
                        best_branch_score = score
                        best_branch = branch

            nearby = _get_nearby_targets(temp_grid, pos_o)
            for pos_f, asp_f in nearby:
                branch = _find_best_edge(
                    temp_grid,
                    pos_o,
                    asp_o,
                    pos_f,
                    asp_f,
                    weights,
                    extra_slack,
                    existing_branch_paths=branch_paths,
                )
                if branch:
                    score = (
                        branch["count"],
                        branch["weight"],
                        branch.get("straightness", 0),
                    )
                    if score < best_branch_score:
                        best_branch_score = score
                        best_branch = branch

            if best_branch is None:
                success = False
                break

            branch_paths.append(best_branch["tile_path"])
            edges_used.append(best_branch)

            for pos, asp in best_branch["placements"]:
                if temp_grid[pos].get("aspect") is None:
                    temp_grid[pos]["aspect"] = asp
                    temp_grid[pos]["player_placed"] = False
                    all_placements.append((pos, asp))

            connected.add(other_idx)

        if success and are_all_aspects_connected(temp_grid):
            score = (
                len(all_placements),
                sum(weights.get(a, 10) for _, a in all_placements),
            )
            if score < best_score:
                best_score = score
                best_result = all_placements
                best_edges = edges_used

    return best_result, best_edges


# ============================================================
# Main solver — adaptive slack + early exit
# ============================================================

_last_solve_details = {
    "strategy": None,
    "edges": [],
    "placements": [],
    "user_placed": [],
}


def get_last_solve_details():
    return _last_solve_details


def _score_placements(placements, weights):
    return (
        len(placements),
        sum(weights.get(a, 10) for _, a in placements),
    )


def solve_with_spine_strategy(
    grid,
    prefer_ordo=True,
    extra_slack=6,
    progress_cb=None,
):
    """
    """
    global _last_solve_details

    def _progress(frac, msg=""):
        if progress_cb:
            try:
                progress_cb(frac, msg)
            except Exception:
                pass

    clear_chain_cache()

    full_user_placed = get_user_placed(grid)
    if len(full_user_placed) < 2:
        _last_solve_details = {
            "strategy": None,
            "edges": [],
            "placements": [],
            "user_placed": full_user_placed,
        }
        return []

    if are_all_aspects_connected(grid):
        _last_solve_details = {
            "strategy": "AlreadyConnected",
            "edges": [],
            "placements": [],
            "user_placed": full_user_placed,
        }
        return []

    ring_count = grid_ring_count(grid)
    edge_user_placed = [
        (pos, asp)
        for (pos, asp) in full_user_placed
        if is_edge_position(grid, pos, ring_count)
    ]

    if len(edge_user_placed) >= 2:
        user_placed = edge_user_placed
    else:
        user_placed = full_user_placed

    weights = calculate_aspect_weights(prefer_ordo=prefer_ordo)
    use_all_orders = len(user_placed) <= 5

    best_placements = None
    best_edges = None
    best_score = (float("inf"), float("inf"))
    best_strategy = None

    slack_levels = [2, 4, extra_slack]
    seen_slacks = set()
    unique_slacks = []
    for s in slack_levels:
        if s not in seen_slacks:
            seen_slacks.add(s)
            unique_slacks.append(s)
    slack_levels = unique_slacks

    for slack_idx, current_slack in enumerate(slack_levels):
        slack_frac_base = slack_idx / len(slack_levels)
        slack_frac_span = 1.0 / len(slack_levels)

        if slack_idx > 0:
            print(f"\n[Solver] Increasing slack to {current_slack}...")
            _progress(
                slack_frac_base,
                f"Retrying with slack {current_slack}...",
            )

        if use_all_orders:
            mst_base = slack_frac_base
            mst_span = slack_frac_span * 0.33
            spine_base = slack_frac_base + slack_frac_span * 0.33
            spine_span = slack_frac_span * 0.34
            order_base = slack_frac_base + slack_frac_span * 0.67
            order_span = slack_frac_span * 0.33
        else:
            mst_base = slack_frac_base
            mst_span = slack_frac_span * 0.50
            spine_base = slack_frac_base + slack_frac_span * 0.50
            spine_span = slack_frac_span * 0.50
            order_base = 0.0
            order_span = 0.0

        # ── MST ────────────────────────────────────────────────────────
        _progress(mst_base, "MST: building edges...")
        if slack_idx == 0:
            print("\n[Solver] Trying MST strategy...")

        result, edges = _try_mst_strategy(
            grid,
            user_placed,
            weights,
            current_slack,
            progress_cb=lambda f, m: _progress(f, m),
            base=mst_base,
            span=mst_span,
        )
        if result is not None:
            score = _score_placements(result, weights)
            if slack_idx == 0:
                print(
                    f"[MST] Result: {score[0]} placements, weight {score[1]}"
                )
            if score < best_score:
                best_score = score
                best_placements = result
                best_edges = edges
                best_strategy = "MST"

            if best_score[1] == 0:
                _progress(1.0, "Done!")
                break

        # ── Spine ───────────────────────────────────────────────────────
        _progress(spine_base, "Spine: trying pairs...")
        if slack_idx == 0:
            print("\n[Solver] Trying Spine strategy (all pairs)...")

        result, edges = _try_spine_strategy(
            grid,
            user_placed,
            weights,
            current_slack,
            progress_cb=lambda f, m: _progress(f, m),
            base=spine_base,
            span=spine_span,
        )
        if result is not None:
            score = _score_placements(result, weights)
            if slack_idx == 0:
                print(
                    f"[Spine] Result: {score[0]} placements, weight {score[1]}"
                )
            if score < best_score:
                best_score = score
                best_placements = result
                best_edges = edges
                best_strategy = "Spine"

            if best_score[1] == 0:
                _progress(1.0, "Done!")
                break

        # ── AllOrders ─────────────────────────────────────────────────
        if use_all_orders:
            _progress(order_base, "AllOrders: trying orderings...")
            if slack_idx == 0:
                print("\n[Solver] Trying AllOrders strategy...")

            result, edges = _try_all_orderings(
                grid,
                user_placed,
                weights,
                current_slack,
                progress_cb=lambda f, m: _progress(f, m),
                base=order_base,
                span=order_span,
            )
            if result is not None:
                score = _score_placements(result, weights)
                if slack_idx == 0:
                    print(
                        f"[AllOrders] Result: {score[0]} placements, "
                        f"weight {score[1]}"
                    )
                if score < best_score:
                    best_score = score
                    best_placements = result
                    best_edges = edges
                    best_strategy = "AllOrders"

                if best_score[1] == 0:
                    _progress(1.0, "Done!")
                    break

        if best_placements is not None:
            break

    _progress(1.0, "Done!")

    _last_solve_details = {
        "strategy": best_strategy,
        "edges": best_edges or [],
        "placements": best_placements or [],
        "user_placed": full_user_placed,
    }

    if best_strategy:
        print(
            f"\n[Solver] *** Best: {best_strategy} — "
            f"{best_score[0]} placements, weight {best_score[1]} ***\n"
        )

    return best_placements


def solve_mst(grid, prefer_ordo=True, extra_slack=6, progress_cb=None):
    """
    """
    return solve_with_spine_strategy(
        grid,
        prefer_ordo,
        extra_slack,
        progress_cb=progress_cb,
    )


def apply_placements(grid, placements):
    """
    """
    for pos, asp in placements:
        grid[pos]["aspect"] = asp
        grid[pos]["player_placed"] = False
