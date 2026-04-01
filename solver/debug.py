from __future__ import annotations
from typing import Dict, Any

from .types import Pos, SolveResult
from .aspects import calculate_aspect_weights, ASPECT_TIERS


def debug_output_board(grid: Dict[Pos, dict], ring_count: int = 4, prefer_oi: bool = True) -> Dict[str, Any]:
    weights = calculate_aspect_weights(prefer_oi)
    
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
        w = weights.get(asp, 10)
        t = ASPECT_TIERS.get(asp, "?")
        print(f"  {str(pos):12} {asp:15} [weight: {w}, tier: {t}]")
    
    print(f"\nSolver-placed ({len(solver_placed)}):")
    print("-" * 50)
    for pos, asp in solver_placed:
        w = weights.get(asp, 10)
        t = ASPECT_TIERS.get(asp, "?")
        print(f"  {str(pos):12} {asp:15} [weight: {w}, tier: {t}]")
    
    if solver_placed:
        counts = {}
        for _, asp in solver_placed:
            counts[asp] = counts.get(asp, 0) + 1
        
        print("\nAspect Usage Summary:")
        print("-" * 50)
        for asp, cnt in sorted(counts.items(), key=lambda x: -x[1]):
            print(f"  {asp:15} {cnt}x (weight: {weights.get(asp, 10)})")
        
        total = sum(weights.get(a, 10) for _, a in solver_placed)
        print(f"\nTotal Weight: {total}")
        print(f"Total Placements: {len(solver_placed)}")
        
        for threshold, grade in [(4, "S"), (10, "A"), (20, "B"), (35, "C"), (50, "D")]:
            if total <= threshold:
                break
        else:
            grade = "F"
        print(f"Rating: {grade} (weight: {total})")
    
    print("=" * 70 + "\n")
    
    return {"user_placed": user_placed, "solver_placed": solver_placed}


def debug_output_solve_result(result: SolveResult) -> None:
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
    
    if result.placements:
        weights = calculate_aspect_weights(result.prefer_oi)
        print(f"\nPlacements ({len(result.placements)}):")
        print("-" * 50)
        for pos, asp in result.placements:
            w = weights.get(asp, 10)
            print(f"  {pos} -> {asp} (weight: {w})")
    
    print("=" * 70 + "\n")
