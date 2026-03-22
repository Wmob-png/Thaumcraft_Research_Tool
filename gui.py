# gui.py

import pygame
import math
import random
import threading
from aspects import aspect_parents, get_all_connections, PRIMALS
from solver import (
    solve_with_center_priority, get_solve_stats, SolveResult,
    ASPECT_GRAPH, is_board_solved, are_all_aspects_connected,
    get_neighbors, get_user_placed_positions, is_edge_position,
    ASPECT_WEIGHTS, calculate_solve_rating,
    debug_output_board, debug_output_solve_result
)
from resources import asset_path

# ═══════════════════════════════════════════════════════════════════════════════
# TILEMAP CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

TILEMAP_FILE = "Tilesheet_TC4A_32_0.png"
TILE_SIZE = 32

LEFT_ASPECTS = [
    'Ordo', 'Terra', 'Aqua', 'Permutatio',
    'Vitreus', 'Victus', 'Metallum', 'Sano',
    'Tempus', 'Iter', 'Mortuus', 'Herba',
    'Limus', 'Bestia', 'Caelum', 'Spiritus',
    'Magneto', 'Aequalitas', 'Corpus', 'Humanus',
    'Instrumentum', 'Perfodio', 'Luxuria', 'Tutamen',
    'Machina', 'Gloria', 'Messis', 'Lucrum',
    'Electrum', 'Tabernus', 'Pannus', 'Fabrico',
    'Meto', 'Nebrisum',
]

RIGHT_ASPECTS = [
    'Perditio', 'Ignis', 'Aer', 'Potentia',
    'Gelum', 'Motus', 'Venenum', 'Vacuos',
    'Lux', 'Tempesta', 'Vinculum', 'Volatus',
    'Praecantatio', 'Primordium', 'Radio', 'Fames',
    'Arbor', 'Tenebrae', 'Vitium', 'Infernus',
    'Exanimis', 'Auram', 'Superbia', 'Cognitio',
    'Gula', 'Sensus', 'Astrum', 'Alienis',
    'Stronito', 'Desidia', 'Invidia', 'Vesania',
    'Telum', 'Ira', 'Terminus',
]


def _build_tile_positions():
    positions = {}
    for i, aspect in enumerate(LEFT_ASPECTS):
        if aspect:
            positions[aspect] = (i % 4, i // 4)
    for i, aspect in enumerate(RIGHT_ASPECTS):
        if aspect:
            positions[aspect] = ((i % 4) + 5, i // 4)
    return positions


ASPECT_TILE_POSITIONS = _build_tile_positions()

left_aspects  = [LEFT_ASPECTS[i:i+4]  for i in range(0, len(LEFT_ASPECTS),  4)]
right_aspects = [RIGHT_ASPECTS[i:i+4] for i in range(0, len(RIGHT_ASPECTS), 4)]

# ═══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

BASE_WIDTH     = 1100
BASE_HEIGHT    = 700
BASE_CENTER_X  = 550
BASE_CENTER_Y  = 350

HEX_RADIUS        = 22
HEX_SPACING       = 1.3
ICON_SIZE         = 36
TOOLTIP_ICON_SIZE = 20

PARCHMENT_SCALE = 3.3

HEX_FILL_COLOR  = (140, 135, 120, 100)
HEX_LINE_COLOR  = (100,  95,  80, 150)
HEX_HOVER_TINT  = (180, 175, 160, 120)

CHAIN_COLOR      = ( 80, 150, 255)
CHAIN_GLOW_COLOR = (100, 160, 255)

HEX_DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1)]

# Credits text (customize as needed)
CREDITS_TEXT = [
    "Thaumcraft Research Solver (GTNH)",
    "",
    "Maker: Wmob",
    "Contact: Discord or GitHub - Wmob (DM for issues)",
    "",
    "Asset Credits:",
    "Thaumcraft 4 - Azanor for the original aspect icons and decorative UI elements",
    "Avaritia 1.85 - SpitefulFox for the Terminus aspect icon",
    "GregTech 5.09.52.2462 - GregoriusT & GTNH Team for GTNH-specific aspect icons",
    "Thaumic Boots 1.5.8 - alastors_game for the Tabernus & Caelum aspect icons",
    "Magic Bees 2.10.2-GTNH - MysteriousAges for the Tempus aspect icon",
    "Forbidden Magic 0.9.7-GTNH - SpitefulFox for Desidia, Gula, Infernus,",
    "Invidia, Ira, Luxuria, and Superbia aspect icons",
    "",
    "Code License: MIT License (https://opensource.org/licenses/MIT)",
    "Fan-made tool for educational purposes and to assist players in solving",
    "Thaumcraft research puzzles. Not affiliated with Azanor, GregoriusT, or any",
    "original content creators. All trademarks and assets belong to their",
    "respective owners.",
]

# ═══════════════════════════════════════════════════════════════════════════════
# TILEMAP LOADER
# ═══════════════════════════════════════════════════════════════════════════════

