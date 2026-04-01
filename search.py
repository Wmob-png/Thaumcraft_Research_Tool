from __future__ import annotations

import os
import random
import sys
from collections import deque
from dataclasses import dataclass
from typing import Callable, Dict, FrozenSet, List, Optional, Set, Tuple

from .aspects import ASPECT_GRAPH, ASPECT_TIERS, can_connect, calculate_aspect_weights, get_neighbors_of
from .hex import get_neighbors, hex_distance
from .state import SolverState
from .types import Aspect, Placement, Pos, SearchStats

_parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _parent_dir not in sys.path:
    sys.path.insert(0, _parent_dir)

from aspects import PRIMALS, aspect_parents

DEBUG = True


def debug_log(msg: str):
    if DEBUG:
        print(f"[DEBUG] {msg}")


_ASPECT_CHAIN_CACHE: Dict[Tuple[Aspect, Aspect, int, bool], List[List[Aspect]]] = {}
_PATH_CANDIDATE_CACHE: Dict[Tuple, List[List[Tuple[Pos, Aspect]]]] = {}


def clear_search_caches():
    _ASPECT_CHAIN_CACHE.clear()
    _PATH_CANDIDATE_CACHE.clear()


def is_io_chaining_enabled(state: SolverState) -> bool:
    for attr in ("io_chaining_enabled", "enable_io_chaining", "io_chaining"):
        if hasattr(state, attr):
            try:
                return bool(getattr(state, attr))
            except Exception:
                pass
    return False


def aspect_bias_cost(asp: Aspect, weights: Dict[Aspect, float], io_chaining: bool) -> float:
    base = weights.get(asp, 10.0) + ASPECT_TIERS.get(asp, 0) * 1.5

    if not io_chaining:
        return base

    if asp == "Instrumentum":
        return -8.0
    if asp == "Ordo":
        return -5.0
    if asp == "Motus":
        return base - 1.5
    if asp == "Vacuos":
        return base - 1.0
    if asp == "Lux":
        return base - 0.75

    return base


def sort_aspects_for_choice(
    aspects: Set[Aspect],
    weights: Dict[Aspect, float],
    io_chaining: bool,
) -> List[Aspect]:
    return sorted(aspects, key=lambda a: (aspect_bias_cost(a, weights, io_chaining), a))


def canonical_placements_key(placements: Dict[Pos, Aspect]) -> Tuple[Tuple[Pos, Aspect], ...]:
    return tuple(sorted(placements.items()))


def score_solution(
    placements: List[Tuple[Pos, Aspect]],
    weights: Dict[Aspect, float],
) -> Tuple[int, float]:
    if not placements:
        return (0, 0.0)
    num = len(placements)
    total_weight = sum(weights.get(asp, 10.0) for _, asp in placements)
    tier_penalty = sum(ASPECT_TIERS.get(asp, 0) * 1.5 for _, asp in placements)
    return (num, total_weight + tier_penalty)


def score_partial_path(
    result: List[Tuple[Pos, Aspect]],
    weights: Dict[Aspect, float],
    placements: Dict[Pos, Aspect],
    io_chaining: bool,
) -> Tuple[int, float, int]:
    if not result:
        return (0, 0.0, 0)

    total_weight = 0.0
    reuse_touch = 0
    for pos, asp in result:
        total_weight += aspect_bias_cost(asp, weights, io_chaining)
        for nbr in get_neighbors(pos):
            if nbr in placements:
                reuse_touch += 1

    if io_chaining:
        instrumentum_count = sum(1 for _, asp in result if asp == "Instrumentum")
        ordo_count = sum(1 for _, asp in result if asp == "Ordo")
        total_weight -= instrumentum_count * 4.0
        total_weight -= ordo_count * 2.0

    return (len(result), total_weight, -reuse_touch)


def get_aspect_parents(asp: Aspect) -> Set[Aspect]:
    if asp in PRIMALS:
        return set()
    return set(aspect_parents.get(asp, []))


@dataclass
class SearchResult:
    state: Optional[SolverState]
    stats: SearchStats

    @property
    def found(self) -> bool:
        return self.state is not None

    @property
    def placements(self):
        if self.state:
            return self.state.to_placement_list()
        return []


