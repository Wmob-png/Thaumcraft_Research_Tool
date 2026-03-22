# solver_paths.py
"""
"""

from collections import deque
from heapq import heappush, heappop

from solver_core.solver_board import get_neighbors, hex_distance


# ============================================================
# Path utilities (geometry / scoring)
# ============================================================

def _path_straightness(tile_path):
    """
    """
    if len(tile_path) < 3:
        return 0
    changes = 0
    prev_dir = (
        tile_path[1][0] - tile_path[0][0],
        tile_path[1][1] - tile_path[0][1],
    )
    for k in range(2, len(tile_path)):
        curr_dir = (
            tile_path[k][0] - tile_path[k - 1][0],
            tile_path[k][1] - tile_path[k - 1][1],
        )
        if curr_dir != prev_dir:
            changes += 1
        prev_dir = curr_dir
    return changes


def _path_direction_signature(tile_path):
    """
    """
    if len(tile_path) < 2:
        return ()
    return tuple(
        (tile_path[i + 1][0] - tile_path[i][0],
         tile_path[i + 1][1] - tile_path[i][1])
        for i in range(len(tile_path) - 1)
    )


# ============================================================
# Board path search — fast BFS
# ============================================================

def find_path_of_length(grid, start, end, length):
    """
    """
    if length < 2:
        return None
    if length == 2:
        if end in get_neighbors(start):
            return [start, end]
        return None

    queue = deque([(start, 1, (start,))])
    seen = {(start, 1)}

    while queue:
        pos, steps, path_positions = queue.popleft()

        if steps == length:
            if pos == end:
                return list(path_positions)
            continue

        for nbr in get_neighbors(pos):
            if nbr not in grid:
                continue
            cell = grid[nbr]
            if cell.get("void", False):
                continue
            if cell.get("aspect") is not None and nbr != end:
                continue
            if nbr in path_positions:
                continue

            next_state = (nbr, steps + 1)
            if next_state in seen:
                continue
            seen.add(next_state)

            queue.append((nbr, steps + 1, path_positions + (nbr,)))

    return None


# ============================================================
# Board path search — straightest (Dijkstra on direction changes)
# ============================================================

def _find_straightest_path(grid, start, end, length):
    """
    """
    if length < 2:
        return None
    if length == 2:
        if end in get_neighbors(start):
            return [start, end]
        return None

    init_state = (start, 1, None)
    parent = {init_state: None}
    best_cost = {}
    best_result = None
    best_changes = float("inf")
    tiebreak = 0
    heap = [(0, 0, 1, start, None)]
    MAX_HEAP = 50_000

    while heap:
        if len(heap) > MAX_HEAP:
            break

        changes, _, steps, pos, prev_dir = heappop(heap)

        if changes > best_changes:
            continue

        state = (pos, steps, prev_dir)

        if steps == length:
            if pos == end and changes <= best_changes:
                path = []
                s = state
                while s is not None:
                    path.append(s[0])
                    s = parent.get(s)
                best_result = path[::-1]
                best_changes = changes
            continue

        if state in best_cost and best_cost[state] <= changes:
            continue
        best_cost[state] = changes

        remaining = length - steps

        for nbr in get_neighbors(pos):
            if nbr not in grid:
                continue
            cell = grid[nbr]
            if cell.get("void", False):
                continue
            if cell.get("aspect") is not None and nbr != end:
                continue
            if remaining == 1 and nbr != end:
                continue

            curr_dir = (nbr[0] - pos[0], nbr[1] - pos[1])
            new_changes = changes + (
                1 if prev_dir is not None and curr_dir != prev_dir else 0
            )

            if new_changes > best_changes:
                continue

            next_state = (nbr, steps + 1, curr_dir)
            if next_state in best_cost and best_cost[next_state] <= new_changes:
                continue

            in_path = False
            s = state
            depth = 0
            while s is not None and depth < length:
                if s[0] == nbr:
                    in_path = True
                    break
                s = parent.get(s)
                depth += 1
            if in_path:
                continue

            tiebreak += 1
            parent[next_state] = state
            heappush(heap, (new_changes, tiebreak, steps + 1, nbr, curr_dir))

    if best_result is None:
        best_result = find_path_of_length(grid, start, end, length)

    return best_result