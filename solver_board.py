# solver_board.py
"""
"""

from collections import deque

from solver_core.solver_graph import ASPECT_GRAPH, _GRAPH_FROZEN, _EMPTY_FSET

# ============================================================
# Hex utilities
# ============================================================

HEX_DIRECTIONS = (
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1)
)


def get_neighbors(pos):
    q, r = pos
    return [(q + dq, r + dr) for dq, dr in HEX_DIRECTIONS]


def hex_distance(a, b):
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    return max(abs(dq), abs(dr), abs(dq + dr))


def can_aspects_connect(a, b):
    if a is None or b is None:
        return True
    return b in _GRAPH_FROZEN.get(a, _EMPTY_FSET)


def is_edge_position(grid, pos, ring_count):
    q, r = pos
    s = -q - r
    return (
        abs(q) == ring_count
        or abs(r) == ring_count
        or abs(s) == ring_count
    )


def grid_ring_count(grid):
    """
    """
    max_ring = 0
    for (q, r) in grid.keys():
        s = -q - r
        max_ring = max(max_ring, abs(q), abs(r), abs(s))
    return max_ring


# ============================================================
# Board connectivity
# ============================================================

def are_all_aspects_connected(grid):
    """
    """
    aspect_positions = [
        pos for pos, cell in grid.items()
        if cell.get("aspect") and not cell.get("void", False)
    ]

    if not aspect_positions:
        return True
    if len(aspect_positions) == 1:
        return True

    start = aspect_positions[0]
    seen = {start}
    queue = deque([start])

    while queue:
        pos = queue.popleft()
        asp = grid[pos]["aspect"]
        nbr_aspects = _GRAPH_FROZEN.get(asp, _EMPTY_FSET)

        for nbr in get_neighbors(pos):
            if nbr in seen or nbr not in grid:
                continue
            cell = grid[nbr]
            if cell.get("void", False):
                continue
            other = cell.get("aspect")
            if not other:
                continue
            if other in nbr_aspects:
                seen.add(nbr)
                queue.append(nbr)

    return len(seen) == len(aspect_positions)


def compute_aspect_components(grid):
    """
    """
    positions = [
        pos for pos, cell in grid.items()
        if cell.get("aspect") and not cell.get("void", False)
    ]

    comp_index = {}
    comp_id = 0

    for start in positions:
        if start in comp_index:
            continue

        queue = deque([start])
        comp_index[start] = comp_id

        while queue:
            pos = queue.popleft()
            asp = grid[pos]["aspect"]
            nbr_aspects = _GRAPH_FROZEN.get(asp, _EMPTY_FSET)

            for nbr in get_neighbors(pos):
                if nbr not in grid or nbr in comp_index:
                    continue
                cell = grid[nbr]
                if cell.get("void", False):
                    continue
                other = cell.get("aspect")
                if not other:
                    continue
                if other in nbr_aspects:
                    comp_index[nbr] = comp_id
                    queue.append(nbr)

        comp_id += 1

    return comp_index


# ============================================================
# Board state helpers
# ============================================================

def get_user_placed(grid):
    """
    """
    return [
        (pos, cell["aspect"])
        for pos, cell in grid.items()
        if cell.get("aspect")
        and cell.get("player_placed", False)
        and not cell.get("void", False)
    ]


def get_user_placed_positions(grid):
    """
    """
    return {
        pos for pos, cell in grid.items()
        if cell.get("aspect")
        and cell.get("player_placed", False)
        and not cell.get("void", False)
    }


def is_board_solved(grid):
    """
    """
    return (
        len(get_user_placed_positions(grid)) >= 2
        and are_all_aspects_connected(grid)
    )


def clear_solver_placements(grid):
    """
    """
    cleared = 0
    for cell in grid.values():
        if cell.get("aspect") and not cell.get("player_placed", False):
            cell["aspect"] = None
            cleared += 1
    return cleared


def get_solve_stats(grid):
    """
    """
    total = len(grid)
    voided = sum(1 for c in grid.values() if c.get("void", False))
    filled = sum(
        1 for c in grid.values()
        if c.get("aspect") and not c.get("void", False)
    )
    empty = total - voided - filled
    return {
        "total": total,
        "voided": voided,
        "filled": filled,
        "empty": empty,
        "fill_percent": (
            (filled / (total - voided) * 100) if (total - voided) > 0 else 0
        ),
    }