def find_all_geometric_paths(
    grid_positions: FrozenSet[Pos],
    void_positions: FrozenSet[Pos],
    start: Pos,
    end: Pos,
    blocked: Set[Pos] = None,
    max_extra: int = 4,
    max_paths: int = 40,
) -> List[List[Pos]]:
    if blocked is None:
        blocked = set()

    if start == end:
        return [[start]]

    shortest_length = None
    results: List[List[Pos]] = []

    queue = deque([(start, [start])])
    visited: Dict[Pos, int] = {start: 1}

    while queue:
        pos, path = queue.popleft()

        if shortest_length is not None and len(path) > shortest_length + max_extra:
            continue
        if len(results) >= max_paths:
            continue

        for nbr in get_neighbors(pos):
            if nbr == end:
                new_path = path + [nbr]
                if shortest_length is None:
                    shortest_length = len(new_path)
                if len(new_path) <= shortest_length + max_extra:
                    results.append(new_path)
                continue

            if nbr not in grid_positions or nbr in void_positions or nbr in blocked:
                continue

            new_len = len(path) + 1
            if nbr in visited and visited[nbr] <= new_len - 2:
                continue
            if nbr in path:
                continue
            if shortest_length is not None and new_len > shortest_length + max_extra:
                continue

            if nbr not in visited or new_len < visited[nbr]:
                visited[nbr] = new_len

            queue.append((nbr, path + [nbr]))

    results.sort(key=lambda p: (len(p), p))
    return results[:max_paths]


def find_aspect_path_bfs(
    start_asp: Aspect,
    end_asp: Aspect,
    max_length: int = 15,
) -> Optional[List[Aspect]]:
    if start_asp == end_asp:
        return [start_asp]
    if can_connect(start_asp, end_asp):
        return [start_asp, end_asp]

    queue = deque([(start_asp, [start_asp])])
    visited = {start_asp}

    while queue:
        current, path = queue.popleft()
        if len(path) >= max_length:
            continue
        for nbr in sorted(get_neighbors_of(current)):
            new_path = path + [nbr]
            if nbr == end_asp:
                return new_path
            if nbr in visited:
                continue
            visited.add(nbr)
            queue.append((nbr, new_path))
    return None


