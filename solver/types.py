"""
Core type definitions for the solver.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Tuple, List, Optional, Dict, Any

Pos = Tuple[int, int]
Aspect = str


@dataclass
class Placement:
    pos: Pos
    aspect: Aspect
    weight: float = 0.0


@dataclass
class SolveResult:
    success: bool = False
    placements: List[Tuple[Pos, Aspect]] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    all_connected: bool = False
    rating_score: float = 0.0
    rating_grade: str = "F"
    attempts: int = 0
    prefer_oi: bool = True
    stats: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def total_count(self) -> int:
        return len(self.placements)
    
    @property
    def total_weight(self) -> float:
        return self.rating_score


@dataclass
class SearchStats:
    states_explored: int = 0
    states_pruned: int = 0
    max_frontier_size: int = 0
    solution_found: bool = False
