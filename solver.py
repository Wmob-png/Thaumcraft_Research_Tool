# solver.py
"""
"""

# ============================================================
# Graph / weights / chains
# ============================================================

from solver_core.solver_graph import (
    ASPECT_GRAPH,
    ASPECT_TIERS,
    ASPECT_WEIGHTS,
    calculate_aspect_weights,
    clear_chain_cache,
    find_aspect_chain_exact,
)

# ============================================================
# Board / grid utilities
# ============================================================

from solver_core.solver_board import (
    HEX_DIRECTIONS,
    get_neighbors,
    hex_distance,
    can_aspects_connect,
    is_edge_position,
    are_all_aspects_connected,
    get_user_placed,
    get_user_placed_positions,
    is_board_solved,
    clear_solver_placements,
    get_solve_stats,
)

# ============================================================
# Tile pathfinding
# ============================================================

from solver_core.solver_paths import (
    find_path_of_length,
    _find_straightest_path,
    _path_straightness,
    _path_direction_signature,
)

# ============================================================
# Edge construction / MST
# ============================================================

from solver_core.solver_edges import (
    _get_nearby_targets,
    _find_best_edge,
    build_pairwise_edges,
    UnionFind,
    build_mst,
    merge_mst_placements,
)

# ============================================================
# Strategies / main solver
# ============================================================

from solver_core.solver_strategies import (
    _try_mst_strategy,
    _try_spine_with_pair,
    _try_spine_strategy,
    _try_all_orderings,
    solve_with_spine_strategy,
    solve_mst,
    apply_placements,
    get_last_solve_details,
)

# ============================================================
# GUI-facing API / rating / debug
# ============================================================

from solver_core.solver_api import (
    calculate_solve_rating,
    SolveResult,
    solve_with_center_priority,
    debug_output_board,
    debug_output_solve_result,
    debug_output_connections_simple,
)

__all__ = [
    # Graph / weights
    "ASPECT_GRAPH",
    "ASPECT_TIERS",
    "ASPECT_WEIGHTS",
    "calculate_aspect_weights",
    "clear_chain_cache",
    "find_aspect_chain_exact",

    # Board / grid
    "HEX_DIRECTIONS",
    "get_neighbors",
    "hex_distance",
    "can_aspects_connect",
    "is_edge_position",
    "are_all_aspects_connected",
    "get_user_placed",
    "get_user_placed_positions",
    "is_board_solved",
    "clear_solver_placements",
    "get_solve_stats",

    # Paths
    "find_path_of_length",
    "_find_straightest_path",
    "_path_straightness",
    "_path_direction_signature",

    # Edges / MST
    "_get_nearby_targets",
    "_find_best_edge",
    "build_pairwise_edges",
    "UnionFind",
    "build_mst",
    "merge_mst_placements",

    # Strategies
    "_try_mst_strategy",
    "_try_spine_with_pair",
    "_try_spine_strategy",
    "_try_all_orderings",
    "solve_with_spine_strategy",
    "solve_mst",
    "apply_placements",
    "get_last_solve_details",

    # API / rating / debug
    "calculate_solve_rating",
    "SolveResult",
    "solve_with_center_priority",
    "debug_output_board",
    "debug_output_solve_result",
    "debug_output_connections_simple",
]