"""
Thaumcraft Aspect Solver
"""

from .types import Pos, Aspect, Placement, SolveResult, SearchStats
from .hex import get_neighbors, hex_distance, is_edge_position, grid_ring_count
from .aspects import (
    ASPECT_GRAPH,
    ASPECT_WEIGHTS,
    ASPECT_TIERS,
    get_graph,
    calculate_aspect_weights,
    can_connect,
    get_neighbors_of,
)
from .state import SolverState
from .heuristics import combined_heuristic
from .search import a_star, SearchResult, is_io_chaining_enabled
from .solver import (
    solve,
    solve_with_center_priority,
    clear_solver_placements,
    is_board_solved,
    are_all_aspects_connected,
    get_user_placed_positions,
    get_solve_stats,
    calculate_solve_rating,
)
from .debug import debug_output_board, debug_output_solve_result

__all__ = [
    'Pos',
    'Aspect',
    'Placement',
    'SolveResult',
    'SearchStats',
    'get_neighbors',
    'hex_distance',
    'is_edge_position',
    'grid_ring_count',
    'ASPECT_GRAPH',
    'ASPECT_WEIGHTS',
    'ASPECT_TIERS',
    'get_graph',
    'calculate_aspect_weights',
    'can_connect',
    'get_neighbors_of',
    'SolverState',
    'combined_heuristic',
    'a_star',
    'SearchResult',
    'is_io_chaining_enabled',
    'solve',
    'solve_with_center_priority',
    'clear_solver_placements',
    'is_board_solved',
    'are_all_aspects_connected',
    'get_user_placed_positions',
    'get_solve_stats',
    'calculate_solve_rating',
    'debug_output_board',
    'debug_output_solve_result',
]
