from typing import Any, Dict, List, Tuple

Pos = Tuple[int, int]

DIRECTIONS: Tuple[Pos, ...] = (
    (1, 0),
    (1, -1),
    (0, -1),
    (-1, 0),
    (-1, 1),
    (0, 1),
)


def get_neighbors(pos: Pos) -> List[Pos]:
    q, r = pos
    return [(q + dq, r + dr) for dq, dr in DIRECTIONS]


def hex_distance(a: Pos, b: Pos) -> int:
    dq = a[0] - b[0]
    dr = a[1] - b[1]
    ds = -dq - dr
    return (abs(dq) + abs(dr) + abs(ds)) // 2


def grid_ring_count(grid: Dict[Pos, Any]) -> int:
    max_ring = 0
    for q, r in grid.keys():
        s = -q - r
        max_ring = max(max_ring, abs(q), abs(r), abs(s))
    return max_ring


def is_edge_position(grid: Dict[Pos, Any], pos: Pos, ring_count: int) -> bool:
    q, r = pos
    s = -q - r
    return abs(q) == ring_count or abs(r) == ring_count or abs(s) == ring_count