def enumerate_aspect_chains(
    start_asp: Aspect,
    end_asp: Aspect,
    length: int,
    weights: Dict[Aspect, float],
    io_chaining: bool,
    max_chains: int = 30,
) -> List[List[Aspect]]:
    cache_key = (start_asp, end_asp, length, io_chaining)
    cached = _ASPECT_CHAIN_CACHE.get(cache_key)
    if cached is not None:
        return cached[:max_chains]

    if length < 2:
        return []
    if length == 2:
        result = [[start_asp, end_asp]] if can_connect(start_asp, end_asp) else []
        _ASPECT_CHAIN_CACHE[cache_key] = result[:]
        return result[:max_chains]

    results: List[List[Aspect]] = []
    seen: Set[Tuple[Aspect, ...]] = set()

    pool: Set[Aspect] = {start_asp, end_asp}
    pool.update(get_neighbors_of(start_asp))
    pool.update(get_neighbors_of(end_asp))
    pool.update(get_aspect_parents(start_asp))
    pool.update(get_aspect_parents(end_asp))
    for a in list(pool):
        pool.update(get_neighbors_of(a))
        pool.update(get_aspect_parents(a))

    if io_chaining:
        pool.update({"Instrumentum", "Ordo"})

    ordered_pool = sort_aspects_for_choice(pool, weights, io_chaining)

    def endpoint_connectivity_bias(a: Aspect) -> int:
        score = 0
        if a == end_asp:
            score -= 100
        if can_connect(a, end_asp):
            score -= 20
        if get_neighbors_of(a) & get_neighbors_of(end_asp):
            score -= 8
        if io_chaining:
            if a == "Instrumentum":
                score -= 30
            elif a == "Ordo":
                score -= 15
        return score

    def dfs(chain: List[Aspect]):
        if len(results) >= max_chains:
            return

        if len(chain) == length:
            if chain[-1] == end_asp:
                tpl = tuple(chain)
                if tpl not in seen:
                    seen.add(tpl)
                    results.append(chain[:])
            return

        idx = len(chain)
        if idx == length - 1:
            if can_connect(chain[-1], end_asp):
                dfs(chain + [end_asp])
            return

        prev = chain[-1]
        next_set = get_neighbors_of(prev) & set(ordered_pool)

        next_candidates = sorted(
            next_set,
            key=lambda a: (
                endpoint_connectivity_bias(a),
                aspect_bias_cost(a, weights, io_chaining),
                a,
            ),
        )

        branch_limit = 14 if io_chaining else 10

        for nxt in next_candidates[:branch_limit]:
            dfs(chain + [nxt])

    dfs([start_asp])

    if len(results) < max_chains:
        bfs_path = find_aspect_path_bfs(start_asp, end_asp, max_length=length + 6)
        if bfs_path and len(bfs_path) <= length:
            queue = deque([bfs_path])
            seen_pad = {tuple(bfs_path)}

            while queue and len(results) < max_chains:
                cur = queue.popleft()

                if len(cur) == length:
                    tpl = tuple(cur)
                    if tpl not in seen and all(can_connect(cur[i], cur[i + 1]) for i in range(len(cur) - 1)):
                        seen.add(tpl)
                        results.append(cur)
                    continue

                if len(cur) > length:
                    continue

                expanded = False

                for i in range(len(cur) - 1):
                    a = cur[i]
                    b = cur[i + 1]
                    mids = sort_aspects_for_choice(get_neighbors_of(a) & get_neighbors_of(b), weights, io_chaining)

                    for mid in mids[: 6 if io_chaining else 4]:
                        nxt = cur[: i + 1] + [mid] + cur[i + 1 :]
                        tpl = tuple(nxt)
                        if tpl not in seen_pad and len(nxt) <= length:
                            seen_pad.add(tpl)
                            queue.append(nxt)
                            expanded = True

                if not expanded and len(cur) + 2 <= length:
                    for i in range(len(cur) - 1):
                        a = cur[i]
                        xs = sort_aspects_for_choice(get_neighbors_of(a), weights, io_chaining)
                        for x in xs[: 6 if io_chaining else 4]:
                            if can_connect(a, x) and can_connect(x, a):
                                nxt = cur[: i + 1] + [x, a] + cur[i + 1 :]
                                tpl = tuple(nxt)
                                if tpl not in seen_pad and len(nxt) <= length:
                                    seen_pad.add(tpl)
                                    queue.append(nxt)

    def chain_sort_key(chain: List[Aspect]):
        instrumentum_count = sum(1 for a in chain[1:-1] if a == "Instrumentum")
        ordo_count = sum(1 for a in chain[1:-1] if a == "Ordo")
        return (
            sum(aspect_bias_cost(a, weights, io_chaining) for a in chain[1:-1]),
            -instrumentum_count if io_chaining else 0,
            -ordo_count if io_chaining else 0,
            chain,
        )

    results.sort(key=chain_sort_key)

    _ASPECT_CHAIN_CACHE[cache_key] = results[:]
    return results[:max_chains]


