"""
Heuristics for A* search.
"""

from __future__ import annotations
from typing import Dict, TYPE_CHECKING

from .hex import hex_distance

if TYPE_CHECKING:
    from .state import SolverState


def null_heuristic(state: "SolverState") -> float:
    return 0.0


def component_heuristic(state: "SolverState") -> float:
    n = state.component_count
    if n <= 1:
        return 0.0
    return float(n - 1)


def mst_distance_heuristic(state: "SolverState") -> float:
    if state.is_connected:
        return 0.0
    
    user_aspects = state.user_aspects
    n = len(user_aspects)
    
    if n <= 1:
        return 0.0
    
    comps = state._components
    
    comp_positions: Dict[int, list] = {}
    for pos, asp in user_aspects:
        comp = comps.get(pos, -1)
        if comp >= 0:
            comp_positions.setdefault(comp, []).append(pos)
    
    unique_comps = list(comp_positions.keys())
    if len(unique_comps) <= 1:
        return 0.0
    
    in_tree = {unique_comps[0]}
    total = 0.0
    
    while len(in_tree) < len(unique_comps):
        best_dist = float('inf')
        best_comp = None
        
        for comp_out in unique_comps:
            if comp_out in in_tree:
                continue
            
            for comp_in in in_tree:
                for pos_out in comp_positions[comp_out]:
                    for pos_in in comp_positions[comp_in]:
                        d = hex_distance(pos_out, pos_in)
                        if d < best_dist:
                            best_dist = d
                            best_comp = comp_out
        
        if best_comp is None:
            break
        
        in_tree.add(best_comp)
        total += max(0, best_dist - 1)
    
    return total


def combined_heuristic(state: "SolverState") -> float:
    return max(
        component_heuristic(state),
        mst_distance_heuristic(state),
    )