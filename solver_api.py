# solver_api.py
"""
"""

from solver_core.solver_board import (
    clear_solver_placements,
    get_user_placed,
    are_all_aspects_connected,
)
from solver_core.solver_graph import (
    ASPECT_GRAPH,
    ASPECT_WEIGHTS,
    ASPECT_TIERS,
    calculate_aspect_weights,
)
from solver_core.solver_strategies import (
    solve_mst,
    get_last_solve_details,
)


# ============================================================
# Rating
# ============================================================

def calculate_solve_rating(placements, prefer_oi=True):
    """
    """
    if not placements:
        return 0, "S"
    weights = calculate_aspect_weights(prefer_oi)
    total_weight = sum(weights.get(a, 10) for _, a in placements)
    for threshold, grade in [
        (4, "S"),
        (10, "A"),
        (20, "B"),
        (35, "C"),
        (50, "D"),
    ]:
        if total_weight <= threshold:
            return total_weight, grade
    return total_weight, "F"


# ============================================================
# SolveResult container
# ============================================================

class SolveResult:
    __slots__ = (
        "success",
        "attempts",
        "placements",
        "errors",
        "warnings",
        "all_connected",
        "rating_score",
        "rating_grade",
        "stats",
    )

    def __init__(self):
        self.success = False
        self.attempts = 0
        self.placements = []
        self.errors = []
        self.warnings = []
        self.all_connected = False
        self.rating_score = 0
        self.rating_grade = ""
        self.stats = {}


# ============================================================
# GUI-friendly solve wrapper
# ============================================================

def solve_with_center_priority(
    grid,
    prefer_oi=True,
    callback=None,
    max_attempts=60,
    progress_cb=None,
):
    """
    """
    result = SolveResult()
    emit = (
        (lambda e, d=None: callback(e, d))
        if callback
        else (lambda e, d=None: None)
    )

    try:
        cleared = clear_solver_placements(grid)
        if cleared > 0:
            emit("cleared", {"count": cleared})

        user_placed = get_user_placed(grid)
        if len(user_placed) < 2:
            result.errors.append("Need at least 2 aspects")
            emit("error", result.errors[-1])
            return result

        if are_all_aspects_connected(grid):
            result.success = True
            result.all_connected = True
            result.rating_score = 0
            result.rating_grade = "S"
            result.attempts = 0
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

        emit(
            "start",
            {"placed_count": len(user_placed), "max_attempts": 1},
        )

        placements = solve_mst(
            grid,
            prefer_ordo=prefer_oi,
            extra_slack=6,
            progress_cb=progress_cb,
        )
        result.attempts = 1

        if placements is None:
            result.errors.append("No solution found")
            emit("error", result.errors[-1])
            return result

        for pos, asp in placements:
            grid[pos]["aspect"] = asp
            grid[pos]["player_placed"] = False
            result.placements.append((pos, asp))
            emit("place", {"pos": pos, "aspect": asp})

        result.all_connected = are_all_aspects_connected(grid)
        result.rating_score, result.rating_grade = calculate_solve_rating(
            result.placements,
            prefer_oi,
        )
        result.stats = {
            "orders_tried": 1,
            "best_count": len(result.placements),
            "best_weight": result.rating_score,
        }

        if result.all_connected:
            result.success = True
            emit(
                "complete",
                {
                    "total_placements": len(result.placements),
                    "attempts": result.attempts,
                    "rating_score": result.rating_score,
                    "rating_grade": result.rating_grade,
                },
            )
        else:
            result.errors.append("Solution incomplete")
            emit("error", result.errors[-1])

        return result

    except Exception as e:
        result.errors.append(str(e))
        emit("error", str(e))
        return result


# ============================================================
# Debug functions
# ============================================================