def find_path_with_chain_candidates(
    grid_positions: FrozenSet[Pos],
    void_positions: FrozenSet[Pos],
    placements: Dict[Pos, Aspect],
    start_pos: Pos,
    start_asp: Aspect,
    end_pos: Pos,
    end_asp: Aspect,
    weights: Dict[Aspect, float],
    io_chaining: bool,
    allow_reuse: bool = True,
    max_extra_length: int = 5,
    max_geo_paths: int = 25,
    max_chains_per_len: int = 20,
    max_candidates: int = 12,
) -> List[List[Tuple[Pos, Aspect]]]:
    debug_log(f"find_path_with_chain_candidates: {start_asp}@{start_pos} -> {end_asp}@{end_pos}")

    cache_key = (
        canonical_placements_key(placements),
        start_pos,
        start_asp,
        end_pos,
        end_asp,
        io_chaining,
        allow_reuse,
        max_extra_length,
        max_geo_paths,
        max_chains_per_len,
        max_candidates,
    )
    cached = _PATH_CANDIDATE_CACHE.get(cache_key)
    if cached is not None:
        debug_log(f"  Cache hit: {len(cached)} candidates")
        return cached[:max_candidates]

    blocked = set() if allow_reuse else (set(placements.keys()) - {start_pos, end_pos})

    min_aspect_path = find_aspect_path_bfs(start_asp, end_asp, max_length=20)
    if min_aspect_path is None:
        debug_log(f"  No aspect path exists between {start_asp} and {end_asp}")
        _PATH_CANDIDATE_CACHE[cache_key] = []
        return []

    min_aspect_length = len(min_aspect_path)
    debug_log(f"  Minimum aspect chain length: {min_aspect_length} ({min_aspect_path})")

    geo_paths = find_all_geometric_paths(
        grid_positions,
        void_positions,
        start_pos,
        end_pos,
        blocked,
        max_extra=max_extra_length,
        max_paths=max_geo_paths,
    )

    if not geo_paths:
        debug_log("  No geometric paths found")
        _PATH_CANDIDATE_CACHE[cache_key] = []
        return []

    debug_log(f"  Found {len(geo_paths)} geometric paths (lengths: {[len(p) for p in geo_paths]})")

    seen_assignments: Set[Tuple[Tuple[Pos, Aspect], ...]] = set()
    best_by_positions: Dict[Tuple[Pos, ...], Tuple[Tuple[int, float, int], List[Tuple[Pos, Aspect]]]] = {}

    for geo_path in geo_paths:
        path_len = len(geo_path)
        if path_len < min_aspect_length:
            continue

        chains = enumerate_aspect_chains(
            start_asp,
            end_asp,
            path_len,
            weights,
            io_chaining,
            max_chains=max_chains_per_len,
        )
        if not chains:
            continue

        for chain in chains:
            result: List[Tuple[Pos, Aspect]] = []
            conflict = False

            for pos, asp in zip(geo_path, chain):
                existing = placements.get(pos)
                if existing is not None and existing != asp:
                    conflict = True
                    break
                if existing is None:
                    result.append((pos, asp))

            if conflict:
                continue

            assign_key = tuple(sorted(result))
            if assign_key in seen_assignments:
                continue
            seen_assignments.add(assign_key)

            score = score_partial_path(result, weights, placements, io_chaining)
            pos_key = tuple(sorted(pos for pos, _ in result))

            prev = best_by_positions.get(pos_key)
            if prev is None or score < prev[0]:
                best_by_positions[pos_key] = (score, result)

    all_candidates = list(best_by_positions.values())
    all_candidates.sort(key=lambda x: x[0])

    trimmed = [res for _, res in all_candidates[:max_candidates]]
    _PATH_CANDIDATE_CACHE[cache_key] = trimmed[:]

    debug_log(f"  Valid path candidates: {len(all_candidates)}")
    for i, cand in enumerate(trimmed[:5]):
        debug_log(f"    cand[{i}] => {cand} score={score_partial_path(cand, weights, placements, io_chaining)}")

    return trimmed


def find_path_with_chain(
    grid_positions: FrozenSet[Pos],
    void_positions: FrozenSet[Pos],
    placements: Dict[Pos, Aspect],
    start_pos: Pos,
    start_asp: Aspect,
    end_pos: Pos,
    end_asp: Aspect,
    weights: Dict[Aspect, float],
    io_chaining: bool,
    allow_reuse: bool = True,
    max_extra_length: int = 5,
) -> Optional[List[Tuple[Pos, Aspect]]]:
    cands = find_path_with_chain_candidates(
        grid_positions,
        void_positions,
        placements,
        start_pos,
        start_asp,
        end_pos,
        end_asp,
        weights,
        io_chaining=io_chaining,
        allow_reuse=allow_reuse,
        max_extra_length=max_extra_length,
        max_candidates=1,
    )
    return cands[0] if cands else None