class TilemapLoader:
    def __init__(self, tilemap_path=TILEMAP_FILE):
        self.tilemap      = None
        self.tile_size    = TILE_SIZE
        self.loaded       = False
        self.tilemap_path = tilemap_path

    def load(self):
        try:
            path = asset_path(self.tilemap_path)
            self.tilemap = pygame.image.load(path).convert_alpha()
            self.loaded  = True
            cols = self.tilemap.get_width()  // self.tile_size
            rows = self.tilemap.get_height() // self.tile_size
            print(f"Loaded tilemap: {cols}x{rows} tiles")
            return True
        except Exception as e:
            print(f"Failed to load tilemap: {e}")
            return False

    def get_tile(self, col, row):
        if not self.loaded:
            return None
        x, y = col * self.tile_size, row * self.tile_size
        if (x + self.tile_size > self.tilemap.get_width() or
                y + self.tile_size > self.tilemap.get_height()):
            return None
        tile = pygame.Surface((self.tile_size, self.tile_size), pygame.SRCALPHA)
        tile.blit(self.tilemap, (0, 0), (x, y, self.tile_size, self.tile_size))
        return tile

    def get_aspect_icon(self, aspect_name):
        if aspect_name not in ASPECT_TILE_POSITIONS:
            return None
        col, row = ASPECT_TILE_POSITIONS[aspect_name]
        return self.get_tile(col, row)


# ═══════════════════════════════════════════════════════════════════════════════
# HEX BOARD CLASS
# ═══════════════════════════════════════════════════════════════════════════════