def debug_output_board(grid, ring_count=4):
    """
    """
    print("\n" + "=" * 70)
    print("BOARD STATE DEBUG OUTPUT")
    print("=" * 70)

    user_placed = []
    solver_placed = []

    for pos, cell in sorted(grid.items(), key=lambda x: (x[0][1], x[0][0])):
        if cell.get("void", False):
            continue
        asp = cell.get("aspect")
        if asp:
            if cell.get("player_placed", False):
                user_placed.append((pos, asp))
            else:
                solver_placed.append((pos, asp))

    print(f"\nUser-placed ({len(user_placed)}):")
    print("-" * 50)
    for pos, asp in user_placed:
        w = ASPECT_WEIGHTS.get(asp, 10)
        t = ASPECT_TIERS.get(asp, "?")
        print(f"  {pos!s:12} {asp:15} [weight: {w}, tier: {t}]")

    print(f"\nSolver-placed ({len(solver_placed)}):")
    print("-" * 50)
    for pos, asp in solver_placed:
        w = ASPECT_WEIGHTS.get(asp, 10)
        t = ASPECT_TIERS.get(asp, "?")
        print(f"  {pos!s:12} {asp:15} [weight: {w}, tier: {t}]")

    if solver_placed:
        counts = {}
        for _, asp in solver_placed:
            counts[asp] = counts.get(asp, 0) + 1
        print("\nAspect Usage Summary:")
        print("-" * 50)
        for asp, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            print(
                f"  {asp:15} {cnt}x "
                f"(weight: {ASPECT_WEIGHTS.get(asp, 10)})"
            )
        total = sum(ASPECT_WEIGHTS.get(a, 10) for _, a in solver_placed)
        print(f"\nTotal Weight: {total}")
        print(f"Total Placements: {len(solver_placed)}")

    print("=" * 70 + "\n")
    return {"user_placed": user_placed, "solver_placed": solver_placed}


def debug_output_solve_result(result):
    """
    """
    print("\n" + "=" * 70)
    print("SOLVE RESULT")
    print("=" * 70)
    print(f"Success:    {result.success}")
    print(f"Attempts:   {result.attempts}")
    print(f"Placements: {len(result.placements)}")
    print(f"Rating:     {result.rating_grade} (weight: {result.rating_score})")

    if result.stats:
        print("\nStats:")
        for k, v in result.stats.items():
            print(f"  {k}: {v}")

    if result.errors:
        print("\nErrors:", result.errors)

    details = get_last_solve_details()
    if details["strategy"]:
        print(f"\nStrategy Used: {details['strategy']}")

    if details["edges"]:
        print(f"\nConnections Made ({len(details['edges'])} edges):")
        print("-" * 70)

        for i, edge in enumerate(details["edges"], 1):
            from_pos = edge.get("from_pos", "?")
            from_asp = edge.get("from_asp", "?")
            to_pos = edge.get("to_pos", "?")
            to_asp = edge.get("to_asp", "?")
            tile_path = edge.get("tile_path", [])
            aspect_chain = edge.get("aspect_chain", [])
            count = edge.get("count", 0)
            weight = edge.get("weight", 0)
            straight = edge.get("straightness", 0)
            sym = edge.get("sym_penalty", 0.0)

            print(
                f"\n  Edge {i}: {from_asp} {from_pos} --> "
                f"{to_asp} {to_pos}"
            )
            print(
                f"          Placements: {count}, Weight: {weight}, "
                f"Straightness: {straight}, SymPenalty: {sym:.2f}"
            )

            if tile_path:
                print(
                    "          Tile Path:    "
                    + " -> ".join(str(p) for p in tile_path)
                )
            if aspect_chain:
                print(
                    "          Aspect Chain: "
                    + " -> ".join(aspect_chain)
                )

            if edge.get("placements"):
                print("          New Placements:")
                for pos, asp in edge["placements"]:
                    w = ASPECT_WEIGHTS.get(asp, 10)
                    print(f"            {pos} = {asp} (w:{w})")

    print("=" * 70 + "\n")


def debug_output_connections_simple():
    """
    """
    details = get_last_solve_details()
    if not details["strategy"]:
        print("[Debug] No solve data available")
        return

    print(f"\n=== SOLVE CONNECTIONS ({details['strategy']}) ===\n")

    if details["user_placed"]:
        print("User-placed aspects:")
        for pos, asp in details["user_placed"]:
            print(f"  * {asp} at {pos}")

    if details["edges"]:
        print(f"\nConnections ({len(details['edges'])}):\n")
        for i, edge in enumerate(details["edges"], 1):
            print(
                f"  {i}. {edge.get('from_asp')}@{edge.get('from_pos')} "
                f"--> {edge.get('to_asp')}@{edge.get('to_pos')}"
            )
            chain = edge.get("aspect_chain", [])
            if chain:
                print(f"     Chain:        {' - '.join(chain)}")
            print(
                "     Straightness: "
                f"{edge.get('straightness', 0)}, "
                f"SymPenalty: {edge.get('sym_penalty', 0.0):.2f}"
            )
            print()

    total_placements = len(details["placements"])
    total_weight = sum(
        ASPECT_WEIGHTS.get(a, 10) for _, a in details["placements"]
    )
    print(f"Total: {total_placements} placements, weight {total_weight}\n")