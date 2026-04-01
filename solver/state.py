from __future__ import annotations
from dataclasses import dataclass, field
from typing import FrozenSet, Dict, Optional, Iterator, Set, Tuple, List
from .types import Pos, Aspect, Placement
from .hex import get_neighbors
from .aspects import can_connect, get_neighbors_of, ASPECT_GRAPH, calculate_aspect_weights


@dataclass(frozen=True)
class SolverState:
    
    grid_positions: FrozenSet[Pos]
    void_positions: FrozenSet[Pos]
    placements: Dict[Pos, Aspect]
    user_positions: FrozenSet[Pos]
    cost: float = 0.0
    solver_placements: Tuple[Placement, ...] = ()
    io_chaining_enabled: bool = False
    _weights: Dict[Aspect, float] = field(default_factory=dict, hash=False, compare=False)
    
    @classmethod
    def from_grid(
        cls,
        grid: Dict[Pos, dict],
        prefer_ordo: bool = True,
        io_chaining_enabled: bool = False,
    ) -> "SolverState":
        grid_positions = frozenset(grid.keys())
        void_positions = frozenset(
            pos for pos, cell in grid.items()
            if cell.get("void", False)
        )
        
        placements = {}
        user_positions = set()
        
        for pos, cell in grid.items():
            asp = cell.get("aspect")
            if asp and not cell.get("void", False):
                placements[pos] = asp
                if cell.get("player_placed", False):
                    user_positions.add(pos)
        
        weights = calculate_aspect_weights(prefer_ordo)
        
        return cls(
            grid_positions=grid_positions,
            void_positions=void_positions,
            placements=placements,
            user_positions=frozenset(user_positions),
            cost=0.0,
            solver_placements=(),
            io_chaining_enabled=io_chaining_enabled,
            _weights=weights,
        )
    
    def aspect_at(self, pos: Pos) -> Optional[Aspect]:
        return self.placements.get(pos)
    
    def is_empty(self, pos: Pos) -> bool:
        return (
            pos in self.grid_positions
            and pos not in self.void_positions
            and pos not in self.placements
        )
    
    def is_valid_pos(self, pos: Pos) -> bool:
        return pos in self.grid_positions and pos not in self.void_positions
    
    @property
    def user_aspects(self) -> Tuple[Tuple[Pos, Aspect], ...]:
        return tuple(
            (pos, self.placements[pos])
            for pos in sorted(self.user_positions)
            if pos in self.placements
        )
    
    @property
    def _components(self) -> Dict[Pos, int]:
        """Compute connected components."""
        components: Dict[Pos, int] = {}
        comp_id = 0
        
        for start in self.placements:
            if start in components:
                continue
            
            components[start] = comp_id
            frontier = [start]
            
            while frontier:
                pos = frontier.pop()
                asp = self.placements[pos]
                
                for nbr in get_neighbors(pos):
                    if nbr in components:
                        continue
                    nbr_asp = self.placements.get(nbr)
                    if nbr_asp and can_connect(asp, nbr_asp):
                        components[nbr] = comp_id
                        frontier.append(nbr)
            
            comp_id += 1
        
        return components
    
    @property
    def is_connected(self) -> bool:
        if len(self.user_positions) <= 1:
            return True
        
        comps = self._components
        first_comp = None
        
        for pos in self.user_positions:
            if pos not in comps:
                return False
            if first_comp is None:
                first_comp = comps[pos]
            elif comps[pos] != first_comp:
                return False
        
        return True
    
    @property
    def component_count(self) -> int:
        if not self.user_positions:
            return 0
        
        comps = self._components
        user_comps = {comps.get(pos) for pos in self.user_positions}
        user_comps.discard(None)
        return len(user_comps)
    
    def place(self, pos: Pos, aspect: Aspect) -> "SolverState":
        weight = self._weights.get(aspect, 10.0)
        
        new_placements = dict(self.placements)
        new_placements[pos] = aspect
        
        new_solver_placements = self.solver_placements + (
            Placement(pos, aspect, weight),
        )
        
        return SolverState(
            grid_positions=self.grid_positions,
            void_positions=self.void_positions,
            placements=new_placements,
            user_positions=self.user_positions,
            cost=self.cost + weight,
            solver_placements=new_solver_placements,
            io_chaining_enabled=self.io_chaining_enabled,
            _weights=self._weights,
        )
    
    def valid_placements_at(self, pos: Pos) -> Iterator[Tuple[Aspect, float]]:
        if not self.is_empty(pos):
            return
        
        adjacent_aspects: Set[Aspect] = set()
        for nbr in get_neighbors(pos):
            asp = self.placements.get(nbr)
            if asp:
                adjacent_aspects.add(asp)
        
        if not adjacent_aspects:
            return
        
        valid: Set[Aspect] = set(ASPECT_GRAPH.keys())
        for adj_asp in adjacent_aspects:
            connectable = get_neighbors_of(adj_asp) | {adj_asp}
            valid = valid & connectable
        
        for aspect in valid:
            yield aspect, self._weights.get(aspect, 10.0)
    
    @property
    def frontier(self) -> FrozenSet[Pos]:
        frontier_set: Set[Pos] = set()
        
        for pos in self.placements:
            for nbr in get_neighbors(pos):
                if self.is_empty(nbr):
                    frontier_set.add(nbr)
        
        return frozenset(frontier_set)
    
    def expand(self) -> Iterator["SolverState"]:
        for pos in self.frontier:
            for aspect, weight in self.valid_placements_at(pos):
                yield self.place(pos, aspect)
    
    def to_placement_list(self) -> List[Tuple[Pos, Aspect]]:
        return [(p.pos, p.aspect) for p in self.solver_placements]