def find_network_solution(
    state: SolverState,
    weights: Dict[Aspect, float],
) -> Optional[List[Tuple[Pos, Aspect]]]:
    debug_log("=== NETWORK STRATEGY (Backtracking Multi-order) ===")
    user_aspects = list(state.user_aspects)
    io_chaining = is_io_chaining_enabled(state)
    debug_log(f"User aspects: {user_aspects}")
    debug_log(f"IO chaining enabled: {io_chaining}")

    if len(user_aspects) < 2:
        return None

    pairs_base = []
    for i in range(len(user_aspects)):
        for j in range(i + 1, len(user_aspects)):
            pos_a, asp_a = user_aspects[i]
            pos_b, asp_b = user_aspects[j]
            dist = hex_distance(pos_a, pos_b)
            pairs_base.append((dist, i, j, pos_a, asp_a, pos_b, asp_b))

    rng = random.Random(0)
    closest = sorted(pairs_base, key=lambda x: (x[0], x[1], x[2]))
    farthest = sorted(pairs_base, key=lambda x: (-x[0], x[1], x[2]))
    shuf1 = pairs_base[:]
    shuf2 = pairs_base[:]
    rng.shuffle(shuf1)
    rng.shuffle(shuf2)

    orders = [
        ("closest", closest),
        ("farthest", farthest),
        ("shuffled1", shuf1),
        ("shuffled2", shuf2),
    ]

    best_placements: Optional[List[Tuple[Pos, Aspect]]] = None
    best_score = (999999, 999999.0)

    user_positions = [pos for pos, _ in user_aspects]
    best_state_score: Dict[
        Tuple[Tuple[Tuple[Pos, Aspect], ...], Tuple[Tuple[Pos, ...], ...]],
        Tuple[int, float],
    ] = {}

    def build_parent(positions: List[Pos]) -> Dict[Pos, Pos]:
        return {p: p for p in positions}

    def find(parent: Dict[Pos, Pos], x: Pos) -> Pos:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(parent: Dict[Pos, Pos], a: Pos, b: Pos) -> bool:
        ra = find(parent, a)
        rb = find(parent, b)
        if ra == rb:
            return False
        parent[ra] = rb
        return True

    def components_count(parent: Dict[Pos, Pos], positions: List[Pos]) -> int:
        return len({find(parent, p) for p in positions})

    def component_signature(parent: Dict[Pos, Pos], positions: List[Pos]) -> Tuple[Tuple[Pos, ...], ...]:
        groups: Dict[Pos, List[Pos]] = {}
        for p in positions:
            root = find(parent, p)
            groups.setdefault(root, []).append(p)
        return tuple(sorted(tuple(sorted(v)) for v in groups.values()))

    for order_name, pairs in orders:
        debug_log(f"Network attempt: {order_name}")

        def recurse(
            pair_idx: int,
            current_placements: Dict[Pos, Aspect],
            current_new: List[Tuple[Pos, Aspect]],
            parent: Dict[Pos, Pos],
            depth: int = 0,
            branch_budget: int = 50,
        ):
            nonlocal best_placements, best_score

            if branch_budget <= 0:
                return

            partial_score = score_solution(current_new, weights)
            if partial_score >= best_score:
                return

            state_key = (
                canonical_placements_key(current_placements),
                component_signature(parent, user_positions),
            )

            prev_best_for_state = best_state_score.get(state_key)
            if prev_best_for_state is not None and partial_score >= prev_best_for_state:
                return
            best_state_score[state_key] = partial_score

            comp = components_count(parent, user_positions)
            if comp <= 1:
                if partial_score < best_score:
                    best_score = partial_score
                    best_placements = current_new[:]
                return

            next_options = []
            seen_component_pairs = set()

            for k in range(pair_idx, len(pairs)):
                _, _, _, pos_a, asp_a, pos_b, asp_b = pairs[k]
                ra = find(parent, pos_a)
                rb = find(parent, pos_b)
                if ra == rb:
                    continue

                comp_pair = tuple(sorted((ra, rb)))
                if comp_pair in seen_component_pairs:
                    continue
                seen_component_pairs.add(comp_pair)

                next_options.append((k, pos_a, asp_a, pos_b, asp_b))

            if not next_options:
                return

            chosen_option = None
            chosen_candidates = None
            chosen_len = None

            probe_options = next_options[:4]
            for option in probe_options:
                k, pos_a, asp_a, pos_b, asp_b = option
                cands = find_path_with_chain_candidates(
                    state.grid_positions,
                    state.void_positions,
                    current_placements,
                    pos_a,
                    asp_a,
                    pos_b,
                    asp_b,
                    weights,
                    io_chaining=io_chaining,
                    allow_reuse=True,
                    max_extra_length=5,
                    max_geo_paths=20,
                    max_chains_per_len=16,
                    max_candidates=6,
                )
                if not cands:
                    chosen_option = option
                    chosen_candidates = []
                    chosen_len = 0
                    break
                if chosen_len is None or len(cands) < chosen_len:
                    chosen_option = option
                    chosen_candidates = cands
                    chosen_len = len(cands)

            if chosen_option is None:
                return

            k, pos_a, asp_a, pos_b, asp_b = chosen_option
            candidates = chosen_candidates if chosen_candidates is not None else []

            if not candidates:
                return

            for cand in candidates:
                new_map = dict(current_placements)
                conflict = False

                for pos, asp in cand:
                    ex = new_map.get(pos)
                    if ex is not None and ex != asp:
                        conflict = True
                        break
                    new_map[pos] = asp

                if conflict:
                    continue

                new_parent = dict(parent)
                union(new_parent, pos_a, pos_b)

                merged_new = current_new[:]
                existing_new_positions = {p for p, _ in merged_new}
                for pos, asp in cand:
                    if pos not in existing_new_positions:
                        merged_new.append((pos, asp))

                recurse(
                    k + 1,
                    new_map,
                    merged_new,
                    new_parent,
                    depth + 1,
                    branch_budget - 1,
                )

        recurse(
            0,
            dict(state.placements),
            [],
            build_parent(user_positions),
            0,
            50,
        )

    if best_placements is not None:
        debug_log(f"Network best: {len(best_placements)} placements, score {best_score}")
    return best_placements


