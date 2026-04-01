from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Set, Tuple

from .aspects import calculate_aspect_weights, can_connect
from .heuristics import combined_heuristic
from .hex import get_neighbors
from .search import a_star
from .state import SolverState
from .types import Aspect, Pos, SolveResult


def solve(
    grid: Dict[Pos, dict],
    prefer_ordo: bool = True,
    io_chaining_enabled: bool = False,
    max_states: int = 100_000,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> SolveResult:
    result = SolveResult()
    result.prefer_oi = prefer_ordo

    state = SolverState.from_grid(
        grid,
        prefer_ordo=prefer_ordo,
        io_chaining_enabled=io_chaining_enabled,
    )

    if state.is_connected and len(state.user_aspects) >= 2:
        result.success = True
        result.all_connected = True
        result.rating_score = 0
        result.rating_grade = "S"
        result.stats = {"already_connected": True}
        return result

    if len(state.user_aspects) < 2:
        result.errors.append("Need at least 2 user-placed aspects")
        return result

    search_result = a_star(
        initial=state,
        heuristic=combined_heuristic,
        max_states=max_states,
        progress_cb=progress_cb,
    )

    if not search_result.found:
        result.errors.append("No solution found")
        result.stats = {"states_explored": search_result.stats.states_explored}
        return result

    result.success = True
    result.all_connected = True
    result.placements = search_result.placements
    result.attempts = 1

    weights = calculate_aspect_weights(prefer_ordo)
    total_weight = sum(weights.get(asp, 10) for _, asp in result.placements)
    result.rating_score = total_weight
    result.rating_grade = _compute_grade(total_weight)

    result.stats = {
        "states_explored": search_result.stats.states_explored,
        "states_pruned": search_result.stats.states_pruned,
        "max_frontier": search_result.stats.max_frontier_size,
    }

    return result


def solve_with_center_priority(
    grid: Dict[Pos, dict],
    prefer_oi: bool = True,
    io_chaining_enabled: bool = False,
    callback: Optional[Callable] = None,
    max_attempts: int = 60,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> SolveResult:
    emit = callback if callback else lambda e, d=None: None

    cleared = clear_solver_placements(grid)
    if cleared > 0:
        emit("cleared", {"count": cleared})

    user_placed = get_user_placed_positions(grid)
    if len(user_placed) < 2:
        result = SolveResult()
        result.errors.append("Need at least 2 aspects")
        emit("error", result.errors[-1])
        return result

    if are_all_aspects_connected(grid):
        result = SolveResult()
        result.success = True
        result.all_connected = True
        result.rating_score = 0
        result.rating_grade = "S"
        emit(
            "complete",
            {
                "total_placements": 0,
                "attempts": 0,
                "rating_score": 0,
                "rating_grade": "S",
            },
        )
        return result

    emit("start", {"placed_count": len(user_placed), "max_attempts": 1})

    result = solve(
        grid,
        prefer_ordo=prefer_oi,
        io_chaining_enabled=io_chaining_enabled,
        progress_cb=progress_cb,
    )

    if not result.success:
        emit("error", result.errors[0] if result.errors else "Unknown error")
        return result

    for pos, asp in result.placements:
        grid[pos]["aspect"] = asp
        grid[pos]["player_placed"] = False
        emit("place", {"pos": pos, "aspect": asp})

    emit(
        "complete",
        {
            "total_placements": len(result.placements),
            "attempts": result.attempts,
            "rating_score": result.rating_score,
            "rating_grade": result.rating_grade,
        },
    )

    return result


def _compute_grade(weight: float) -> str:
    for threshold, grade in [(4, "S"), (10, "A"), (20, "B"), (35, "C"), (50, "D")]:
        if weight <= threshold:
            return grade
    return "F"


def clear_solver_placements(grid: Dict[Pos, dict]) -> int:
    cleared = 0
    for cell in grid.values():
        if cell.get("aspect") and not cell.get("player_placed", False):
            cell["aspect"] = None
            cleared += 1
    return cleared


def is_board_solved(grid: Dict[Pos, dict]) -> bool:
    user_positions = get_user_placed_positions(grid)
    if len(user_positions) < 2:
        return False
    return are_all_aspects_connected(grid)


def are_all_aspects_connected(grid: Dict[Pos, dict]) -> bool:
    aspect_positions = [
        pos for pos, cell in grid.items() if cell.get("aspect") and not cell.get("void", False)
    ]

    if len(aspect_positions) <= 1:
        return True

    start = aspect_positions[0]
    visited = {start}
    queue = [start]

    while queue:
        pos = queue.pop(0)
        asp = grid[pos]["aspect"]

        for nbr in get_neighbors(pos):
            if nbr in visited or nbr not in grid:
                continue
            cell = grid[nbr]
            if cell.get("void", False):
                continue
            nbr_asp = cell.get("aspect")
            if nbr_asp and can_connect(asp, nbr_asp):
                visited.add(nbr)
                queue.append(nbr)

    return len(visited) == len(aspect_positions)


def get_user_placed_positions(grid: Dict[Pos, dict]) -> Set[Pos]:
    return {
        pos
        for pos, cell in grid.items()
        if cell.get("aspect") and cell.get("player_placed", False) and not cell.get("void", False)
    }


def get_solve_stats(grid: Dict[Pos, dict]) -> Dict[str, Any]:
    total = len(grid)
    voided = sum(1 for c in grid.values() if c.get("void", False))
    filled = sum(1 for c in grid.values() if c.get("aspect") and not c.get("void", False))
    empty = total - voided - filled

    return {
        "total": total,
        "voided": voided,
        "filled": filled,
        "empty": empty,
        "fill_percent": (filled / (total - voided) * 100) if (total - voided) > 0 else 0,
    }


def calculate_solve_rating(placements: List[Tuple[Pos, Aspect]], prefer_oi: bool = True) -> Tuple[float, str]:
    if not placements:
        return 0, "S"

    weights = calculate_aspect_weights(prefer_oi)
    total_weight = sum(weights.get(asp, 10) for _, asp in placements)
    grade = _compute_grade(total_weight)

    return total_weight, grade