class HexBoard:
    def __init__(self, ring_count=3, center=(550, 350)):
        self.grid        = {}
        self.ring_count  = ring_count
        self.base_center = center

        self.window_width  = BASE_WIDTH
        self.window_height = BASE_HEIGHT

        self.scale_x = 1.0
        self.scale_y = 1.0

        self.selected_aspect      = None
        self.aspect_icons_raw     = {}
        self.aspect_buttons_left  = []
        self.aspect_buttons_right = []
        self.hovered_hex          = None
        self.hovered_aspect       = None
        self.hex_idle             = None
        self.hex_hover            = None
        self.parchment_base       = None

        self.oi_chaining    = False
        self.history        = []
        self.redo_stack     = []
        self.status_message = ""
        self.status_timer   = 0
        self.solving        = False
        self.show_coords    = False
        self.show_tooltips  = True
        self.show_credits   = False  # NEW

        self.lightning_seed  = 0
        self.lightning_timer = 0
        self.is_solved       = False

        self._connected_cache       = {}
        self._connected_cache_dirty = True
        self._icon_cache            = {}
        self._last_cache_key        = None

        # ── Thread / progress state ──────────────────────────────────────────
        self._solve_thread      = None
        self._solve_lock        = threading.Lock()
        self._pending_result    = None
        self._pending_grid      = None
        self.solve_running      = False
        self.solve_progress     = 0.0
        self.solve_progress_msg = ""
        self._solve_done_timer  = 0
        # ─────────────────────────────────────────────────────────────────────

        self.generate_grid()
        self.load_assets()
        self.build_aspect_buttons()

    # ── Coordinate helpers ───────────────────────────────────────────────────

    def get_scale(self):
        return min(self.scale_x, self.scale_y)

    def get_offset(self):
        scale         = self.get_scale()
        scaled_width  = BASE_WIDTH  * scale
        scaled_height = BASE_HEIGHT * scale
        offset_x = (self.window_width  - scaled_width)  / 2
        offset_y = (self.window_height - scaled_height) / 2
        return offset_x, offset_y

    def base_to_screen(self, base_x, base_y):
        scale = self.get_scale()
        offset_x, offset_y = self.get_offset()
        return int(base_x * scale + offset_x), int(base_y * scale + offset_y)

    def screen_to_base(self, screen_x, screen_y):
        scale = self.get_scale()
        offset_x, offset_y = self.get_offset()
        return (screen_x - offset_x) / scale, (screen_y - offset_y) / scale

    def scale_value(self, value):
        return int(value * self.get_scale())

    # ── Undo / Redo ──────────────────────────────────────────────────────────

    def save_state(self):
        state = {pos: dict(cell) for pos, cell in self.grid.items()}
        self.history.append(state)
        self.redo_stack.clear()
        if len(self.history) > 50:
            self.history.pop(0)

    def undo(self):
        if not self.history:
            self.set_status("Nothing to undo")
            return False
        self.redo_stack.append(
            {pos: dict(cell) for pos, cell in self.grid.items()}
        )
        state = self.history.pop()
        for pos, cell_data in state.items():
            self.grid[pos] = cell_data
        self._connected_cache_dirty = True
        self.update_solved_state()
        self.set_status("Undone!")
        return True

    def redo(self):
        if not self.redo_stack:
            self.set_status("Nothing to redo")
            return False
        self.history.append(
            {pos: dict(cell) for pos, cell in self.grid.items()}
        )
        state = self.redo_stack.pop()
        for pos, cell_data in state.items():
            self.grid[pos] = cell_data
        self._connected_cache_dirty = True
        self.update_solved_state()
        self.set_status("Redone!")
        return True

    # ── Status / timers ──────────────────────────────────────────────────────

    def set_status(self, message, duration=120):
        self.status_message = message
        self.status_timer   = duration

    def update_status(self):
        if self.status_timer > 0:
            self.status_timer -= 1
            if self.status_timer == 0:
                self.status_message = ""
        self.lightning_timer += 1
        if self.lightning_timer >= 4:
            self.lightning_timer = 0
            self.lightning_seed  = random.randint(0, 10000)

    def update_solved_state(self):
        self.is_solved = is_board_solved(self.grid)
        self._connected_cache_dirty = True

    # ── Connected cache ──────────────────────────────────────────────────────

    def _rebuild_connected_cache(self):
        self._connected_cache = {}
        anchor_positions = set()

        for pos, cell in self.grid.items():
            if not cell.get('aspect') or cell.get('void', False):
                continue
            if (cell.get('player_placed', False) and
                    is_edge_position(self.grid, pos, self.ring_count)):
                anchor_positions.add(pos)

        if not anchor_positions:
            for pos, cell in self.grid.items():
                if cell.get('aspect') and not cell.get('void', False):
                    self._connected_cache[pos] = False
            self._connected_cache_dirty = False
            return

        visited = set(anchor_positions)
        queue   = list(anchor_positions)

        while queue:
            current     = queue.pop(0)
            current_asp = self.grid[current].get('aspect')
            if not current_asp:
                continue
            for neighbor_pos in self.get_hex_neighbors(current):
                if neighbor_pos in visited or neighbor_pos not in self.grid:
                    continue
                neighbor_cell = self.grid[neighbor_pos]
                if neighbor_cell.get('void', False):
                    continue
                neighbor_asp = neighbor_cell.get('aspect')
                if (neighbor_asp and
                        neighbor_asp in ASPECT_GRAPH.get(current_asp, set())):
                    visited.add(neighbor_pos)
                    queue.append(neighbor_pos)

        for pos, cell in self.grid.items():
            if cell.get('aspect') and not cell.get('void', False):
                if (cell.get('player_placed', False) and
                        is_edge_position(self.grid, pos, self.ring_count)):
                    self._connected_cache[pos] = True
                else:
                    self._connected_cache[pos] = pos in visited

        self._connected_cache_dirty = False

    def is_position_active(self, pos):
        if self._connected_cache_dirty:
            self._rebuild_connected_cache()
        return self._connected_cache.get(pos, False)

    # ── Grid ─────────────────────────────────────────────────────────────────

    def generate_grid(self):
        self.grid.clear()
        for q in range(-self.ring_count, self.ring_count + 1):
            for r in range(-self.ring_count, self.ring_count + 1):
                if abs(-q - r) <= self.ring_count:
                    self.grid[(q, r)] = {
                        'aspect': None,
                        'void':   False,
                        'player_placed': False,
                    }
        self.is_solved = False
        self._connected_cache_dirty = True

    # ── Icon helpers ─────────────────────────────────────────────────────────

    def _create_dimmed_icon(self, surface):
        if surface is None:
            return None
        dimmed = surface.copy()
        dark   = pygame.Surface(dimmed.get_size(), pygame.SRCALPHA)
        dark.fill((80, 80, 80, 160))
        dimmed.blit(dark, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)
        return dimmed

    def _get_icon(self, aspect, size, dimmed=False):
        key = (aspect, size, dimmed)
        if key in self._icon_cache:
            return self._icon_cache[key]
        raw = self.aspect_icons_raw.get(aspect)
        if raw is None:
            return None
        scaled = pygame.transform.smoothscale(raw, (size, size))
        if dimmed:
            scaled = self._create_dimmed_icon(scaled)
        self._icon_cache[key] = scaled
        return scaled

    def _check_cache(self):
        cache_key = (self.scale_x, self.scale_y)
        if cache_key != self._last_cache_key:
            self._icon_cache.clear()
            self._last_cache_key = cache_key

    # ── Asset loading ────────────────────────────────────────────────────────

    def _load_hex_images(self):
        try:
            h1 = pygame.image.load(asset_path("hex1.png")).convert_alpha()
            h2 = pygame.image.load(asset_path("hex2.png")).convert_alpha()
            self.hex_idle  = h1
            self.hex_hover = h2
        except Exception as e:
            print(f"Could not load hex images: {e}")

    def _load_parchment(self):
        try:
            self.parchment_base = pygame.image.load(
                asset_path("parchment3.png")
            ).convert_alpha()
        except Exception as e:
            print(f"Could not load parchment: {e}")
            self.parchment_base = None

    def load_assets(self):
        loader = TilemapLoader()
        if loader.load():
            all_aspects = set(LEFT_ASPECTS + RIGHT_ASPECTS)
            all_aspects.update(PRIMALS)
            loaded = 0
            for asp in all_aspects:
                icon = loader.get_aspect_icon(asp)
                if icon:
                    self.aspect_icons_raw[asp] = icon
                    loaded += 1
            print(f"Loaded {loaded} aspect icons")
        else:
            print("ERROR: Failed to load tilemap!")
        self._load_hex_images()
        self._load_parchment()

    # ── Button layout ────────────────────────────────────────────────────────

    def build_aspect_buttons(self):
        self.aspect_buttons_left.clear()
        self.aspect_buttons_right.clear()

        spacing = ICON_SIZE + 4
        x_left  = 60
        x_right = BASE_WIDTH - 60 - spacing * 4
        y_start = 60

        for row_i, row in enumerate(left_aspects):
            for col_i, asp in enumerate(row):
                if asp:
                    x = x_left + col_i * spacing
                    y = y_start + row_i * spacing
                    self.aspect_buttons_left.append(
                        (pygame.Rect(x, y, ICON_SIZE, ICON_SIZE), asp)
                    )

        for row_i, row in enumerate(right_aspects):
            for col_i, asp in enumerate(row):
                if asp:
                    x = x_right + col_i * spacing
                    y = y_start + row_i * spacing
                    self.aspect_buttons_right.append(
                        (pygame.Rect(x, y, ICON_SIZE, ICON_SIZE), asp)
                    )

    # ── Hex coordinate helpers ───────────────────────────────────────────────

    def axial_to_base(self, q, r):
        x = HEX_RADIUS * 3/2 * q * HEX_SPACING + BASE_CENTER_X
        y = HEX_RADIUS * math.sqrt(3) * (r + q/2) * HEX_SPACING + BASE_CENTER_Y
        return x, y

    def axial_to_screen(self, q, r):
        base_x, base_y = self.axial_to_base(q, r)
        return self.base_to_screen(base_x, base_y)

    def get_hex_at_pixel(self, mx, my):
        base_x, base_y = self.screen_to_base(mx, my)
        for (q, r) in self.grid:
            hx, hy = self.axial_to_base(q, r)
            if math.hypot(base_x - hx, base_y - hy) < HEX_RADIUS * 0.9:
                return (q, r)
        return None

    def get_hex_neighbors(self, pos):
        q, r = pos
        return [(q + dq, r + dr) for dq, dr in HEX_DIRECTIONS]

    def are_aspects_connected(self, asp1, asp2):
        if asp1 is None or asp2 is None:
            return False
        return asp2 in ASPECT_GRAPH.get(asp1, set())

    # ── Lightning ────────────────────────────────────────────────────────────

    def draw_lightning_chains(self, screen):
        drawn = set()
        scale = self.get_scale()

        for pos, cell in self.grid.items():
            if cell['void'] or not cell['aspect'] or not self.is_position_active(pos):
                continue
            x1, y1 = self.axial_to_screen(*pos)

            for npos in self.get_hex_neighbors(pos):
                if npos not in self.grid:
                    continue
                ncell = self.grid[npos]
                if (ncell['void'] or not ncell['aspect'] or
                        not self.is_position_active(npos)):
                    continue
                pair = tuple(sorted([pos, npos]))
                if pair in drawn:
                    continue
                if self.are_aspects_connected(cell['aspect'], ncell['aspect']):
                    drawn.add(pair)
                    x2, y2 = self.axial_to_screen(*npos)
                    self._draw_lightning(
                        screen, x1, y1, x2, y2,
                        hash(pair) + self.lightning_seed, scale
                    )

    def _draw_lightning(self, screen, x1, y1, x2, y2, seed, scale):
        rng    = random.Random(seed)
        dx, dy = x2 - x1, y2 - y1
        length = math.hypot(dx, dy)
        if length == 0:
            return

        perp_x, perp_y = -dy / length, dx / length
        segments = max(4, int(length / (8 * scale)))
        points   = [(x1, y1)]

        for i in range(1, segments):
            t      = i / segments
            offset = rng.uniform(-6 * scale, 6 * scale)
            points.append((
                x1 + dx * t + perp_x * offset,
                y1 + dy * t + perp_y * offset,
            ))
        points.append((x2, y2))

        for i in range(len(points) - 1):
            pygame.draw.line(screen, CHAIN_GLOW_COLOR,
                             points[i], points[i+1], max(1, int(4 * scale)))
            pygame.draw.line(screen, CHAIN_COLOR,
                             points[i], points[i+1], max(1, int(2 * scale)))
            pygame.draw.line(screen, (220, 240, 255),
                             points[i], points[i+1], 1)

    # ── Progress bar ─────────────────────────────────────────────────────────

    def _draw_progress_bar(self, screen, font):
        with self._solve_lock:
            progress = self.solve_progress
            msg      = self.solve_progress_msg

        is_done = self._solve_done_timer > 0

        if is_done:
            title_surf = font.render("Complete!", True, (100, 255, 100))
        else:
            title_surf = font.render("Solving...", True, (255, 255, 255))

        pct_surf = font.render(
            f"{int(progress * 100)}%", True, (255, 255, 255)
        )
        msg_surf = font.render(msg, True, (160, 160, 160)) if msg else None

        bar_w   = 280
        bar_h   = 20
        padding = 14

        panel_base_w = bar_w + padding * 2
        panel_base_h = (
            padding
            + title_surf.get_height()
            + 8
            + bar_h
            + 6
            + pct_surf.get_height()
            + (6 + msg_surf.get_height() if msg_surf else 0)
            + padding
        )

        panel_base_x = BASE_CENTER_X - panel_base_w // 2
        panel_base_y = BASE_CENTER_Y - panel_base_h // 2

        sx, sy = self.base_to_screen(panel_base_x, panel_base_y)
        sw     = self.scale_value(panel_base_w)
        sh     = self.scale_value(panel_base_h)
        pad    = self.scale_value(padding)

        bar_sw = self.scale_value(bar_w)
        bar_sh = self.scale_value(bar_h)
        bar_sx = sx + pad
        bar_sy = (
            sy + pad
            + self.scale_value(title_surf.get_height())
            + self.scale_value(8)
        )

        panel = pygame.Surface((sw, sh), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 230))
        pygame.draw.rect(panel, (100, 100, 100), (0, 0, sw, sh), 1)
        screen.blit(panel, (sx, sy))

        title_scaled = pygame.transform.smoothscale(
            title_surf,
            (self.scale_value(title_surf.get_width()),
             self.scale_value(title_surf.get_height()))
        )
        screen.blit(title_scaled, title_scaled.get_rect(
            centerx=sx + sw // 2,
            top=sy + pad
        ))

        pygame.draw.rect(screen, (50, 50, 50),
                         (bar_sx, bar_sy, bar_sw, bar_sh))
        pygame.draw.rect(screen, (100, 100, 100),
                         (bar_sx, bar_sy, bar_sw, bar_sh), 1)

        fill_w = max(0, int(bar_sw * progress))
        if fill_w > 0:
            if is_done:
                fill_color = (60, 200, 80)
            else:
                r = int(60  + 60  * progress)
                g = int(120 + 80  * progress)
                b = int(200 + 55  * progress)
                fill_color = (r, g, b)

            pygame.draw.rect(screen, fill_color,
                             (bar_sx, bar_sy, fill_w, bar_sh))

            if not is_done and progress < 1.0:
                edge_x = bar_sx + fill_w - 1
                pygame.draw.line(
                    screen, (220, 240, 255),
                    (edge_x, bar_sy),
                    (edge_x, bar_sy + bar_sh - 1)
                )

        pct_y      = bar_sy + bar_sh + self.scale_value(6)
        pct_scaled = pygame.transform.smoothscale(
            pct_surf,
            (self.scale_value(pct_surf.get_width()),
             self.scale_value(pct_surf.get_height()))
        )
        screen.blit(pct_scaled, pct_scaled.get_rect(
            centerx=sx + sw // 2,
            top=pct_y
        ))

        if msg_surf:
            msg_y = (
                pct_y
                + self.scale_value(pct_surf.get_height())
                + self.scale_value(6)
            )
            msg_scaled = pygame.transform.smoothscale(
                msg_surf,
                (self.scale_value(msg_surf.get_width()),
                 self.scale_value(msg_surf.get_height()))
            )
            screen.blit(msg_scaled, msg_scaled.get_rect(
                centerx=sx + sw // 2,
                top=msg_y
            ))

    # ── Thread result handler ────────────────────────────────────────────────

    def tick(self):
        if self._solve_done_timer > 0:
            self._solve_done_timer -= 1
            if self._solve_done_timer == 0:
                self.solve_running = False
            return

        with self._solve_lock:
            if self._pending_result is None:
                return
            result      = self._pending_result
            solved_grid = self._pending_grid
            self._pending_result = None
            self._pending_grid   = None

        self.solve_progress     = 1.0
        self.solve_progress_msg = "Done!"
        self.solve_running      = True
        self._solve_done_timer  = 30

        if result.success:
            for pos, cell in solved_grid.items():
                if pos in self.grid:
                    self.grid[pos] = cell

        self._connected_cache_dirty = True
        self.update_solved_state()

        if not result.success and result.errors:
            self.set_status(f"[X] {result.errors[0]}")

        debug_output_solve_result(result)
        debug_output_board(self.grid, self.ring_count)

    # ── Main draw ────────────────────────────────────────────────────────────

    def draw(self, screen, font):
        self.window_width, self.window_height = screen.get_size()

        self._check_cache()
        self.update_status()
        self.tick()

        mx, my = pygame.mouse.get_pos()
        self.hovered_hex = self.get_hex_at_pixel(mx, my)

        icon_size = self.scale_value(ICON_SIZE)
        hex_size  = self.scale_value(HEX_RADIUS * 2)

        # Parchment
        if self.parchment_base:
            pw = self.scale_value(
                self.parchment_base.get_width()  * PARCHMENT_SCALE
            )
            ph = self.scale_value(
                self.parchment_base.get_height() * PARCHMENT_SCALE
            )
            parchment    = pygame.transform.smoothscale(
                self.parchment_base, (pw, ph)
            )
            parch_base_x = BASE_CENTER_X + 170
            parch_base_y = BASE_CENTER_Y + 170
            px, py = self.base_to_screen(parch_base_x, parch_base_y)
            screen.blit(parchment, parchment.get_rect(center=(px, py)))

        # Hexes
        for (q, r), cell in self.grid.items():
            if cell['void']:
                continue
            x, y       = self.axial_to_screen(q, r)
            is_hovered = (q, r) == self.hovered_hex

            if self.hex_idle:
                img    = (self.hex_hover
                          if is_hovered and self.hex_hover
                          else self.hex_idle)
                scaled = pygame.transform.smoothscale(img, (hex_size, hex_size))
                scaled.set_alpha(150 if is_hovered else 120)
                screen.blit(scaled, scaled.get_rect(center=(x, y)))
            else:
                radius  = self.scale_value(HEX_RADIUS)
                corners = [
                    (x + radius * math.cos(math.radians(60 * i + 30)),
                     y + radius * math.sin(math.radians(60 * i + 30)))
                    for i in range(6)
                ]
                color = HEX_HOVER_TINT if is_hovered else HEX_FILL_COLOR
                pygame.draw.polygon(screen, color, corners)
                pygame.draw.polygon(screen, HEX_LINE_COLOR, corners, 2)

            if self.show_coords:
                txt = font.render(f"{q},{r}", True, (255, 255, 255))
                screen.blit(txt, (x - 15, y + 15))

        # Lightning
        self.draw_lightning_chains(screen)

        # Aspect icons
        for (q, r), cell in self.grid.items():
            if cell['void']:
                continue
            aspect = cell.get('aspect')
            if aspect:
                x, y      = self.axial_to_screen(q, r)
                is_active = self.is_position_active((q, r))
                icon      = self._get_icon(
                    aspect, icon_size, dimmed=not is_active
                )
                if icon:
                    screen.blit(
                        icon, (x - icon_size // 2, y - icon_size // 2)
                    )
                else:
                    txt = font.render(aspect[:3], True, (255, 255, 0))
                    screen.blit(txt, (x - 12, y - 10))

        if self.status_message:
            self._draw_status_bar(screen, font)

        if self.hovered_hex and self.show_tooltips:
            self._draw_hex_tooltip(screen, font, mx, my)

        if self.solve_running or self._solve_done_timer > 0:
            self._draw_progress_bar(screen, font)

    # ── Status bar ───────────────────────────────────────────────────────────

    def _draw_status_bar(self, screen, font):
        cx, cy = self.base_to_screen(BASE_CENTER_X, 590)
        text   = font.render(self.status_message, True, (255, 255, 255))
        rect   = text.get_rect(center=(cx, cy))
        bg     = rect.inflate(30, 16)
        surf   = pygame.Surface((bg.width, bg.height), pygame.SRCALPHA)
        surf.fill((30, 30, 30, 230))
        pygame.draw.rect(
            surf, (100, 100, 100), (0, 0, bg.width, bg.height), 1
        )
        screen.blit(surf, bg)
        screen.blit(text, rect)

    # ── Hex tooltip ──────────────────────────────────────────────────────────

    def _draw_hex_tooltip(self, screen, font, mx, my):
        pos = self.hovered_hex
        if pos not in self.grid:
            return
        aspect = self.grid[pos].get('aspect')
        if not aspect:
            return

        parents = aspect_parents.get(aspect, [])
        w, h    = 150, 60

        tx, ty = mx + 15, my + 15
        sw, sh = screen.get_size()
        if tx + w > sw: tx = mx - w - 15
        if ty + h > sh: ty = my - h - 15

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((30, 30, 30, 230))
        pygame.draw.rect(surf, (100, 100, 100), (0, 0, w, h), 1)
        screen.blit(surf, (tx, ty))

        icon = self._get_icon(aspect, TOOLTIP_ICON_SIZE, False)
        if icon:
            screen.blit(icon, (tx + 8, ty + 8))
        screen.blit(
            font.render(aspect, True, (255, 255, 255)),
            (tx + TOOLTIP_ICON_SIZE + 14, ty + 10)
        )

        if parents:
            screen.blit(
                font.render("=", True, (180, 180, 180)),
                (tx + 10, ty + 34)
            )
            px = tx + 28
            for p in parents:
                picon = self._get_icon(p, TOOLTIP_ICON_SIZE, False)
                if picon:
                    screen.blit(picon, (px, ty + 32))
                px += TOOLTIP_ICON_SIZE + 4
        else:
            screen.blit(
                font.render("Primal", True, (200, 180, 100)),
                (tx + 10, ty + 34)
            )

    # ── Sidebars ─────────────────────────────────────────────────────────────

    def draw_sidebars(self, screen, font):
        mx, my = pygame.mouse.get_pos()
        self.hovered_aspect = None

        icon_size = self.scale_value(ICON_SIZE)

        for base_rect, asp in (self.aspect_buttons_left +
                                self.aspect_buttons_right):
            sx, sy      = self.base_to_screen(base_rect.x, base_rect.y)
            screen_rect = pygame.Rect(sx, sy, icon_size, icon_size)

            is_hovered  = screen_rect.collidepoint(mx, my)
            is_selected = asp == self.selected_aspect

            if is_hovered:
                self.hovered_aspect = asp

            icon = self._get_icon(asp, icon_size, dimmed=is_selected)
            if icon:
                screen.blit(icon, (sx, sy))
            else:
                screen.blit(
                    font.render(asp[:3], True, (255, 255, 0)),
                    (sx + 2, sy + 4)
                )

            if is_hovered and not is_selected:
                pygame.draw.rect(
                    screen, (255, 255, 255),
                    screen_rect.inflate(2, 2), 1
                )

        if self.hovered_aspect and self.show_tooltips:
            self._draw_aspect_tooltip(
                screen, font, mx, my, self.hovered_aspect
            )

    def _draw_aspect_tooltip(self, screen, font, mx, my, aspect):
        parents     = aspect_parents.get(aspect, [])
        connections = get_all_connections(aspect)

        w, h   = 150, 80
        tx, ty = mx + 15, my - h - 5
        sw, sh = screen.get_size()
        if tx + w > sw: tx = mx - w - 15
        if ty < 0:      ty = my + 15

        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        surf.fill((30, 30, 30, 230))
        pygame.draw.rect(surf, (100, 100, 100), (0, 0, w, h), 1)
        screen.blit(surf, (tx, ty))

        icon = self._get_icon(aspect, TOOLTIP_ICON_SIZE, False)
        if icon:
            screen.blit(icon, (tx + 8, ty + 8))
        screen.blit(
            font.render(aspect, True, (255, 255, 255)),
            (tx + TOOLTIP_ICON_SIZE + 14, ty + 10)
        )

        y = ty + 32
        if parents:
            screen.blit(
                font.render("=", True, (180, 180, 180)),
                (tx + 10, y)
            )
            px = tx + 28
            for p in parents:
                picon = self._get_icon(p, TOOLTIP_ICON_SIZE, False)
                if picon:
                    screen.blit(picon, (px, y))
                px += TOOLTIP_ICON_SIZE + 4
        else:
            screen.blit(
                font.render("Primal", True, (200, 180, 100)),
                (tx + 10, y)
            )

        screen.blit(
            font.render(
                f"Connects: {len(connections)}", True, (150, 150, 150)
            ),
            (tx + 10, ty + 56)
        )

    def sidebar_click(self, mx, my):
        icon_size = self.scale_value(ICON_SIZE)

        for base_rect, asp in (self.aspect_buttons_left +
                                self.aspect_buttons_right):
            sx, sy      = self.base_to_screen(base_rect.x, base_rect.y)
            screen_rect = pygame.Rect(sx, sy, icon_size, icon_size)

            if screen_rect.collidepoint(mx, my):
                if self.selected_aspect == asp:
                    self.selected_aspect = None
                    self.set_status("Deselected aspect")
                else:
                    self.selected_aspect = asp
                    self.set_status(f"Selected: {asp}")
                return True
        return False

    # ── Board controls ───────────────────────────────────────────────────────

    def deselect_aspect(self):
        if self.selected_aspect:
            self.selected_aspect = None
            self.set_status("Deselected aspect")
            return True
        return False

    def place_aspect(self, pos):
        if not self.selected_aspect:
            self.set_status("No aspect selected!")
            return False
        if pos not in self.grid:
            return False
        cell = self.grid[pos]
        if cell['void']:
            self.set_status("Can't place on voided hex")
            return False
        self.save_state()
        cell['aspect']        = self.selected_aspect
        cell['player_placed'] = True
        self._connected_cache_dirty = True
        self.update_solved_state()
        self.set_status(f"Placed {self.selected_aspect}")
        return True

    def clear_aspect(self, pos):
        if pos not in self.grid:
            return False
        cell = self.grid[pos]
        if cell['aspect']:
            self.save_state()
            old                   = cell['aspect']
            cell['aspect']        = None
            cell['player_placed'] = False
            self._connected_cache_dirty = True
            self.update_solved_state()
            self.set_status(f"Cleared {old}")
            return True
        return False

    def toggle_void(self, pos):
        if pos not in self.grid:
            return False
        self.save_state()
        cell         = self.grid[pos]
        cell['void'] = not cell['void']
        self._connected_cache_dirty = True
        self.update_solved_state()
        self.set_status("Voided" if cell['void'] else "Unvoided")
        return True

    def toggle_oi_chaining(self):
        self.oi_chaining = not self.oi_chaining
        self.set_status(
            f"IO Chain: {'ON' if self.oi_chaining else 'OFF'}"
        )

    def clear_board(self):
        self.save_state()
        cleared = sum(
            1 for c in self.grid.values()
            if c['aspect'] and not c.get('player_placed')
        )
        for cell in self.grid.values():
            if cell['aspect'] and not cell.get('player_placed'):
                cell['aspect'] = None
        self._connected_cache_dirty = True
        self.update_solved_state()
        self.set_status(
            f"Cleared {cleared} placements"
            if cleared else "Nothing to clear"
        )

    def clear_all(self):
        self.save_state()
        for cell in self.grid.values():
            cell['aspect']        = None
            cell['void']          = False
            cell['player_placed'] = False
        self.is_solved = False
        self._connected_cache_dirty = True
        self.set_status("Board cleared!")

    def cycle_board_size(self):
        self.save_state()
        self.ring_count = {2: 3, 3: 4, 4: 2}.get(self.ring_count, 3)
        self.generate_grid()
        self.set_status(f"Board size: {self.ring_count} rings")

    def toggle_coords(self):
        self.show_coords = not self.show_coords
        self.set_status(
            f"Coordinates: {'ON' if self.show_coords else 'OFF'}"
        )

    def toggle_tooltips(self):
        self.show_tooltips = not self.show_tooltips
        self.set_status(
            f"Tooltips: {'ON' if self.show_tooltips else 'OFF'}"
        )

    # ── Credits overlay ──────────────────────────────────────────────────────

    def _draw_credits_overlay(self, screen, font):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 230))
        screen.blit(overlay, (0, 0))

        if not CREDITS_TEXT:
            return

        line_height = font.get_linesize()
        max_width = max(font.size(line)[0] for line in CREDITS_TEXT)
        padding_x = 24
        padding_y = 18

        panel_w = max_width + padding_x * 2
        panel_h = line_height * len(CREDITS_TEXT) + padding_y * 2

        panel_x = (self.window_width  - panel_w) // 2
        panel_y = (self.window_height - panel_h) // 2

        panel = pygame.Surface((panel_w, panel_h), pygame.SRCALPHA)
        panel.fill((30, 30, 30, 240))
        pygame.draw.rect(panel, (120, 120, 120), (0, 0, panel_w, panel_h), 2)
        screen.blit(panel, (panel_x, panel_y))

        for i, line in enumerate(CREDITS_TEXT):
            if i == 0:
                color = (255, 215, 0)
            elif line.endswith(":"):
                color = (200, 200, 255)
            else:
                color = (220, 220, 220)
            text_surf = font.render(line, True, color)
            tx = panel_x + padding_x
            ty = panel_y + padding_y + i * line_height
            screen.blit(text_surf, (tx, ty))

    def toggle_credits(self):
        self.show_credits = not self.show_credits
        if self.show_credits:
            self.set_status("Showing credits")
        else:
            self.set_status("Credits hidden")

    # ── Solve / Debug ────────────────────────────────────────────────────────

    def can_solve(self):
        placed = get_user_placed_positions(self.grid)
        if len(placed) < 2:
            return False, "Need at least 2 aspects"

        off_edge = [
            pos for pos in placed
            if not is_edge_position(self.grid, pos, self.ring_count)
        ]
        if off_edge:
            return (
                False,
                "User aspects must be on the outer ring only "
                "(clear/move interior aspects).",
            )

        if self.is_solved:
            return False, "Already solved"
        return True, ""

    def solve_board(self):
        if self.solve_running:
            self.set_status("Already solving...")
            return None

        can, reason = self.can_solve()
        if not can:
            self.set_status(reason)
            return None

        self.save_state()
        self.set_status(f"Solving... (IO={self.oi_chaining})")

        with self._solve_lock:
            self.solve_running      = True
            self.solve_progress     = 0.0
            self.solve_progress_msg = "Starting..."
            self._pending_result    = None
            self._pending_grid      = None
        self._solve_done_timer = 0

        grid_copy = {pos: dict(cell) for pos, cell in self.grid.items()}

        def progress_cb(frac, msg=""):
            with self._solve_lock:
                self.solve_progress     = max(0.0, min(1.0, frac))
                self.solve_progress_msg = msg

        def on_event(event, data):
            if event == 'complete':
                g = data.get('rating_grade', '?')
                s = data.get('rating_score', 0)
                c = data['total_placements']
                self.set_status(
                    f"Solved! {c} placements | Grade: {g} ({s})"
                )
            elif event == 'error':
                self.set_status(f"[X] {data}")

        def run():
            try:
                result = solve_with_center_priority(
                    grid_copy,
                    prefer_oi=self.oi_chaining,
                    callback=on_event,
                    progress_cb=progress_cb,
                )
            except Exception as e:
                result = SolveResult()
                result.errors.append(str(e))

            with self._solve_lock:
                self._pending_result = result
                self._pending_grid   = grid_copy
                self.solve_running   = False

        self._solve_thread = threading.Thread(target=run, daemon=True)
        self._solve_thread.start()

    def debug_dump(self):
        debug_output_board(self.grid, self.ring_count)
        self.set_status("Debug output printed")