def find_center_hub_solution(
    state: SolverState,
    weights: Dict[Aspect, float],
) -> Optional[List[Tuple[Pos, Aspect]]]:
    debug_log("=== CENTER HUB STRATEGY ===")
    center = (0, 0)
    if center not in state.grid_positions or center in state.void_positions:
        debug_log("Center not available")
        return None

    io_chaining = is_io_chaining_enabled(state)
    user_aspects = list(state.user_aspects)
    if len(user_aspects) < 2:
        return None

    best_solution = None
    best_score = (float("inf"), float("inf"))

    candidates = set(PRIMALS)
    for _, asp in user_aspects:
        candidates.update(get_neighbors_of(asp))
        candidates.update(get_aspect_parents(asp))
        for parent in get_aspect_parents(asp):
            candidates.update(get_neighbors_of(parent))

    if io_chaining:
        if "Instrumentum" in ASPECT_GRAPH:
            center_order = ["Instrumentum"] + [
                a
                for a in sort_aspects_for_choice(candidates | {"Instrumentum", "Ordo"}, weights, io_chaining)
                if a != "Instrumentum"
            ]
        else:
            center_order = sort_aspects_for_choice(candidates | {"Ordo"}, weights, io_chaining)
    else:
        center_order = sort_aspects_for_choice(candidates, weights, io_chaining)

    debug_log(f"Trying {len(center_order)} center candidates")
    if io_chaining:
        debug_log(f"IO mode center priority: first candidate = {center_order[0] if center_order else None}")

    for center_asp in center_order:
        placements = dict(state.placements)
        all_paths = []
        valid = True

        if center not in placements:
            placements[center] = center_asp
            all_paths.append((center, center_asp))
        elif placements[center] != center_asp:
            continue

        for user_pos, user_asp in user_aspects:
            if user_pos == center:
                continue

            path_candidates = find_path_with_chain_candidates(
                state.grid_positions,
                state.void_positions,
                placements,
                user_pos,
                user_asp,
                center,
                center_asp,
                weights,
                io_chaining=io_chaining,
                allow_reuse=True,
                max_extra_length=4,
                max_geo_paths=15,
                max_chains_per_len=12,
                max_candidates=4,
            )

            if not path_candidates:
                valid = False
                break

            chosen = None
            for cand in path_candidates:
                ok = True
                for pos, asp in cand:
                    if pos in placements and placements[pos] != asp:
                        ok = False
                        break
                if ok:
                    chosen = cand
                    break

            if chosen is None:
                valid = False
                break

            for pos, asp in chosen:
                if pos in placements and placements[pos] != asp:
                    valid = False
                    break
                placements[pos] = asp
                all_paths.append((pos, asp))

            if not valid:
                break

        if not valid:
            continue

        solution = [p for p in all_paths if p[0] not in state.placements]

        seen = set()
        deduped = []
        for item in solution:
            if item[0] not in seen:
                seen.add(item[0])
                deduped.append(item)

        score = score_solution(deduped, weights)
        debug_log(f"  Center {center_asp}: {len(deduped)} placements, score {score}")

        if best_solution is None:
            best_score = score
            best_solution = deduped
        else:
            if score < best_score:
                best_score = score
                best_solution = deduped
            elif io_chaining and center_asp == "Instrumentum" and score[0] == best_score[0]:
                best_score = score
                best_solution = deduped

        if io_chaining and center_asp == "Instrumentum" and best_solution is not None:
            debug_log("IO mode: accepting Instrumentum-centered solution immediately")
            return best_solution

    return best_solution


def find_direct_path_solution(
    state: SolverState,
    weights: Dict[Aspect, float],
) -> Optional[List[Tuple[Pos, Aspect]]]:
    debug_log("=== DIRECT PATH STRATEGY ===")
    user_aspects = list(state.user_aspects)
    if len(user_aspects) != 2:
        debug_log("Not exactly 2 user aspects, skipping")
        return None

    io_chaining = is_io_chaining_enabled(state)
    (pos_a, asp_a), (pos_b, asp_b) = user_aspects
    return find_path_with_chain(
        state.grid_positions,
        state.void_positions,
        dict(state.placements),
        pos_a,
        asp_a,
        pos_b,
        asp_b,
        weights,
        io_chaining=io_chaining,
        allow_reuse=True,
        max_extra_length=4,
    )


def solve_optimally(
    initial: SolverState,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> SearchResult:
    debug_log("========== STARTING SOLVE ==========")
    clear_search_caches()

    weights = dict(initial._weights)

    if initial.is_connected:
        debug_log("Already connected!")
        return SearchResult(
            state=initial,
            stats=SearchStats(states_explored=0, solution_found=True),
        )

    solutions = []
    strategies = [
        ("Direct", find_direct_path_solution),
        ("Center Hub", find_center_hub_solution),
        ("Network", find_network_solution),
    ]

    for i, (name, func) in enumerate(strategies):
        if progress_cb:
            progress_cb((i + 1) / len(strategies), f"Trying {name}...")
        result = func(initial, weights)
        if result:
            seen = set()
            deduped = []
            for pos, asp in result:
                if pos not in seen:
                    seen.add(pos)
                    deduped.append((pos, asp))

            score = score_solution(deduped, weights)
            solutions.append((score, deduped))
            debug_log(f"{name} found solution: {len(deduped)} placements, score {score}")

    if not solutions:
        debug_log("NO SOLUTION FOUND!")
        return SearchResult(
            state=None,
            stats=SearchStats(states_explored=3, solution_found=False),
        )

    io_chaining = is_io_chaining_enabled(initial)

    def final_sort_key(item):
        score, placements = item
        if not io_chaining:
            return score
        io_bonus = sum(1 for _, a in placements if a == "Instrumentum") * 2 + sum(1 for _, a in placements if a == "Ordo")
        return (score[0], score[1], -io_bonus)

    solutions.sort(key=final_sort_key)
    best_score, best_placements = solutions[0]
    debug_log(f"Best solution chosen: {len(best_placements)} placements, score {best_score}")

    state = initial
    for pos, asp in best_placements:
        state = state.place(pos, asp)

    return SearchResult(
        state=state,
        stats=SearchStats(states_explored=3, solution_found=True),
    )


def solve_by_connecting_components(
    initial: SolverState,
    max_iterations: int = 100,
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> SearchResult:
    return solve_optimally(initial, progress_cb)


def a_star(
    initial: SolverState,
    heuristic: Callable[[SolverState], float],
    max_states: int = 100_000,
    max_cost: float = float("inf"),
    progress_cb: Optional[Callable[[float, str], None]] = None,
) -> SearchResult:
    return solve_optimally(initial, progress_cb)